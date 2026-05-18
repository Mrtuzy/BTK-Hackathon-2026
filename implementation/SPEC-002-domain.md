# SPEC-002 — Domain Layer Services

Read CLAUDE.md first. Domain services must have zero imports from adapters, infrastructure, fastapi, langchain, or pandas. (Ports may import pandas for type hints as specified in CLAUDE.md/SPEC-001.)

## What to build

Implement the three domain services exactly as designed in CLAUDE.md.
Each service receives `ILanguageModel` via constructor — never instantiates adapters directly.

---

### GeoAnalysisService (`domain/services/geo_service.py`)

Full class structure from CLAUDE.md. Key implementation details:

**`_build_prompt`** — use the 4-criteria scoring prompt from CLAUDE.md verbatim. Include:
- `product.title`, `product.description`, `product.reviews[:5]`, `product.competitor_titles`

**`_extract_json(text: str) -> dict`:**
```python
import re, json

def _extract_json(self, text: str) -> dict:
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM response")
    return json.loads(match.group())
```

**`_parse_response(raw: str) -> GeoReport`:**
- Call `_extract_json`, catch `(ValueError, json.JSONDecodeError, KeyError)`
- On any failure: log warning, return `GeoReport(score=0, missing_keywords=[], competitor_keywords=[], suggested_title="", suggested_description_intro="")`
- Validate `score` is int 0–100: clamp with `max(0, min(100, data["score"]))`

---

### CorrelationService (`domain/services/correlation_service.py`)

**`_compute_stats(ad_df, returns_df) -> pd.DataFrame`:**
```python
# Case-insensitive keyword join
ad = ad_df.copy()
ad["keyword_lower"] = ad["keyword"].str.lower()

if returns_df is not None:
    ret = returns_df.copy()
    ret["keyword_lower"] = ret["keyword"].str.lower()
    merged = ad.merge(ret[["keyword_lower","quantity"]], on="keyword_lower", how="left")
else:
    merged = ad.copy()
    merged["quantity"] = 0

merged["return_quantity"] = merged["quantity"].fillna(0).astype(int)
merged["return_rate"] = (merged["return_quantity"] / merged["clicks"]).fillna(0.0)
return merged
```

**`_compute_wasted_spend_pct(stats: pd.DataFrame) -> float`:**
```python
high_risk = stats[stats["return_rate"] > 0.3]
total_spend = stats["spend"].sum()
return float(high_risk["spend"].sum() / total_spend) if total_spend > 0 else 0.0
```

**LLM prompt** — from CLAUDE.md. Pass only `stats.head(10).to_markdown()` and `product.description[:400]`.
Ask LLM to explain WHY, not to recompute numbers.

**`_parse_response`:** same `_extract_json` pattern. On failure: return `CorrelationReport(high_return_keywords=[], root_causes=[], wasted_spend_pct=computed_value, top_return_reason=None)` — note: `wasted_spend_pct` comes from Pandas, not LLM, so it's always correct even on LLM failure.

---

### ActionService (`domain/services/action_service.py`)

**`_sort_and_validate(actions: list[ActionItem]) -> list[ActionItem]`:**
```python
PRIORITY_ORDER = {"critical": 0, "important": 1, "improvement": 2}

def _sort_and_validate(self, actions):
    for a in actions:
        if a.priority not in self.VALID_PRIORITIES:
            a.priority = "improvement"
    return sorted(actions, key=lambda a: PRIORITY_ORDER[a.priority])
```

**`_fallback_action(geo: GeoReport) -> list[ActionItem]`:**
Returns a single `ActionItem` built from `geo.suggested_title` if available, otherwise a generic title improvement action. This is the last resort — never return an empty list.

**`_parse_response`:** `re.search(r'\[.*\]', raw, re.DOTALL)` to extract JSON array. On failure: call `_fallback_action`.

---

## Unit tests (`tests/test_domain_services.py`)

Use a `MockLanguageModel(ILanguageModel)` that returns a hardcoded valid JSON string.

Test cases:
- `GeoAnalysisService.analyze()` with valid LLM response → `GeoReport` with correct score
- `GeoAnalysisService.analyze()` with LLM returning plain text (no JSON) → default `GeoReport(score=0, ...)`
- `CorrelationService._compute_wasted_spend_pct()` with known data → correct float
- `CorrelationService.analyze()` with `returns_df=None` → `CorrelationReport` with `wasted_spend_pct=0.0`
- `ActionService._sort_and_validate()` with mixed priorities → sorted correctly
- `ActionService._sort_and_validate()` with invalid priority `"urgent"` → changed to `"improvement"`
- `ActionService.generate()` with LLM returning invalid JSON → returns fallback action (non-empty list)

## Done when

- All three services instantiable with `MockLanguageModel`
- `from domain.services.geo_service import GeoAnalysisService` → no ImportError from adapters/infra
- All unit tests pass
- `domain/services/` has zero imports from `adapters/`, `infrastructure/`, `fastapi`, `langchain`, `pandas` (grep check)
