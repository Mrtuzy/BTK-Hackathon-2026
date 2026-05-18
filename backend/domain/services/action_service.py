import json
import logging
import re

from domain.entities import ActionItem, CorrelationReport, GeoReport, ProductData
from domain.ports import ILanguageModel

logger = logging.getLogger(__name__)


class ActionService:
    VALID_PRIORITIES: frozenset[str] = frozenset({"critical", "important", "improvement"})

    def __init__(self, llm: ILanguageModel) -> None:
        self._llm = llm

    def generate(
        self,
        product: ProductData,
        geo: GeoReport,
        correlation: CorrelationReport | None,
    ) -> list[ActionItem]:
        """Generate a prioritized Turkish action list."""
        prompt = self._build_prompt(product, geo, correlation)
        raw = self._llm.generate(prompt)
        actions = self._parse_response(raw, geo)
        return self._sort_and_validate(actions)

    def generate_combined_insight(
        self,
        product: ProductData,
        geo: GeoReport,
        correlation: CorrelationReport | None,
    ) -> str:
        """Generate a holistic narrative connecting GEO, ad spend, and return data."""
        prompt = self._build_combined_insight_prompt(product, geo, correlation)
        raw = self._llm.generate(prompt)
        cleaned = raw.strip()
        # Strip surrounding quotes if LLM wrapped in JSON string
        if cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1]
        return cleaned[:900]

    def _build_combined_insight_prompt(
        self,
        product: ProductData,
        geo: GeoReport,
        correlation: CorrelationReport | None,
    ) -> str:
        geo_label = "kritik düşük" if geo.score < 40 else "orta" if geo.score < 70 else "iyi"
        missing_kw = ", ".join(geo.missing_keywords[:3]) if geo.missing_keywords else "tespit edilmedi"

        blocks = [
            "Sen bir e-ticaret kâr analisti olarak bu satıcının tüm verilerini bütünleştir.",
            "",
            f"ÜRÜN: {product.title}",
            f"GEO SKORU: {geo.score}/100 ({geo_label}) — Yapay zeka aramalarındaki görünürlük",
            f"EKSİK ANAHTAR KELİMELER: {missing_kw}",
        ]

        if correlation:
            waste_pct = correlation.wasted_spend_pct * 100
            eff = correlation.budget_efficiency_score
            funnel = "; ".join(correlation.funnel_drop_points) if correlation.funnel_drop_points else "huni sorunu tespit edilmedi"
            top_reason = correlation.top_return_reason or "bilinmiyor"
            high_risk_kw = [k.get("keyword", "") for k in correlation.high_return_keywords[:3]]
            cpa = f"₺{correlation.cost_per_conversion_avg:.0f}" if correlation.cost_per_conversion_avg else "hesaplanamadı"

            blocks.extend([
                f"REKLAM BÜTÇESİ ISRAFI: %{waste_pct:.0f} boşa gidiyor",
                f"BÜTÇE VERİMLİLİK SKORU: {eff:.0f}/100",
                f"ORTALAMA MÜŞTERİ EDİNİM MALİYETİ (CPA): {cpa}",
                f"HUNİ SORUNLARI: {funnel}",
                f"EN RİSKLİ REKLAMLAR: {', '.join(high_risk_kw) if high_risk_kw else 'yok'}",
                f"TEMEL İADE NEDENİ: {top_reason}",
            ])

        blocks.extend([
            "",
            "GÖREV: Yukarıdaki verileri birleştiren bütünsel bir analiz yaz.",
            "Şunları içermeli:",
            "- Sorunların birbirini nasıl beslediği (örn: düşük GEO → yanlış kitle → yüksek iade)",
            "- Spesifik sayılar ve yüzdeler",
            "- Aylık tahmini kâr kaybı (somut tahmin yap)",
            "Kurallar:",
            "- 3-5 Türkçe cümle",
            "- 'Bu ürün...' ile başla",
            "- Sadece düz metin döndür, başlık/madde işareti/JSON KULLANMA",
        ])

        return "\n".join(blocks)

    def _build_prompt(
        self,
        product: ProductData,
        geo: GeoReport,
        correlation: CorrelationReport | None,
    ) -> str:
        blocks = [
            "Sen Türkiye'nin en deneyimli e-ticaret kâr optimizasyon danışmanısın. Bu satıcı için somut, uygulanabilir ve önceliklendirilmiş aksiyon listesi oluştur.",
            "",
            "=== ÜRÜN BİLGİSİ ===",
            f"Başlık: {product.title}",
            f"Açıklama (ilk 600 karakter): {product.description[:600]}",
            "",
            f"=== GEO ANALİZİ (Puan: {geo.score}/100) ===",
            f"Eksik anahtar kelimeler: {geo.missing_keywords}",
            f"Önerilen başlık: {geo.suggested_title}",
            f"Önerilen açıklama girişi: {geo.suggested_description_intro}",
        ]

        if correlation is not None:
            blocks.extend([
                "",
                "=== REKLAM & İADE ANALİZİ ===",
                f"Bütçe israfı: Toplam harcamanın %{correlation.wasted_spend_pct * 100:.0f}'i boşa gidiyor",
                f"Bütçe verimlilik skoru: {correlation.budget_efficiency_score:.0f}/100",
                f"Yüksek iadeli reklamlar: {[item.get('keyword') for item in correlation.high_return_keywords[:5]]}",
                f"Huni sorunları: {correlation.funnel_drop_points}",
                f"Kök sebepler: {correlation.root_causes}",
            ])
            if correlation.top_return_reason:
                blocks.append(f"Ana iade sebebi: {correlation.top_return_reason}")
            if correlation.audience_analysis:
                blocks.append(f"Kitle analizi: {correlation.audience_analysis}")
            if correlation.cost_per_conversion_avg:
                blocks.append(f"Ortalama müşteri edinim maliyeti: ₺{correlation.cost_per_conversion_avg:.0f}")

        blocks.extend([
            "",
            "AKSIYON KURALLARI:",
            "1. Her aksiyon yukarıdaki verilerden belirli bir kelime, sayı veya metriği referans almalıdır — genel tavsiyeler YASAK",
            "2. Her aksiyon kopyalanıp doğrudan uygulanabilir, adım adım talimatlar içermelidir",
            "3. Her aksiyon somut etki tahmini içermelidir (%, TL tutarı veya çarpan olarak ifade et)",
            "4. priority 'critical' = şu an aktif para veya satış kaybı yaşanıyor",
            "5. priority 'important' = önemli iyileştirme fırsatı, bu hafta uygulanmalı",
            "6. priority 'improvement' = kademeli kazanım, sıradaki sprint'e alınabilir",
            "",
            "SADECE JSON dizisi olarak yanıt ver (giriş cümlesi veya açıklama YAZMA):",
            "[",
            "  {",
            '    "priority": "critical|important|improvement",',
            '    "title": "maksimum 8 kelime, Türkçe ve net",',
            '    "description": "Bu ürüne özgü 1-2 cümle. Genel tavsiye yok. Türkçe.",',
            '    "estimated_impact": "Spesifik sayı veya aralık (örn: %15-20 dönüşüm artışı, aylık 2.500 TL tasarruf)",',
            '    "how_to_apply": "Adım adım talimat. Doğrudan kopyalanıp uygulanabilir. Türkçe."',
            "  }",
            "]",
            "",
            "3-6 aksiyon üret. Önce critical, sonra important, sonra improvement sıralamasını koru.",
            "ZORUNLU: Tüm metin değerleri Türkçe olmalıdır.",
        ])

        return "\n".join(blocks)

    def _extract_json_array(self, raw: str) -> list[dict]:
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            raise ValueError("LLM yanıtında JSON dizisi bulunamadı")
        data = json.loads(match.group())
        if not isinstance(data, list):
            raise ValueError("JSON dizisi beklendi")
        return [item for item in data if isinstance(item, dict)]

    def _parse_response(self, raw: str, geo: GeoReport) -> list[ActionItem]:
        try:
            items = self._extract_json_array(raw)
            actions = [
                ActionItem(
                    priority=str(item.get("priority", "improvement")),
                    title=str(item.get("title", "")),
                    description=str(item.get("description", "")),
                    estimated_impact=str(item.get("estimated_impact", "")),
                    how_to_apply=str(item.get("how_to_apply", "")),
                )
                for item in items
            ]
            return actions if actions else self._fallback_action(geo)
        except (ValueError, json.JSONDecodeError, TypeError) as exc:
            logger.warning("Aksiyon yanıtı ayrıştırılamadı: %s", exc)
            return self._fallback_action(geo)

    def _sort_and_validate(self, actions: list[ActionItem]) -> list[ActionItem]:
        priority_order = {"critical": 0, "important": 1, "improvement": 2}
        for action in actions:
            if action.priority not in self.VALID_PRIORITIES:
                action.priority = "improvement"
        return sorted(actions, key=lambda item: priority_order[item.priority])

    def _fallback_action(self, geo: GeoReport) -> list[ActionItem]:
        if geo.suggested_title.strip():
            return [
                ActionItem(
                    priority="important",
                    title="Ürün başlığını GEO analizine göre güncelle",
                    description="GEO analizinde tespit edilen eksik anahtar kelimeler başlığa eklenerek yapay zeka arama görünürlüğü artırılabilir.",
                    estimated_impact="%10-15 GEO skor artışı, %5-8 organik tıklama artışı",
                    how_to_apply=f"Mevcut başlığı şununla değiştir: {geo.suggested_title}",
                )
            ]
        return [
            ActionItem(
                priority="important",
                title="Başlığa ölçülebilir özellik ekle",
                description="Yapay zeka arama motorları spesifik özelliklere göre ürünleri sıralıyor. Başlığı daha spesifik hale getir.",
                estimated_impact="%8-12 GEO skor artışı",
                how_to_apply="Başlığa en az 1 ölçülebilir özellik ekle: ağırlık (g/kg), malzeme, boyut (cm/ml) veya kapasite.",
            )
        ]
