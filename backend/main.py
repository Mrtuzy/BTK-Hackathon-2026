from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adapters.inbound.analyze_controller import AnalyzeController
from adapters.outbound.csv_parser_factory import CsvParserFactory
from adapters.outbound.gemini_competitor_searcher import GeminiCompetitorSearcher
from adapters.outbound.gemini_language_model import GeminiLanguageModel
from adapters.outbound.playwright_scraper import PlaywrightScraper
from application.analysis_pipeline import AnalysisPipeline
from config import config
from domain.services.action_service import ActionService
from domain.services.correlation_service import CorrelationService
from domain.services.geo_service import GeoAnalysisService

app = FastAPI(title="doThis API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://dothis.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compose infrastructure
scraper = PlaywrightScraper(headless=config.playwright_headless)
llm = GeminiLanguageModel(api_key=config.gemini_api_key)
csv_parser = CsvParserFactory()
competitor_searcher = GeminiCompetitorSearcher(api_key=config.gemini_api_key)

# Inject into domain services
geo_service = GeoAnalysisService(llm=llm)
correlation_service = CorrelationService(llm=llm)
action_service = ActionService(llm=llm)

# Compose application pipeline
pipeline = AnalysisPipeline(
    scraper=scraper,
    llm=llm,
    geo_service=geo_service,
    correlation_service=correlation_service,
    action_service=action_service,
    competitor_searcher=competitor_searcher,
)

# Wire inbound adapter
controller = AnalyzeController(pipeline=pipeline, csv_parser=csv_parser)
app.include_router(controller.router)


@app.get("/health")
def health() -> dict:
    """Return service status."""
    return {"status": "ok", "version": "1.0.0"}
