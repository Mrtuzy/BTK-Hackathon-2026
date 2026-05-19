import logging

from google import genai
from google.genai import types

from domain.ports import ICompetitorSearcher

logger = logging.getLogger(__name__)


class GeminiCompetitorSearcher(ICompetitorSearcher):
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def search(self, product_title: str, platform_hint: str) -> str:
        """Search for competitors using Gemini's Google Search grounding. Never raises."""
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=self._build_prompt(product_title, platform_hint),
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                ),
            )
            return (response.text or "").strip()
        except Exception as exc:
            logger.warning("Competitor search failed: %s", exc)
            return ""

    def _build_prompt(self, product_title: str, platform_hint: str) -> str:
        return (
            f"Türk e-ticaret platformunda ({platform_hint}) şu ürünün rakiplerini Google'da ara ve analiz et:\n"
            f"Ürün: {product_title}\n\n"
            "Gerçek rakip ürünleri bul ve şunları özetle:\n"
            "1. Rakipler başlıklarında hangi anahtar kelimeleri kullanıyor? (bu ürün kullanmıyor)\n"
            "2. Lider rakip bu üründen nasıl farklılaşıyor? (özellik, fiyat, ambalaj)\n"
            "3. Rakiplerin öne çıkardığı 2-3 somut avantaj nedir?\n\n"
            "Türkçe, maksimum 5 cümle. Her cümle 'Rakipler...' veya 'Lider rakip...' ile başlasın. "
            "Sadece düz metin yaz, madde işareti veya başlık kullanma."
        )
