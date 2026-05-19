import logging
from typing import Any
from urllib.parse import urlparse

import pandas as pd

logger = logging.getLogger(__name__)
from langgraph.graph import END, StateGraph

from application.pipeline_state import PipelineState
from domain.entities import AnalysisResult
from domain.ports import ICompetitorSearcher, ILanguageModel, IProductScraper
from domain.services.action_service import ActionService
from domain.services.correlation_service import CorrelationService
from domain.services.geo_service import GeoAnalysisService


class AnalysisPipeline:
    def __init__(
        self,
        scraper: IProductScraper,
        llm: ILanguageModel,
        geo_service: GeoAnalysisService,
        correlation_service: CorrelationService,
        action_service: ActionService,
        competitor_searcher: ICompetitorSearcher,
    ) -> None:
        self._scraper = scraper
        self._llm = llm
        self._geo = geo_service
        self._correlation = correlation_service
        self._action = action_service
        self._competitor = competitor_searcher
        self._graph = self._build_graph()

    async def run(
        self,
        url: str,
        ad_df: pd.DataFrame | None,
        returns_df: pd.DataFrame | None,
    ) -> AnalysisResult:
        initial: PipelineState = {
            "url": url,
            "ad_df": ad_df,
            "returns_df": returns_df,
            "product": None,
            "geo_report": None,
            "correlation_report": None,
            "actions": None,
            "combined_insight": "",
            "competitor_insight": "",
            "used_fixture": False,
            "error": None,
        }
        final_state: PipelineState = await self._graph.ainvoke(initial)
        return AnalysisResult(
            geo_report=final_state["geo_report"],
            correlation_report=final_state["correlation_report"],
            actions=final_state["actions"] or [],
            used_fixture=final_state["used_fixture"],
            combined_insight=final_state.get("combined_insight", ""),
            competitor_insight=final_state.get("competitor_insight", ""),
        )

    async def _scrape_node(self, state: PipelineState) -> PipelineState:
        product = await self._scraper.scrape(state["url"])
        return {**state, "product": product, "used_fixture": product.source == "fixture"}

    def _geo_node(self, state: PipelineState) -> PipelineState:
        try:
            geo = self._geo.analyze(state["product"])
        except Exception as exc:
            logger.warning("GEO analizi başarısız, fallback kullanılıyor: %s", exc)
            from domain.entities import GeoReport
            geo = GeoReport(
                score=0,
                missing_keywords=[],
                competitor_keywords=[],
                suggested_title="",
                suggested_description_intro="",
            )
        return {**state, "geo_report": geo}

    def _correlation_node(self, state: PipelineState) -> PipelineState:
        try:
            report = self._correlation.analyze(
                state["ad_df"],
                state["returns_df"],
                state["product"],
            )
        except Exception as exc:
            logger.warning("Korelasyon analizi başarısız, atlanıyor: %s", exc)
            report = None
        return {**state, "correlation_report": report}

    def _action_node(self, state: PipelineState) -> PipelineState:
        try:
            actions = self._action.generate(
                state["product"],
                state["geo_report"],
                state["correlation_report"],
            )
        except Exception as exc:
            logger.warning("Aksiyon üretimi başarısız, fallback kullanılıyor: %s", exc)
            actions = self._action._fallback_action(state["geo_report"])

        try:
            combined_insight = self._action.generate_combined_insight(
                state["product"],
                state["geo_report"],
                state["correlation_report"],
            )
        except Exception as exc:
            logger.warning("Birleşik analiz başarısız, atlanıyor: %s", exc)
            combined_insight = ""

        try:
            platform_hint = self._detect_platform(state["url"])
            competitor_insight = self._competitor.search(
                product_title=state["product"].title,
                platform_hint=platform_hint,
            )
        except Exception as exc:
            logger.warning("Rakip araması başarısız, atlanıyor: %s", exc)
            competitor_insight = ""

        return {
            **state,
            "actions": actions,
            "combined_insight": combined_insight,
            "competitor_insight": competitor_insight,
        }

    def _detect_platform(self, url: str) -> str:
        host = urlparse(url).netloc.lower()
        if "trendyol" in host:
            return "Trendyol"
        if "hepsiburada" in host:
            return "Hepsiburada"
        if "amazon" in host:
            return "Amazon Türkiye"
        return "Türk e-ticaret"

    def _build_graph(self) -> Any:
        graph = StateGraph(PipelineState)
        graph.add_node("scrape", self._scrape_node)
        graph.add_node("geo", self._geo_node)
        graph.add_node("correlation", self._correlation_node)
        graph.add_node("action", self._action_node)
        graph.set_entry_point("scrape")
        graph.add_edge("scrape", "geo")
        graph.add_conditional_edges(
            "geo",
            lambda state: "correlation" if state["ad_df"] is not None else "action",
        )
        graph.add_edge("correlation", "action")
        graph.add_edge("action", END)
        return graph.compile()
