---
sidebar_position: 4
---

# Sprint 3: DLT Calculation Tests

Sprint 3 validates the **Delta Live Tables (DLT)** cost calculation logic across both frontend and backend, covering all three editions (Core, Pro, Advanced), classic and serverless compute modes, Photon pricing, SKU alignment, and Excel export accuracy.

## What's Tested

Sprint 3 contains **161 tests** across 12 test files — the largest test suite in the project. Unlike Sprints 1-2, these tests do **not** call the AI assistant. Instead, they directly test the calculation functions and export pipeline.

### Test Categories

| Category | Files | Tests | What's Verified |
|----------|-------|-------|----------------|
| **Classic Calculations** | `test_dlt_calc_classic.py` | 25 | Hours/month, DBU rates, edition multipliers, Photon pricing |
| **Serverless Calculations** | `test_dlt_calc_serverless.py` | 26 | Serverless DBU rates, edge cases, NaN guards |
| **SKU Discrepancies** | `test_dlt_disc_sku.py` | 16 | Frontend-backend SKU name alignment |
| **Pricing Discrepancies** | `test_dlt_disc_pricing.py` | 19 | Frontend-backend calculation alignment |
| **Export SKU Lookup** | `test_dlt_export_sku.py` | 17 | Backend SKU + DBU price resolution |
| **Export Calculations** | `test_dlt_export_calc.py` | 14 | Backend hours, serverless, calc pipeline |
| **Excel Formulas** | `test_dlt_excel_e2e_formulas.py` | 10 | Real .xlsx formula cell verification |
| **Excel Totals** | `test_dlt_excel_e2e_totals.py` | 5 | Real .xlsx SUM formula verification |
| **Excel Display** | `test_dlt_excel_export.py` | 22 | Display names, pipeline editions, matrix coverage |
| **VM Costs** | `test_dlt_vm_costs.py` | 7 | VM cost dollar amounts for node types |

![Workload Calculation Detail](/img/workload-calculation-detail.png)
*DLT workload configuration with cost breakdown — Sprint 3 tests verify every number in this view is calculated correctly.*

### Hours Calculation

DLT workloads support two methods for specifying usage:

1. **Direct hours**: `hours_per_month = 730` (24/7 operation)
2. **Run-based**: `runs_per_day × avg_runtime_minutes × days_per_month / 60`

When both are provided, run-based takes priority. Tests verify this precedence:

```python
def test_run_based_priority_over_hours(self):
    result = frontend_calc_dlt(
        runs_per_day=10, avg_runtime_minutes=30, days_per_month=22,
        hours_per_month=730,  # This should be ignored
    )
    assert result["hours_per_month"] == pytest.approx(110.0)  # 10 * 30 * 22 / 60
```

### Edition Multipliers

DLT has three editions with different DBU multipliers:

| Edition | Multiplier | Use Case |
|---------|-----------|----------|
| **Core** | 1.0x | Basic ETL pipelines |
| **Pro** | 1.0x (same rate, different SKU) | CDC, SCD Type 2 |
| **Advanced** | 1.0x (same rate, different SKU) | Full monitoring, expectations |

Tests verify that the correct SKU is selected for each edition and that multipliers are applied correctly to DBU calculations.

### Photon Pricing

Photon-enabled DLT workloads use different DBU rates. Tests verify:

- Photon SKU is selected when `photon_enabled=True`
- Non-Photon SKU is used when `photon_enabled=False`
- The DBU rate difference is correctly reflected in cost calculations

### Excel Export Verification

Sprint 3 includes end-to-end Excel tests that:

1. Generate a real `.xlsx` file using the export pipeline
2. Open it with `openpyxl` and verify cell formulas
3. Check that SUM formulas in totals rows reference the correct cell ranges
4. Validate display names match expected DLT terminology

![Estimates List](/img/estimates-list.png)
*The estimates list with export option — Sprint 3 tests verify the exported Excel files contain accurate formulas.*

## Running Sprint 3 Tests

```bash
cd "/path/to/lakemeter_app"
source .venv/bin/activate
python -m pytest tests/sprint_3/ -v
```

Expected output:

```
tests/sprint_3/test_dlt_calc_classic.py::TestDLTHoursCalculation::test_direct_hours_24x7 PASSED
tests/sprint_3/test_dlt_calc_classic.py::TestDLTHoursCalculation::test_run_based_24_runs_60min_30days PASSED
...
tests/sprint_3/test_dlt_excel_e2e_formulas.py::TestDLTExcelFormulas::test_formula_structure PASSED
tests/sprint_3/test_dlt_vm_costs.py::TestDLTVMCosts::test_m6i_xlarge_cost PASSED

161 passed in ~2s
```

:::tip Fast Execution
Sprint 3 tests run in under 2 seconds because they don't make any AI API calls. They test calculation logic directly using imported Python functions.
:::

## Shared Calculation Helpers

The `dlt_calc_helpers.py` module provides shared functions that mirror the frontend and backend calculation logic:

```python
def frontend_calc_dlt(
    driver_dbu_rate, worker_dbu_rate, num_workers,
    dlt_edition, hours_per_month=0,
    runs_per_day=0, avg_runtime_minutes=0, days_per_month=22,
    photon_enabled=False, serverless_enabled=False,
) -> dict:
    """Replicate frontend DLT cost calculation."""
    # Returns: hours_per_month, dbu_per_hour, monthly_dbus, dbu_cost
```

This ensures tests validate the same calculation path that users see in the browser.

## Known Limitations

- Backend DLT Photon SKU and Serverless SKU discrepancies are **documented**, not fixed (by design — these are known differences between frontend display names and backend SKU lookup keys)
- Tests use `pytest.approx()` for floating-point comparisons to avoid precision issues
- Excel formula tests require `openpyxl` as a test dependency

## Troubleshooting

| Issue | Resolution |
|-------|-----------|
| `ModuleNotFoundError: tests.sprint_3.dlt_calc_helpers` | Run from the project root directory so Python can find the test modules. |
| `FileNotFoundError` on Excel tests | The export endpoint must be accessible. Ensure the backend can connect to Lakebase. |
| `AssertionError: NaN != 0` | A NaN guard test caught an edge case where division by zero produces NaN. This is expected behavior — the test verifies the guard works. |
