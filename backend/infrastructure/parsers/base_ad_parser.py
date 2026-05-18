from abc import ABC, abstractmethod

import pandas as pd


class BaseAdParser(ABC):
    COLUMN_MAP: dict[str, str]

    @abstractmethod
    def parse(self, content: bytes) -> pd.DataFrame:
        """Parse raw CSV bytes, return normalized DataFrame."""

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rename via COLUMN_MAP, compute derived columns, return clean df."""
        df = df.rename(columns=self.COLUMN_MAP)[list(self.COLUMN_MAP.values())]
        df["clicks"] = pd.to_numeric(df["clicks"], errors="coerce").fillna(0).astype(int)
        df["spend"] = pd.to_numeric(df["spend"], errors="coerce").fillna(0.0)
        df["impressions"] = (
            pd.to_numeric(df["impressions"], errors="coerce")
            .fillna(0)
            .astype(int)
        )
        df["conversions"] = (
            pd.to_numeric(df["conversions"], errors="coerce")
            .fillna(0)
            .astype(int)
        )
        df["ctr"] = (df["clicks"] / df["impressions"]).replace(
            [float("inf"), float("nan")],
            0.0,
        )
        df["conversion_rate"] = (df["conversions"] / df["clicks"]).replace(
            [float("inf"), float("nan")],
            0.0,
        )
        df["cost_per_conversion"] = df.apply(
            lambda row: row["spend"] / row["conversions"]
            if row["conversions"] > 0
            else float("inf"),
            axis=1,
        )
        return df
