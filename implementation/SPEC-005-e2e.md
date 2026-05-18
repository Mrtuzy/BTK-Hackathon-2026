# SPEC-005 — Full E2E + Prompt Tuning

Read CLAUDE.md first. This spec is about verifying the full pipeline and refining prompt output quality — not adding new structure.

## What to verify

Run the following scenarios and confirm output quality. If actions are generic or LLM responses fail to parse, tune prompts per the rules below.

---

### Scenario 1 — URL only (no CSVs)
Input: fixture URL (e.g. a non-existent URL so fixture activates)
Expected:
- `geo_score` between 0–100
- `actions` list has ≥3 items
- At least one action references a specific word from `suggested_title` or `missing_keywords`
- `return_rate = null`, `ad_waste_pct = null`
- `used_fixture = true`

### Scenario 2 — URL + Google Ads CSV
Input: fixture URL + `google_ads_sample.csv` from tests/fixtures/
Expected:
- At least 1 action with `priority = "critical"` or `"important"`
- That action's `how_to_apply` references a specific keyword from the CSV
- `ad_waste_pct` is a float > 0 (assuming sample CSV has some low-conversion keywords)

### Scenario 3 — URL + all CSVs
Input: fixture URL + both CSVs
Expected:
- `wasted_spend_pct > 0`
- At least 1 action references a return reason from `trendyol_returns_sample.csv`
- `return_rate` is a float

### Scenario 4 — Performance
- Fixture path: full pipeline ≤ 15 seconds
- Live scrape path: full pipeline ≤ 45 seconds

---

## Prompt tuning rules (if output is poor)

**If actions are generic ("improve your title", "add keywords"):**
Add to the ActionService prompt:
```
BAD example (do not generate): "Improve your product title to include more keywords."
GOOD example: "Replace 'Erkek Spor Ayakkabı' with 'Erkek Parkur Koşu Ayakkabısı 280gr' — this exact phrase appears in 3 of your top 5 competitor titles."
```

**If JSON extraction fails frequently:**
Add to every prompt before the JSON schema:
```
Important: respond with raw JSON only. Do not use markdown code blocks. Do not write any text before or after the JSON.
```

**If GEO scores are inconsistently distributed (all 70+, all 30-):**
Recalibrate the 4-criteria description — make the bar for each 25-point block more concrete with examples.

**If correlation root causes are vague:**
Add to CorrelationService prompt: "Each root_cause must be a single sentence that directly quotes or paraphrases a word from the product description above."

---

## Done when

All 4 scenarios pass. Actions are product-specific (reference actual data, not generic advice). Pipeline meets performance targets.
