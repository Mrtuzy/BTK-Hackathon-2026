from abc import ABC, abstractmethod

import pandas as pd

from domain.entities import ActionItem, CorrelationReport, GeoReport, ProductData


class IProductScraper(ABC):
    @abstractmethod
    async def scrape(self, url: str) -> ProductData:
        """Never raises. Falls back to fixture on any failure."""


class ILanguageModel(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Returns raw text. Caller is responsible for parsing."""


class ICsvParser(ABC):
    @abstractmethod
    def parse_ads(self, content: bytes) -> pd.DataFrame:
        """Returns normalized ad DataFrame. Raises ValueError on unknown format."""

    @abstractmethod
    def parse_returns(self, content: bytes) -> pd.DataFrame:
        """Returns normalized returns DataFrame. Raises ValueError on unknown format."""
