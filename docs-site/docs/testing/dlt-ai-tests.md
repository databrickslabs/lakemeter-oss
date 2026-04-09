---
sidebar_position: 5
---

# Sprint 3 (AI): DLT/SDP Proposal Tests

Sprint 3 validates the AI assistant's ability to propose **Spark Declarative Pipelines (DLT/SDP)** workloads across all three editions (Pro, Core, Advanced) and correctly reject non-DLT requests.

## What's Tested

### Overview

| Variant | File | Tests | AI Calls | Edition |
|---------|------|-------|----------|---------|
| Pro Serverless | `test_dlt_pro.py` | 9 | 1 | PRO |
| Core Classic | `test_dlt_core.py` | 10 | 1 | CORE |
| Advanced | `test_dlt_advanced.py` | 8 | 1 | ADVANCED |
| Negative Discrimination | `test_dlt_negative.py` | 2 | 1 | N/A |
| **Total** | **4 files** | **29** | **4** | |

### DLT Pro — Serverless CDC Pipeline (9 tests)

A single AI call simulates a user requesting a CDC pipeline with Pro edition:

> *"I need to set up a CDC pipeline using Spark Declarative Pipelines (SDP) with Pro edition and serverless compute on AWS us-east-1."*

| Field | Assertion |
|-------|-----------|
| `workload_type` | Equals `"DLT"` |
| `dlt_edition` | Contains `"PRO"` |
| `serverless_enabled` | `True` |
| `workload_name` | Non-empty, at least 3 characters |
| `reason` | Populated, at least 10 characters |
| `notes` | Populated |
| `proposal_id` | Present |
| Scheduling fields | `runs_per_day`, `avg_runtime_minutes`, `days_per_month` present |

![DLT Pipeline Configuration](/img/workload-expanded-config.png)
*A DLT workload configuration in the calculator — the AI assistant generates equivalent configurations from natural language descriptions.*

### DLT Core — Basic Batch ETL (10 tests)

Tests a basic ETL pipeline with Core edition and classic compute:

> *"I need a basic DLT pipeline for simple batch ETL — just reading from S3, transforming, and writing to Delta tables."*

Verifies all Pro assertions plus:
- `dlt_edition` contains `"CORE"`
- `num_workers` present when classic compute
- Node types (`driver_node_type`, `worker_node_type`) populated for classic
- `photon_enabled` field is set

### DLT Advanced — Full Monitoring Pipeline (8 tests)

Tests an advanced pipeline with data quality expectations:

> *"I need an advanced DLT pipeline with full data quality expectations, monitoring, and enhanced autoscaling on AWS us-east-1."*

Verifies:
- `dlt_edition` contains `"ADVANCED"`
- Standard metadata fields (name, reason, notes, proposal_id)
- Scheduling fields present

### Negative Discrimination (2 tests)

Tests that the AI does **not** propose a DLT workload when the request is clearly for interactive compute:

> *"I need an interactive cluster for ad-hoc data exploration with 4 workers on AWS us-east-1."*

Verifies:
1. The proposed `workload_type` is **not** `"DLT"`
2. The AI correctly identifies this as an All-Purpose Compute request

This prevents false positives where the AI might incorrectly map any compute request to DLT.

## File Structure

```
tests/ai_assistant/sprint_3/
├── __init__.py
├── prompts.py          # 4 prompt sequences (3 messages each)
├── conftest.py         # 4 module-scoped fixtures (1 AI call each)
├── test_dlt_pro.py     # 9 tests — Pro serverless CDC
├── test_dlt_core.py    # 10 tests — Core classic batch ETL
├── test_dlt_advanced.py # 8 tests — Advanced monitoring
└── test_dlt_negative.py # 2 tests — non-DLT discrimination
```

### Design Decision: File Splitting

The original monolithic `test_dlt_proposal.py` (262 lines) was split into 4 per-variant files to meet the 200-line guideline. Module-scoped fixtures moved to `conftest.py` so each variant makes exactly one AI call — identical behavior to the monolithic version.

## Running Sprint 3 AI Tests

```bash
cd "/path/to/lakemeter_app"
source .venv/bin/activate
python -m pytest tests/ai_assistant/sprint_3/ -v
```

Expected output:

```
tests/ai_assistant/sprint_3/test_dlt_pro.py::TestDltPro::test_workload_type_is_dlt PASSED
tests/ai_assistant/sprint_3/test_dlt_pro.py::TestDltPro::test_edition_is_pro PASSED
...
tests/ai_assistant/sprint_3/test_dlt_core.py::TestDltCore::test_edition_is_core PASSED
tests/ai_assistant/sprint_3/test_dlt_core.py::TestDltCore::test_has_workers PASSED
...
tests/ai_assistant/sprint_3/test_dlt_advanced.py::TestDltAdvanced::test_edition_is_advanced PASSED
...
tests/ai_assistant/sprint_3/test_dlt_negative.py::TestDltNegative::test_not_dlt PASSED
tests/ai_assistant/sprint_3/test_dlt_negative.py::TestDltNegative::test_correct_type PASSED

29 passed in ~216s
```

![All Workloads Overview](/img/all-workloads-overview.png)
*The workload type selector showing DLT (Spark Declarative Pipelines) — tests verify the AI correctly selects this type and the appropriate edition for pipeline use cases.*

## Edition Selection Logic

The AI must correctly map user intent to the right DLT edition:

| User Intent | Expected Edition | Key Signals |
|-------------|-----------------|-------------|
| Basic batch ETL, no CDC | **CORE** | "simple", "basic", "batch ETL", no mention of CDC/SCD |
| CDC pipelines, SCD Type 2 | **PRO** | "CDC", "change data capture", "SCD", "slowly changing dimensions" |
| Full monitoring, expectations | **ADVANCED** | "advanced", "data quality", "expectations", "enhanced monitoring" |

## Bug Fixes Included

| Bug | Description | Fix |
|-----|-------------|-----|
| BUG-S3-001 | Advanced prompt not specific enough — AI sometimes chose Pro | Hardened `DLT_ADVANCED_FINAL` prompt with explicit "Advanced edition" |
| BUG-S3-002 | Missing `test_scheduling_fields_present` for Core variant | Added test to reach 15/15 acceptance criteria |
| BUG-S3-003 | FMAPI tool_use/tool_result message conversion failure | Fixed in `ai_client.py` and `ai_agent.py` — affected all AI tests |

## Known Limitations

- **Non-determinism**: DLT Core may choose serverless instead of classic — classic-specific tests use `pytest.skip` when this happens
- The negative test adds a 4th AI call per run (~30s additional runtime)
- AI may need all 3 messages in a prompt sequence to produce a proposal

## Troubleshooting

| Issue | Resolution |
|-------|-----------|
| Core test returns serverless instead of classic | Expected non-determinism. The test skips classic-specific assertions gracefully. |
| Advanced edition test fails with Pro | The prompt may need strengthening. Ensure the final message explicitly says "Advanced edition." |
| `tool_use`/`tool_result` conversion error | Verify BUG-S3-003 fix is present in `ai_client.py`. This was a message format issue with FMAPI. |
