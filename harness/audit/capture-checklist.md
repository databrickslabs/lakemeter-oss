# Screenshot Capture Checklist — Core Screenshots (Sprint 1)

**App URL**: https://lakemeter-e2e-v2-335310294452632.aws.databricksapps.com
**Viewport**: 1280px wide
**Format**: PNG
**Tool**: Chrome DevTools MCP / agent-browser

## Pre-capture Setup

- [ ] Open app in Chrome at 1280px viewport width
- [ ] Authenticate via Databricks OAuth
- [ ] Delete or rename any estimates with real customer names (especially "Maya Merchant")
- [ ] Delete debug workloads ("Debug Minimal", "Debug SN", "Debug CL", "Debug Word", "Debug Photon 1")
- [ ] Create clean demo estimates using ONLY sanitized names:
  - "QA Test Account" — AWS us-east-1, Premium tier
  - "Demo Corp - AWS Estimate" — AWS us-east-1, Enterprise tier
  - "Sample Analytics Platform" — Azure westus2, Premium tier
  - "Acme Industries - Production" — GCP us-central1, Enterprise tier
- [ ] Add 3-5 realistic workloads to each estimate (Jobs, DBSQL, Model Serving, etc.)
- [ ] Verify Cost Summary panel shows numbers without overflow

## Core Screenshots (8 files)

### 1. home-page.png (RE-CAPTURE REQUIRED — customer name violation)
- **Navigate to**: Home page / Estimates list
- **What to capture**: Full estimates list with sanitized names, cloud/region/tier columns, status indicators
- **Verify**: No "Maya Merchant" or real customer names visible
- **Save to**: `docs-site/static/img/home-page.png`

### 2. estimates-list.png (RE-CAPTURE REQUIRED — customer name violation)
- **Navigate to**: Home page / Estimates list (same view as home-page)
- **What to capture**: Full estimates list
- **Verify**: No "Maya Merchant" or real customer names visible
- **Save to**: `docs-site/static/img/estimates-list.png`

### 3. login-page.png (PASS — no action needed)
- **Status**: Clean — standard Databricks OAuth login page
- **Skip**: Unless UI has changed since last capture

### 4. calculator-overview.png (PASS — no action needed)
- **Status**: Clean — shows workload list with cost summary
- **Skip**: Unless UI has changed since last capture

### 5. all-workloads-overview.png (RE-CAPTURE REQUIRED — cluttered)
- **Navigate to**: Calculator page for "QA Test Account" estimate
- **What to capture**: Full workload list showing 5-8 clean workloads with costs
- **Verify**: No debug entries visible, professional-looking data
- **Save to**: `docs-site/static/img/all-workloads-overview.png`

### 6. workload-expanded-config.png (PASS — no action needed)
- **Status**: Clean — shows expanded workload configuration panel
- **Skip**: Unless UI has changed since last capture

### 7. estimate-with-workloads.png (PASS — no action needed)
- **Status**: Clean — shows estimate with workloads and cost summary
- **Skip**: Unless UI has changed since last capture

### 8. workload-calculation-detail.png (PASS — no action needed)
- **Status**: Clean — shows expanded calculation detail for a workload
- **Skip**: Unless UI has changed since last capture

## Post-capture Validation

- [ ] All 3 re-captured files saved to correct paths
- [ ] File sizes reasonable (100KB-500KB each)
- [ ] No customer names visible in any screenshot
- [ ] No number overflow in Cost Summary cells
- [ ] Run `pytest tests/docs_media/ -v` — all tests pass
- [ ] Run `cd docs-site && npm run build` — builds without errors
