import logging
import re
import time

from google import genai
from google.genai.errors import ClientError, ServerError

from domain.ports import ILanguageModel

logger = logging.getLogger(__name__)


class GeminiLanguageModel(ILanguageModel):
    MAX_RETRIES = 4
    RETRY_DELAY = 20.0

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    @property
    def model(self) -> str:
        """Active Gemini model name."""
        return self._model

    @model.setter
    def model(self, value: str) -> None:
        self._model = value

    def generate(self, prompt: str) -> str:
        """Calls Gemini. Retries on 429/503. Hard-fails on exhausted quota."""
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                logger.debug("Gemini prompt length: %s chars", len(prompt))
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=prompt,
                )
                text = response.text
                logger.debug("Gemini response length: %s chars", len(text))
                return text
            except (ClientError, ServerError) as exc:
                status = getattr(exc, "status_code", 0)
                msg = str(exc)

                # Hard quota exhaustion (free tier limit=0) — retrying won't help
                if status == 429 and "limit: 0" in msg:
                    raise RuntimeError(
                        "Gemini API kotası tükendi. Lütfen farklı bir model seçin "
                        "veya API kotanızı kontrol edin."
                    ) from exc

                # Retryable: rate-limit (429) or temporary overload (503)
                if status in (429, 503) and attempt < self.MAX_RETRIES:
                    delay = self._parse_retry_delay(msg) or self.RETRY_DELAY
                    logger.warning(
                        "Gemini geçici hata %s. Retry %s/%s, %.0fs bekleniyor.",
                        status,
                        attempt + 1,
                        self.MAX_RETRIES,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    raise RuntimeError(f"Gemini isteği başarısız: {exc}") from exc

    @staticmethod
    def _parse_retry_delay(message: str) -> float | None:
        """Extract suggested retry delay in seconds from the error message."""
        match = re.search(r"retry in (\d+(?:\.\d+)?)\s*s", message, re.IGNORECASE)
        return float(match.group(1)) if match else None
