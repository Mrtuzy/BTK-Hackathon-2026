import io

import pandas as pd

from infrastructure.parsers.base_ad_parser import BaseAdParser


class MetaAdsParser(BaseAdParser):
    COLUMN_MAP = {
        "Ad Set Name": "keyword",
        "Clicks (all)": "clicks",
        "Amount spent": "spend",
        "Impressions": "impressions",
        "Results": "conversions",
    }

    def parse(self, content: bytes) -> pd.DataFrame:
        df = pd.read_csv(io.BytesIO(content))
        return self._normalize(df)
