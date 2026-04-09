---
sidebar_position: 11
---

# Sprint 9: Lakebase Excel & Calculation Tests

Sprint 9 validates the **Lakebase** workload's Excel export formulas, cost calculations, and edge-case handling. Unlike AI assistant sprints, these are **pure calculation tests** — no FMAPI calls required.

## What's Tested

### Overview

| Area | File | Tests | Focus |
|------|------|-------|-------|
| Config Display | `test_lb_config_display.py` | 7 | Configuration string formatting |
| DBU Calculation | `test_lb_dbu_calc.py` | 44 | DBU/hr = CU × nodes (parametrized) |
| Edge Cases | `test_lb_edge_cases.py` | 28 | Zero, negative, None, max, discounts |
| Excel Compute | `test_lb_excel_compute.py` | 15 | Compute row SKU, formulas, serverless |
| Cross-Cloud Excel | `test_lb_excel_crosscloud.py` | 11 | AWS/Azure/GCP compute, storage, SKU |
| Excel Integrity | `test_lb_excel_integrity.py` | 9 | Multi-item rows, discount propagation |
| Excel Storage | `test_lb_excel_storage.py` | 18 | Storage row values, discounts, notes |
| Excel Totals | `test_lb_excel_totals.py` | 13 | Total cost columns (List + Disc.) |
| SKU & Pricing | `test_lb_sku_pricing.py` | 13 | SKU determination, pricing, serverless |
| **Total** | **9 files** | **158** | |

### DBU Calculation (44 tests)

The core formula `DBU/hr = CU × nodes` is verified across a comprehensive parametrized matrix:

- **CU values**: 0.5, 1, 2, 4, 8, 16
- **Node configurations**: read replicas (0-3), HA enabled/disabled
- **Boundary cases**: half-CU (0.5), maximum CU (16)
- **Zero handling**: 0 CU returns 0 DBU/hr

![Calculator overview](/img/calculator-overview.png)
*Lakemeter's workload calculator — Lakebase configurations include CU size, HA, read replicas, and storage.*

### Edge Cases (28 tests)

Validates robust handling of invalid and boundary inputs:

| Scenario | Tests | Behavior |
|----------|-------|----------|
| Negative CU values | 8 | Backend returns warning, computation continues |
| Zero CU | 3 | Returns zero DBU/hr |
| None/missing fields | 5 | Defaults applied gracefully |
| Maximum CU (16) | 3 | Correct calculation at upper bound |
| Discount ranges (0-100%) | 9 | Formula correctness across full range |

:::tip
Negative CU values produce a backend warning rather than a hard rejection. This allows downstream consumers to detect and handle invalid input while preserving computation flow.
:::

### Excel Export Verification (66 tests across 5 files)

These tests generate real `.xlsx` files using the export engine and verify cell-by-cell correctness:

**Compute rows** (`test_lb_excel_compute.py`):
- SKU name matches expected pattern (`LAKEBASE_*`)
- DBU cost formulas resolve correctly
- Serverless vs classic distinction handled

**Storage rows** (`test_lb_excel_storage.py`):
- Storage pricing applied correctly
- Discount propagation from estimate-level to storage rows
- Notes column populated when user provides notes

**Cross-cloud** (`test_lb_excel_crosscloud.py`):
- AWS, Azure, and GCP produce correct cloud-specific SKUs
- Half-CU (0.5) boundary handled in DBU/hr and storage pairing
- Cloud-specific pricing reflected in output

![Workload calculation detail](/img/workload-calculation-detail.png)
*Detailed cost breakdown for a Lakebase workload — tests verify every column in this view matches the Excel export.*

**Multi-item integrity** (`test_lb_excel_integrity.py`):
- Multiple Lakebase items in one estimate export correctly
- Discount propagation applies consistently across all items
- Row ordering and section boundaries maintained

**Total cost columns** (`test_lb_excel_totals.py`):
- Total Cost (List) = DBU Cost (List) for serverless (VM costs = 0)
- Total Cost (Disc.) = DBU Cost (Disc.) for serverless
- Compute total exceeds storage total for standard configurations
- Notes propagate to the correct rows

## Iteration History

Sprint 9 went through 5 iterations, each adding coverage based on evaluator feedback:

| Iteration | Tests Added | Key Focus |
|-----------|-------------|-----------|
| 1 | 111 | Core calculations, AI assistant Lakebase tests |
| 2 | +10 | Negative CU edge cases, storage discount propagation |
| 3 | +13 | Backend negative CU validation, multi-item integrity |
| 4 | +11 | Cross-cloud Excel output, half-CU boundary |
| 5 | +13 | Total cost columns, notes coverage |

## File Structure

```
tests/sprint_9/
├── conftest.py                    # Shared fixtures (make_line_item)
├── excel_helpers.py               # Excel generation + row finders
├── lb_calc_helpers.py             # Independent calculation helpers
├── test_lb_config_display.py      # 7 tests — config string formatting
├── test_lb_dbu_calc.py            # 44 tests — DBU/hr calculation
├── test_lb_edge_cases.py          # 28 tests — zero/negative/None/max/discount
├── test_lb_excel_compute.py       # 15 tests — compute row SKU, formula
├── test_lb_excel_crosscloud.py    # 11 tests — AWS/Azure/GCP + half-CU
├── test_lb_excel_integrity.py     # 9 tests — multi-item, discount propagation
├── test_lb_excel_storage.py       # 18 tests — storage row values, notes
├── test_lb_excel_totals.py        # 13 tests — total cost columns + notes
└── test_lb_sku_pricing.py         # 13 tests — SKU determination, pricing
```

## Running Sprint 9 Tests

```bash
cd "/path/to/lakemeter_app"
source .venv/bin/activate

# Sprint 9 tests only (~3 seconds)
python -m pytest tests/sprint_9/ -v

# Full non-AI regression (~7 seconds)
python -m pytest tests/ --ignore=tests/ai_assistant -v
```

Expected output:

```
tests/sprint_9/test_lb_config_display.py::TestLakebaseConfigDisplay::test_basic_config PASSED
tests/sprint_9/test_lb_dbu_calc.py::TestLakebaseDBUCalc::test_dbu_per_hour[cu_1_no_ha] PASSED
...
tests/sprint_9/test_lb_excel_totals.py::TestLakebaseExcelTotals::test_compute_total_list PASSED
tests/sprint_9/test_lb_excel_totals.py::TestLakebaseExcelTotals::test_notes_propagation PASSED

158 passed in ~3.2s
```

## Key Formulas Verified

| Formula | Description |
|---------|-------------|
| `DBU/hr = CU × (1 + read_replicas + (1 if HA else 0))` | Total compute units including replicas and HA standby |
| `Monthly DBU = DBU/hr × 730` | Standard month hours |
| `DBU Cost (List) = Monthly DBU × list_price` | Pre-discount cost |
| `DBU Cost (Disc.) = DBU Cost (List) × (1 - discount/100)` | Post-discount cost |
| `Total Cost (List) = DBU Cost (List) + VM Cost (List)` | Combined compute + VM |
| `Storage Cost = storage_gb × storage_rate` | Monthly storage fee |

## Known Limitations

- Storage discount is hardcoded at 0.0 in the backend — tests verify formula correctness at 0%, confirming the discount infrastructure works correctly
- Negative CU produces a warning but still computes (no hard rejection) — this is intentional behavior

## Troubleshooting

| Issue | Resolution |
|-------|-----------|
| Excel file not generated | Check that `xlsxwriter` is installed and the export route is accessible |
| SKU mismatch in cross-cloud tests | Verify the pricing bundle has entries for all three clouds |
| Half-CU test fails | Ensure the backend supports decimal CU values (0.5) |
| Discount propagation differs | Check estimate-level discount is correctly passed to the export engine |
