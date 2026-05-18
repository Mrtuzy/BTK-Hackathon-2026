# TASKS.md — doThis

Give Claude: CLAUDE.md + the active SPEC file. Nothing else needed.
Mark tasks done with [x] as you go.

---

## Build Order

```
SPEC-001 → SPEC-002 → SPEC-003 → SPEC-004 → SPEC-005 → SPEC-006
 Setup      Domain     Infra       Pipeline    Full        Frontend
            Layer      Adapters    Wiring      E2E
```

SPEC-002 and SPEC-003 can be built in parallel — no dependency between them.

---

## SPEC-001 — Project Setup
- [x] Full folder structure per CLAUDE.md
- [x] `main.py` — FastAPI + CORS + DI wiring (stubs for now)
- [x] `config.py` — env vars only
- [x] `domain/entities.py` — all dataclasses
- [x] `domain/ports.py` — IProductScraper, ILanguageModel, ICsvParser
- [x] `application/pipeline_state.py` — PipelineState TypedDict
- [x] `application/dto.py` — AnalyzeRequest, AnalyzeResponse
- [x] Stub `GET /health` → `{"status":"ok","version":"1.0.0"}`
- [x] Stub `POST /api/analyze` → `{"status":"not implemented"}`
- [x] `requirements.txt`
- [x] `Dockerfile`
- [x] Next.js scaffold + blank pages + `lib/api.ts`
- [x] ✅ `GET /health` → 200, `npm run build` → 0 errors

---

## SPEC-002 — Domain Layer
- [x] `domain/services/geo_service.py` — GeoAnalysisService
- [x] `domain/services/correlation_service.py` — CorrelationService
- [x] `domain/services/action_service.py` — ActionService
- [x] Unit tests with mock ILanguageModel returning fixture JSON
- [x] ✅ All services instantiable with a mock ILanguageModel, no infrastructure imports

---

## SPEC-003 — Infrastructure Adapters
- [x] `infrastructure/scraping/fixtures/trendyol_sample.json` (10+ reviews)
- [x] `infrastructure/scraping/fixtures/hepsiburada_sample.json`
- [x] `adapters/outbound/playwright_scraper.py` — implements IProductScraper
- [x] `adapters/outbound/gemini_language_model.py` — implements ILanguageModel
- [x] `infrastructure/parsers/base_ad_parser.py` — BaseAdParser ABC
- [x] `infrastructure/parsers/google_ads_parser.py`
- [x] `infrastructure/parsers/meta_ads_parser.py`
- [x] `infrastructure/parsers/trendyol_parser.py` (ads + returns)
- [x] `adapters/outbound/csv_parser_factory.py` — implements ICsvParser
- [x] ✅ Invalid URL → fixture, no crash. 4 CSV formats parse correctly.

---

## SPEC-004 — Pipeline Wiring
- [x] `application/analysis_pipeline.py` — AnalysisPipeline with LangGraph
- [x] `adapters/inbound/analyze_controller.py` — AnalyzeController
- [x] `main.py` — full DI wiring (real adapters, not stubs)
- [x] ✅ `POST /api/analyze` with URL → full AnalyzeResponse (geo_score, actions)

---

## SPEC-005 — Full E2E + Prompt Tuning
- [x] Test URL only → actions list non-empty, return_rate null
- [x] Test URL + Google Ads CSV → at least 1 critical/important action referencing a keyword
- [x] Test URL + all CSVs → wasted_spend_pct > 0, actions reference return data
- [x] Tune prompts if output is generic or unparseable
- [x] ✅ Pipeline completes ≤15s fixture, ≤45s live

---

## SPEC-006 — Frontend
- [ ] UrlInput, CsvUpload, AgentProgress, MetricCard, ActionItem, ActionList components
- [ ] Input screen (page.tsx)
- [ ] Results screen (analyze/page.tsx)
- [ ] Loading overlay + error states
- [ ] "Demo modu" badge when used_fixture=true
- [ ] ✅ `npm run build` → 0 errors, full UI renders with mock response
