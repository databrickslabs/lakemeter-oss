# Sprint 4 Contract: Workflow GIFs

## Acceptance Criteria

- [ ] 6 GIF files exist in `docs-site/static/img/gifs/`:
  1. `creating-estimate.gif` — New Estimate flow (click New, fill form, submit)
  2. `adding-workload.gif` — Add Workload flow (click Add, select type, configure, save)
  3. `drag-and-drop.gif` — Workload reordering via drag-and-drop
  4. `ai-assistant.gif` — AI chat interaction with tool calls
  5. `export-excel.gif` — Export button click and download
  6. `cost-summary.gif` — Expand/collapse workload costs and hover tooltips
- [ ] Each GIF is a valid GIF89a file (correct magic bytes)
- [ ] Each GIF is non-trivial (>50KB — not a blank placeholder)
- [ ] Each GIF is optimized (<5MB per file)
- [ ] Width target: ~800px
- [ ] No real customer names visible in any GIF frame
- [ ] GIF directory contains exactly 6 files (no extras)
- [ ] All validation tests pass

## GIF Capture Approach

GIFs are captured from the live app at `https://lakemeter-e2e-v2-335310294452632.aws.databricksapps.com` using browser automation. The Build Agent:
1. Ensures `docs-site/static/img/gifs/` directory exists
2. Creates a Python capture utility script for recording browser interactions as GIF
3. Creates the 6 GIF files by recording browser workflows
4. Writes comprehensive validation tests

The Visual QA Agent will verify each GIF's visual content and accuracy.

## Test Plan

- **File validation**: existence, GIF89a magic bytes, size bounds (50KB–5MB), count = 6
- **Naming convention**: all files match expected names exactly
- **No customer name violations**: filenames don't contain forbidden names
- **Path readiness**: GIF paths resolve correctly for Docusaurus static assets

## Production Readiness Items

- GIF files in `docs-site/static/img/gifs/` per spec file structure
- File sizes optimized for web delivery (<5MB each)
