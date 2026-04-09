# Screenshot Audit Report

**Date**: 2026-04-04
**Auditor**: Build Agent (Sprint 1)
**Total screenshots**: 39 (8 core + 31 guides)
**App URL**: https://lakemeter-e2e-v2-335310294452632.aws.databricksapps.com

## Summary

| Category | Count | Customer Name Violation | Needs Re-capture | Clean |
|----------|-------|------------------------|------------------|-------|
| Core screenshots | 8 | 2 | 1 | 5 |
| Guide screenshots | 31 | 0 | 0 | 31 |
| **Total** | **39** | **2** | **1** | **36** |

## Critical Findings

### Customer Name Violations (MUST FIX)

| File | Violation | Details |
|------|-----------|---------|
| `static/img/home-page.png` | Real customer name | Shows "Maya Merchant Commerci..." in estimates list |
| `static/img/estimates-list.png` | Real customer name | Shows "Maya Merchant Commerci..." in estimates list (same view as home-page) |

### Needs Re-capture (Quality Issues)

| File | Issue | Details |
|------|-------|---------|
| `static/img/all-workloads-overview.png` | Cluttered with debug data | Shows 25+ workloads including "Debug Minimal", "Debug SN", "Debug CL", "Debug Word", "Debug Photon 1" entries — not professional for documentation |

## Core Screenshots (8 files in `static/img/`)

| # | File | Size | Status | Issue | Action |
|---|------|------|--------|-------|--------|
| 1 | `home-page.png` | 178KB | FAIL | "Maya Merchant Commerci..." visible | RE-CAPTURE with sanitized data |
| 2 | `estimates-list.png` | 178KB | FAIL | "Maya Merchant Commerci..." visible | RE-CAPTURE with sanitized data |
| 3 | `login-page.png` | 47KB | PASS | Standard Databricks OAuth login | No action needed |
| 4 | `calculator-overview.png` | 228KB | PASS | Shows "Vector Search \| Standard M" estimate | No action needed |
| 5 | `all-workloads-overview.png` | 444KB | WARN | Cluttered with debug/test entries | RE-CAPTURE with clean data |
| 6 | `workload-expanded-config.png` | 228KB | PASS | Shows workload config panel | No action needed |
| 7 | `estimate-with-workloads.png` | 218KB | PASS | Shows "QA Test - Renamed" estimate | No action needed |
| 8 | `workload-calculation-detail.png` | 210KB | PASS | Shows Vector Search calculation detail | No action needed |

## Guide Screenshots — Doc Page Screenshots (31 files in `static/img/guides/`)

These are screenshots of the Docusaurus documentation site pages. They show doc content (text, tables, formulas) — NOT direct app UI with customer data.

### Workload Type Guides (12 files)

| # | File | Status | Content |
|---|------|--------|---------|
| 1 | `dbsql-warehouses-guide.png` | PASS | DBSQL doc page with embedded app screenshot |
| 2 | `dbsql-worked-example.png` | PASS | DBSQL worked example — text/tables only |
| 3 | `model-serving-guide.png` | PASS | Model Serving doc page with embedded app screenshot |
| 4 | `model-serving-worked-example.png` | PASS | Model Serving worked example — text/tables only |
| 5 | `vector-search-guide.png` | PASS | Vector Search doc page with embedded app screenshot |
| 6 | `vector-search-worked-example.png` | PASS | Vector Search worked example — doc page text |
| 7 | `fmapi-databricks-guide.png` | PASS | FMAPI Databricks doc page with embedded app screenshot |
| 8 | `fmapi-databricks-worked-example.png` | PASS | FMAPI Databricks worked example — text/tables only |
| 9 | `fmapi-proprietary-guide.png` | PASS | FMAPI Proprietary doc page with embedded app screenshot |
| 10 | `fmapi-proprietary-worked-example.png` | PASS | FMAPI Proprietary worked example — text/tables only |
| 11 | `lakebase-guide.png` | PASS | Lakebase doc page with embedded app screenshot |
| 12 | `lakebase-worked-example.png` | PASS | Lakebase worked example — doc page text |

### Feature Guides (8 files)

| # | File | Status | Content |
|---|------|--------|---------|
| 1 | `ai-assistant-guide.png` | PASS | AI Assistant doc page — text only, no customer data |
| 2 | `ai-assistant-tools.png` | PASS | AI Assistant tools section — text only |
| 3 | `export-guide.png` | PASS | Export to Excel doc page — text only |
| 4 | `export-excel-structure.png` | PASS | Excel structure table — text only |
| 5 | `calculation-reference-guide.png` | PASS | Calculation Reference doc page — formulas only |
| 6 | `calculation-worked-example.png` | PASS | Calculation worked example — formulas only |
| 7 | `faq-guide.png` | PASS | FAQ doc page — text only |
| 8 | `faq-workload-table.png` | PASS | FAQ workload decision table — text only |

### Admin Guides (8 files)

| # | File | Status | Content |
|---|------|--------|---------|
| 1 | `admin-deployment-guide.png` | PASS | Deployment doc page — architecture diagram, text |
| 2 | `admin-configuration-guide.png` | PASS | Configuration doc page — env vars table |
| 3 | `admin-api-reference-guide.png` | PASS | API Reference doc page — endpoints, no customer data |
| 4 | `admin-architecture-guide.png` | PASS | Architecture doc page — system diagram |
| 5 | `admin-database-guide.png` | PASS | Database doc page — schema tables |
| 6 | `admin-database-schema.png` | PASS | Database schema detail — column definitions |
| 7 | `admin-permissions-guide.png` | PASS | Permissions doc page — SP roles, OAuth config |
| 8 | `admin-troubleshooting-guide.png` | PASS | Troubleshooting doc page — symptom/fix table |

### Navigation/Overview Screenshots (3 files)

| # | File | Status | Content |
|---|------|--------|---------|
| 1 | `overview-page.png` | PASS | Overview doc page — has embedded estimates list screenshot (small, names not legible) |
| 2 | `getting-started-page.png` | PASS | Getting Started doc page — tutorial text only |
| 3 | `workloads-overview-page.png` | PASS | Workloads overview doc page — has embedded app screenshot |

## Re-capture Priority

### Sprint 1 (Core Screenshots — 3 must re-capture)
1. **home-page.png** — CRITICAL: Customer name violation
2. **estimates-list.png** — CRITICAL: Customer name violation
3. **all-workloads-overview.png** — WARN: Cluttered debug data

### Sprint 2-3 (Guide Screenshots — optional refresh)
All guide screenshots pass the audit. They can be refreshed for visual consistency but have no blocking issues.

## Data Sanitization Checklist (Before Any Re-capture)

1. Delete or rename any estimates containing "Maya Merchant" or other real customer names
2. Ensure remaining estimates use ONLY: "QA Test Account", "Demo Corp", "Sample Account", "Acme Industries", "Test Workspace"
3. Remove debug workloads ("Debug Minimal", "Debug SN", etc.) from visible estimates
4. Verify Cost Summary panel renders without number overflow
5. Use consistent, realistic configuration values across all visible workloads
