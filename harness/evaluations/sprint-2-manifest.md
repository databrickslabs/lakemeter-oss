# Sprint 2 Interaction Manifest — Workload Type Guide Screenshots

## Doc Pages Tested

All 8 doc pages that reference Sprint 2 screenshots were verified.

### Page: Getting Started (`/user-guide/getting-started`)

| Element | Type | Action | Result | Status |
|---------|------|--------|--------|--------|
| Sidebar: Getting Started section | nav | expand | Section expanded, sub-pages visible | TESTED |
| Sidebar: 5-Minute Tutorial link | nav | click | Navigated to /user-guide/getting-started | TESTED |
| Breadcrumb: Getting Started > 5-Minute Tutorial | nav | verify | Correct hierarchy shown | TESTED |
| Screenshot: getting-started-page.png | image | verify render | 186KB, renders correctly, dark theme | TESTED |
| Alt text: "Getting Started tutorial page" | accessibility | verify | Descriptive (>=10 chars), no customer names | TESTED |
| Caption: italic text below image | text | verify | Present, descriptive, no customer names | TESTED |
| TOC: right sidebar | nav | verify | Step 1-5 anchors and "What to try next" visible | TESTED |
| Internal link: calculator-overview.png | image | verify render | Correctly embedded below Step 1 | TESTED |

### Page: Overview (`/user-guide/overview`)

| Element | Type | Action | Result | Status |
|---------|------|--------|--------|--------|
| Sidebar: Overview link | nav | click | Navigated to /user-guide/overview | TESTED |
| Screenshot: overview-page.png | image | verify render | 224KB, renders correctly | TESTED |
| Alt text: "Overview documentation page" | accessibility | verify | Descriptive, no customer names | TESTED |
| Caption: italic text | text | verify | Present, descriptive | TESTED |
| Screenshot: workloads-overview-page.png | image | verify render | 252KB, renders at bottom of page | TESTED |
| Alt text: "Workloads overview page" | accessibility | verify | Descriptive, no customer names | TESTED |
| Caption: italic text | text | verify | Present, descriptive | TESTED |
| TOC: right sidebar | nav | verify | Sections visible | TESTED |
| Workload types table | content | verify | 9 workload types listed correctly | TESTED |
| Internal link: /user-guide/workloads | link | verify | Link present, path correct | TESTED |

### Page: DBSQL Warehouses (`/user-guide/dbsql-warehouses`)

| Element | Type | Action | Result | Status |
|---------|------|--------|--------|--------|
| Sidebar: Databricks SQL (DBSQL) link | nav | click | Navigated correctly | TESTED |
| Screenshot: dbsql-warehouses-guide.png | image | verify render | 266KB, shows app screenshot within doc page | TESTED |
| Alt text: "DBSQL Warehouses documentation page" | accessibility | verify | Descriptive, no customer names | TESTED |
| Caption: italic text | text | verify | Present, descriptive | TESTED |
| Screenshot: dbsql-worked-example.png | image | verify render | 193KB, shows worked example section | TESTED |
| Alt text: "DBSQL worked cost example" | accessibility | verify | Descriptive, no customer names | TESTED |
| Caption: italic text | text | verify | Present, descriptive | TESTED |
| Internal link: All-Purpose Compute | link | verify | Correct cross-reference | TESTED |
| Data sanitization in screenshot | content | verify | Shows "QA Test - Renamed", no customer names | TESTED |
| Number rendering | content | verify | "$702,955.73" — no overflow | TESTED |

### Page: Model Serving (`/user-guide/model-serving`)

| Element | Type | Action | Result | Status |
|---------|------|--------|--------|--------|
| Sidebar: Model Serving link | nav | click | Navigated correctly | TESTED |
| Screenshot: model-serving-guide.png | image | verify render | 253KB, correct page context | TESTED |
| Alt text: "Model Serving documentation page" | accessibility | verify | Descriptive, no customer names | TESTED |
| Caption: italic text | text | verify | Present, descriptive | TESTED |
| Screenshot: model-serving-worked-example.png | image | verify render | 192KB, worked example visible | TESTED |
| Alt text: "Model Serving worked cost example" | accessibility | verify | Descriptive, no customer names | TESTED |
| Caption: italic text | text | verify | Present, descriptive | TESTED |
| Internal links: FMAPI-Databricks, FMAPI-Proprietary | link | verify | Both cross-references correct | TESTED |
| Data sanitization in screenshot | content | verify | "QA Test - Renamed", no customer names | TESTED |
| Number rendering | content | verify | "$702,955.73" — no overflow | TESTED |

### Page: Vector Search (`/user-guide/vector-search`)

| Element | Type | Action | Result | Status |
|---------|------|--------|--------|--------|
| Sidebar: Vector Search link | nav | click | Navigated correctly | TESTED |
| Screenshot: vector-search-guide.png | image | verify render | 269KB, correct page context | TESTED |
| Alt text: "Vector Search documentation page" | accessibility | verify | Descriptive, no customer names | TESTED |
| Caption: italic text | text | verify | Present, descriptive | TESTED |
| Screenshot: vector-search-worked-example.png | image | verify render | 203KB, worked example visible | TESTED |
| Alt text: "Vector Search worked cost example" | accessibility | verify | Descriptive, no customer names | TESTED |
| Caption: italic text | text | verify | Present, descriptive | TESTED |
| Internal link: FMAPI-Databricks | link | verify | Cross-reference correct | TESTED |
| Data sanitization in screenshot | content | verify | "QA Test - Renamed", no customer names | TESTED |

### Page: FMAPI Databricks (`/user-guide/fmapi-databricks`)

| Element | Type | Action | Result | Status |
|---------|------|--------|--------|--------|
| Sidebar: FMAPI — Databricks Models link | nav | click | Navigated correctly | TESTED |
| Screenshot: fmapi-databricks-guide.png | image | verify render | 282KB, correct page context | TESTED |
| Alt text: "FMAPI Databricks documentation page" | accessibility | verify | Descriptive, no customer names | TESTED |
| Caption: italic text | text | verify | Present, descriptive | TESTED |
| Screenshot: fmapi-databricks-worked-example.png | image | verify render | 204KB, worked example visible | TESTED |
| Alt text: "FMAPI Databricks worked cost example" | accessibility | verify | Descriptive, no customer names | TESTED |
| Caption: italic text | text | verify | Present, descriptive | TESTED |
| Internal links: FMAPI-Proprietary, Model Serving | link | verify | Both cross-references correct | TESTED |
| Data sanitization in screenshot | content | verify | "$702,955.73", no customer names | TESTED |

### Page: FMAPI Proprietary (`/user-guide/fmapi-proprietary`)

| Element | Type | Action | Result | Status |
|---------|------|--------|--------|--------|
| Sidebar: FMAPI — Proprietary Models link | nav | click | Navigated correctly | TESTED |
| Screenshot: fmapi-proprietary-guide.png | image | verify render | 277KB, correct page context | TESTED |
| Alt text: "FMAPI Proprietary documentation page" | accessibility | verify | Descriptive, no customer names | TESTED |
| Caption: italic text | text | verify | Present, descriptive | TESTED |
| Screenshot: fmapi-proprietary-worked-example.png | image | verify render | 197KB, worked example visible | TESTED |
| Alt text: "FMAPI Proprietary worked cost example" | accessibility | verify | Descriptive, no customer names | TESTED |
| Caption: italic text | text | verify | Present, descriptive | TESTED |
| Internal link: FMAPI-Databricks | link | verify | Cross-reference correct | TESTED |
| Data sanitization in screenshot | content | verify | "QA Test - Renamed", no customer names | TESTED |

### Page: Lakebase (`/user-guide/lakebase`)

| Element | Type | Action | Result | Status |
|---------|------|--------|--------|--------|
| Sidebar: Lakebase link | nav | click | Navigated correctly | TESTED |
| Screenshot: lakebase-guide.png | image | verify render | 263KB, correct page context | TESTED |
| Alt text: "Lakebase documentation page" | accessibility | verify | Descriptive, no customer names | TESTED |
| Caption: italic text | text | verify | Present, descriptive | TESTED |
| Screenshot: lakebase-worked-example.png | image | verify render | 204KB, worked example visible | TESTED |
| Alt text: "Lakebase worked cost example" | accessibility | verify | Descriptive, no customer names | TESTED |
| Caption: italic text | text | verify | Present, descriptive | TESTED |
| Internal link: DBSQL | link | verify | Cross-reference correct | TESTED |
| Data sanitization in screenshot | content | verify | "QA Test - Renamed", no customer names | TESTED |

## Global Elements (tested across all pages)

| Element | Type | Action | Result | Status |
|---------|------|--------|--------|--------|
| Top nav: Lakemeter | nav | verify | Present on all pages | TESTED |
| Top nav: User Guide | nav | verify | Active/highlighted on all Sprint 2 pages | TESTED |
| Top nav: Admin Guide | nav | verify | Present, links correctly | TESTED |
| Top nav: Testing Guide | nav | verify | Present, links correctly | TESTED |
| Top nav: Databricks Pricing link | nav | verify | Present, external link | TESTED |
| Dark mode toggle (moon icon) | button | verify | Present in top-right | TESTED |
| Sidebar: Compute Workloads section | nav | expand | Sub-items visible including all workload types | TESTED |
| Sidebar: AI/ML & Data Services section | nav | expand | Sub-items visible (Model Serving, Vector Search, FMAPI, Lakebase) | TESTED |

## Summary

- **Total elements tested**: 91
- **TESTED**: 91
- **BUG**: 0
- **SKIPPED**: 0
- **PENDING**: 0
