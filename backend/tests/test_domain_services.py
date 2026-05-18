import unittest

import pandas as pd

from domain.entities import ActionItem, GeoReport, ProductData
from domain.ports import ILanguageModel
from domain.services.action_service import ActionService
from domain.services.correlation_service import CorrelationService
from domain.services.geo_service import GeoAnalysisService


class MockLanguageModel(ILanguageModel):
    def __init__(self, response: str) -> None:
        self._response = response

    def generate(self, prompt: str) -> str:
        return self._response


class GeoAnalysisServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.product = ProductData(
            title="Trail Running Shoe 280g",
            description="Lightweight trail shoe with EVA foam and 5mm drop.",
            price="$120",
            reviews=["Great grip"],
            competitor_titles=["Trail shoe 260g"],
            source="fixture",
        )

    def test_analyze_with_valid_json(self) -> None:
        response = (
            "{\n"
            "  \"score\": 80,\n"
            "  \"missing_keywords\": [\"grip\"],\n"
            "  \"competitor_keywords\": [\"trail\"],\n"
            "  \"suggested_title\": \"Trail Running Shoe 280g Grip\",\n"
            "  \"suggested_description_intro\": \"A lightweight trail shoe.\"\n"
            "}"
        )
        service = GeoAnalysisService(MockLanguageModel(response))
        report = service.analyze(self.product)
        self.assertEqual(report.score, 80)
        self.assertEqual(report.missing_keywords, ["grip"])

    def test_analyze_with_invalid_json(self) -> None:
        service = GeoAnalysisService(MockLanguageModel("no json"))
        report = service.analyze(self.product)
        self.assertEqual(report.score, 0)
        self.assertEqual(report.missing_keywords, [])


class CorrelationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.product = ProductData(
            title="Yoga Mat",
            description="Non-slip mat, 6mm thickness, TPE material.",
            price="$35",
            reviews=[],
            competitor_titles=[],
            source="fixture",
        )

    def test_compute_wasted_spend_pct(self) -> None:
        stats = pd.DataFrame(
            {"return_rate": [0.4, 0.1], "spend": [100.0, 50.0]}
        )
        service = CorrelationService(MockLanguageModel("{}"))
        wasted = service._compute_wasted_spend_pct(stats)
        self.assertAlmostEqual(wasted, 100.0 / 150.0)

    def test_analyze_without_returns(self) -> None:
        ad_df = pd.DataFrame(
            {
                "keyword": ["yoga", "mat"],
                "clicks": [10, 5],
                "spend": [100.0, 50.0],
            }
        )
        response = (
            "{\n"
            "  \"high_return_keywords\": [],\n"
            "  \"root_causes\": [],\n"
            "  \"top_return_reason\": null\n"
            "}"
        )
        service = CorrelationService(MockLanguageModel(response))
        report = service.analyze(ad_df, None, self.product)
        self.assertEqual(report.wasted_spend_pct, 0.0)


class ActionServiceTests(unittest.TestCase):
    def test_sort_and_validate(self) -> None:
        service = ActionService(MockLanguageModel("[]"))
        actions = [
            ActionItem(
                priority="important",
                title="B",
                description="",
                estimated_impact="",
                how_to_apply="",
            ),
            ActionItem(
                priority="critical",
                title="A",
                description="",
                estimated_impact="",
                how_to_apply="",
            ),
            ActionItem(
                priority="urgent",
                title="C",
                description="",
                estimated_impact="",
                how_to_apply="",
            ),
        ]
        sorted_actions = service._sort_and_validate(actions)
        self.assertEqual(sorted_actions[0].priority, "critical")
        self.assertEqual(sorted_actions[-1].priority, "improvement")

    def test_generate_with_invalid_json_returns_fallback(self) -> None:
        service = ActionService(MockLanguageModel("no json"))
        product = ProductData(
            title="Bottle",
            description="Stainless steel bottle 750ml",
            price="$20",
            reviews=[],
            competitor_titles=[],
            source="fixture",
        )
        geo = GeoReport(
            score=0,
            missing_keywords=[],
            competitor_keywords=[],
            suggested_title="Bottle 750ml stainless",
            suggested_description_intro="",
        )
        actions = service.generate(product, geo, None)
        self.assertTrue(len(actions) > 0)


if __name__ == "__main__":
    unittest.main()
