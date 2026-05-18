import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from application.analysis_pipeline import AnalysisPipeline
from application.dto import AnalyzeResponse
from domain.ports import ICsvParser

logger = logging.getLogger(__name__)


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
    ) -> AnalyzeResponse:
        """Parse input, run pipeline, and return the full analysis result."""
        ad_df = None
        returns_df = None

        try:
            if ad_csv:
                ad_df = self._csv_parser.parse_ads(await ad_csv.read())
            if returns_csv:
                returns_df = self._csv_parser.parse_returns(await returns_csv.read())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            result = await self._pipeline.run(url, ad_df, returns_df)
        except Exception as exc:
            logger.exception("Pipeline failed")
            raise HTTPException(
                status_code=500,
                detail="Analiz sırasında bir hata oluştu. Lütfen tekrar deneyin.",
            ) from exc

        return_rate = None
        if returns_df is not None and ad_df is not None:
            total_returns = returns_df["quantity"].sum()
            total_clicks = ad_df["clicks"].sum()
            return_rate = float(total_returns / total_clicks) if total_clicks > 0 else None

        corr = result.correlation_report
        return AnalyzeResponse(
            geo_score=result.geo_report.score,
            return_rate=return_rate,
            ad_waste_pct=corr.wasted_spend_pct if corr else None,
            actions=result.actions,
            used_fixture=result.used_fixture,
            geo_suggested_title=result.geo_report.suggested_title,
            geo_suggested_description=result.geo_report.suggested_description_intro,
            geo_missing_keywords=result.geo_report.missing_keywords,
            geo_competitor_keywords=result.geo_report.competitor_keywords,
            ad_format_insights=corr.ad_format_insights if corr else None,
            audience_analysis=corr.audience_analysis if corr else None,
            ad_type=corr.ad_type if corr else None,
            top_return_reason=corr.top_return_reason if corr else None,
            keyword_roi_map=corr.keyword_roi_map if corr else [],
            budget_efficiency_score=corr.budget_efficiency_score if corr else None,
            funnel_drop_points=corr.funnel_drop_points if corr else [],
            cost_per_conversion_avg=corr.cost_per_conversion_avg if corr else None,
            combined_insight=result.combined_insight or None,
            high_return_keywords=corr.high_return_keywords if corr else [],
            root_causes=corr.root_causes if corr else [],
            total_impressions=corr.total_impressions if corr else 0,
            total_clicks=corr.total_clicks if corr else 0,
            total_conversions=corr.total_conversions if corr else 0,
            total_returns=corr.total_returns if corr else 0,
        )
