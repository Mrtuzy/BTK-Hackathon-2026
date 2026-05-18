import io

import pandas as pd

from infrastructure.parsers.base_ad_parser import BaseAdParser


class TrendyolAdsParser(BaseAdParser):
    COLUMN_MAP = {
        "Anahtar Kelime": "keyword",
        "Tıklama": "clicks",
        "Harcama": "spend",
        "Gösterim": "impressions",
        "Dönüşüm": "conversions",
    }

    def parse(self, content: bytes) -> pd.DataFrame:
        df = pd.read_csv(io.BytesIO(content))
        return self._normalize(df)


class TrendyolReturnsParser:
    COLUMN_MAP = {
        "Ürün Adı": "product_title",
        "İade Sebebi": "return_reason",
        "Kaynak Anahtar Kelime": "keyword",
        "İade Adedi": "quantity",
    }

    def parse(self, content: bytes) -> pd.DataFrame:
        df = pd.read_csv(io.BytesIO(content))
        df = df.rename(columns=self.COLUMN_MAP)[list(self.COLUMN_MAP.values())]
        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
        df["keyword"] = df["keyword"].fillna("").str.lower()
        return df
