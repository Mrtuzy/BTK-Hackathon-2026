import logging
import re
import time

from google import genai
from google.api_core.exceptions import ResourceExhausted

from domain.ports import ILanguageModel

logger = logging.getLogger(__name__)


class GeminiLanguageModel(ILanguageModel):
    MAX_RETRIES = 2
    RETRY_DELAY = 30.0

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate(self, prompt: str) -> str:
        """Calls Gemini. Retries on 429. Raises RuntimeError after max retries."""
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
            except ResourceExhausted as exc:
                if attempt < self.MAX_RETRIES:
                    delay = self._parse_retry_delay(str(exc)) or self.RETRY_DELAY
                    logger.warning(
                        "Gemini rate limit hit. Retry %s/%s in %.0fs",
                        attempt + 1,
                        self.MAX_RETRIES,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    raise RuntimeError("Gemini rate limit exceeded after max retries") from exc

    @staticmethod
    def _parse_retry_delay(message: str) -> float | None:
        """Extract suggested retry delay in seconds from the error message."""
        match = re.search(r"retry in (\d+(?:\.\d+)?)\s*s", message, re.IGNORECASE)
        return float(match.group(1)) if match else None
