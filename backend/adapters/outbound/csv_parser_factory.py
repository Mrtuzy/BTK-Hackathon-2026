import io
import re

import pandas as pd

from domain.ports import ICsvParser
from infrastructure.parsers.google_ads_parser import GoogleAdsParser
from infrastructure.parsers.meta_ads_parser import MetaAdsParser
from infrastructure.parsers.trendyol_parser import TrendyolAdsParser, TrendyolReturnsParser

_COLUMN_ALIASES: dict[str, list[str]] = {
    "keyword": [
        "keyword", "keywords", "anahtar kelime", "anahtar kelimeler",
        "ad set name", "ad set", "kampanya adı", "campaign name", "campaign",
        "ad name", "reklam adı", "search term", "arama terimi", "query",
        "ad group", "reklam grubu", "set adı", "hedef kitle",
    ],
    "clicks": [
        "clicks", "click", "tıklama", "tıklamalar", "clicks (all)",
        "link clicks", "outbound clicks", "link tıklamaları",
    ],
    "spend": [
        "cost", "spend", "harcama", "amount spent", "harcanan tutar",
        "toplam harcama", "maliyet", "cost (try)", "bütçe kullanımı",
    ],
    "impressions": [
        "impressions", "impression", "gösterim", "gösterimler",
        "reach", "erişim", "görüntülenme",
    ],
    "conversions": [
        "conversions", "conversion", "dönüşüm", "dönüşümler",
        "results", "purchases", "satışlar", "orders", "siparişler",
    ],
}

_RETURNS_ALIASES: dict[str, list[str]] = {
    "keyword": [
        "kaynak anahtar kelime", "arama terimi", "search term",
        "keyword", "kampanya", "anahtar kelime",
    ],
    "quantity": [
        "iade adedi", "return quantity", "quantity", "adet", "miktar", "iade miktarı",
    ],
    "product_title": [
        "ürün adı", "product name", "ürün başlığı", "title", "product title",
    ],
    "return_reason": [
        "iade sebebi", "return reason", "sebep", "reason", "neden",
    ],
}

_VIDEO_COLS = frozenset({
    "video views", "thruplay", "thruplays", "3-second video plays",
    "video oynatma", "watch time", "video görüntülenme", "completions",
    "video completion rate", "video_plays",
})

_DISPLAY_COLS = frozenset({
    "viewable impressions", "banner", "display impressions",
    "görüntülü reklam", "active view",
})

_SHOPPING_COLS = frozenset({
    "product title", "ürün başlığı", "product id", "roas",
    "revenue", "gelir", "product category", "product type",
})

_COLD_SIGNALS = frozenset({
    "cold", "soğuk", "prospecting", "acquisition", "lookalike", "benzer",
    "interest", "ilgi", "awareness", "farkındalık", "reach", "broad", "geniş",
    "new audience", "yeni kitle",
})

_WARM_SIGNALS = frozenset({
    "warm", "ılık", "consideration", "engagement", "etkileşim",
    "video viewer", "page fan", "sayfa", "website visitor", "site ziyaretçi",
})

_HOT_SIGNALS = frozenset({
    "hot", "sıcak", "retargeting", "remarketing", "yeniden",
    "cart", "sepet", "abandoned", "terk", "purchase", "dönüşüm kitlesi",
})


def _fuzzy_remap(df: pd.DataFrame, alias_map: dict[str, list[str]]) -> pd.DataFrame:
    """Rename DataFrame columns using fuzzy alias matching."""
    cols_lower = {c.lower(): c for c in df.columns}
    col_map: dict[str, str] = {}

    for target, aliases in alias_map.items():
        for alias in aliases:
            if alias.lower() in cols_lower:
                col_map[cols_lower[alias.lower()]] = target
                break
        else:
            for col_l, col_orig in cols_lower.items():
                for alias in aliases:
                    if alias.lower() in col_l or col_l in alias.lower():
                        if col_orig not in col_map:
                            col_map[col_orig] = target
                        break

    return df.rename(columns=col_map)


def _detect_ad_type(df: pd.DataFrame) -> str:
    cols_lower = {c.lower() for c in df.columns}
    if _VIDEO_COLS & cols_lower:
        return "video"
    if _SHOPPING_COLS & cols_lower:
        return "shopping"
    if _DISPLAY_COLS & cols_lower:
        return "display"
    return "search"


def _detect_audience_signals(df: pd.DataFrame) -> list[str]:
    if "keyword" not in df.columns:
        return ["bilinmiyor"]
    text = " ".join(df["keyword"].astype(str).str.lower().tolist())
    words = set(re.split(r"[\s_\-|,]+", text))
    signals = []
    if _COLD_SIGNALS & words:
        signals.append("soğuk")
    if _WARM_SIGNALS & words:
        signals.append("ılık")
    if _HOT_SIGNALS & words:
        signals.append("sıcak")
    return signals or ["bilinmiyor"]


class CsvParserFactory(ICsvParser):
    _AD_STRATEGIES: dict[str, type] = {
        "google_ads": GoogleAdsParser,
        "meta_ads": MetaAdsParser,
        "trendyol_ads": TrendyolAdsParser,
    }
    _AD_SIGNATURES = {
        "google_ads": {"Keyword", "Clicks", "Cost", "Impressions"},
        "meta_ads": {"Ad Set Name", "Clicks (all)", "Amount spent", "Impressions"},
        "trendyol_ads": {"Anahtar Kelime", "Tıklama", "Harcama", "Gösterim"},
    }

    def parse_ads(self, content: bytes) -> pd.DataFrame:
        """Parse ad CSV. Tries exact format detection, falls back to fuzzy mapping."""
        df = self._try_exact_parse(content)
        if df is None:
            df = self._universal_ad_parse(content)
        self._enrich_metadata(df)
        return df

    def parse_returns(self, content: bytes) -> pd.DataFrame:
        """Parse returns CSV. Tries Trendyol format, falls back to fuzzy mapping."""
        try:
            return TrendyolReturnsParser().parse(content)
        except Exception:
            return self._universal_returns_parse(content)

    def _try_exact_parse(self, content: bytes) -> pd.DataFrame | None:
        try:
            cols = set(pd.read_csv(io.BytesIO(content), nrows=0).columns.tolist())
            for fmt, sig in self._AD_SIGNATURES.items():
                if sig.issubset(cols):
                    return self._AD_STRATEGIES[fmt]().parse(content)
        except Exception:
            pass
        return None

    def _universal_ad_parse(self, content: bytes) -> pd.DataFrame:
        """Map any CSV columns to standard ad schema using fuzzy matching."""
        df = pd.read_csv(io.BytesIO(content))
        df = _fuzzy_remap(df, _COLUMN_ALIASES)

        for col in ["keyword", "clicks", "spend", "impressions", "conversions"]:
            if col not in df.columns:
                df[col] = "" if col == "keyword" else 0.0

        for col in ["clicks", "spend", "impressions", "conversions"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        df["keyword"] = df["keyword"].astype(str)

        df["ctr"] = (df["clicks"] / df["impressions"].replace(0.0, float("inf"))).fillna(0.0)
        df["conversion_rate"] = (df["conversions"] / df["clicks"].replace(0.0, float("inf"))).fillna(0.0)
        df["cost_per_conversion"] = df.apply(
            lambda r: r["spend"] / r["conversions"] if r["conversions"] > 0 else float("inf"),
            axis=1,
        )
        return df

    def _universal_returns_parse(self, content: bytes) -> pd.DataFrame:
        """Fuzzy returns parsing for non-Trendyol formats."""
        df = pd.read_csv(io.BytesIO(content))
        df = _fuzzy_remap(df, _RETURNS_ALIASES)

        for col in ["keyword", "quantity", "product_title", "return_reason"]:
            if col not in df.columns:
                df[col] = 0 if col == "quantity" else ""

        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
        df["keyword"] = df["keyword"].fillna("").str.lower()
        return df

    def _enrich_metadata(self, df: pd.DataFrame) -> None:
        """Store detected ad type and audience signals in df.attrs."""
        df.attrs["ad_type"] = _detect_ad_type(df)
        df.attrs["audience_signals"] = _detect_audience_signals(df)
