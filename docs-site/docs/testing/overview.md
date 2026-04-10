---
sidebar_position: 1
---

# Test Suite Overview

Lakemeter includes a comprehensive end-to-end test harness that validates the AI assistant's ability to interpret natural language requests and produce correct workload configurations for all 14 supported workload types.

## Purpose

The test suite verifies that:

- The AI assistant correctly maps natural language descriptions to the right workload type
- Proposed workload configurations contain all required fields with valid values
- The confirm/reject workflow functions correctly
- Cost calculation logic matches between frontend and backend
- Excel export formulas produce accurate results

## Test Architecture

```
tests/
├── parity/                 # UI vs Excel export parity tests (Sprints 1-3)
│   ├── frontend_calc.py    # Python reimplementation of frontend formulas
│   ├── test_parity_jobs.py
│   ├── test_parity_allpurpose.py
│   ├── test_parity_dlt.py
│   ├── test_parity_dbsql.py
│   ├── test_parity_vector_search.py
│   ├── test_parity_model_serving.py
│   └── test_parity_lakebase.py
├── ai_assistant/           # AI assistant end-to-end tests (Sprints 1-11)
│   ├── conftest.py         # Shared fixtures: TestClient, estimate, FMAPI skip logic
│   ├── chat_helpers.py     # Extracted chat helper functions
│   ├── sprint_1/
│   │   ├── test_jobs_proposal.py      # JOBS workload proposals (15 tests)
│   │   └── test_confirm_flow.py       # Confirm/reject workflow (3 tests)
│   ├── sprint_2/
│   │   └── test_allpurpose_proposal.py  # ALL_PURPOSE proposals (13 tests)
│   ├── sprint_3/
│   │   ├── test_dlt_pro.py            # DLT Pro serverless (9 tests)
│   │   ├── test_dlt_core.py           # DLT Core classic (10 tests)
│   │   ├── test_dlt_advanced.py       # DLT Advanced (8 tests)
│   │   └── test_dlt_negative.py       # Non-DLT discrimination (2 tests)
│   ├── sprint_4/
│   │   ├── test_dbsql_serverless.py   # DBSQL Serverless (9 tests)
│   │   ├── test_dbsql_pro.py          # DBSQL Pro (8 tests)
│   │   ├── test_dbsql_classic.py      # DBSQL Classic (7 tests)
│   │   └── test_dbsql_negative.py     # Non-DBSQL discrimination (4 tests)
│   ├── sprint_5/
│   │   ├── test_model_serving_gpu_medium.py  # GPU Medium A10G (8 tests)
│   │   ├── test_model_serving_cpu.py         # CPU only (8 tests)
│   │   ├── test_model_serving_gpu_small.py   # GPU Small T4 (8 tests)
│   │   └── test_model_serving_negative.py    # Non-Serving discrimination (4 tests)
│   ├── sprint_6/
│   │   ├── test_vector_search_standard.py          # Standard endpoint (8 tests)
│   │   ├── test_vector_search_storage_optimized.py  # Storage-Optimized (7 tests)
│   │   ├── test_vector_search_small_rag.py          # Small RAG chatbot (7 tests)
│   │   └── test_vector_search_negative.py           # Non-VS discrimination (4 tests)
│   ├── sprint_7/
│   │   ├── test_fmapi_db_llama_input.py    # Llama input tokens (8 tests)
│   │   ├── test_fmapi_db_output_tokens.py  # Output tokens (8 tests)
│   │   ├── test_fmapi_db_embeddings.py     # BGE embeddings (7 tests)
│   │   └── test_fmapi_db_negative.py       # Proprietary + GPU discrimination (7 tests)
│   ├── sprint_8/
│   │   ├── test_fmapi_prop_claude.py       # Anthropic Claude (9 tests)
│   │   ├── test_fmapi_prop_openai.py       # OpenAI GPT (9 tests)
│   │   ├── test_fmapi_prop_google.py       # Google Gemini (9 tests)
│   │   └── test_fmapi_prop_negative.py     # DB-hosted + GPU discrimination (7 tests)
│   ├── sprint_10/
│   │   ├── test_data_platform_types.py     # Multi-workload JOBS+AP+DBSQL types
│   │   └── test_data_platform_confirm.py   # Multi-workload confirm flow
│   └── sprint_11/
│       ├── test_ml_pipeline_types.py       # ML pipeline VS+FMAPI+MS types (24 tests)
│       ├── test_ml_pipeline_confirm.py     # ML pipeline confirm flow (12 tests)
│       ├── test_ml_pipeline_two.py         # 2-workload VS+FMAPI variant (14 tests)
│       └── test_ml_pipeline_negative.py    # MS-only discrimination (7 tests)
├── sprint_3/               # DLT calculation verification tests
│   ├── conftest.py         # make_line_item fixture
│   ├── dlt_calc_helpers.py # Shared FE/BE calculation functions
│   ├── test_dlt_calc_classic.py       # Classic hours, editions, photon (25 tests)
│   ├── test_dlt_calc_serverless.py    # Serverless, edge cases (26 tests)
│   ├── test_dlt_disc_sku.py           # SKU alignment (16 tests)
│   ├── test_dlt_disc_pricing.py       # Pricing alignment (19 tests)
│   ├── test_dlt_export_sku.py         # Backend SKU lookup (17 tests)
│   ├── test_dlt_export_calc.py        # Backend calc + hours (14 tests)
│   ├── test_dlt_excel_e2e_formulas.py # Excel formula verification (10 tests)
│   ├── test_dlt_excel_e2e_totals.py   # Excel totals SUM verification (5 tests)
│   ├── test_dlt_excel_export.py       # Display names, matrix (22 tests)
│   └── test_dlt_vm_costs.py           # VM cost amounts (7 tests)
├── sprint_7/               # FMAPI backend pricing tests
│   ├── test_fmapi_db_pricing.py       # SKU, rates, calculations (36 tests)
│   └── test_fmapi_prop_edge_cases.py  # Fallback edge cases (10 tests)
├── sprint_9/               # Lakebase Excel & calculation tests (158 tests)
│   ├── test_lb_dbu_calc.py            # DBU/hr = CU × nodes (44 tests)
│   ├── test_lb_edge_cases.py          # Zero/negative/None/max (28 tests)
│   ├── test_lb_excel_compute.py       # Compute row SKU, formula (15 tests)
│   ├── test_lb_excel_crosscloud.py    # AWS/Azure/GCP + half-CU (11 tests)
│   ├── test_lb_excel_integrity.py     # Multi-item, discount propagation (9 tests)
│   ├── test_lb_excel_storage.py       # Storage row values, notes (18 tests)
│   ├── test_lb_excel_totals.py        # Total cost columns (13 tests)
│   └── test_lb_sku_pricing.py         # SKU determination, pricing (13 tests)
├── sprint_10/              # Sprint 10 regression + timeout fix (123 tests)
│   └── test_regression_s10.py         # Bug regression guards
├── sprint_11/              # Sprint 11 non-AI tests (50 tests)
│   ├── test_regression_s10_bugs.py    # S10 regression guards (8 tests)
│   ├── test_ms_combined_validation.py # Model Serving combined Excel (34 tests)
│   └── test_notes_completeness.py     # Notes column completeness (8 tests)
├── regression/             # Regression tests from prior bug fixes
├── docs_media/             # Documentation media validation tests
│   ├── test_sprint3_guide_screenshots.py  # Screenshot validation (113 tests)
│   ├── test_sprint4_workflow_gifs.py      # GIF format/naming validation (63 tests)
│   └── test_sprint5_video_and_embeds.py   # Video + embed validation (49 tests)
└── export/                 # Export-related tests
```

## How Tests Connect to the App

### AI Assistant Tests (Sprints 1-8)

These tests use a **FastAPI TestClient** that wraps the actual backend. The TestClient:

1. Starts the FastAPI app in-process (no separate server needed)
2. Uses the Databricks CLI token for FMAPI calls (Foundation Model API)
3. Connects to the live Lakebase database for estimate storage
4. Sends natural language prompts to `POST /api/v1/chat`
5. Validates the AI's proposed workload configuration

![AI Assistant Chat Panel](/img/calculator-overview.png)
*The AI assistant chat panel where users send natural language requests — test prompts simulate this interaction.*

### Calculation Tests (Sprint 3)

These tests validate the cost calculation logic directly — no AI calls needed:

1. Import frontend and backend calculation functions
2. Construct test workload configurations with known inputs
3. Verify calculated outputs match expected values
4. Test Excel export formulas against real `.xlsx` files

![Workload Calculation Detail](/img/workload-calculation-detail.png)
*Workload configuration with cost breakdown — Sprint 3 tests verify these calculations are accurate.*

### Documentation Media Tests (Docs Overhaul Sprints 3-5)

These tests validate all documentation media assets — screenshots, GIFs, and video:

1. **Screenshot validation** (113 tests): every guide screenshot exists, is non-empty, has reasonable file size (10KB-2MB), is referenced with descriptive alt text and caption in its doc page, and contains no forbidden customer names
2. **GIF validation** (63 tests): all 6 workflow GIFs exist in `static/img/gifs/`, use GIF89a format with multiple frames, are 800px wide, follow kebab-case naming, and stay under 5MB
3. **Video + embed validation** (49 tests): tutorial video exists as a valid MP4 container, all 7 GIF embeds and 2 video embeds are present in the correct doc pages with proper syntax, alt text, and accessibility attributes

```bash
# Run all docs media tests
python -m pytest tests/docs_media/ -v
```

## Running the Tests

### Prerequisites

- Python 3.11+ with a virtual environment
- Databricks CLI profile `lakemeter` configured
- Access to the `fe-vm-lakemeter` workspace

### Quick Start

```bash
cd "/path/to/lakemeter_app"
source .venv/bin/activate

# Run all tests
python -m pytest tests/ -v

# Run parity tests (UI vs Excel export — fast, no AI calls)
python -m pytest tests/parity/ -v

# Run a specific sprint
python -m pytest tests/ai_assistant/sprint_1/ -v  # JOBS
python -m pytest tests/ai_assistant/sprint_2/ -v  # ALL_PURPOSE
python -m pytest tests/sprint_3/ -v               # DLT calculations
python -m pytest tests/ai_assistant/sprint_3/ -v  # DLT/SDP AI proposals
python -m pytest tests/ai_assistant/sprint_4/ -v  # DBSQL AI proposals
python -m pytest tests/ai_assistant/sprint_5/ -v  # MODEL_SERVING AI proposals
python -m pytest tests/ai_assistant/sprint_6/ -v  # VECTOR_SEARCH AI proposals
python -m pytest tests/ai_assistant/sprint_7/ -v  # FMAPI_DATABRICKS AI proposals
python -m pytest tests/sprint_7/ -v               # FMAPI backend pricing
python -m pytest tests/ai_assistant/sprint_8/ -v  # FMAPI_PROPRIETARY AI proposals

# Sprint 9 — Lakebase Excel (no AI calls)
python -m pytest tests/sprint_9/ -v

# Sprint 10 — Multi-workload AI tests (requires FMAPI)
python -m pytest tests/ai_assistant/sprint_10/ --no-header --timeout=300

# Sprint 11 — ML pipeline AI tests (requires FMAPI)
python -m pytest tests/ai_assistant/sprint_11/ --no-header --timeout=300

# Run all non-AI tests (fast, ~9 seconds)
python -m pytest tests/ --ignore=tests/ai_assistant -v
```

### Test Performance

| Suite | Tests | Typical Runtime | AI Calls |
|-------|-------|----------------|----------|
| Parity Tests (UI vs Excel) | 152 | ~5 seconds | 0 |
| Sprint 1 — JOBS (AI) | 18 | ~2-3 minutes | 5 |
| Sprint 2 — ALL_PURPOSE (AI) | 13 | ~2 minutes | 2-4 |
| Sprint 3 — DLT Calculations | 161 | ~2 seconds | 0 |
| Sprint 3 — DLT/SDP (AI) | 29 | ~3.5 minutes | 4 |
| Sprint 4 — DBSQL (AI) | 28 | ~4 minutes | 5 |
| Sprint 5 — MODEL_SERVING (AI) | 28 | ~4 minutes | 5 |
| Sprint 6 — VECTOR_SEARCH (AI) | 26 | ~5 minutes | 5 |
| Sprint 7 — FMAPI_DATABRICKS (AI) | 30 | ~4 minutes | 5 |
| Sprint 7 — FMAPI Backend Pricing | 46 | ~1 second | 0 |
| Sprint 8 — FMAPI_PROPRIETARY (AI) | 34 | ~5 minutes | 5 |
| Sprint 9 — Lakebase Excel (non-AI) | 158 | ~3 seconds | 0 |
| Sprint 10 — Multi-Workload (AI) | ~40 | ~5 minutes | 3-5 |
| Sprint 10 — Regression (non-AI) | 123 | ~4 seconds | 0 |
| Sprint 11 — ML Pipeline (AI) | 57 | ~8 minutes | 3 |
| Sprint 11 — Non-AI Tests | 50 | ~3 seconds | 0 |
| Docs Media — Screenshots (non-AI) | 113 | under 1 second | 0 |
| Docs Media — GIFs (non-AI) | 63 | under 1 second | 0 |
| Docs Media — Video + Embeds (non-AI) | 49 | under 1 second | 0 |
| Non-AI Regression (all sprints) | 1,409 | ~9 seconds | 0 |
| **Total** | **~2,109+** | **~45 minutes** | **42-46** |

:::note
AI assistant tests take 30-60 seconds per API call due to Claude processing time. Module-scoped fixtures minimize the number of calls by sharing responses across test methods.
:::

## Test Design Principles

### Module-Scoped Fixtures

Expensive AI calls are made once per module and shared across all test methods in that module. This reduces a 15-test class from 15 API calls to 1.

### Multi-Message Retry

The AI may ask clarifying questions instead of proposing immediately. Tests send up to 3 progressively more specific messages to handle this non-determinism.

### Wide Assertion Ranges

Since AI responses vary between runs, numeric assertions use ranges rather than exact values. For example, `hours_per_month` for "8 hours a day on weekdays" is asserted as `50 <= value <= 750` rather than exactly `176`.

### Regression Protection

Every bug found during evaluation gets a dedicated regression test to prevent recurrence.
