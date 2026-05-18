# SPEC-001 — Project Setup

Read CLAUDE.md first. Follow the folder structure, entity definitions, and port interfaces exactly.

## What to build

### Backend skeleton

**`domain/entities.py`**
All dataclasses from CLAUDE.md: `ProductData`, `GeoReport`, `CorrelationReport`, `ActionItem`, `AnalysisResult`.
No imports outside stdlib and `dataclasses`. Domain is pure Python.

**`domain/ports.py`**
Three abstract base classes from CLAUDE.md: `IProductScraper`, `ILanguageModel`, `ICsvParser`.
Import only `abc`, `pandas`, and `domain.entities`.

**`application/pipeline_state.py`**
`PipelineState` TypedDict from CLAUDE.md.

**`application/dto.py`**
```python
@dataclass
class AnalyzeRequest:
    url: str
    ad_csv_content: bytes | None
    returns_csv_content: bytes | None

@dataclass
class AnalyzeResponse:
    geo_score: int
    return_rate: float | None
    ad_waste_pct: float | None
    actions: list[ActionItem]
    used_fixture: bool
```

**`config.py`**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gemini_api_key: str
    playwright_headless: bool = True

    class Config:
        env_file = ".env"

config = Settings()
```

**`main.py`** — stub only for now:
```python
app = FastAPI(title="doThis API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "https://dothis.vercel.app"], ...)

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

@app.post("/api/analyze")
async def analyze():
    return {"status": "not implemented"}
```

**`requirements.txt`:**
`fastapi uvicorn[standard] pydantic pydantic-settings python-dotenv pandas langchain langgraph langchain-google-genai playwright`

**`Dockerfile`:** Python 3.11-slim, `pip install -r requirements.txt`, `playwright install --with-deps chromium`, `CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]`

**`.env.example`:** `GEMINI_API_KEY=your_key_here` and `PLAYWRIGHT_HEADLESS=true`

### Frontend skeleton

- `npx create-next-app@latest frontend --typescript --tailwind --app`
- `app/page.tsx`: `<h1>doThis</h1>` placeholder
- `app/analyze/page.tsx`: `<h1>Results</h1>` placeholder
- `lib/api.ts`: full `AnalyzeRequest`, `AnalyzeResponse`, `ActionItem` types + `analyze()` fetch function per CLAUDE.md API contract
- `.env.local.example`: `NEXT_PUBLIC_API_URL=http://localhost:8000`
- `README.md`: how to run both services locally

## Done when

- `GET /health` → `{"status":"ok","version":"1.0.0"}`
- `POST /api/analyze` → `{"status":"not implemented"}`
- `from domain.ports import ILanguageModel` → no ImportError
- `from domain.entities import ActionItem` → no ImportError
- `npm run build` → zero TypeScript errors
- `docker build -t dothis-backend .` → exits 0
