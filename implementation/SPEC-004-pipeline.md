# SPEC-004 — Pipeline Wiring

Read CLAUDE.md first. The pipeline is an application-layer concern — it orchestrates domain services but contains no business logic itself.

## What to build

---

### AnalysisPipeline (`application/analysis_pipeline.py`)

Full class from CLAUDE.md. Each LangGraph node is a private method of the class — no standalone module-level functions.

```python
class AnalysisPipeline:
    def __init__(
        self,
        scraper: IProductScraper,
        geo_service: GeoAnalysisService,
        correlation_service: CorrelationService,
        action_service: ActionService,
    ) -> None:
        self._scraper = scraper
        self._geo = geo_service
        self._correlation = correlation_service
        self._action = action_service
        self._graph = self._build_graph()

    async def run(self, url: str, ad_df: pd.DataFrame | None, returns_df: pd.DataFrame | None) -> AnalysisResult:
        initial: PipelineState = {
            "url": url, "ad_df": ad_df, "returns_df": returns_df,
            "product": None, "geo_report": None, "correlation_report": None,
            "actions": None, "used_fixture": False, "error": None,
        }
        final_state = await self._graph.ainvoke(initial)
        return AnalysisResult(
            geo_report=final_state["geo_report"],
            correlation_report=final_state["correlation_report"],
            actions=final_state["actions"] or [],
            used_fixture=final_state["used_fixture"],
        )

    async def _scrape_node(self, state: PipelineState) -> PipelineState:
        product = await self._scraper.scrape(state["url"])
        return {**state, "product": product, "used_fixture": product.source == "fixture"}

    def _geo_node(self, state: PipelineState) -> PipelineState:
        geo = self._geo.analyze(state["product"])
        return {**state, "geo_report": geo}

    def _correlation_node(self, state: PipelineState) -> PipelineState:
        report = self._correlation.analyze(state["ad_df"], state["returns_df"], state["product"])
        return {**state, "correlation_report": report}

    def _action_node(self, state: PipelineState) -> PipelineState:
        actions = self._action.generate(state["product"], state["geo_report"], state["correlation_report"])
        return {**state, "actions": actions}

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

---

### AnalyzeController (`adapters/inbound/analyze_controller.py`)

Inbound adapter. Handles HTTP, parses multipart form, calls pipeline, formats response. No business logic.

```python
class AnalyzeController:
    def __init__(self, pipeline: AnalysisPipeline, csv_parser: ICsvParser) -> None:
        self._pipeline = pipeline
        self._csv_parser = csv_parser
        self.router = APIRouter()
        self.router.add_api_route("/api/analyze", self.analyze, methods=["POST"])

    async def analyze(
        self,
        url: str = Form(...),
        ad_csv: UploadFile | None = File(None),
        returns_csv: UploadFile | None = File(None),
    ):
        ad_df = None
        returns_df = None

        try:
            if ad_csv:
                ad_df = self._csv_parser.parse_ads(await ad_csv.read())
            if returns_csv:
                returns_df = self._csv_parser.parse_returns(await returns_csv.read())
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        try:
            result = await self._pipeline.run(url, ad_df, returns_df)
        except Exception:
            logger.exception("Pipeline failed")
            raise HTTPException(status_code=500, detail="Pipeline failed. Please try again.")

        return_rate = None
        if returns_df is not None and ad_df is not None:
            total_returns = returns_df["quantity"].sum()
            total_clicks = ad_df["clicks"].sum()
            return_rate = float(total_returns / total_clicks) if total_clicks > 0 else None

        return AnalyzeResponse(
            geo_score=result.geo_report.score,
            return_rate=return_rate,
            ad_waste_pct=result.correlation_report.wasted_spend_pct if result.correlation_report else None,
            actions=result.actions,
            used_fixture=result.used_fixture,
        )
```

---

### main.py — Full DI wiring

Replace stub with full composition from CLAUDE.md DI section.

---

## Done when

- `POST /api/analyze` with a Trendyol URL (or any URL) → valid `AnalyzeResponse` JSON with `geo_score` int and non-empty `actions`
- `POST /api/analyze` with no CSVs → `return_rate=null`, `ad_waste_pct=null`
- `POST /api/analyze` with ad CSV → `ad_waste_pct` is a float
- `POST /api/analyze` with invalid CSV → HTTP 400 with correct error message
- `POST /api/analyze` unreachable URL → uses fixture, returns 200 (not 500)
- No business logic in controller or pipeline — only orchestration
