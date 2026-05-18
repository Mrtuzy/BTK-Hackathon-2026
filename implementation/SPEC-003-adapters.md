# SPEC-003 — Infrastructure Adapters

Read CLAUDE.md first. Every adapter implements a port from `domain/ports.py`. No adapter imports from `domain/services`.

## What to build

---

### Fixture files

**`infrastructure/scraping/fixtures/trendyol_sample.json`**
Turkish sports shoe product. Include ≥10 reviews — at least 3 must mention "beden tablosu eksik" or "beklediğimden sert taban" (realistic return-trigger language for correlation testing).

**`infrastructure/scraping/fixtures/hepsiburada_sample.json`**
Different product, same category. ≥8 reviews.

Both follow `ProductData` field names: `title`, `description`, `price`, `reviews`, `competitor_titles`, `source="fixture"`.

---

### GeminiLanguageModel (`adapters/outbound/gemini_language_model.py`)
Implements `ILanguageModel`.

```python
import logging
import time
from google.api_core.exceptions import ResourceExhausted
from google.generativeai import GenerativeModel, configure
from domain.ports import ILanguageModel

logger = logging.getLogger(__name__)

class GeminiLanguageModel(ILanguageModel):
    MAX_RETRIES = 2
    RETRY_DELAY = 3.0

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        configure(api_key=api_key)
        self._model = GenerativeModel(model)

    def generate(self, prompt: str) -> str:
        """Calls Gemini. Retries on 429. Raises RuntimeError after max retries."""
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                logger.debug(f"Gemini prompt length: {len(prompt)} chars")
                response = self._model.generate_content(prompt)
                text = response.text
                logger.debug(f"Gemini response length: {len(text)} chars")
                return text
            except ResourceExhausted:
                if attempt < self.MAX_RETRIES:
                    logger.warning(f"Gemini rate limit hit. Retry {attempt + 1}/{self.MAX_RETRIES}")
                    time.sleep(self.RETRY_DELAY)
                else:
                    raise RuntimeError("Gemini rate limit exceeded after max retries")
```

---

### PlaywrightScraper (`adapters/outbound/playwright_scraper.py`)
Implements `IProductScraper`.

```python
class PlaywrightScraper(IProductScraper):
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
        # 4 more real UA strings
    ]
    FIXTURES_DIR = Path(__file__).parent.parent.parent / "infrastructure/scraping/fixtures"

    def __init__(self, headless: bool = True) -> None:
        self._headless = headless

    async def scrape(self, url: str) -> ProductData:
        """Never raises. Falls back to fixture on any failure."""
        try:
            return await self._scrape_live(url)
        except Exception as e:
            logger.warning(f"Scrape failed ({type(e).__name__}): {e}. Loading fixture.")
            return self._load_fixture(url)

    async def _scrape_live(self, url: str) -> ProductData:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self._headless)
            context = await browser.new_context(user_agent=random.choice(self.USER_AGENTS))
            page = await context.new_page()
            await page.goto(url, timeout=15000)
            await asyncio.sleep(random.uniform(1.0, 2.5))
            domain = self._detect_domain(url)
            if "trendyol" in domain:
                return await self._parse_trendyol(page)
            if "hepsiburada" in domain:
                return await self._parse_hepsiburada(page)
            return await self._parse_generic(page)

    async def _parse_trendyol(self, page) -> ProductData:
        title = await page.locator('[data-testid="product-name"]').text_content() or ""
        description = await page.locator('[data-testid="product-description"]').text_content() or ""
        price = await page.locator('[data-testid="price-current-price"]').text_content() or ""
        review_els = await page.locator(".user-comment-item .comment").all()
        reviews = [await el.text_content() for el in review_els[:10]]
        return ProductData(title=title.strip(), description=description.strip(),
                           price=price.strip(), reviews=[r.strip() for r in reviews if r],
                           competitor_titles=[], source="scraped")

    async def _parse_hepsiburada(self, page) -> ProductData: ...  # similar pattern

    async def _parse_generic(self, page) -> ProductData:
        title = await page.title()
        desc_el = page.locator('meta[name="description"]')
        description = await desc_el.get_attribute("content") or ""
        return ProductData(title=title, description=description, price="",
                           reviews=[], competitor_titles=[], source="scraped")

    def _load_fixture(self, url: str) -> ProductData:
        domain = self._detect_domain(url)
        fixture_file = "hepsiburada_sample.json" if "hepsiburada" in domain else "trendyol_sample.json"
        data = json.loads((self.FIXTURES_DIR / fixture_file).read_text(encoding="utf-8"))
        return ProductData(**{k: data[k] for k in ProductData.__dataclass_fields__
                              if k != "source"}, source="fixture")

    def _detect_domain(self, url: str) -> str:
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower()
```

---

### BaseAdParser + Concrete Parsers (`infrastructure/parsers/`)

**`base_ad_parser.py`:**
```python
class BaseAdParser(ABC):
    COLUMN_MAP: dict[str, str]  # must be defined by subclass

    @abstractmethod
    def parse(self, content: bytes) -> pd.DataFrame:
        """Parse raw CSV bytes, return normalized DataFrame."""

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rename via COLUMN_MAP, compute derived columns, return clean df."""
        df = df.rename(columns=self.COLUMN_MAP)[list(self.COLUMN_MAP.values())]
        df["clicks"] = pd.to_numeric(df["clicks"], errors="coerce").fillna(0).astype(int)
        df["spend"] = pd.to_numeric(df["spend"], errors="coerce").fillna(0.0)
        df["impressions"] = pd.to_numeric(df["impressions"], errors="coerce").fillna(0).astype(int)
        df["conversions"] = pd.to_numeric(df["conversions"], errors="coerce").fillna(0).astype(int)
        df["ctr"] = (df["clicks"] / df["impressions"]).replace([float("inf"), float("nan")], 0.0)
        df["conversion_rate"] = (df["conversions"] / df["clicks"]).replace([float("inf"), float("nan")], 0.0)
        df["cost_per_conversion"] = df.apply(
            lambda r: r["spend"] / r["conversions"] if r["conversions"] > 0 else float("inf"), axis=1
        )
        return df
```

**`google_ads_parser.py`:**
```python
class GoogleAdsParser(BaseAdParser):
    COLUMN_MAP = {"Keyword": "keyword", "Clicks": "clicks", "Cost": "spend",
                  "Impressions": "impressions", "Conversions": "conversions"}

    def parse(self, content: bytes) -> pd.DataFrame:
        df = pd.read_csv(io.BytesIO(content))
        return self._normalize(df)
```

**`meta_ads_parser.py`** and **`trendyol_parser.py`** follow the same pattern with their respective `COLUMN_MAP` values from CLAUDE.md.

`TrendyolReturnsParser` is a separate class — does not extend `BaseAdParser`:
```python
class TrendyolReturnsParser:
    COLUMN_MAP = {"Ürün Adı": "product_title", "İade Sebebi": "return_reason",
                  "Kaynak Anahtar Kelime": "keyword", "İade Adedi": "quantity"}

    def parse(self, content: bytes) -> pd.DataFrame:
        df = pd.read_csv(io.BytesIO(content))
        df = df.rename(columns=self.COLUMN_MAP)[list(self.COLUMN_MAP.values())]
        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
        df["keyword"] = df["keyword"].fillna("").str.lower()
        return df
```

---

### CsvParserFactory (`adapters/outbound/csv_parser_factory.py`)
Implements `ICsvParser`. Strategy pattern.

```python
class CsvParserFactory(ICsvParser):
    _AD_STRATEGIES: dict[str, type[BaseAdParser]] = {
        "google_ads": GoogleAdsParser,
        "meta_ads": MetaAdsParser,
        "trendyol_ads": TrendyolAdsParser,
    }
    _AD_SIGNATURES = {
        "google_ads": {"Campaign", "Ad group", "Keyword", "Impressions"},
        "meta_ads": {"Campaign name", "Ad Set Name", "Amount spent"},
        "trendyol_ads": {"Kampanya Adı", "Tıklama", "Harcama"},
    }
    _RETURNS_SIGNATURE = {"Ürün Adı", "İade Sebebi", "İade Adedi"}

    def parse_ads(self, content: bytes) -> pd.DataFrame:
        fmt = self._detect_ad_format(content)
        return self._AD_STRATEGIES[fmt]().parse(content)

    def parse_returns(self, content: bytes) -> pd.DataFrame:
        return TrendyolReturnsParser().parse(content)

    def _detect_ad_format(self, content: bytes) -> str:
        cols = set(pd.read_csv(io.BytesIO(content), nrows=0).columns.tolist())
        for fmt, sig in self._AD_SIGNATURES.items():
            if sig.issubset(cols):
                return fmt
        raise ValueError(
            "Unrecognized CSV format. Supported: Google Ads, Meta Ads, Trendyol Ads, Trendyol Returns."
        )
```

## Done when

- Invalid URL passed to `PlaywrightScraper.scrape()` → returns fixture `ProductData`, no exception raised
- All 4 CSV formats parse to correct normalized column names
- `clicks=0` → `ctr=0.0` (no ZeroDivisionError)
- Unknown CSV format → `ValueError` with the exact message from CLAUDE.md
- `GeminiLanguageModel` is importable and implements `ILanguageModel` interface (LSP check)
- `CsvParserFactory` is importable and implements `ICsvParser` interface
