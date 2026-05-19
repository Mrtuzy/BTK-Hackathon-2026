from dataclasses import dataclass, field

from domain.entities import ActionItem


@dataclass
class AnalyzeRequest:
    url: str
    ad_csv_content: bytes | None
    returns_csv_content: bytes | None


@dataclass
class AnalyzeResponse:
    geo_score: int
    return_rate: float | None
    ad_waste_pct: float | None
    actions: list[ActionItem]
    used_fixture: bool
    geo_suggested_title: str = ""
    geo_suggested_description: str = ""
    geo_missing_keywords: list[str] = field(default_factory=list)
    geo_competitor_keywords: list[str] = field(default_factory=list)
    ad_format_insights: str | None = None
    audience_analysis: str | None = None
    ad_type: str | None = None
    top_return_reason: str | None = None
    keyword_roi_map: list[dict] = field(default_factory=list)
    budget_efficiency_score: float | None = None
    funnel_drop_points: list[str] = field(default_factory=list)
    cost_per_conversion_avg: float | None = None
    combined_insight: str | None = None
    competitor_insight: str | None = None
    high_return_keywords: list[dict] = field(default_factory=list)
    root_causes: list[str] = field(default_factory=list)
    total_impressions: int = 0
    total_clicks: int = 0
    total_conversions: int = 0
    total_returns: int = 0
