# Integration Test Report 2 — Full Regression (Sprints 1–5)

**Date**: 2026-04-04
**Quality Target**: 9.0/10
**Sprints Covered**: 1 (Screenshot Audit), 2 (Workload Screenshots), 3 (Admin Screenshots), 4 (Workflow GIFs), 5 (Tutorial Video + Embeds)

---

## Feature Dependency Matrix

| Source (Sprint) | Target (Sprint) | Data Flow | Status |
|----------------|-----------------|-----------|--------|
| S1: Screenshot Audit | S2: Guide Screenshots | Audit identified screenshots needing re-capture; S2 validates against audit criteria | PASS |
| S1: Screenshot Audit | S3: Admin Screenshots | Same audit criteria applied to admin guide screenshots | PASS |
| S1: Directory Setup | S4: Workflow GIFs | S1 created `docs-site/static/img/gifs/` directory; S4 writes GIFs there | PASS |
| S1: Directory Setup | S5: Tutorial Video | S1 created `docs-site/static/video/` directory; S5 writes MP4 there | PASS |
| S1: Test Fixes | All Sprints | S1 fixed broken path references in integration validation tests; all subsequent sprint tests depend on these | PASS |
| S2: Doc Page References | S5: GIF Embeds | S2 added screenshot refs to getting-started.md and overview.md; S5 adds GIF embeds to same pages | PASS |
| S4: GIF Files | S5: GIF Embeds | S4 created 6 GIFs; S5 embeds them in 7 doc pages across 6 files | PASS |
| S5: Video File | S5: Video Embeds | MP4 exists; `<video>` tags in getting-started.md and end-to-end-workflow.md reference it | PASS |
| All Sprints | Docs Build | All 72 image/GIF/video references resolve during `npm run build` (zero errors) | PASS |

---

## Regression Sweep

### Sprint 1 Acceptance Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Audit report exists at `harness/audit/screenshot-audit-report.md` | PASS | File present |
| Capture checklist at `harness/audit/capture-checklist.md` | PASS | File present |
| GIF/video directory structure created | PASS | Both dirs exist with `.gitkeep` |
| `test_workload_coverage.py` fixed (no sprint_N paths) | PASS | 180+ integration validation tests pass |
| `test_suite_completeness.py` fixed | PASS | Passes in integration validation suite |
| `test_regression_s10.py` path fixes (3 relative paths) | PASS | Passes in regression suite |
| `test_jobs_bugs.py` path fix | PASS | Passes in regression suite |
| Full pytest passes | PASS | 2628 passed, 0 failed |
| `npm run build`: zero errors | PASS | Build successful |

### Sprint 2 Acceptance Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| 15 workload guide screenshots exist | PASS | All 15 in `static/img/guides/` (186–282KB) |
| `getting-started.md` updated with screenshot reference | PASS | Reference + alt text + caption verified |
| `overview.md` updated with screenshot reference | PASS | Reference + alt text + caption verified |
| No customer name violations in alt text/captions | PASS | 15 sanitization tests pass |
| 106 Sprint 2 validation tests pass | PASS | All 106 pass in 0.11s |

### Sprint 3 Acceptance Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| 8 user guide Part 2 screenshots exist | PASS | ai-assistant, export, calculation, faq — all present |
| 8 admin guide screenshots exist | PASS | deployment, configuration, api-reference, architecture, database (x2), permissions, troubleshooting |
| All 16 referenced in correct doc pages with alt text + captions | PASS | 48 reference + 48 caption tests pass |
| No customer name violations | PASS | 16 sanitization tests pass |
| 113 Sprint 3 validation tests pass | PASS | All 113 pass in 0.11s |

### Sprint 4 Acceptance Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| 6 GIF files exist in `static/img/gifs/` | PASS | creating-estimate, adding-workload, drag-and-drop, ai-assistant, export-excel, cost-summary |
| GIF format: GIF89a, multi-frame, 800px wide | PASS | All 6 validated via magic bytes and format tests |
| GIF size: >50KB and <5MB each | PASS | Range: 51–69KB |
| Kebab-case naming | PASS | All 6 follow convention |
| No forbidden customer names | PASS | 12 naming tests pass |
| 63 Sprint 4 validation tests pass | PASS | All 63 pass in 0.12s |

### Sprint 5 Acceptance Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Tutorial video MP4 exists at `static/video/getting-started-tutorial.mp4` | PASS | 5.7KB placeholder with valid ftyp header |
| 7 GIF embeds across 6 doc pages | PASS | All embeds verified with correct `![...]` syntax |
| 2 video embeds (getting-started + e2e workflow) | PASS | Both `<video>` tags present with controls, aria-label, source, fallback |
| No forbidden names in new content | PASS | 7 sanitization tests pass |
| 49 Sprint 5 validation tests pass | PASS | All 49 pass in 0.10s |

**Regression count: 0 regressions across all 5 sprints.**

---

## Cross-Feature Test Results

### Image Reference Integrity
- **72 total image references** across 39 doc files (up from 65 after Sprint 5 GIF/video embeds)
- **0 broken references** — every `![...](/img/...)` path resolves to an existing file
- **7 GIF embeds** across 6 doc pages — all resolve to valid GIF89a files
- **2 video embeds** — both resolve to valid MP4 file

### Data Sanitization (Cross-Sprint)
- Grepped all docs for forbidden names ("Maya", "Merchant", "Commerci" as customer name)
- **0 violations** — grep hits were false positives from "commercial" in FMAPI docs
- All GIF alt text and video aria-labels use sanitized references only

### Media Format Validation
- **8 core PNGs**: 47–444KB (healthy range)
- **31 guide PNGs**: 128–282KB (healthy range)
- **6 GIFs**: valid GIF89a, multi-frame, 800px wide, 51–69KB each
- **1 MP4**: valid ftyp container, 5.7KB placeholder
- **0 empty media files** (only `.gitkeep` files are empty)

### Docs Site Build
- `npm run build`: **SUCCESS** — zero errors
- `onBrokenLinks: 'throw'` config active — broken links would cause build failure

---

## User Journey: Documentation Reader

| Step | Page | Media Present | Status |
|------|------|--------------|--------|
| 1. Landing | `intro.md` | calculator-overview.png | PASS |
| 2. Getting Started | `getting-started.md` | creating-estimate GIF + tutorial video + screenshots | PASS |
| 3. Overview | `overview.md` | cost-summary GIF + screenshots | PASS |
| 4. DBSQL Warehouses | `dbsql-warehouses.md` | guide + worked example screenshots | PASS |
| 5. Model Serving | `model-serving.md` | guide + worked example screenshots | PASS |
| 6. Vector Search | `vector-search.md` | guide + worked example screenshots | PASS |
| 7. FMAPI Databricks | `fmapi-databricks.md` | guide + worked example screenshots | PASS |
| 8. FMAPI Proprietary | `fmapi-proprietary.md` | guide + worked example screenshots | PASS |
| 9. Lakebase | `lakebase.md` | guide + worked example screenshots | PASS |
| 10. AI Assistant | `ai-assistant.md` | ai-assistant GIF + guide + tools screenshots | PASS |
| 11. Creating Estimates | `creating-estimates.md` | creating-estimate GIF + drag-and-drop GIF + screenshots | PASS |
| 12. Exporting | `exporting.md` | export-excel GIF + guide + excel-structure screenshots | PASS |
| 13. Workloads | `workloads.md` | adding-workload GIF | PASS |
| 14. End-to-End Workflow | `end-to-end-workflow.md` | tutorial video embed | PASS |
| 15. Admin Guides (7 pages) | `admin-guide/*.md` | 8 admin screenshots across 7 pages | PASS |

---

## Edge Case Results

| Edge Case | Status | Notes |
|-----------|--------|-------|
| Empty/zero-byte media files | PASS | Only `.gitkeep` files are empty |
| GIF magic byte validation | PASS | All 6 are valid GIF89a |
| MP4 magic byte validation | PASS | Valid ftyp box header |
| Orphaned images | INFO | `docusaurus.png` (Docusaurus default) and `login-page.png` (noted in S1 as acceptable) unreferenced |
| Duplicate image references | PASS | `calculator-overview.png` used 12x across docs (intentional) |
| Cross-sprint GIF reuse | PASS | `creating-estimate.gif` in both getting-started.md and creating-estimates.md (intentional) |
| Customer name false positives | PASS | "commerci" matches are "commercial" in FMAPI docs, not customer names |
| Video placeholder content | INFO | Tutorial video is valid MP4 container but placeholder (5.7KB) — needs real recording |
| Cross-page consistency | PASS | Same GIF used on multiple pages renders correctly in build |

---

## Test Suite Summary

| Test Suite | Passed | Skipped | Failed | Duration |
|------------|--------|---------|--------|----------|
| **Full pytest** | **2628** | 2 | **0** | 152.51s |
| Sprint 1 (audit + docs build) | 57 | 0 | 0 | 2.21s |
| Sprint 2 (guide screenshots) | 106 | 0 | 0 | 0.11s |
| Sprint 3 (screenshots P2 + admin) | 113 | 0 | 0 | 0.11s |
| Sprint 4 (workflow GIFs) | 63 | 0 | 0 | 0.12s |
| Sprint 5 (video + embeds) | 49 | 0 | 0 | 0.10s |
| Integration validation | 96 | 0 | 0 | — |
| Regression tests | 240 | 0 | 0 | 62.43s |
| **Docs site build** | — | — | **0** | ~5s |

---

## Notes

1. **Tutorial video is a placeholder** — valid MP4 container but no actual video content (5.7KB). Sprint 5 handoff notes this as expected. A real screen recording needs to replace it.
2. **Two orphaned images** — `docusaurus.png` (Docusaurus default, harmless) and `login-page.png` (Sprint 1 noted as acceptable). Neither referenced in docs.
3. **GIFs are programmatic mockups** — generated via Pillow, not live app captures. Sprint 4 handoff notes this. They accurately represent UI workflows but may diverge if app UI changes.

---

## Verdict: PASS

All cross-feature data flows work correctly. **Zero regressions** across all 5 sprints. **2628 tests pass** with 0 failures. Docs site builds cleanly with all 72 image/GIF/video references resolving. No customer name violations. The full documentation media pipeline (audit → screenshots → doc references → GIF creation → GIF/video embeds → docs build) is fully integrated and functional.
