import json
import logging
import re

from domain.entities import GeoReport, ProductData
from domain.ports import ILanguageModel

logger = logging.getLogger(__name__)


class GeoAnalysisService:
    def __init__(self, llm: ILanguageModel) -> None:
        self._llm = llm

    def analyze(self, product: ProductData) -> GeoReport:
        """Analyze GEO visibility for a product listing."""
        prompt = self._build_prompt(product)
        raw = self._llm.generate(prompt)
        return self._parse_response(raw)

    def _build_prompt(self, product: ProductData) -> str:
        return f"""Sen Türkiye'nin en deneyimli e-ticaret GEO (Generative Engine Optimization) danışmanısın. ChatGPT, Gemini ve Perplexity gibi yapay zeka arama motorlarında ürün görünürlüğünü artırma konusunda uzmansın.

Bu ürün sayfasını yapay zeka arama görünürlüğü açısından kapsamlı değerlendir. Her kriteri 0-25 puan üzerinden puanla:

KRITER 1 — Başlık Özgüllüğü (0-25 puan):
  Başlık; ürün kategorisi + en az 1 ölçülebilir özellik içeriyor mu?
  Düşük puan örneği: "Koşu Ayakkabısı" → 5 puan (yalnızca kategori)
  Yüksek puan örneği: "Arazi Koşu Ayakkabısı 280g EVA Taban 5mm Drop" → 25 puan

KRITER 2 — Teknik Özellik Zenginliği (0-25 puan):
  Açıklama ≥3 somut, ölçülebilir teknik özellik içeriyor mu?
  Geçerli: ağırlık, malzeme, boyut, renk seçeneği sayısı, sertifikasyon, teknik standart
  Geçersiz: "hafif", "dayanıklı", "kaliteli" gibi muğlak sıfatlar

KRITER 3 — Yapay Zeka Bağlam Zenginliği (0-25 puan):
  "Bu ürünü kim için önerirsiniz ve neden?" sorusunu yalnızca bu sayfa verisiyle yanıtlayabilir misin?
  Yüksek puan: hedef kitle, kullanım senaryosu ve rakibe göre avantaj net belli

KRITER 4 — Rakip Anahtar Kelime Açığı (0-25 puan):
  Rakip başlıklarda geçen ama bu listede olmayan belirgin anahtar kelimeler var mı?
  Açık yok = 0 puan | Belirgin açıklar tespit edildi = 25 puan

Ürün başlığı: {product.title}
Açıklama: {product.description}
Müşteri yorumları (örnek): {product.reviews[:5]}
Rakip ürün başlıkları: {product.competitor_titles}

SADECE aşağıdaki JSON formatında yanıt ver. Ek açıklama veya giriş cümlesi YAZMA:
{{
  "score": <4 kriterin toplamı, 0-100 arası tam sayı>,
  "missing_keywords": ["eksik kelime 1", "eksik kelime 2", "eksik kelime 3"],
  "competitor_keywords": ["rakip kelime 1", "rakip kelime 2", "rakip kelime 3"],
  "suggested_title": "<SEO ve GEO için optimize edilmiş, Türkçe yeniden yazılmış başlık>",
  "suggested_description_intro": "<Yapay zeka aramalarında üst sıralarda çıkacak, Türkçe açıklama girişi — 2 cümle, somut özellikler içermeli>"
}}

ZORUNLU: Tüm metin değerleri Türkçe olmalıdır."""

    @staticmethod
    def _strip_fences(text: str) -> str:
        m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        return m.group(1) if m else text

    def _extract_json(self, text: str) -> dict:
        text = self._strip_fences(text)
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("LLM yanıtında JSON bulunamadı")
        return json.loads(match.group())

    def _coerce_list(self, value: object) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("Liste beklendi")
        return [str(item) for item in value]

    def _parse_response(self, raw: str) -> GeoReport:
        try:
            data = self._extract_json(raw)
            score = max(0, min(100, int(data["score"])))
            return GeoReport(
                score=score,
                missing_keywords=self._coerce_list(data["missing_keywords"]),
                competitor_keywords=self._coerce_list(data["competitor_keywords"]),
                suggested_title=str(data["suggested_title"]),
                suggested_description_intro=str(data["suggested_description_intro"]),
            )
        except (ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("GEO yanıtı ayrıştırılamadı: %s", exc)
            return GeoReport(
                score=0,
                missing_keywords=[],
                competitor_keywords=[],
                suggested_title="",
                suggested_description_intro="",
            )
