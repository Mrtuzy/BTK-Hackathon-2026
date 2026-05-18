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
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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
            browser = await playwright.chromium.launch(headless=self._headless)
            context = await browser.new_context(
                user_agent=random.choice(self.USER_AGENTS)
            )
            page = await context.new_page()
            try:
                await page.goto(url, timeout=15000)
                await asyncio.sleep(random.uniform(1.0, 2.5))
                domain = self._detect_domain(url)
                if "trendyol" in domain:
                    return await self._parse_trendyol(page)
                if "hepsiburada" in domain:
                    return await self._parse_hepsiburada(page)
                return await self._parse_generic(page)
            finally:
                await context.close()
                await browser.close()

    async def _parse_trendyol(self, page) -> ProductData:
        title = await page.locator('[data-testid="product-name"]').text_content()
        description = await page.locator(
            '[data-testid="product-description"]'
        ).text_content()
        price = await page.locator(
            '[data-testid="price-current-price"]'
        ).text_content()
        review_els = await page.locator(".user-comment-item .comment").all()
        reviews = [await el.text_content() for el in review_els[:10]]
        return ProductData(
            title=(title or "").strip(),
            description=(description or "").strip(),
            price=(price or "").strip(),
            reviews=[r.strip() for r in reviews if r],
            competitor_titles=[],
            source="scraped",
        )

    async def _parse_hepsiburada(self, page) -> ProductData:
        title = await page.locator("h1").first.text_content()
        description = await page.locator(".product-description").text_content()
        price = await page.locator("[data-bind='markupText: price']").text_content()
        review_els = await page.locator(".review-item .review-text").all()
        reviews = [await el.text_content() for el in review_els[:10]]
        return ProductData(
            title=(title or "").strip(),
            description=(description or "").strip(),
            price=(price or "").strip(),
            reviews=[r.strip() for r in reviews if r],
            competitor_titles=[],
            source="scraped",
        )

    async def _parse_generic(self, page) -> ProductData:
        title = await page.title()
        desc_el = page.locator('meta[name="description"]')
        description = await desc_el.get_attribute("content") or ""
        return ProductData(
            title=title,
            description=description,
            price="",
            reviews=[],
            competitor_titles=[],
            source="scraped",
        )

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
