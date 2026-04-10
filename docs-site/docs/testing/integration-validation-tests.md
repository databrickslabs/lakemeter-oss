---
sidebar_position: 14
---

# Integration Validation Tests

The integration validation suite (`tests/test_integration_validation/`) verifies the completeness, coverage, and consistency of the entire Lakemeter test suite. It contains 141 tests across 4 files.

## Purpose

These tests answer the question: **"Is the test suite itself complete and correct?"** They validate:

- Every sprint has test files
- Every workload type has calculation and export tests
- Pricing data is consistent across all workloads
- The SP OAuth flow works end-to-end (when network is available)

## Test Files

### `test_suite_completeness.py` (44 tests)

Structural validation of the test directory:

| Test Area | Tests | What It Checks |
|-----------|-------|----------------|
| Sprint directories | 11 | Sprint directories 1-11 all exist |
| Support directories | 4 | `ai_assistant`, `regression`, `test_installation`, `test_integration_validation` exist |
| Conftest files | 9 | Each sprint directory (1-9) has a `conftest.py` |
| Test file counts | 11 | Minimum test files per directory (e.g., sprint_3 has >= 8 files) |
| Permission tests | 3 | Permission test file exists with 5 test classes and skip-guard |
| Package structure | 6 | `__init__.py` files in all test packages |

### `test_workload_coverage.py` (49 tests)

Validates that every workload type has adequate test coverage:

| Workload Type | Checks |
|--------------|--------|
| JOBS | Has calculation tests + export tests + AI tests |
| ALL_PURPOSE | Has calculation tests + export tests + AI tests |
| DLT | Has calculation tests (8+ files) + export tests + AI tests |
| DBSQL | Has calculation tests + export tests + AI tests |
| MODEL_SERVING | Has AI tests + combined validation tests |
| VECTOR_SEARCH | Has AI tests |
| FMAPI_DATABRICKS | Has pricing tests + AI tests |
| FMAPI_PROPRIETARY | Has edge case tests + AI tests |
| LAKEBASE | Has 7+ test files covering DBU calc, edge cases, Excel, SKU pricing |

Additional coverage checks:

- Multi-workload sprints (10, 11) have cross-workload and regression tests
- All 9 pricing data files exist, are valid JSON, and non-empty
- Manifest lists all 9 files with total entries > 4,000
- AI assistant has test coverage for JOBS and ALL_PURPOSE
- Regression test files exist for sprints 1-4

### `test_permission_flow.py` (7 tests, skip-guarded)

Live integration tests that verify the SP OAuth flow end-to-end. These tests are **skip-guarded** — they only run when the Databricks workspace is network-reachable.

| Test | What It Verifies |
|------|-----------------|
| Full SP OAuth flow | Token generation -> DB connection -> query execution |
| Token reuse | Same token works across multiple connections |
| App health endpoint | `GET /health` returns 200 with `status: healthy` |
| Pricing data access | All 14 workload types readable, names match expected set |
| DBU rates populated | DBU rate values are present and > 0 |

### `test_cross_feature_consistency.py` (41 tests)

Data consistency checks across all pricing files:

| Check Area | Tests | Validations |
|-----------|-------|-------------|
| DBU rates | 6 | All 3 clouds (AWS, Azure, GCP) present, all rates > 0 |
| Instance rates | 6 | All 3 clouds present, all rates > 0 |
| Multipliers | 6 | All 3 clouds present, all values > 0 |
| DBSQL rates | 4 | Non-empty, correct `cloud:type:size` key format |
| FMAPI (Databricks) | 4 | Non-empty, correct key format |
| FMAPI (Proprietary) | 4 | Non-empty, correct key format |
| Model Serving | 4 | Non-empty, correct key format |
| Vector Search | 4 | Non-empty, correct key format |
| Manifest integrity | 7 | File count = 9, total > 4000, all listed files exist |

## Running the Tests

```bash
cd "/path/to/lakemeter_app"
source .venv/bin/activate

# Run all integration validation tests
python -m pytest tests/test_integration_validation/ -v

# Run only the offline tests (no network required)
python -m pytest tests/test_integration_validation/ -v --ignore=tests/test_integration_validation/test_permission_flow.py

# Run the full suite including permission flow (requires network)
python -m pytest tests/test_integration_validation/ -v
```

## Test Results Summary

The full test suite (1,651 tests) breaks down as:

| Module | Tests |
|--------|-------|
| Sprint 1 — JOBS | 128 |
| Sprint 2 — ALL_PURPOSE | 101 |
| Sprint 3 — DLT | 157 |
| Sprint 4 — DBSQL | 146 |
| Sprint 5 — MODEL_SERVING | 125 |
| Sprint 6 — FMAPI_DATABRICKS | 135 |
| Sprint 7 — FMAPI_PROPRIETARY | 116 |
| Sprint 8 — VECTOR_SEARCH | 118 |
| Sprint 9 — LAKEBASE | 158 |
| Sprint 10 — Multi-Workload | 123 |
| Sprint 11 — ML Pipeline | 50 |
| AI Assistant | 348 |
| Regression | 52 |
| Installation Validation | 91 |
| **Integration Validation** | **141** |
| **Total** | **1,651** |
