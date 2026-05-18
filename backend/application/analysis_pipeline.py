from typing import Any

import pandas as pd
from langgraph.graph import END, StateGraph

from application.pipeline_state import PipelineState
from domain.entities import AnalysisResult
from domain.ports import IProductScraper
from domain.services.action_service import ActionService
from domain.services.correlation_service import CorrelationService
from domain.services.geo_service import GeoAnalysisService


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
        )

    async def _scrape_node(self, state: PipelineState) -> PipelineState:
        product = await self._scraper.scrape(state["url"])
        return {**state, "product": product, "used_fixture": product.source == "fixture"}

    def _geo_node(self, state: PipelineState) -> PipelineState:
        geo = self._geo.analyze(state["product"])
        return {**state, "geo_report": geo}

    def _correlation_node(self, state: PipelineState) -> PipelineState:
        report = self._correlation.analyze(
            state["ad_df"],
            state["returns_df"],
            state["product"],
        )
        return {**state, "correlation_report": report}

    def _action_node(self, state: PipelineState) -> PipelineState:
        actions = self._action.generate(
            state["product"],
            state["geo_report"],
            state["correlation_report"],
        )
        combined_insight = self._action.generate_combined_insight(
            state["product"],
            state["geo_report"],
            state["correlation_report"],
        )
        return {**state, "actions": actions, "combined_insight": combined_insight}

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
