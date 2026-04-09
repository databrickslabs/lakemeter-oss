# Sprint 2 Contract: User Guide Screenshots (Part 1) — Workload Types

## Scope

Re-capture 15 guide screenshots for workload type doc pages. Verify all doc pages reference them correctly with accurate alt text and captions. Write validation tests.

## Acceptance Criteria

### Screenshot Files (15 files in `docs-site/static/img/guides/`)

- [ ] `getting-started-page.png` exists and is non-empty
- [ ] `overview-page.png` exists and is non-empty
- [ ] `workloads-overview-page.png` exists and is non-empty
- [ ] `dbsql-warehouses-guide.png` exists and is non-empty
- [ ] `dbsql-worked-example.png` exists and is non-empty
- [ ] `model-serving-guide.png` exists and is non-empty
- [ ] `model-serving-worked-example.png` exists and is non-empty
- [ ] `vector-search-guide.png` exists and is non-empty
- [ ] `vector-search-worked-example.png` exists and is non-empty
- [ ] `fmapi-databricks-guide.png` exists and is non-empty
- [ ] `fmapi-databricks-worked-example.png` exists and is non-empty
- [ ] `fmapi-proprietary-guide.png` exists and is non-empty
- [ ] `fmapi-proprietary-worked-example.png` exists and is non-empty
- [ ] `lakebase-guide.png` exists and is non-empty
- [ ] `lakebase-worked-example.png` exists and is non-empty

### Doc Page References

- [ ] Each of the 15 screenshots is referenced in its corresponding doc page
- [ ] All image references have descriptive, accurate alt text (not generic)
- [ ] All image references have caption text (italic line below the image)
- [ ] `getting-started.md` references `getting-started-page.png`
- [ ] `overview.md` references `overview-page.png`
- [ ] No customer names appear in alt text or captions

### Validation Tests

- [ ] `tests/docs_media/test_sprint2_guide_screenshots.py` validates all 15 screenshots
- [ ] Tests verify: file existence, non-empty, reasonable size, doc page references
- [ ] Tests verify: alt text quality (non-empty, descriptive, no customer names)
- [ ] Tests verify: caption text exists for each screenshot

### Build

- [ ] `cd docs-site && npm run build` succeeds with zero errors
- [ ] Full `pytest` suite passes

## Test Plan

- `pytest tests/docs_media/` — all Sprint 2 tests pass
- `pytest` — full suite passes (2275+ tests)
- `cd docs-site && npm run build` — zero errors

## Files to Change

- `docs-site/docs/user-guide/getting-started.md` — add `getting-started-page.png` reference
- `docs-site/docs/user-guide/overview.md` — add `overview-page.png` reference
- `tests/docs_media/test_sprint2_guide_screenshots.py` — new validation tests
