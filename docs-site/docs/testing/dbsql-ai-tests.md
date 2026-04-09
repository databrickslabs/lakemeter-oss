---
sidebar_position: 6
---

# Sprint 4: DBSQL Warehouse Tests

Sprint 4 validates the AI assistant's ability to propose **Databricks SQL (DBSQL)** warehouse workloads across all three warehouse types (Serverless, Pro, Classic) and correctly reject non-DBSQL requests.

## What's Tested

### Overview

| Variant | File | Tests | AI Calls | Warehouse Type |
|---------|------|-------|----------|----------------|
| Serverless | `test_dbsql_serverless.py` | 9 | 1 | SERVERLESS |
| Pro | `test_dbsql_pro.py` | 8 | 1 | PRO |
| Classic | `test_dbsql_classic.py` | 7 | 1 | CLASSIC |
| Negative (Interactive) | `test_dbsql_negative.py` | 2 | 1 | N/A |
| Negative (Batch ETL) | `test_dbsql_negative.py` | 2 | 1 | N/A |
| **Total** | **4 files** | **28** | **5** | |

### Serverless SQL Warehouse (9 tests)

A single AI call simulates a user requesting a serverless warehouse for BI dashboards:

> *"I need a serverless SQL warehouse for BI dashboards on AWS us-east-1. Medium size, expecting about 50 concurrent queries at peak."*

| Field | Assertion |
|-------|-----------|
| `workload_type` | Equals `"DBSQL"` |
| `dbsql_warehouse_type` | `"SERVERLESS"` |
| `dbsql_warehouse_size` | Valid size (one of: 2X-Small through 4X-Large) |
| `dbsql_num_clusters` | >= 1 |
| `workload_name` | Non-empty, at least 3 characters |
| `reason` | Populated, at least 10 characters |
| `notes` | Populated |
| `proposal_id` | Present |

![DBSQL Warehouse Configuration](/img/workload-expanded-config.png)
*A DBSQL workload configuration in the calculator — the AI assistant maps natural language warehouse requests to these fields.*

### Pro SQL Warehouse (8 tests)

Tests a Pro warehouse with scaling for analytics:

> *"I need a Databricks SQL Pro warehouse for analytics queries on AWS us-east-1. Large size with 2 clusters for scaling."*

Verifies:
- `dbsql_warehouse_type` is `"PRO"`
- `dbsql_warehouse_size` is `"Large"` or larger
- `dbsql_num_clusters` is populated and > 0
- Standard metadata fields present

### Classic SQL Warehouse (7 tests)

Tests a legacy Classic warehouse:

> *"I need a classic legacy Databricks SQL warehouse on AWS us-east-1. Small size, single cluster. We have a legacy integration that requires it."*

Verifies:
- `dbsql_warehouse_type` is `"CLASSIC"`
- Standard DBSQL fields present
- Metadata fields populated

### Negative Discrimination (4 tests)

Two separate negative test scenarios prevent the AI from incorrectly proposing DBSQL:

**Interactive Compute (AC-12)**:
> *"I need an interactive notebook cluster for data science work with 4 workers."*
- Verifies: `workload_type` is **not** `"DBSQL"`

**Batch ETL (AC-13)**:
> *"I need a batch ETL pipeline that runs daily to process raw data into curated Delta tables."*
- Verifies: `workload_type` is **not** `"DBSQL"`

These tests ensure the AI understands that SQL warehouses serve BI/analytics use cases — not interactive development or batch processing.

## File Structure

```
tests/ai_assistant/sprint_4/
├── __init__.py
├── prompts.py               # 5 prompt sequences (serverless, pro, classic, 2 negative)
├── conftest.py              # 5 module-scoped fixtures (1 AI call each)
├── test_dbsql_serverless.py # 9 tests — Serverless warehouse
├── test_dbsql_pro.py        # 8 tests — Pro warehouse
├── test_dbsql_classic.py    # 7 tests — Classic warehouse
└── test_dbsql_negative.py   # 4 tests — interactive + ETL discrimination
```

## Running Sprint 4 Tests

```bash
cd "/path/to/lakemeter_app"
source .venv/bin/activate
python -m pytest tests/ai_assistant/sprint_4/ -v
```

Expected output:

```
tests/ai_assistant/sprint_4/test_dbsql_serverless.py::TestDbsqlServerless::test_workload_type PASSED
tests/ai_assistant/sprint_4/test_dbsql_serverless.py::TestDbsqlServerless::test_warehouse_type PASSED
...
tests/ai_assistant/sprint_4/test_dbsql_pro.py::TestDbsqlPro::test_warehouse_type_pro PASSED
tests/ai_assistant/sprint_4/test_dbsql_pro.py::TestDbsqlPro::test_warehouse_size_large_or_bigger PASSED
...
tests/ai_assistant/sprint_4/test_dbsql_classic.py::TestDbsqlClassic::test_warehouse_type_classic PASSED
...
tests/ai_assistant/sprint_4/test_dbsql_negative.py::TestDbsqlNegativeInteractive::test_not_dbsql PASSED
tests/ai_assistant/sprint_4/test_dbsql_negative.py::TestDbsqlNegativeEtl::test_not_dbsql PASSED

28 passed in ~252s
```

![Estimates List](/img/estimates-list.png)
*An estimate with DBSQL workloads — the confirm flow creates these line items from AI-proposed configurations.*

## Warehouse Type Selection Logic

The AI must correctly map user intent to the right warehouse type:

| User Intent | Expected Type | Key Signals |
|-------------|--------------|-------------|
| BI dashboards, ad-hoc SQL | **SERVERLESS** | "serverless", "BI", "dashboards", no mention of legacy |
| Analytics with scaling | **PRO** | "Pro", "analytics", "scaling", "multiple clusters" |
| Legacy integration | **CLASSIC** | "classic", "legacy", explicit Classic request |

### Valid Warehouse Sizes

The AI must propose one of these standard sizes:

`2X-Small` | `X-Small` | `Small` | `Medium` | `Large` | `X-Large` | `2X-Large` | `3X-Large` | `4X-Large`

## Acceptance Criteria

All 13 acceptance criteria pass:

| AC | Description | Status |
|----|-------------|--------|
| AC-1 | Serverless → `workload_type=DBSQL` | PASS |
| AC-2 | Serverless → `dbsql_warehouse_type=SERVERLESS` | PASS |
| AC-3 | Valid warehouse size (Medium) | PASS |
| AC-4 | `dbsql_num_clusters >= 1` | PASS |
| AC-5–7 | Metadata: name, reason/notes, proposal_id | PASS |
| AC-8 | Pro → `dbsql_warehouse_type=PRO` | PASS |
| AC-9 | Pro → Large or bigger size | PASS |
| AC-10 | Pro → `num_clusters` populated | PASS |
| AC-11 | Classic → `dbsql_warehouse_type=CLASSIC` | PASS |
| AC-12 | Interactive compute ≠ DBSQL | PASS |
| AC-13 | Batch ETL ≠ DBSQL | PASS |

## Bug Fixes Included

| Bug | Description | Fix |
|-----|-------------|-----|
| BUG-S4-001 | Missing batch ETL negative test (AC-13) — handoff incorrectly claimed 13/13 | Added `TestDbsqlNegativeEtl` class with 2 tests and a 5th prompt variant |

## Known Limitations

- AI may choose slightly different warehouse sizes or cluster counts across runs
- Sprint 1 AI tests may show transient fixture timeouts when running the full suite sequentially (concurrent API load issue, not a Sprint 4 regression)

## Troubleshooting

| Issue | Resolution |
|-------|-----------|
| Pro warehouse returns Medium instead of Large | AI interpretation varies. The assertion accepts Large or bigger — if it returns Medium, the prompt may need strengthening. |
| Classic test returns Pro or Serverless | Ensure the prompt explicitly says "classic" and "legacy." The 3-message retry handles most cases. |
| Negative test returns DBSQL | The AI misinterpreted the request. Check that the prompt doesn't mention "SQL" or "warehouse." |
