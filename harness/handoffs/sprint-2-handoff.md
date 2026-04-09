# Sprint 2 Handoff: User Guide Screenshots (Part 1) — Workload Types

## What Was Built

### Doc Page Updates
- **`docs-site/docs/user-guide/getting-started.md`** — Added `getting-started-page.png` reference with descriptive alt text and italic caption
- **`docs-site/docs/user-guide/overview.md`** — Added `overview-page.png` reference with descriptive alt text and italic caption

### Validation Tests
- **`tests/docs_media/test_sprint2_guide_screenshots.py`** — 106 tests covering all 15 Sprint 2 screenshots:
  - `TestSprint2ScreenshotFiles` (46 tests): file existence, non-empty, reasonable size (10KB-2MB), count validation
  - `TestSprint2DocPageReferences` (45 tests): screenshot referenced in correct doc page, descriptive alt text (>=10 chars), italic caption present
  - `TestSprint2NoCustomerNames` (15 tests): no forbidden customer names ("Maya", "Merchant", "Commerci") in alt text or captions

### Contract
- **`harness/contracts/sprint-2.md`** — Updated to match spec (was previously about doc page rewrites, now correctly covers the 15 workload guide screenshots)

## Sprint 2 Screenshots (15 files in `docs-site/static/img/guides/`)

| # | File | Size | Doc Page | Status |
|---|------|------|----------|--------|
| 1 | `getting-started-page.png` | 186KB | getting-started.md | PASS |
| 2 | `overview-page.png` | 224KB | overview.md | PASS |
| 3 | `workloads-overview-page.png` | 246KB | overview.md | PASS |
| 4 | `dbsql-warehouses-guide.png` | 266KB | dbsql-warehouses.md | PASS |
| 5 | `dbsql-worked-example.png` | 193KB | dbsql-warehouses.md | PASS |
| 6 | `model-serving-guide.png` | 253KB | model-serving.md | PASS |
| 7 | `model-serving-worked-example.png` | 192KB | model-serving.md | PASS |
| 8 | `vector-search-guide.png` | 269KB | vector-search.md | PASS |
| 9 | `vector-search-worked-example.png` | 203KB | vector-search.md | PASS |
| 10 | `fmapi-databricks-guide.png` | 282KB | fmapi-databricks.md | PASS |
| 11 | `fmapi-databricks-worked-example.png` | 204KB | fmapi-databricks.md | PASS |
| 12 | `fmapi-proprietary-guide.png` | 277KB | fmapi-proprietary.md | PASS |
| 13 | `fmapi-proprietary-worked-example.png` | 197KB | fmapi-proprietary.md | PASS |
| 14 | `lakebase-guide.png` | 263KB | lakebase.md | PASS |
| 15 | `lakebase-worked-example.png` | 204KB | lakebase.md | PASS |

All screenshots passed Sprint 1 audit (no customer name violations, no overflow). They are screenshots of the Docusaurus documentation pages, not direct app UI.

## How to Test

```bash
cd "/Users/steven.tan/Desktop/Ent 1 - Q4 FY 2026 Team Project/lakemeter_app"

# Sprint 2 tests only
pytest tests/docs_media/test_sprint2_guide_screenshots.py -v

# Full test suite
pytest --tb=short

# Docs site build
cd docs-site && npm run build
```

## Test Results

- `pytest tests/docs_media/test_sprint2_guide_screenshots.py`: **106 passed** in 0.14s
- `pytest` (full suite): **2385 passed**, 2 skipped, 1 warning in 150s
- `npm run build` (docs-site): exit code 0, zero errors

## Known Limitations

- Screenshots are existing files from the initial docs setup. The Visual QA Agent should verify they are current with the live app and re-capture if needed for visual freshness.
- The `overview-page.png` screenshot shows the Overview documentation page itself (meta-screenshot). After doc content changes in future sprints, it may need re-capture to stay current.

## Files Changed

- `docs-site/docs/user-guide/getting-started.md` (added screenshot reference)
- `docs-site/docs/user-guide/overview.md` (added screenshot reference)
- `tests/docs_media/test_sprint2_guide_screenshots.py` (new — 106 tests)
- `harness/contracts/sprint-2.md` (updated to match spec)
