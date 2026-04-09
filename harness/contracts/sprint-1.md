# Sprint 1 Contract: Screenshot Audit & Core Screenshot Re-capture

## Acceptance Criteria

- [ ] All 46 existing screenshots audited for: customer name violations, number overflow, stale UI
- [ ] Audit report written to `harness/audit/screenshot-audit-report.md` with per-file status and action
- [ ] Validation test suite at `tests/docs_media/` that:
  - Verifies all image refs in doc pages point to existing files
  - Validates no zero-byte or missing screenshot files
  - Checks alt text is present for every image reference
- [ ] Screenshot capture checklist created with exact steps for 8 core screenshots
- [ ] Directory structure prepared: `docs-site/static/img/gifs/`, `docs-site/static/video/`
- [ ] Doc page alt text reviewed and updated where needed for core screenshots
- [ ] `cd docs-site && npm run build` succeeds with zero errors

## Test Plan

- `tests/docs_media/test_image_references.py` — all markdown `![...](/img/...)` refs resolve to files
- `tests/docs_media/test_screenshot_audit.py` — audit report exists and covers all 46 screenshots
- `tests/docs_media/test_docs_build.py` — docs site builds without broken link errors

## Production Readiness Items This Sprint
- Directory structure for GIFs and video prepared
- Audit report establishes baseline for all future sprints
