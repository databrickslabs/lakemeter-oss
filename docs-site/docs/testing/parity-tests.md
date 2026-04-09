---
sidebar_position: 2
---

# Parity Tests (UI vs Excel Export)

The parity test suite verifies that Lakemeter's Excel export produces cost values identical to those displayed in the browser UI. These tests were introduced in Sprint 1-3 of the Excel Export Parity Fix project.

## Purpose

Lakemeter has two independent calculation paths:

1. **Frontend** (`frontend/src/utils/costCalculation.ts`) — calculates costs for the browser UI
2. **Backend** (`backend/app/routes/export/`) — independently calculates costs for the Excel export

These paths can diverge, producing mismatched numbers. The parity test framework systematically verifies every workload type and configuration against both paths, ensuring the Excel export is pixel-perfect with the UI.

## Test Architecture

```
tests/parity/
├── frontend_calc.py              # Python reimplementation of frontend formulas
├── test_parity_jobs.py           # Jobs Classic, Photon, Serverless
├── test_parity_allpurpose.py     # All-Purpose Classic, Photon, Serverless
├── test_parity_dlt.py            # DLT Core/Pro/Advanced x Classic/Photon/Serverless
├── test_parity_dbsql.py          # DBSQL Classic/Pro/Serverless x 9 sizes
├── test_parity_vector_search.py  # Vector Search Standard/Storage-Optimized
├── test_parity_model_serving.py  # Model Serving all GPU types
└── test_parity_lakebase.py       # Lakebase CU sizes, HA nodes, storage
```

## Comparison Methodology

For each workload configuration, the tests compare:

| Comparison Point | Description | Tolerance |
|-----------------|-------------|-----------|
| **DBU/hr** | Computed DBU rate per hour | $0.01 |
| **$/DBU** | Price per DBU from pricing lookup | Exact match |
| **Hours/month** | From config or run-based calculation | Exact match |
| **Monthly DBUs** | DBU/hr x Hours/month | $0.01 |
| **Monthly DBU cost** | Monthly DBUs x $/DBU | $0.01 |
| **VM cost** | Driver + worker VM costs (where applicable) | $0.01 |
| **Total monthly cost** | DBU cost + VM cost | $0.01 |
| **SKU product type** | Correct SKU used for pricing lookup | Exact match |
| **Storage costs** | For Vector Search and Lakebase sub-rows | $0.01 |

## Running the Tests

```bash
# Run all parity tests
pytest tests/parity/ -v

# Run by workload type
pytest tests/parity/test_parity_jobs.py -v
pytest tests/parity/test_parity_dlt.py -v
pytest tests/parity/test_parity_dbsql.py -v
pytest tests/parity/test_parity_vector_search.py -v
pytest tests/parity/test_parity_model_serving.py -v
pytest tests/parity/test_parity_lakebase.py -v
```

All parity tests are non-AI and run in under 5 seconds.

## Test Coverage by Sprint

### Sprint 1: Jobs + All-Purpose (18 tests)

| Workload | Configuration | Tests |
|----------|--------------|-------|
| Jobs | Classic (2, 4, 8 workers) | 3 |
| Jobs | Classic (0 workers, driver only) | 1 |
| Jobs | Classic (run-based hours) | 1 |
| Jobs | Photon (2, 6 workers) | 2 |
| Jobs | Serverless Standard | 1 |
| Jobs | Serverless Performance | 1 |
| Jobs | Unknown instance fallback | 1 |
| All-Purpose | Classic (3 workers) | 1 |
| All-Purpose | Photon (2, 10 workers) | 2 |
| All-Purpose | Serverless (always 2x) | 1 |
| All-Purpose | Serverless ignores standard mode | 1 |
| All-Purpose | Unknown instance fallback | 1 |
| All-Purpose | Zero workers | 1 |
| General | Days per month default (22) | 1 |

**Bugs found and fixed**:
- Driver DBU fallback rate: 0.25 -> 0.5 (aligned with frontend)
- Vector Search storage sub-row: AttributeError on missing field (safe getattr)
- Fallback warning message said "0.25" but actual value was 0.5

### Sprint 2: DLT + DBSQL (76 tests)

| Workload | Configuration | Tests |
|----------|--------------|-------|
| DLT | Core/Pro/Advanced x Classic/Photon/Serverless (all 9 combos) | 12 |
| DLT | Zero workers, default edition, run-based hours | 3 |
| DBSQL | Classic x 9 sizes (DBU/hr + monthly cost) | 18 |
| DBSQL | Pro x 9 sizes | 18 |
| DBSQL | Serverless x 9 sizes | 18 |
| DBSQL | Multi-cluster (1-5 clusters, various types) | 9 |
| DBSQL | Default type/size, empty size, null clusters, run-based | 5 |

**Bugs found and fixed**:
- Frontend DLT serverless photon lookup hardcoded to `DLT_CORE_COMPUTE` instead of edition-specific SKU

### Sprint 3: Vector Search + Model Serving + Lakebase (58 tests)

| Workload | Configuration | Tests |
|----------|--------------|-------|
| Vector Search | Standard mode (6 capacity levels) | 6 |
| Vector Search | Storage-Optimized mode (4 capacity levels) | 4 |
| Vector Search | Storage sub-rows (5 scenarios) | 5 |
| Vector Search | Total cost (compute + storage) | 3 |
| Model Serving | All 7 AWS GPU types | 7 |
| Model Serving | Case-insensitive GPU names | 1 |
| Model Serving | Run-based usage | 1 |
| Model Serving | Parametrized cost matrix (all GPUs) | 8 |
| Lakebase | CU sizes (1, 2, 4, 8, 16) | 5 |
| Lakebase | HA nodes (1, 2, 3 with CU combos) | 6 |
| Lakebase | Storage DSU pricing (100-8192 GB) | 4 |
| Lakebase | Total cost (compute + storage) | 3 |
| Lakebase | Run-based usage | 1 |
| Lakebase | Edge cases (CU=0, storage=None, zero) | 4 |

**No backend code changes were needed** — existing export calculations already matched the frontend for all three workload types.

## Total Test Count

| Sprint | New Parity Tests | Cumulative Total |
|--------|-----------------|------------------|
| Sprint 1 | 18 | 18 |
| Sprint 2 | 76 | 94 |
| Sprint 3 | 58 | 152 |

Combined with all existing tests: **1,884 tests passing** as of Sprint 3 completion.

## Writing New Parity Tests

To add parity tests for a new configuration:

1. Add the frontend calculation to `tests/parity/frontend_calc.py`
2. Create a test that constructs a `LineItem` with known inputs
3. Call both the frontend calc helper and the backend export function
4. Assert that all comparison points match within $0.01 tolerance

```python
def test_new_config(self, make_line_item):
    item = make_line_item(
        workload_type="JOBS",
        num_workers=4,
        photon_enabled=True,
        # ... other config
    )
    fe_result = fe_jobs_cost(item)
    be_result = be_export_calc(item)
    assert abs(fe_result.dbu_per_hour - be_result.dbu_per_hour) < 0.01
    assert fe_result.sku == be_result.sku
```
