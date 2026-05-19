from typing import TypedDict

import pandas as pd

from domain.entities import ActionItem, CorrelationReport, GeoReport, ProductData


class PipelineState(TypedDict):
    url: str
    ad_df: pd.DataFrame | None
    returns_df: pd.DataFrame | None
    product: ProductData | None
    geo_report: GeoReport | None
    correlation_report: CorrelationReport | None
    actions: list[ActionItem] | None
    combined_insight: str
    competitor_insight: str
    used_fixture: bool
    error: str | None
