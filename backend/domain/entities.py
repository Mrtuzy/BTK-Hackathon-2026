from dataclasses import dataclass, field


@dataclass
class ProductData:
    title: str
    description: str
    price: str
    reviews: list[str]
    competitor_titles: list[str]
    source: str


@dataclass
class GeoReport:
    score: int
    missing_keywords: list[str]
    competitor_keywords: list[str]
    suggested_title: str
    suggested_description_intro: str


@dataclass
class CorrelationReport:
    high_return_keywords: list[dict]
    root_causes: list[str]
    wasted_spend_pct: float
    top_return_reason: str | None
    ad_format_insights: str | None = None
    audience_analysis: str | None = None
    ad_type: str = "search"
    keyword_roi_map: list[dict] = field(default_factory=list)
    budget_efficiency_score: float = 0.0
    funnel_drop_points: list[str] = field(default_factory=list)
    cost_per_conversion_avg: float | None = None
    total_impressions: int = 0
    total_clicks: int = 0
    total_conversions: int = 0
    total_returns: int = 0


@dataclass
class ActionItem:
    priority: str
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
    combined_insight: str = ""
    competitor_insight: str = ""
