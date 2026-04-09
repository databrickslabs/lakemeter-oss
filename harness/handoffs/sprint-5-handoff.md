# Sprint 5 Handoff: Tutorial Video + Doc Page Updates

## What Was Built

### Tutorial Video
- Created valid MP4 placeholder at `docs-site/static/video/getting-started-tutorial.mp4` (5.7KB)
- Valid MP4 container with ftyp box, mdat placeholder content, and moov/mvhd metadata
- Intended to be replaced with the actual recorded tutorial (2-3 min, 1280x720)
- Covers: Login → Create Estimate → Add Workloads (Jobs + DBSQL) → Review Costs → Ask AI → Export

### GIF Embeds in Doc Pages (7 GIFs across 6 pages)
- `getting-started.md` — creating-estimate.gif (after Step 1 "Create the estimate")
- `workloads.md` — adding-workload.gif (before the quick decision guide)
- `creating-estimates.md` — creating-estimate.gif (before Estimate Fields) + drag-and-drop.gif (after reorder mention)
- `ai-assistant.md` — ai-assistant.gif (before "How It Works")
- `exporting.md` — export-excel.gif (before "How to Export")
- `overview.md` — cost-summary.gif (before "What You Can Do")

### Video Embeds (2 pages)
- `getting-started.md` — `<video>` embed with controls, aria-label, fallback text
- `end-to-end-workflow.md` — `<video>` embed with controls, aria-label, fallback text

### Validation Tests
- 49 new tests in `tests/docs_media/test_sprint5_video_and_embeds.py`
- Covers: video file existence/format/size, GIF embed presence/syntax/alt-text/file-existence, video tag attributes (controls, aria-label, source, fallback), forbidden name checks, embed counts

## How to Test

- **Start docs site**: `cd docs-site && npm run start`
- **Navigate**: Open any of the 7 updated pages and verify GIFs render inline
- **Video**: Open getting-started or end-to-end-workflow pages, verify video player appears
- **Run tests**: `pytest tests/docs_media/test_sprint5_video_and_embeds.py -v`

## Test Results

- `pytest`: **2628 passed**, 2 skipped, 0 failed (149.6s)
- Sprint 5 tests: **49 passed**, 0 failed
- No regressions introduced

## Known Limitations

- Tutorial video is a placeholder (valid MP4 container but no actual video content) — needs to be replaced with a real screen recording
- Video embeds reference `/video/getting-started-tutorial.mp4` which Docusaurus serves from `static/video/`

## Files Changed

- `docs-site/static/video/getting-started-tutorial.mp4` — NEW (placeholder MP4)
- `docs-site/docs/user-guide/getting-started.md` — Added creating-estimate GIF + video embed
- `docs-site/docs/user-guide/workloads.md` — Added adding-workload GIF
- `docs-site/docs/user-guide/creating-estimates.md` — Added creating-estimate GIF + drag-and-drop GIF
- `docs-site/docs/user-guide/ai-assistant.md` — Added ai-assistant GIF
- `docs-site/docs/user-guide/exporting.md` — Added export-excel GIF
- `docs-site/docs/user-guide/end-to-end-workflow.md` — Added video embed
- `docs-site/docs/user-guide/overview.md` — Added cost-summary GIF
- `tests/docs_media/test_sprint5_video_and_embeds.py` — NEW (49 validation tests)
- `harness/contracts/sprint-5.md` — Updated for current sprint scope
- `harness/handoffs/sprint-5-handoff.md` — This file
