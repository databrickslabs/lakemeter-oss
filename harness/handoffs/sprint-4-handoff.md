# Sprint 4 Handoff: Workflow GIFs

## What Was Built

### 6 Workflow GIF Animations (`docs-site/static/img/gifs/`)

| # | File | Frames | Size | Workflow |
|---|------|--------|------|----------|
| 1 | `creating-estimate.gif` | 5 | 67KB | New Estimate: click button, fill form, submit, land on calculator |
| 2 | `adding-workload.gif` | 5 | 67KB | Add Workload: select type, configure Jobs Compute, save |
| 3 | `drag-and-drop.gif` | 4 | 59KB | Drag workload from position 3 to position 2 |
| 4 | `ai-assistant.gif` | 5 | 64KB | Type question, AI responds with tool call, applies workload |
| 5 | `export-excel.gif` | 4 | 51KB | Click Export, select Excel, download completes |
| 6 | `cost-summary.gif` | 4 | 67KB | Expand workload costs, hover tooltip shows formula |

All GIFs are 800x600px, GIF89a format, multi-frame animated, using sanitized data only ("Demo Corp", "Acme Industries", "QA Test Account").

### GIF Generation Scripts (`scripts/`)

| File | Lines | Purpose |
|------|-------|---------|
| `gif_ui_helpers.py` | 197 | Shared drawing primitives (sidebar, header, buttons, cards, cursors) |
| `gif_workflow_frames.py` | 200 | Frame generators: creating-estimate, adding-workload, drag-and-drop |
| `gif_workflow_frames_2.py` | 173 | Frame generators: ai-assistant, export-excel |
| `gif_workflow_frames_3.py` | 122 | Frame generator: cost-summary |
| `generate_workflow_gifs.py` | 59 | Main entry point — generates all 6 GIFs |

### Validation Tests (`tests/docs_media/test_sprint4_workflow_gifs.py`)

63 tests across 5 test classes:
- `TestGifFilesExist` (9 tests): directory exists, all 6 files exist, count = 6, no unexpected files
- `TestGifFormat` (18 tests): GIF89a magic bytes, multiple frames, 800px width
- `TestGifSizeBounds` (12 tests): each GIF >50KB and <5MB
- `TestGifNaming` (12 tests): kebab-case, no forbidden customer names
- `TestGifDocPageReadiness` (12 tests): static paths resolve, target doc pages exist

### Contract

- `harness/contracts/sprint-4.md` — updated from old scope to Workflow GIFs scope

## How to Test

```bash
cd "/Users/steven.tan/Desktop/Ent 1 - Q4 FY 2026 Team Project/lakemeter_app"

# Sprint 4 tests only
pytest tests/docs_media/test_sprint4_workflow_gifs.py -v

# Full test suite
pytest --tb=short

# Regenerate GIFs (if needed)
cd scripts && python3 generate_workflow_gifs.py
```

## Test Results

- `pytest tests/docs_media/test_sprint4_workflow_gifs.py`: **63 passed** in 0.11s
- `pytest` (full suite): **2565 passed**, 2 skipped, 1 warning in 144s

## Known Limitations

- GIFs are programmatically generated UI mockups (Pillow), not live app captures. The Visual QA Agent should verify they accurately represent the live app's UI and re-capture from the live app if needed.
- GIFs use Menlo font (macOS system font) — rendering may differ on other platforms.
- The GIF generation scripts require Pillow (`pip install Pillow`).

## Files Changed

| File | Status |
|------|--------|
| `docs-site/static/img/gifs/creating-estimate.gif` | New |
| `docs-site/static/img/gifs/adding-workload.gif` | New |
| `docs-site/static/img/gifs/drag-and-drop.gif` | New |
| `docs-site/static/img/gifs/ai-assistant.gif` | New |
| `docs-site/static/img/gifs/export-excel.gif` | New |
| `docs-site/static/img/gifs/cost-summary.gif` | New |
| `scripts/gif_ui_helpers.py` | New |
| `scripts/gif_workflow_frames.py` | New |
| `scripts/gif_workflow_frames_2.py` | New |
| `scripts/gif_workflow_frames_3.py` | New |
| `scripts/generate_workflow_gifs.py` | New |
| `tests/docs_media/test_sprint4_workflow_gifs.py` | New (63 tests) |
| `harness/contracts/sprint-4.md` | Updated |
| `harness/handoffs/sprint-4-handoff.md` | Updated (this file) |
