import json
import logging
import re
from typing import Any

from domain.entities import CorrelationReport, ProductData
from domain.ports import ILanguageModel

logger = logging.getLogger(__name__)

_AD_TYPE_LABELS = {
    "video": "Video Reklamı",
    "display": "Görüntülü Reklam (Display)",
    "shopping": "Alışveriş Reklamı (Shopping)",
    "search": "Arama Reklamı (Search)",
}


class CorrelationService:
    def __init__(self, llm: ILanguageModel) -> None:
        self._llm = llm

    def analyze(
        self,
        ad_df: Any,
        returns_df: Any | None,
        product: ProductData,
    ) -> CorrelationReport:
        """Full ad × returns analysis: Pandas stats + LLM root-cause explanation."""
        ad_type = ad_df.attrs.get("ad_type", "search")
        audience_signals = ad_df.attrs.get("audience_signals", ["bilinmiyor"])

        stats = self._compute_stats(ad_df, returns_df)
        wasted_spend_pct = self._compute_wasted_spend_pct(stats)
        keyword_roi_map = self._compute_keyword_roi_map(stats)
        budget_efficiency_score = self._compute_budget_efficiency(keyword_roi_map)
        funnel_drop_points = self._compute_funnel_drop_points(stats)
        cost_per_conversion_avg = self._compute_cpa_avg(stats)

        totals = self._compute_totals(stats)
        explanation = self._explain_with_llm(stats, product, ad_type, audience_signals)

        return self._build_report(
            explanation,
            wasted_spend_pct,
            ad_type,
            keyword_roi_map,
            budget_efficiency_score,
            funnel_drop_points,
            cost_per_conversion_avg,
            totals,
        )

    def _compute_stats(self, ad_df: Any, returns_df: Any | None) -> Any:
        ad = ad_df.copy()
        ad["keyword_lower"] = ad["keyword"].str.lower()

        if returns_df is not None:
            ret = returns_df.copy()
            ret["keyword_lower"] = ret["keyword"].str.lower()
            merged = ad.merge(
                ret[["keyword_lower", "quantity"]],
                on="keyword_lower",
                how="left",
            )
        else:
            merged = ad.copy()
            merged["quantity"] = 0

        merged["return_quantity"] = merged["quantity"].fillna(0).astype(int)
        merged["return_rate"] = (merged["return_quantity"] / merged["clicks"]).fillna(0.0)
        merged["return_rate"] = merged["return_rate"].replace(
            [float("inf"), float("-inf")], 0.0
        ).fillna(0.0)
        return merged

    def _compute_wasted_spend_pct(self, stats: Any) -> float:
        high_risk = stats[stats["return_rate"] > 0.3]
        total_spend = stats["spend"].sum()
        return float(high_risk["spend"].sum() / total_spend) if total_spend > 0 else 0.0

    def _compute_keyword_roi_map(self, stats: Any) -> list[dict]:
        """Per-keyword ROI analysis with efficiency scoring (0-100)."""
        rows = []
        for _, row in stats.iterrows():
            ctr = float(row.get("ctr", 0))
            conv_rate = float(row.get("conversion_rate", 0))
            ret_rate = float(row.get("return_rate", 0))
            spend = float(row.get("spend", 0))

            # Efficiency score: penalize waste, reward conversions
            eff = 50.0
            if ctr > 0.05:
                eff += 15
            elif ctr > 0.03:
                eff += 8
            elif ctr < 0.01:
                eff -= 10

            if conv_rate > 0.10:
                eff += 25
            elif conv_rate > 0.05:
                eff += 15
            elif conv_rate > 0.02:
                eff += 8
            elif conv_rate < 0.01:
                eff -= 10

            if ret_rate > 0.50:
                eff -= 40
            elif ret_rate > 0.30:
                eff -= 25
            elif ret_rate > 0.20:
                eff -= 10
            elif ret_rate < 0.05 and conv_rate > 0.02:
                eff += 10

            cpa_raw = row.get("cost_per_conversion")
            cpa = None
            if cpa_raw is not None and cpa_raw != float("inf") and cpa_raw == cpa_raw:
                cpa = round(float(cpa_raw), 2)

            rows.append({
                "keyword": str(row.get("keyword", "")),
                "spend": round(spend, 2),
                "clicks": int(row.get("clicks", 0)),
                "impressions": int(row.get("impressions", 0)),
                "conversions": int(row.get("conversions", 0)),
                "return_quantity": int(row.get("return_quantity", 0)),
                "return_rate": round(ret_rate, 4),
                "ctr": round(ctr, 4),
                "conversion_rate": round(conv_rate, 4),
                "cpa": cpa,
                "efficiency_score": round(max(0.0, min(100.0, eff)), 1),
            })

        return sorted(rows, key=lambda x: x["spend"], reverse=True)[:20]

    def _compute_budget_efficiency(self, keyword_roi_map: list[dict]) -> float:
        """Spend-weighted average efficiency score across all keywords."""
        if not keyword_roi_map:
            return 50.0
        total_spend = sum(k["spend"] for k in keyword_roi_map)
        if total_spend == 0:
            return 50.0
        weighted = sum(k["efficiency_score"] * k["spend"] for k in keyword_roi_map)
        return round(weighted / total_spend, 1)

    def _compute_funnel_drop_points(self, stats: Any) -> list[str]:
        """Identify the weakest links in the conversion funnel (Turkish labels)."""
        drops = []

        avg_ctr = float(stats["ctr"].mean()) if "ctr" in stats.columns else 0.0
        if avg_ctr < 0.02:
            drops.append(
                f"Reklamlar yeterince tıklanmıyor — ortalama CTR %{avg_ctr * 100:.1f} "
                "(gösterim → tıklama dönüşümü çok düşük)"
            )

        if "conversion_rate" in stats.columns:
            avg_conv = float(stats["conversion_rate"].mean())
            if avg_conv < 0.03:
                drops.append(
                    f"Tıklayanlar satın almıyor — ortalama dönüşüm oranı %{avg_conv * 100:.1f} "
                    "(tıklama → satın alma geçişi zayıf)"
                )

        avg_ret = float(stats["return_rate"].mean())
        if avg_ret > 0.20:
            drops.append(
                f"Satın alanlar iade ediyor — ortalama iade oranı %{avg_ret * 100:.1f} "
                "(beklenti ile ürün arasında uyumsuzluk)"
            )

        return drops

    def _compute_cpa_avg(self, stats: Any) -> float | None:
        """Average cost per acquisition across all keywords."""
        if "conversions" not in stats.columns:
            return None
        total_conv = int(stats["conversions"].sum())
        total_spend = float(stats["spend"].sum())
        if total_conv == 0 or total_spend == 0:
            return None
        return round(total_spend / total_conv, 2)

    def _compute_totals(self, stats: Any) -> dict:
        """Aggregate totals across all keywords for funnel overview."""
        return {
            "impressions": int(stats["impressions"].sum()) if "impressions" in stats.columns else 0,
            "clicks": int(stats["clicks"].sum()),
            "conversions": int(stats["conversions"].sum()) if "conversions" in stats.columns else 0,
            "returns": int(stats["return_quantity"].sum()),
            "spend": round(float(stats["spend"].sum()), 2),
        }

    def _explain_with_llm(
        self,
        stats: Any,
        product: ProductData,
        ad_type: str,
        audience_signals: list[str],
    ) -> dict:
        ad_type_label = _AD_TYPE_LABELS.get(ad_type, "Arama Reklamı")
        audience_text = ", ".join(audience_signals)

        audience_section = ""
        if audience_signals != ["bilinmiyor"]:
            audience_section = f"\nTESPİT EDİLEN KİTLE SICAKLIĞI: {audience_text}\n"

        top_stats = stats.nlargest(12, "spend")[
            [c for c in ["keyword", "clicks", "spend", "impressions", "ctr",
                          "conversion_rate", "cost_per_conversion", "return_quantity", "return_rate"]
             if c in stats.columns]
        ]

        prompt = f"""Sen ileri düzey bir dijital pazarlama ve e-ticaret analisti olarak bu reklam verilerini derinlemesine analiz et.

REKLAM FORMATI: {ad_type_label}
{audience_section}
ÜRÜN AÇIKLAMASI:
{product.description[:500]}

REKLAM PERFORMANS VERİSİ (harcamaya göre sıralı ilk 12 kayıt):
{top_stats.to_markdown(index=False)}

GÖREVIN — Aşağıdaki her başlık için kapsamlı Türkçe analiz yap:

1. YÜKSEK RİSKLİ REKLAMLAR: Hangi kelimeler en çok bütçe israfı yapıyor? Bu ürün açıklamasıyla bağlantılı olarak NEDEN yüksek iade/düşük dönüşüm oluşuyor?

2. KÖK SEBEPLER: İadelerin ve düşük dönüşümün temel nedenleri:
   - Ürün-mesaj uyumsuzluğu mu?
   - Yanlış kitle hedeflemesi mi?
   - Eksik/yanıltıcı ürün bilgisi mi?
   - Fiyat-değer uyumsuzluğu mu?

3. KİTLE ANALİZİ: Soğuk (awareness), ılık (consideration), sıcak (conversion) kitle segmentleri için bütçe önerileri.

4. FORMAT ÖZGÜ BULGULAR: {ad_type_label} formatına özgü iyileştirme fırsatları.

SADECE aşağıdaki JSON formatında yanıt ver. Başka açıklama EKLEME:
{{
  "high_return_keywords": [
    {{
      "keyword": "reklam adı veya anahtar kelime",
      "return_rate": <sayısal değer — veriyi olduğu gibi kullan>,
      "spend": <sayısal değer — veriyi olduğu gibi kullan>,
      "root_cause": "Bu spesifik kelime için kök sebep — 1-2 cümle Türkçe",
      "audience_temperature": "soğuk|ılık|sıcak|bilinmiyor"
    }}
  ],
  "root_causes": [
    "Tüm kampanyaya yönelik kök sebep 1 — somut ve spesifik, Türkçe",
    "Tüm kampanyaya yönelik kök sebep 2 — somut ve spesifik, Türkçe"
  ],
  "top_return_reason": "En kritik iade sebebinin tek cümle özeti — Türkçe",
  "ad_format_insights": "{ad_type_label} formatına özgü tespitler ve iyileştirme önerileri — 2-3 cümle Türkçe",
  "audience_analysis": "Soğuk/ılık/sıcak kitle analizi ve bütçe optimizasyon önerileri — 3-4 cümle Türkçe"
}}

Sayısal değerleri yeniden hesaplama. Sadece NEDEN ve NE YAPILMALI sorularını yanıtla.
ZORUNLU: Tüm metin değerleri Türkçe olmalıdır."""

        raw = self._llm.generate(prompt)
        try:
            cleaned = re.sub(r"```(?:json)?\s*\n?(.*?)\n?```", r"\1", raw, flags=re.DOTALL)
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if not match:
                raise ValueError("LLM yanıtında JSON bulunamadı")
            return json.loads(match.group())
        except (ValueError, json.JSONDecodeError, TypeError) as exc:
            logger.warning("Korelasyon açıklaması ayrıştırılamadı: %s", exc)
            return {}

    def _build_report(
        self,
        explanation: dict,
        wasted_spend_pct: float,
        ad_type: str,
        keyword_roi_map: list[dict],
        budget_efficiency_score: float,
        funnel_drop_points: list[str],
        cost_per_conversion_avg: float | None,
        totals: dict,
    ) -> CorrelationReport:
        high_return = explanation.get("high_return_keywords", [])
        root_causes = explanation.get("root_causes", [])
        top_reason = explanation.get("top_return_reason")
        ad_format_insights = explanation.get("ad_format_insights")
        audience_analysis = explanation.get("audience_analysis")

        if not isinstance(high_return, list):
            high_return = []
        if not isinstance(root_causes, list):
            root_causes = []

        return CorrelationReport(
            high_return_keywords=high_return,
            root_causes=[str(item) for item in root_causes],
            wasted_spend_pct=wasted_spend_pct,
            top_return_reason=str(top_reason) if top_reason else None,
            ad_format_insights=str(ad_format_insights) if ad_format_insights else None,
            audience_analysis=str(audience_analysis) if audience_analysis else None,
            ad_type=ad_type,
            keyword_roi_map=keyword_roi_map,
            budget_efficiency_score=budget_efficiency_score,
            funnel_drop_points=funnel_drop_points,
            cost_per_conversion_avg=cost_per_conversion_avg,
            total_impressions=totals.get("impressions", 0),
            total_clicks=totals.get("clicks", 0),
            total_conversions=totals.get("conversions", 0),
            total_returns=totals.get("returns", 0),
        )
