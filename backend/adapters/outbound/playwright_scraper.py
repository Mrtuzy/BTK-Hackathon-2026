import asyncio
import json
import logging
import random
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from domain.entities import ProductData
from domain.ports import IProductScraper

logger = logging.getLogger(__name__)


class PlaywrightScraper(IProductScraper):
    USER_AGENTS: list[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    ]
    FIXTURES_DIR = (
        Path(__file__).parent.parent.parent / "infrastructure/scraping/fixtures"
    )

    def __init__(self, headless: bool = True) -> None:
        self._headless = headless

    async def scrape(self, url: str) -> ProductData:
        """Never raises. Falls back to fixture on any failure."""
        try:
            return await self._scrape_live(url)
        except Exception as exc:
            logger.warning(
                "Scrape failed (%s): %s. Loading fixture.",
                type(exc).__name__,
                exc,
            )
            return self._load_fixture(url)

    async def _scrape_live(self, url: str) -> ProductData:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=self._headless,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ],
            )
            context = await browser.new_context(
                user_agent=random.choice(self.USER_AGENTS),
                viewport={"width": 1440, "height": 900},
                locale="tr-TR",
                extra_http_headers={
                    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
            # Hide automation flag via JS
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            # Block images/fonts/media to speed up loading
            await context.route(
                "**/*.{png,jpg,jpeg,gif,webp,svg,ico,woff,woff2,ttf,eot,mp4,mp3,ogg}",
                lambda route: route.abort(),
            )
            page = await context.new_page()
            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                if response and response.status >= 400:
                    raise RuntimeError(f"HTTP {response.status} for {url}")

                # Give JS some time to render
                try:
                    await page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    pass
                await asyncio.sleep(random.uniform(0.8, 1.8))

                # Sanity check: is there enough content?
                body_text = await page.locator("body").inner_text(timeout=5000)
                if len(body_text.strip()) < 80:
                    raise RuntimeError("Page body too short — likely blocked or empty")

                return await self._extract_product_data(page, url)
            finally:
                await context.close()
                await browser.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Extraction pipeline
    # ─────────────────────────────────────────────────────────────────────────

    async def _extract_product_data(self, page, url: str) -> ProductData:
        """Try extraction strategies in order of reliability."""

        # 1. Next.js __NEXT_DATA__ (Trendyol, many modern shops)
        product = await self._try_next_data(page)
        if product and product.title:
            logger.info("__NEXT_DATA__ extraction succeeded")
            return product

        # 2. JSON-LD schema.org Product
        product = await self._try_json_ld(page)
        if product and product.title:
            logger.info("JSON-LD extraction succeeded")
            return product

        # 3. Platform-specific selectors
        domain = self._detect_domain(url)
        if "trendyol" in domain:
            product = await self._parse_trendyol(page)
        elif "hepsiburada" in domain:
            product = await self._parse_hepsiburada(page)
        else:
            product = await self._parse_generic(page)

        if product and product.title:
            return product

        # 4. Generic meta-tag + body fallback
        return await self._parse_generic(page)

    # ─────────────────────────────────────────────────────────────────────────
    # Strategy 1: Next.js __NEXT_DATA__
    # ─────────────────────────────────────────────────────────────────────────

    async def _try_next_data(self, page) -> "ProductData | None":
        """Extract product from Next.js server-side data object."""
        try:
            raw = await page.evaluate("""
                (() => {
                    const el = document.getElementById('__NEXT_DATA__');
                    return el ? el.textContent : null;
                })()
            """)
            if not raw:
                return None
            data = json.loads(raw)
            return self._find_product_in_next_data(data)
        except Exception as exc:
            logger.debug("__NEXT_DATA__ failed: %s", exc)
            return None

    def _find_product_in_next_data(self, data: dict) -> "ProductData | None":
        """Recursively search Next.js page props for product-like data."""
        props = data.get("props", {})
        page_props = props.get("pageProps", {})

        # Common Trendyol-like patterns
        candidates = [
            page_props.get("product"),
            page_props.get("productDetail"),
            page_props.get("pdpData", {}).get("product") if isinstance(page_props.get("pdpData"), dict) else None,
            page_props.get("initialState", {}).get("productDetail", {}).get("product"),
        ]

        for c in candidates:
            if isinstance(c, dict):
                title = c.get("name") or c.get("title") or c.get("productName") or ""
                if title:
                    description = (
                        c.get("description") or c.get("contentDescriptions", [{}])[0].get("description", "")
                        if isinstance(c.get("contentDescriptions"), list) and c.get("contentDescriptions")
                        else c.get("description", "")
                    )
                    price = ""
                    price_info = c.get("price") or c.get("priceInfo") or {}
                    if isinstance(price_info, dict):
                        price = str(price_info.get("discountedPrice") or price_info.get("sellingPrice") or price_info.get("price") or "")
                    elif isinstance(price_info, (int, float, str)):
                        price = str(price_info)

                    # Reviews from ratingAndReviewResponse or reviewSummary
                    reviews: list[str] = []
                    review_data = c.get("reviews") or c.get("comments") or []
                    if isinstance(review_data, list):
                        for rv in review_data[:10]:
                            if isinstance(rv, dict):
                                text = rv.get("comment") or rv.get("text") or rv.get("content") or ""
                                if text:
                                    reviews.append(str(text).strip())

                    return ProductData(
                        title=str(title).strip(),
                        description=str(description).strip(),
                        price=str(price).strip(),
                        reviews=reviews,
                        competitor_titles=[],
                        source="scraped",
                    )
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Strategy 2: JSON-LD schema.org
    # ─────────────────────────────────────────────────────────────────────────

    async def _try_json_ld(self, page) -> "ProductData | None":
        """Extract Product entity from JSON-LD structured data."""
        try:
            scripts = await page.locator('script[type="application/ld+json"]').all()
            for script in scripts:
                text = await script.text_content() or ""
                if not text.strip():
                    continue
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    continue

                items: list = data if isinstance(data, list) else [data]
                # Flatten @graph arrays
                expanded: list = []
                for item in items:
                    if isinstance(item, dict) and "@graph" in item:
                        expanded.extend(item["@graph"])
                    else:
                        expanded.append(item)

                product_node = next(
                    (x for x in expanded if isinstance(x, dict) and x.get("@type") == "Product"),
                    None,
                )
                if not product_node:
                    continue

                title = product_node.get("name", "")
                if not title:
                    continue

                description = str(
                    product_node.get("description")
                    or product_node.get("disambiguatingDescription")
                    or ""
                ).strip()

                price = ""
                offers = product_node.get("offers")
                if isinstance(offers, dict):
                    price = str(offers.get("price") or offers.get("lowPrice") or "")
                elif isinstance(offers, list) and offers:
                    price = str(offers[0].get("price") or "")

                reviews: list[str] = []
                raw_reviews = product_node.get("review", [])
                if isinstance(raw_reviews, dict):
                    raw_reviews = [raw_reviews]
                for rv in raw_reviews[:10]:
                    if isinstance(rv, dict):
                        body = rv.get("reviewBody") or rv.get("description") or ""
                        if body:
                            reviews.append(str(body).strip())

                return ProductData(
                    title=str(title).strip(),
                    description=description,
                    price=price,
                    reviews=reviews,
                    competitor_titles=[],
                    source="scraped",
                )
        except Exception as exc:
            logger.debug("JSON-LD failed: %s", exc)
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Strategy 3a: Trendyol DOM selectors
    # ─────────────────────────────────────────────────────────────────────────

    async def _parse_trendyol(self, page) -> ProductData:
        title = await self._try_selectors(page, [
            "h1.pr-new-br",
            ".prdct-desc-cntnr-ttl-w h1",
            ".prdct-desc-cntnr-name",
            "h1[class*='product']",
            ".product-name",
            "[class*='productName']",
            "h1",
        ])
        description = await self._try_selectors(page, [
            ".detail-desc-list",
            ".product-description-text",
            ".info-list",
            ".detail-border-bottom",
            "[class*='description']",
            "[class*='detail']",
        ])
        price = await self._try_selectors(page, [
            ".prc-box-dscntd",
            ".prc-box-sllng",
            "[class*='discountedPrice']",
            "[class*='price']",
            ".product-price-container",
        ])
        reviews = await self._try_review_selectors(page, [
            ".user-comment-item .comment",
            ".ry-comment",
            "[class*='comment-text']",
            ".review-text",
        ])
        return ProductData(
            title=(title or "").strip(),
            description=(description or "").strip(),
            price=(price or "").strip(),
            reviews=reviews,
            competitor_titles=[],
            source="scraped",
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Strategy 3b: Hepsiburada DOM selectors
    # ─────────────────────────────────────────────────────────────────────────

    async def _parse_hepsiburada(self, page) -> ProductData:
        title = await self._try_selectors(page, [
            "h1.product-name",
            "h1[itemprop='name']",
            "[data-test-id='title']",
            "h1",
        ])
        description = await self._try_selectors(page, [
            "[itemprop='description']",
            ".product-description",
            ".description-text",
            "[class*='description']",
        ])
        price = await self._try_selectors(page, [
            "[itemprop='price']",
            "[class*='finalPrice']",
            "[class*='price-value']",
            "[class*='price']",
        ])
        reviews = await self._try_review_selectors(page, [
            ".review-item .review-text",
            "[class*='review-comment']",
            "[class*='commentText']",
        ])
        return ProductData(
            title=(title or "").strip(),
            description=(description or "").strip(),
            price=(price or "").strip(),
            reviews=reviews,
            competitor_titles=[],
            source="scraped",
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Strategy 4: Generic / meta-tag fallback
    # ─────────────────────────────────────────────────────────────────────────

    async def _parse_generic(self, page) -> ProductData:
        title = ""
        # Try OG title, then structured h1, then <title>
        for sel, attr in [
            ('meta[property="og:title"]', "content"),
            ('meta[name="twitter:title"]', "content"),
        ]:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    title = (await el.get_attribute(attr) or "").strip()
                    if title:
                        break
            except Exception:
                pass

        if not title:
            title = await self._try_selectors(page, ["h1[itemprop='name']", "h1"]) or await page.title()

        # Description
        description = ""
        for sel, attr in [
            ('meta[property="og:description"]', "content"),
            ('meta[name="description"]', "content"),
        ]:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    description = (await el.get_attribute(attr) or "").strip()
                    if description:
                        break
            except Exception:
                pass

        if not description:
            # Pull visible text from product-like containers
            description = await self._try_selectors(page, [
                "main article",
                "[class*='product-detail']",
                "[class*='product-description']",
                "[id*='product']",
                "main",
            ])
            if description:
                description = description[:700]

        price = await self._try_selectors(page, [
            "[itemprop='price']",
            "[class*='price']",
            "[data-price]",
        ])

        return ProductData(
            title=(title or "").strip(),
            description=(description or "").strip(),
            price=(price or "").strip(),
            reviews=[],
            competitor_titles=[],
            source="scraped",
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    async def _try_selectors(self, page, selectors: list[str]) -> str:
        """Return first non-empty text match from the selector list."""
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    text = await el.text_content(timeout=3000)
                    if text and text.strip():
                        return text.strip()
            except Exception:
                continue
        return ""

    async def _try_review_selectors(self, page, selectors: list[str]) -> list[str]:
        """Return reviews from the first selector that yields results."""
        for sel in selectors:
            try:
                els = await page.locator(sel).all()
                if not els:
                    continue
                reviews: list[str] = []
                for el in els[:10]:
                    try:
                        text = await el.text_content(timeout=2000)
                        if text and text.strip():
                            reviews.append(text.strip())
                    except Exception:
                        continue
                if reviews:
                    return reviews
            except Exception:
                continue
        return []

    # ─────────────────────────────────────────────────────────────────────────
    # Fixture fallback
    # ─────────────────────────────────────────────────────────────────────────

    def _load_fixture(self, url: str) -> ProductData:
        domain = self._detect_domain(url)
        fixture_file = (
            "hepsiburada_sample.json" if "hepsiburada" in domain else "trendyol_sample.json"
        )
        data = json.loads(
            (self.FIXTURES_DIR / fixture_file).read_text(encoding="utf-8")
        )
        fields = {
            key: data[key]
            for key in ProductData.__dataclass_fields__
            if key != "source"
        }
        return ProductData(**fields, source="fixture")

    def _detect_domain(self, url: str) -> str:
        return urlparse(url).netloc.lower()
