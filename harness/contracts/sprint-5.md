# Sprint 5 Contract: Tutorial Video + Doc Page Updates

## Acceptance Criteria

- [ ] Tutorial video placeholder exists at `docs-site/static/video/getting-started-tutorial.mp4`
- [ ] Video file is valid MP4 format, non-zero size
- [ ] 7 doc pages updated with GIF and/or video embeds:
  - `getting-started.md` — creating-estimate GIF + tutorial video embed
  - `workloads.md` — adding-workload GIF
  - `creating-estimates.md` — creating-estimate GIF + drag-and-drop GIF
  - `ai-assistant.md` — AI assistant GIF
  - `exporting.md` — export-excel GIF
  - `end-to-end-workflow.md` — tutorial video embed
  - `overview.md` — cost-summary GIF
- [ ] GIF embeds use `![alt text](/img/gifs/filename.gif)` markdown format
- [ ] Video embeds use `<video>` HTML tag with controls and accessibility attributes
- [ ] All GIF/video references point to existing files on disk
- [ ] No real customer names in any new content
- [ ] All existing tests continue to pass
- [ ] New validation tests cover Sprint 5 deliverables

## Test Plan

- File existence: tutorial video at correct path
- Format validation: MP4 header check
- Doc page embeds: each of 7 pages contains expected GIF/video references
- Reference integrity: all media references resolve to real files
- Sanitization: no forbidden customer names in new content
- Regression: all prior tests pass

## Files to Change

- `docs-site/static/video/getting-started-tutorial.mp4` (new)
- `docs-site/docs/user-guide/getting-started.md`
- `docs-site/docs/user-guide/workloads.md`
- `docs-site/docs/user-guide/creating-estimates.md`
- `docs-site/docs/user-guide/ai-assistant.md`
- `docs-site/docs/user-guide/exporting.md`
- `docs-site/docs/user-guide/end-to-end-workflow.md`
- `docs-site/docs/user-guide/overview.md`
- `tests/docs_media/test_sprint5_video_and_embeds.py` (new)
