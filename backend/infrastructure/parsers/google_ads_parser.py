import io

import pandas as pd

from infrastructure.parsers.base_ad_parser import BaseAdParser


class GoogleAdsParser(BaseAdParser):
    COLUMN_MAP = {
        "Keyword": "keyword",
        "Clicks": "clicks",
        "Cost": "spend",
        "Impressions": "impressions",
        "Conversions": "conversions",
    }

    def parse(self, content: bytes) -> pd.DataFrame:
        df = pd.read_csv(io.BytesIO(content))
        return self._normalize(df)
