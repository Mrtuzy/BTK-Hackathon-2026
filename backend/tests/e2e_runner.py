import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from adapters.outbound.csv_parser_factory import CsvParserFactory
from application.analysis_pipeline import AnalysisPipeline
from domain.entities import ProductData
from domain.ports import ILanguageModel, IProductScraper
from domain.services.action_service import ActionService
from domain.services.correlation_service import CorrelationService
from domain.services.geo_service import GeoAnalysisService

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture_product() -> ProductData:
    data = json.loads(
        (Path(__file__).parents[1]
        / "infrastructure"
        / "scraping"
        / "fixtures"
        / "trendyol_sample.json").read_text(encoding="utf-8")
    )
    return ProductData(
        title=data["title"],
        description=data["description"],
        price=data["price"],
        reviews=data["reviews"],
        competitor_titles=data["competitor_titles"],
        source="fixture",
    )


class FixtureScraper(IProductScraper):
    async def scrape(self, url: str) -> ProductData:
        return load_fixture_product()


class QueueLanguageModel(ILanguageModel):
    def __init__(self, responses: list[str]) -> None:
        self._responses = responses

    def generate(self, prompt: str) -> str:
        if not self._responses:
            return "{}"
        return self._responses.pop(0)


def build_pipeline(responses: list[str]) -> AnalysisPipeline:
    llm = QueueLanguageModel(responses)
    return AnalysisPipeline(
        scraper=FixtureScraper(),
        geo_service=GeoAnalysisService(llm=llm),
        correlation_service=CorrelationService(llm=llm),
        action_service=ActionService(llm=llm),
    )


def scenario_1() -> None:
    responses = [
        (
            "{\n"
            "  \"score\": 68,\n"
            "  \"missing_keywords\": [\"arazi\", \"EVA\"],\n"
            "  \"competitor_keywords\": [\"5mm drop\"],\n"
            "  \"suggested_title\": \"X-Run Arazi Kosu Ayakkabisi 280g EVA\",\n"
            "  \"suggested_description_intro\": \"Arazi kosulari icin 280g hafiflik sunar. EVA taban ile darbe emilimi saglar.\"\n"
            "}"
        ),
        (
            "[\n"
            "  {\"priority\": \"important\", \"title\": \"Basliga arazi ekle\", "
            "\"description\": \"Baslikta 'arazi' kelimesi yok.\", "
            "\"estimated_impact\": \"10-20% GEO artisi\", "
            "\"how_to_apply\": \"Basligi 'X-Run Arazi Kosu Ayakkabisi 280g EVA' olarak degistir.\"},\n"
            "  {\"priority\": \"improvement\", \"title\": \"EVA tabani vurgula\", "
            "\"description\": \"Aciklamaya EVA taban ifadesini ekle.\", "
            "\"estimated_impact\": \"5% GEO artisi\", "
            "\"how_to_apply\": \"Ilk cumleye 'EVA taban' ekle.\"},\n"
            "  {\"priority\": \"improvement\", \"title\": \"5mm drop ekle\", "
            "\"description\": \"Rakiplerde 5mm drop geciyor.\", "
            "\"estimated_impact\": \"3-7% GEO artisi\", "
            "\"how_to_apply\": \"Aciklamaya '5mm drop' ifadesini ekle.\"}\n"
            "]"
        ),
    ]
    pipeline = build_pipeline(responses)
    start = time.perf_counter()
    result = asyncio.run(pipeline.run("https://invalid.invalid", None, None))
    elapsed = time.perf_counter() - start

    action_text = " ".join(
        [
            f"{action.title} {action.description} {action.how_to_apply}"
            for action in result.actions
        ]
    ).lower()
    keyword_refs = [kw.lower() for kw in result.geo_report.missing_keywords]

    checks = {
        "geo_score_range": 0 <= result.geo_report.score <= 100,
        "actions_len": len(result.actions) >= 3,
        "action_references_missing_keyword": any(
            kw in action_text for kw in keyword_refs
        ),
        "return_rate_is_none": True,
        "ad_waste_pct_is_none": True,
        "used_fixture": result.used_fixture is True,
    }
    print("Scenario 1:", checks, f"time={elapsed:.3f}s")


def scenario_2() -> None:
    ad_csv = (FIXTURES_DIR / "google_ads_sample.csv").read_bytes()
    ad_df = CsvParserFactory().parse_ads(ad_csv)

    responses = [
        (
            "{\n"
            "  \"score\": 60,\n"
            "  \"missing_keywords\": [\"arazi\"],\n"
            "  \"competitor_keywords\": [\"EVA\"],\n"
            "  \"suggested_title\": \"X-Run Arazi Kosu Ayakkabisi 280g\",\n"
            "  \"suggested_description_intro\": \"Arazi kosulari icin 280g hafiflik sunar.\"\n"
            "}"
        ),
        (
            "{\n"
            "  \"high_return_keywords\": [\n"
            "    {\"keyword\": \"arazi kosu\", \"return_rate\": 0.45, \"spend\": 100.0, "
            "\"root_cause\": \"beden tablosu eksik\"}\n"
            "  ],\n"
            "  \"root_causes\": [\"beden tablosu eksik\"],\n"
            "  \"top_return_reason\": \"beden tablosu eksik\"\n"
            "}"
        ),
        (
            "[\n"
            "  {\"priority\": \"critical\", \"title\": \"Arazi kosu hedefini daralt\", "
            "\"description\": \"'arazi kosu' anahtar kelimesi geri donus riski tasiyor.\", "
            "\"estimated_impact\": \"20-30% harcama tasarrufu\", "
            "\"how_to_apply\": \"Google Ads'de 'arazi kosu' kelimesini negatif eslesmeye ekle.\"},\n"
            "  {\"priority\": \"important\", \"title\": \"Basliga arazi ekle\", "
            "\"description\": \"Baslikta 'arazi' kelimesi yok.\", "
            "\"estimated_impact\": \"10-20% GEO artisi\", "
            "\"how_to_apply\": \"Basligi 'X-Run Arazi Kosu Ayakkabisi 280g' yap.\"},\n"
            "  {\"priority\": \"improvement\", \"title\": \"EVA tabani belirt\", "
            "\"description\": \"Rakiplerde EVA taban vurgusu var.\", "
            "\"estimated_impact\": \"5% GEO artisi\", "
            "\"how_to_apply\": \"Aciklamaya 'EVA taban' ekle.\"}\n"
            "]"
        ),
    ]
    pipeline = build_pipeline(responses)
    start = time.perf_counter()
    result = asyncio.run(pipeline.run("https://invalid.invalid", ad_df, None))
    elapsed = time.perf_counter() - start

    action_text = " ".join(
        [
            f"{action.title} {action.description} {action.how_to_apply}"
            for action in result.actions
        ]
    ).lower()
    ad_keywords = [kw.lower() for kw in ad_df["keyword"].tolist()]
    has_priority = any(
        action.priority in {"critical", "important"} for action in result.actions
    )

    checks = {
        "ad_waste_pct_float": isinstance(
            result.correlation_report.wasted_spend_pct if result.correlation_report else None,
            float,
        ),
        "has_critical_or_important_action": has_priority,
        "action_references_ad_keyword": any(kw in action_text for kw in ad_keywords),
        "return_rate_is_none": True,
        "used_fixture": result.used_fixture is True,
    }
    print("Scenario 2:", checks, f"time={elapsed:.3f}s")


def scenario_3() -> None:
    ad_csv = (FIXTURES_DIR / "google_ads_sample.csv").read_bytes()
    returns_csv = (FIXTURES_DIR / "trendyol_returns_sample.csv").read_bytes()
    parser = CsvParserFactory()
    ad_df = parser.parse_ads(ad_csv)
    returns_df = parser.parse_returns(returns_csv)

    responses = [
        (
            "{\n"
            "  \"score\": 64,\n"
            "  \"missing_keywords\": [\"arazi\"],\n"
            "  \"competitor_keywords\": [\"5mm drop\"],\n"
            "  \"suggested_title\": \"X-Run Arazi Kosu Ayakkabisi 280g EVA\",\n"
            "  \"suggested_description_intro\": \"Arazi kosulari icin 280g hafiflik sunar.\"\n"
            "}"
        ),
        (
            "{\n"
            "  \"high_return_keywords\": [\n"
            "    {\"keyword\": \"arazi kosu\", \"return_rate\": 0.5, \"spend\": 100.0, "
            "\"root_cause\": \"beden tablosu eksik\"}\n"
            "  ],\n"
            "  \"root_causes\": [\"beden tablosu eksik\"],\n"
            "  \"top_return_reason\": \"beden tablosu eksik\"\n"
            "}"
        ),
        (
            "[\n"
            "  {\"priority\": \"critical\", \"title\": \"Beden tablosu ekle\", "
            "\"description\": \"Iadelerin ana sebebi 'beden tablosu eksik'.\", "
            "\"estimated_impact\": \"30-40% iade azalmasi\", "
            "\"how_to_apply\": \"Urun sayfasina beden tablosu gorseli ekle.\"},\n"
            "  {\"priority\": \"important\", \"title\": \"Arazi kosu hedefini daralt\", "
            "\"description\": \"'arazi kosu' kelimesi yuksek iade getiriyor.\", "
            "\"estimated_impact\": \"15-25% harcama tasarrufu\", "
            "\"how_to_apply\": \"Google Ads'de 'arazi kosu' kelimesini negatif eslesmeye ekle.\"},\n"
            "  {\"priority\": \"improvement\", \"title\": \"5mm drop ekle\", "
            "\"description\": \"Rakiplerde 5mm drop bilgisi var.\", "
            "\"estimated_impact\": \"3-7% GEO artisi\", "
            "\"how_to_apply\": \"Aciklamaya '5mm drop' ifadesini ekle.\"}\n"
            "]"
        ),
    ]
    pipeline = build_pipeline(responses)
    start = time.perf_counter()
    result = asyncio.run(pipeline.run("https://invalid.invalid", ad_df, returns_df))
    elapsed = time.perf_counter() - start

    total_returns = returns_df["quantity"].sum()
    total_clicks = ad_df["clicks"].sum()
    return_rate = float(total_returns / total_clicks) if total_clicks > 0 else None

    action_text = " ".join(
        [
            f"{action.title} {action.description} {action.how_to_apply}"
            for action in result.actions
        ]
    ).lower()
    return_reasons = [reason.lower() for reason in returns_df["return_reason"].tolist()]

    checks = {
        "wasted_spend_pct_gt_zero": (
            result.correlation_report.wasted_spend_pct if result.correlation_report else 0
        )
        > 0,
        "return_rate_float": isinstance(return_rate, float),
        "action_references_return_reason": any(
            reason in action_text for reason in return_reasons
        ),
        "used_fixture": result.used_fixture is True,
    }
    print("Scenario 3:", checks, f"time={elapsed:.3f}s")


if __name__ == "__main__":
    scenario_1()
    scenario_2()
    scenario_3()
