# Lakemeter Documentation Overhaul — Product Spec

## Vision

Complete documentation media overhaul for the Lakemeter Databricks cost estimation app. Every screenshot re-captured with sanitized data (no real customer names, no number overflow), 6 workflow GIFs added, 1 tutorial video created, and all doc pages updated to embed the new media. The result is a polished, demo-ready documentation site that can be shown to any customer without data privacy concerns.

## Scope

This is a **documentation media** project — no application code changes. The app is already running at `https://lakemeter-e2e-v2-335310294452632.aws.databricksapps.com`. The docs site lives in `docs-site/` (Docusaurus).

## Critical Rules

1. **NEVER include real customer names** in any screenshot or GIF. No "Maya", no real account names. Use ONLY: "QA Test Account", "Demo Corp", "Sample Account", "Acme Industries", "Test Workspace".
2. **Fix number overflow** — the Cost Summary DBU/VM cost grid cells had overflow issues (fixed in code). Fresh screenshots will show correct rendering.
3. **All media captured from the live deployed app** at the URL above (requires Databricks OAuth).
4. **Use Chrome DevTools MCP** for all browser-based capture.

## Current State

- **Doc pages**: 38 files across `docs/user-guide/`, `docs/admin-guide/`, `docs/testing/`
- **Existing screenshots**: 46 PNG files in `docs-site/static/img/` and `docs-site/static/img/guides/`
- **Image references in docs**: 61 `![...](/img/...)` references across 38 files
- **Existing GIFs**: 0
- **Existing videos**: 0

## Data Sanitization Rules

Before capturing ANY screenshot or GIF:
1. Create test estimates using ONLY these names: "QA Test Account", "Demo Corp - AWS Estimate", "Sample Analytics Platform", "Acme Industries - Production"
2. Delete or rename any estimates with real customer names
3. Verify the Cost Summary panel renders numbers without overflow
4. Use consistent, realistic-looking configuration values

## Deliverables by Sprint

### Sprint 1: Screenshot Audit & Test Data Setup + Core Screenshots
- Audit all 46 existing screenshots for customer name violations and number overflow
- Log every screenshot that needs re-capture with reason (name violation, overflow, stale UI)
- Set up sanitized test data in the live app (create demo estimates with safe names)
- Verify Cost Summary panel renders correctly (no overflow)
- Re-capture the 8 core screenshots (`static/img/*.png` — non-guides):
  - `home-page.png`, `login-page.png`, `estimates-list.png`, `calculator-overview.png`
  - `all-workloads-overview.png`, `workload-expanded-config.png`, `estimate-with-workloads.png`, `workload-calculation-detail.png`
- Update any doc pages that reference these core screenshots if alt text needs fixing

### Sprint 2: User Guide Screenshots (Part 1) — Workload Types
- Re-capture guide screenshots for workload type pages:
  - `getting-started-page.png`, `overview-page.png`, `workloads-overview-page.png`
  - `dbsql-warehouses-guide.png`, `dbsql-worked-example.png`
  - `model-serving-guide.png`, `model-serving-worked-example.png`
  - `vector-search-guide.png`, `vector-search-worked-example.png`
  - `fmapi-databricks-guide.png`, `fmapi-databricks-worked-example.png`
  - `fmapi-proprietary-guide.png`, `fmapi-proprietary-worked-example.png`
  - `lakebase-guide.png`, `lakebase-worked-example.png`
- Verify each screenshot matches its doc page context and alt text

### Sprint 3: User Guide Screenshots (Part 2) + Admin Screenshots
- Re-capture remaining user guide screenshots:
  - `ai-assistant-guide.png`, `ai-assistant-tools.png`
  - `export-guide.png`, `export-excel-structure.png`
  - `calculation-reference-guide.png`, `calculation-worked-example.png`
  - `faq-guide.png`, `faq-workload-table.png`
- Re-capture all admin guide screenshots:
  - `admin-deployment-guide.png`, `admin-configuration-guide.png`
  - `admin-api-reference-guide.png`, `admin-architecture-guide.png`
  - `admin-database-guide.png`, `admin-database-schema.png`
  - `admin-permissions-guide.png`, `admin-troubleshooting-guide.png`

### Sprint 4: Workflow GIFs
- Create 6 workflow GIFs (10-15 seconds each, 800px wide, optimized file size <5MB each):
  1. **creating-estimate.gif** — click New Estimate, fill form, submit, land on calculator
  2. **adding-workload.gif** — click Add Workload, select type, configure, save
  3. **drag-and-drop.gif** — drag workloads to reorder in the list
  4. **ai-assistant.gif** — type a question, see response with tool calls
  5. **export-excel.gif** — click Export, download completes
  6. **cost-summary.gif** — expand/collapse workload costs, hover tooltips
- Store all GIFs in `docs-site/static/img/gifs/`
- Each GIF must use sanitized data only

### Sprint 5: Tutorial Video + Doc Page Updates
- Record 1 tutorial video (2-3 minutes) showing end-to-end Getting Started flow:
  - Login → Create estimate → Add 2 workloads (Jobs + DBSQL) → Review costs → Ask AI → Export
  - Use sanitized data throughout
  - Store in `docs-site/static/video/getting-started-tutorial.mp4`
- Update all doc pages to embed GIFs at relevant sections:
  - `getting-started.md` — embed creating-estimate GIF + tutorial video
  - `workloads.md` — embed adding-workload GIF
  - `creating-estimates.md` — embed creating-estimate GIF + drag-and-drop GIF
  - `ai-assistant.md` — embed AI assistant GIF
  - `exporting.md` — embed export GIF
  - `end-to-end-workflow.md` — embed tutorial video
  - `overview.md` — embed cost summary GIF
- Add `<video>` embed for the tutorial video

### Sprint 6: Docs Site Build Verification & Final Polish
- Run `cd docs-site && npm run build` — verify zero errors
- Check all image/GIF/video paths resolve correctly
- Verify no broken links (`onBrokenLinks: 'throw'` in Docusaurus config)
- Verify all 61+ image references point to updated files
- Check dark mode rendering of all embedded media
- Final audit: grep all screenshots for any remaining customer name references in alt text
- Verify GIF file sizes are reasonable (<5MB each)
- Verify video file size is reasonable (<50MB)
- Update `intro.md` landing page if needed to showcase new media

## Technical Notes

- **Screenshot format**: PNG, captured at 1280px viewport width for consistency
- **GIF format**: Optimized GIF, 800px wide, 10-15fps, <5MB each
- **Video format**: MP4 (H.264), 1280x720, <50MB
- **Browser**: Chrome via Chrome DevTools MCP
- **App URL**: `https://lakemeter-e2e-v2-335310294452632.aws.databricksapps.com`
- **Auth**: Databricks OAuth (handled by browser session)
- **Docs site**: Docusaurus v3, dark mode default, builds with `npm run build` in `docs-site/`

## File Locations

```
docs-site/
├── static/
│   ├── img/
│   │   ├── *.png                         # Core app screenshots (8 files)
│   │   ├── guides/*.png                  # Guide-specific screenshots (38 files)
│   │   └── gifs/*.gif                    # NEW: Workflow GIFs (6 files)
│   └── video/
│       └── getting-started-tutorial.mp4  # NEW: Tutorial video
├── docs/
│   ├── intro.md                          # Landing page
│   ├── user-guide/*.md                   # User-facing docs (update with GIF/video embeds)
│   ├── admin-guide/*.md                  # Admin docs (screenshots only)
│   └── testing/*.md                      # Test docs (screenshots only)
└── docusaurus.config.ts
```
