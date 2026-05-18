# CLAUDE.md — doThis

Read this file before every prompt. Follow every rule here without exception.

---

## Project

**doThis** — Profit leak detector for e-commerce sellers.

A seller pastes a product URL + optional ad/returns CSV files. The system identifies:
1. Why the product is invisible in AI search (GEO score)
2. Which ad keywords are burning money (ad × returns correlation)
3. What to do about it (prioritized, impact-scored action list)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind CSS |
| Backend | Python 3.11 + FastAPI |
| AI Orchestration | LangGraph + LangChain |
| AI Model | **Gemini 2.0 Flash only** — one model, no Pro/Flash split |
| Web Scraping | Playwright (async) |
| Scraping Fallback | Cached JSON fixtures (`infrastructure/scraping/fixtures/`) |
| CSV Parsing | Pandas |
| Deploy | Vercel (frontend) + Railway (backend) |
| Database | **None** — fully stateless, session-scoped |

---

## Architecture: Clean / Hexagonal

The domain has **zero dependencies** on FastAPI, LangGraph, Playwright, or Gemini.
All external concerns are behind interfaces (Ports). Infrastructure implements those interfaces (Adapters).

```
┌─────────────────────────────────────────────────────┐
│                   Inbound Adapters                   │
│         FastAPI route  →  AnalyzeController          │
└──────────────────────┬──────────────────────────────┘
                       │ calls
┌──────────────────────▼──────────────────────────────┐
│                  Application Layer                   │
│              AnalysisPipeline (use case)             │
│         orchestrates domain services via ports       │
└───┬──────────────┬──────────────┬───────────────────┘
    │              │              │
┌───▼───┐    ┌─────▼────┐   ┌────▼──────┐
│Domain │    │  Domain  │   │  Domain   │
│Service│    │  Service │   │  Service  │
│  Geo  │    │  Correl. │   │  Action   │
└───┬───┘    └─────┬────┘   └────┬──────┘
    │              │              │  all use ports (interfaces)
┌───▼──────────────▼──────────────▼──────────────────┐
│                  Outbound Ports                      │
│  IProductScraper  ILanguageModel  ICsvParser        │
└───┬──────────────┬──────────────┬───────────────────┘
    │              │              │
┌───▼───┐    ┌─────▼────┐   ┌────▼──────┐
│Infra  │    │  Infra   │   │  Infra    │
│Playw. │    │  Gemini  │   │  Pandas   │
│Scraper│    │  Client  │   │  Parsers  │
└───────┘    └──────────┘   └───────────┘
```

---

## Folder Structure

```
backend/
├── main.py                          # FastAPI app init, CORS, DI wiring
├── config.py                        # Env vars only (no logic)
│
├── domain/
│   ├── entities.py                  # ProductData, GeoReport, CorrelationReport,
│   │                                # ActionItem, AnalysisResult — pure dataclasses
│   ├── ports.py                     # Abstract interfaces: IProductScraper,
│   │                                # ILanguageModel, ICsvParser
│   └── services/
│       ├── geo_service.py           # GeoAnalysisService — domain logic only
│       ├── correlation_service.py   # CorrelationService — domain logic only
│       └── action_service.py        # ActionService — domain logic only
│
├── application/
│   ├── pipeline_state.py            # PipelineState TypedDict
│   ├── analysis_pipeline.py         # AnalysisPipeline — LangGraph orchestration
│   └── dto.py                       # AnalyzeRequest, AnalyzeResponse (I/O shapes)
│
├── adapters/
│   ├── inbound/
│   │   └── analyze_controller.py    # FastAPI route handler
│   └── outbound/
│       ├── gemini_language_model.py # Implements ILanguageModel
│       ├── playwright_scraper.py    # Implements IProductScraper
│       └── csv_parser_factory.py   # Implements ICsvParser, Strategy pattern
│
└── infrastructure/
    ├── scraping/
    │   └── fixtures/
    │       ├── trendyol_sample.json
    │       └── hepsiburada_sample.json
    └── parsers/
        ├── google_ads_parser.py
        ├── meta_ads_parser.py
        └── trendyol_parser.py

frontend/
├── app/
│   ├── page.tsx                     # Input screen
│   ├── analyze/page.tsx             # Results screen
│   └── layout.tsx
├── components/
│   ├── UrlInput.tsx
│   ├── CsvUpload.tsx
│   ├── AgentProgress.tsx
│   ├── MetricCard.tsx
│   ├── ActionList.tsx
│   └── ActionItem.tsx
└── lib/
    └── api.ts
```

---

## Domain Layer — Entities & Ports

### Entities (`domain/entities.py`)
Pure Python dataclasses. No imports from FastAPI, LangGraph, Pandas, or Gemini.

```python
@dataclass
class ProductData:
    title: str
    description: str
    price: str
    reviews: list[str]
    competitor_titles: list[str]
    source: str  # "scraped" | "fixture"

@dataclass
class GeoReport:
    score: int               # 0–100, computed from 4 criteria × 25pts each
    missing_keywords: list[str]
    competitor_keywords: list[str]
    suggested_title: str
    suggested_description_intro: str

@dataclass
class CorrelationReport:
    high_return_keywords: list[dict]   # {keyword, return_rate, spend, root_cause}
    root_causes: list[str]
    wasted_spend_pct: float            # computed by Pandas, not LLM
    top_return_reason: str | None

@dataclass
class ActionItem:
    priority: str            # "critical" | "important" | "improvement"
    title: str
    description: str
    estimated_impact: str
    how_to_apply: str

@dataclass
class AnalysisResult:
    geo_report: GeoReport
    correlation_report: CorrelationReport | None
    actions: list[ActionItem]
    used_fixture: bool
```

### Ports (`domain/ports.py`)
Abstract interfaces. Domain services depend only on these — never on concrete adapters.

```python
from abc import ABC, abstractmethod
import pandas as pd
from domain.entities import ProductData, GeoReport, CorrelationReport, ActionItem

class IProductScraper(ABC):
    @abstractmethod
    async def scrape(self, url: str) -> ProductData:
        """Never raises. Falls back to fixture on any failure."""

class ILanguageModel(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Returns raw text. Caller is responsible for parsing."""

class ICsvParser(ABC):
    @abstractmethod
    def parse_ads(self, content: bytes) -> pd.DataFrame:
        """Returns normalized ad DataFrame. Raises ValueError on unknown format."""

    @abstractmethod
    def parse_returns(self, content: bytes) -> pd.DataFrame:
        """Returns normalized returns DataFrame. Raises ValueError on unknown format."""
```

---

## Domain Services

Domain services contain all business logic. They receive ports via constructor injection (DIP).
They never import infrastructure — only `domain.entities` and `domain.ports`.

### GeoAnalysisService (`domain/services/geo_service.py`)

**Responsibilities:**
- Build GEO scoring prompt
- Parse LLM response into `GeoReport`
- Handle parse failures gracefully

**Design:**
```python
class GeoAnalysisService:
    def __init__(self, llm: ILanguageModel) -> None:
        self._llm = llm

    def analyze(self, product: ProductData) -> GeoReport:
        prompt = self._build_prompt(product)
        raw = self._llm.generate(prompt)
        return self._parse_response(raw)

    def _build_prompt(self, product: ProductData) -> str: ...
    def _parse_response(self, raw: str) -> GeoReport: ...
    def _extract_json(self, text: str) -> dict: ...  # regex-based, never raises
```

**Prompt design — GEO scoring (4 criteria × 25 points each):**
```
You are an e-commerce GEO (Generative Engine Optimization) expert.

Score this product listing's AI search visibility. Grade each criterion 0–25:

Criterion 1 — Specificity: Does the title include product category + measurable attribute?
  (e.g. "running shoe" = 5pts, "trail running shoe 280g" = 25pts)
Criterion 2 — Attributes: Does the description contain ≥3 measurable specs?
  (weight, material, dimensions, certifications count; vague adjectives do not)
Criterion 3 — Context richness: Can an AI answer "best X for Y" using only this listing?
Criterion 4 — Keyword gap: Are there ≥2 keywords present in competitor titles but absent here?
  (gap = 0pts, gap found = 25pts)

Product title: {title}
Description: {description}
Sample reviews: {reviews[:5]}
Competitor titles: {competitor_titles}

Respond ONLY with this JSON (no preamble, no explanation):
{{
  "score": <sum of 4 criteria>,
  "missing_keywords": ["keyword1", "keyword2"],
  "competitor_keywords": ["kw1", "kw2"],
  "suggested_title": "<rewritten title>",
  "suggested_description_intro": "<first 2 sentences of rewritten description>"
}}
```

**Parse strategy:** Use `re.search(r'\{.*\}', text, re.DOTALL)` to extract JSON block. On failure, return `GeoReport(score=0, missing_keywords=[], ...)` — never raise.

---

### CorrelationService (`domain/services/correlation_service.py`)

**Responsibilities:**
- Compute return rates per keyword (Pandas — no LLM)
- Ask LLM only for human-readable root cause explanation
- Expose `wasted_spend_pct` as a pure numeric calculation

**Design:**
```python
class CorrelationService:
    def __init__(self, llm: ILanguageModel) -> None:
        self._llm = llm

    def analyze(
        self,
        ad_df: pd.DataFrame,
        returns_df: pd.DataFrame | None,
        product: ProductData,
    ) -> CorrelationReport:
        stats = self._compute_stats(ad_df, returns_df)
        explanation = self._explain_with_llm(stats, product)
        return self._build_report(stats, explanation)

    def _compute_stats(self, ad_df, returns_df) -> pd.DataFrame:
        """Pure Pandas. Returns per-keyword: clicks, spend, return_quantity, return_rate."""

    def _compute_wasted_spend_pct(self, stats: pd.DataFrame) -> float:
        """wasted = spend where return_rate > 0.3. Pure math, no LLM."""

    def _explain_with_llm(self, stats: pd.DataFrame, product: ProductData) -> dict:
        """LLM answers: what does this pattern mean? What is the root cause?"""

    def _build_report(self, stats, explanation) -> CorrelationReport: ...
```

**What Pandas computes (no LLM):**
```python
# Join on keyword (case-insensitive)
merged = ad_df.merge(returns_df, on="keyword", how="left")
merged["return_quantity"] = merged["quantity"].fillna(0)
merged["return_rate"] = (merged["return_quantity"] / merged["clicks"]).fillna(0.0)

wasted = merged[merged["return_rate"] > 0.3]["spend"].sum()
wasted_spend_pct = wasted / merged["spend"].sum() if merged["spend"].sum() > 0 else 0.0
```

**What LLM explains (narrow prompt):**
```
Given this ad performance data with return rates:
{stats.head(10).to_markdown()}

Product description excerpt: {product.description[:400]}

Answer in JSON only:
{{
  "high_return_keywords": [
    {{"keyword": "...", "return_rate": 0.67, "spend": 1200.0, "root_cause": "one sentence"}}
  ],
  "root_causes": ["cause 1", "cause 2"],
  "top_return_reason": "one sentence summary"
}}

Do not recompute numbers. Only explain WHY these patterns exist based on the product description.
```

---

### ActionService (`domain/services/action_service.py`)

**Responsibilities:**
- Merge GeoReport + CorrelationReport into a single prompt context
- Generate specific, product-scoped actions via LLM
- Validate and sort output

**Design:**
```python
class ActionService:
    VALID_PRIORITIES = frozenset({"critical", "important", "improvement"})

    def __init__(self, llm: ILanguageModel) -> None:
        self._llm = llm

    def generate(
        self,
        product: ProductData,
        geo: GeoReport,
        correlation: CorrelationReport | None,
    ) -> list[ActionItem]:
        prompt = self._build_prompt(product, geo, correlation)
        raw = self._llm.generate(prompt)
        actions = self._parse_response(raw)
        return self._sort_and_validate(actions)

    def _build_prompt(...) -> str: ...
    def _parse_response(self, raw: str) -> list[ActionItem]: ...
    def _sort_and_validate(self, actions: list[ActionItem]) -> list[ActionItem]:
        """Fix invalid priorities → 'improvement'. Sort: critical → important → improvement."""
    def _fallback_action(self, geo: GeoReport) -> list[ActionItem]:
        """Returns 1 default action from geo.suggested_title. Called on total LLM failure."""
```

**Prompt design — strict output contract:**
```
You are an e-commerce optimization expert. Generate a prioritized action list for this seller.

=== PRODUCT ===
Title: {product.title}
Description (first 600 chars): {product.description[:600]}

=== GEO ANALYSIS (score: {geo.score}/100) ===
Missing keywords: {geo.missing_keywords}
Suggested title: {geo.suggested_title}

{=== AD & RETURN ANALYSIS === (include block only if correlation is not None)
Wasted budget: {correlation.wasted_spend_pct*100:.0f}% of total spend
High-risk keywords: {[k["keyword"] for k in correlation.high_return_keywords]}
Root causes: {correlation.root_causes}
}

Rules for each action:
- MUST reference a specific word, keyword, or number from the data above — no generic advice
- MUST include the exact text change or step (copy-pasteable)
- MUST estimate a concrete impact (%, multiplier, or currency amount)
- priority "critical" = actively losing money right now
- priority "important" = significant improvement, not urgent
- priority "improvement" = incremental gain

Respond with a JSON array only (no preamble):
[
  {{
    "priority": "critical|important|improvement",
    "title": "max 8 words",
    "description": "1-2 sentences, specific to this product",
    "estimated_impact": "concrete number or range",
    "how_to_apply": "step-by-step, copy-pasteable"
  }}
]

Generate 3–5 actions. Sort by priority: critical first.
```

---

## Application Layer

### PipelineState (`application/pipeline_state.py`)

```python
class PipelineState(TypedDict):
    url: str
    ad_df: pd.DataFrame | None
    returns_df: pd.DataFrame | None
    product: ProductData | None
    geo_report: GeoReport | None
    correlation_report: CorrelationReport | None
    actions: list[ActionItem] | None
    used_fixture: bool
    error: str | None
```

### AnalysisPipeline (`application/analysis_pipeline.py`)

Orchestrates domain services via LangGraph. Receives all services via constructor injection.

```python
class AnalysisPipeline:
    def __init__(
        self,
        scraper: IProductScraper,
        geo_service: GeoAnalysisService,
        correlation_service: CorrelationService,
        action_service: ActionService,
    ) -> None:
        self._graph = self._build_graph()

    async def run(self, state: PipelineState) -> AnalysisResult: ...

    def _build_graph(self) -> CompiledGraph:
        graph = StateGraph(PipelineState)
        graph.add_node("scrape", self._scrape_node)
        graph.add_node("geo", self._geo_node)
        graph.add_node("correlation", self._correlation_node)
        graph.add_node("action", self._action_node)
        graph.set_entry_point("scrape")
        graph.add_edge("scrape", "geo")
        graph.add_conditional_edges(
            "geo",
            lambda s: "correlation" if s["ad_df"] is not None else "action",
        )
        graph.add_edge("correlation", "action")
        graph.add_edge("action", END)
        return graph.compile()
```

Each `_xxx_node` method: calls the relevant domain service, returns updated state dict.

---

## Infrastructure Adapters

### GeminiLanguageModel (`adapters/outbound/gemini_language_model.py`)
Implements `ILanguageModel`.

```python
class GeminiLanguageModel(ILanguageModel):
    MAX_RETRIES = 2
    RETRY_DELAY = 3.0

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None: ...

    def generate(self, prompt: str) -> str:
        """Retries on ResourceExhausted (429). Raises RuntimeError after max retries."""
```

**Single model rule:** `gemini-2.0-flash` only. The `model` param exists for future flexibility — do not pass `pro` anywhere in this project.

### PlaywrightScraper (`adapters/outbound/playwright_scraper.py`)
Implements `IProductScraper`.

```python
class PlaywrightScraper(IProductScraper):
    USER_AGENTS: list[str] = [...]  # 5 real browser user-agent strings

    async def scrape(self, url: str) -> ProductData:
        try:
            return await self._scrape_live(url)
        except Exception as e:
            logger.warning(f"Scrape failed for {url}: {e}. Loading fixture.")
            return self._load_fixture(url)

    async def _scrape_live(self, url: str) -> ProductData: ...
    def _load_fixture(self, url: str) -> ProductData: ...
    def _detect_domain(self, url: str) -> str: ...
```

### CsvParserFactory (`adapters/outbound/csv_parser_factory.py`)
Implements `ICsvParser`. Uses **Strategy pattern** to dispatch to the correct parser.

```python
class CsvParserFactory(ICsvParser):
    _STRATEGIES: dict[str, type[BaseAdParser]] = {
        "google_ads": GoogleAdsParser,
        "meta_ads": MetaAdsParser,
        "trendyol_ads": TrendyolAdsParser,
    }
    _RETURNS_STRATEGY = TrendyolReturnsParser

    def parse_ads(self, content: bytes) -> pd.DataFrame:
        fmt = self._detect_format(content)
        return self._STRATEGIES[fmt]().parse(content)

    def parse_returns(self, content: bytes) -> pd.DataFrame:
        return self._RETURNS_STRATEGY().parse(content)

    def _detect_format(self, content: bytes) -> str:
        """Reads column headers, matches against signature sets. Raises ValueError if unknown."""
```

Each concrete parser (`GoogleAdsParser`, `MetaAdsParser`, etc.) extends `BaseAdParser`:

```python
class BaseAdParser(ABC):
    COLUMN_MAP: dict[str, str]  # source_col → normalized_col

    @abstractmethod
    def parse(self, content: bytes) -> pd.DataFrame: ...

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rename columns, compute ctr/conversion_rate/cost_per_conversion."""
        df = df.rename(columns=self.COLUMN_MAP)
        df["ctr"] = (df["clicks"] / df["impressions"]).fillna(0.0)
        df["conversion_rate"] = (df["conversions"] / df["clicks"]).fillna(0.0)
        df["cost_per_conversion"] = df.apply(
            lambda r: r["spend"] / r["conversions"] if r["conversions"] > 0 else float("inf"),
            axis=1,
        )
        return df
```

---

## Dependency Injection (main.py)

All wiring happens in `main.py`. Nothing else does `new`:

```python
# Compose infrastructure
scraper = PlaywrightScraper(headless=config.PLAYWRIGHT_HEADLESS)
llm = GeminiLanguageModel(api_key=config.GEMINI_API_KEY)
csv_parser = CsvParserFactory()

# Inject into domain services
geo_service = GeoAnalysisService(llm=llm)
correlation_service = CorrelationService(llm=llm)
action_service = ActionService(llm=llm)

# Compose application pipeline
pipeline = AnalysisPipeline(
    scraper=scraper,
    geo_service=geo_service,
    correlation_service=correlation_service,
    action_service=action_service,
)

# Wire inbound adapter
controller = AnalyzeController(pipeline=pipeline, csv_parser=csv_parser)
app.include_router(controller.router)
```

---

## SOLID & Design Principles

| Principle | How it applies |
|---|---|
| **SRP** | Each class has one reason to change. `GeoAnalysisService` changes only if GEO logic changes. `GeminiLanguageModel` changes only if the Gemini SDK changes. |
| **OCP** | New CSV format = new `BaseAdParser` subclass, no changes to `CsvParserFactory._STRATEGIES`. New scrape target = new `_parse_xxx` method in `PlaywrightScraper`. |
| **LSP** | `GoogleAdsParser`, `MetaAdsParser`, `TrendyolAdsParser` are interchangeable behind `BaseAdParser`. `GeminiLanguageModel` is interchangeable behind `ILanguageModel`. |
| **ISP** | `ILanguageModel` has one method. `IProductScraper` has one method. Interfaces are minimal. |
| **DIP** | Domain services depend on `ILanguageModel`, not `GeminiLanguageModel`. `AnalysisPipeline` depends on service abstractions, not implementations. |
| **Strategy** | `CsvParserFactory` selects the correct parser at runtime based on CSV headers. |
| **Factory** | `CsvParserFactory` encapsulates parser instantiation and format detection. |
| **Facade** | `AnalysisPipeline` is a facade over the 4-node LangGraph graph. Controller never touches LangGraph directly. |

---

## API Contract

```
POST /api/analyze
Content-Type: multipart/form-data
  url          string  (required)
  ad_csv       file    (optional, .csv)
  returns_csv  file    (optional, .csv)

Response 200: AnalyzeResponse
  {
    "geo_score": int,            // 0–100
    "return_rate": float | null, // null if no returns CSV
    "ad_waste_pct": float | null,// null if no ad CSV
    "actions": [ActionItem],
    "used_fixture": bool
  }

Response 400: {"detail": "Unrecognized CSV format. Supported: Google Ads, Meta Ads, Trendyol Ads, Trendyol Returns."}
Response 500: {"detail": "Pipeline failed. Please try again."}

GET /health → {"status": "ok", "version": "1.0.0"}
```

CORS: `http://localhost:3000`, `https://dothis.vercel.app`

---

## Coding Rules

**Python:**
- Type hints on every function signature and class attribute
- Docstring on every public method (one line is enough)
- No bare `except` — always catch specific exceptions
- No `new` outside `main.py` — constructor injection only
- Domain layer: zero imports from `adapters`, `infrastructure`, `fastapi`, `langchain`, `pandas`

**TypeScript:**
- Strict mode, no `any`
- Tailwind only — no custom CSS files
- Component props always typed with interfaces

**General:**
- Do not add features not in the active SPEC
- Do not add a database
- Do not replace Playwright with requests/BeautifulSoup
- Do not call Gemini Pro — Flash only

---

## Environment Variables

```bash
# backend/.env
GEMINI_API_KEY=your_key_here
PLAYWRIGHT_HEADLESS=true

# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```
