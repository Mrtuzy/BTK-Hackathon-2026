# doThis

Profit leak detector for e-commerce sellers.

doThis analyzes a product URL plus optional ad and returns CSVs to answer:
- Why the listing is invisible in AI search (GEO score)
- Which ad keywords burn budget (ad x returns correlation)
- What to do next (prioritized action list)

## Tech Stack
- Frontend: Next.js (App Router), TypeScript, Tailwind CSS
- Backend: Python 3.11, FastAPI, LangGraph + LangChain
- AI model: Gemini 2.0 Flash only
- Scraping: Playwright (async) with JSON fixtures fallback
- Data: Stateless (no database)

## Local Development

### Backend (FastAPI)
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload
```

### Frontend (Next.js)
```bash
cd frontend
npm install
```

Create a frontend/.env.local file:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Start the UI:
```bash
npm run dev
```

## API
POST /api/analyze (multipart/form-data)
- url: string (required)
- ad_csv: file (optional)
- returns_csv: file (optional)

GET /health -> {"status":"ok","version":"1.0.0"}

## Project Structure
```
backend/         FastAPI app, domain, adapters
frontend/        Next.js UI
implementation/  Specs and implementation notes
test-data/       Sample CSV fixtures
```

## Notes
- Playwright scraping falls back to cached JSON fixtures on failure.
- All analysis is session-scoped; data is not stored.
