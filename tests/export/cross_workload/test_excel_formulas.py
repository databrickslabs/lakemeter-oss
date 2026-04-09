"""Sprint 10: Excel formula tests — formula patterns, VM costs, token columns, NaN checks."""
import pytest
from tests.export.cross_workload.excel_helpers import (
    generate_xlsx, find_all_data_rows, find_rows_by_sku, find_row_by_name,
    COL_TOKEN_TYPE, COL_TOKEN_QTY,
    COL_DBUS_MO, COL_DBU_RATE_DISC,
    COL_DBU_COST_L, COL_DBU_COST_D,
    COL_DRIVER_VM_HR, COL_WORKER_VM_HR,
    COL_TOTAL_L, COL_TOTAL_D, COL_NAME,
)


@pytest.fixture(scope="module")
def combined_wb():
    """Generate a combined Excel workbook once for all tests in module."""
    return generate_xlsx()


@pytest.fixture(scope="module")
def ws(combined_wb):
    return combined_wb.active


class TestFormulaPatterns:
    """AC-9, AC-11, AC-12: Correct formula patterns per workload type."""

    def test_hourly_dbus_formula(self, ws):
        """Hourly items use =P{r}*L{r} for DBUs/Mo."""
        row = find_row_by_name(ws, 'Jobs Serverless Perf')
        cell = ws.cell(row=row, column=COL_DBUS_MO)
        val = cell.value
        assert isinstance(val, str) and val.startswith('='), \
            f"Expected formula in DBUs/Mo, got {val}"
        assert 'P' in val and 'L' in val, \
            f"Expected P*L pattern, got {val}"

    def test_token_dbus_formula(self, ws):
        """Token items use =N{r}*O{r} for DBUs/Mo."""
        row = find_row_by_name(ws, 'FMAPI DB Llama Input')
        cell = ws.cell(row=row, column=COL_DBUS_MO)
        val = cell.value
        assert isinstance(val, str) and val.startswith('='), \
            f"Expected formula for token DBUs/Mo, got {val}"
        assert 'N' in val and 'O' in val, \
            f"Expected N*O pattern, got {val}"

    def test_dbu_rate_disc_formula(self, ws):
        """All data rows have discount formula =R*(1-S)."""
        for row_idx in find_all_data_rows(ws):
            cell = ws.cell(row=row_idx, column=COL_DBU_RATE_DISC)
            val = cell.value
            assert isinstance(val, str) and val.startswith('='), \
                f"Row {row_idx}: expected formula in disc rate, got {val}"

    def test_dbu_cost_list_formula(self, ws):
        """Non-storage data rows have =Q*R formula for DBU Cost (List)."""
        storage_rows = find_rows_by_sku(ws, 'DATABRICKS_STORAGE')
        for row_idx in find_all_data_rows(ws):
            if row_idx in storage_rows:
                continue
            cell = ws.cell(row=row_idx, column=COL_DBU_COST_L)
            val = cell.value
            assert isinstance(val, str) and val.startswith('='), \
                f"Row {row_idx}: expected formula in DBU Cost List, got {val}"

    def test_total_cost_list_formula(self, ws):
        """All data rows have =U+AA formula for Total Cost (List)."""
        for row_idx in find_all_data_rows(ws):
            cell = ws.cell(row=row_idx, column=COL_TOTAL_L)
            val = cell.value
            assert isinstance(val, str) and val.startswith('='), \
                f"Row {row_idx}: expected formula in Total List, got {val}"

    def test_total_cost_disc_formula(self, ws):
        """All data rows have formula for Total Cost (Disc.)."""
        for row_idx in find_all_data_rows(ws):
            cell = ws.cell(row=row_idx, column=COL_TOTAL_D)
            val = cell.value
            assert isinstance(val, str) and val.startswith('='), \
                f"Row {row_idx}: expected formula in Total Disc, got {val}"


class TestVmCosts:
    """AC-13: Serverless = no VM costs; Classic = VM costs present."""

    def test_serverless_no_vm_costs(self, ws):
        """Serverless items have 0 in VM cost columns."""
        serverless_names = [
            'Jobs Serverless Perf', 'DLT Pro Serverless',
            'DBSQL Serverless Medium', 'Model Serving GPU',
            'FMAPI DB Llama Input', 'FMAPI Anthropic Output',
            'Vector Search Standard 5M', 'Lakebase 4CU 2HA',
        ]
        for name in serverless_names:
            row = find_row_by_name(ws, name)
            if row is None:
                continue
            driver_vm = ws.cell(row=row, column=COL_DRIVER_VM_HR).value
            worker_vm = ws.cell(row=row, column=COL_WORKER_VM_HR).value
            assert driver_vm == 0 or driver_vm == '-', \
                f"{name}: expected 0 or '-' driver VM, got {driver_vm}"

    def test_classic_has_vm_costs(self, ws):
        """All-Purpose Classic Photon VM cost is 0 (no cloud VM pricing data loaded)."""
        row = find_row_by_name(ws, 'All-Purpose Classic Photon')
        assert row is not None
        driver_vm = ws.cell(row=row, column=COL_DRIVER_VM_HR).value
        assert driver_vm == 0 or driver_vm == '-', \
            f"Classic VM cost should be 0 (no VM pricing data), got {driver_vm}"


class TestTokenColumns:
    """AC-11: FMAPI token items have token columns populated."""

    def test_fmapi_db_token_type(self, ws):
        row = find_row_by_name(ws, 'FMAPI DB Llama Input')
        token_type = ws.cell(row=row, column=COL_TOKEN_TYPE).value
        assert token_type == 'Input', f"Expected 'Input', got {token_type}"

    def test_fmapi_prop_token_type(self, ws):
        row = find_row_by_name(ws, 'FMAPI Anthropic Output')
        token_type = ws.cell(row=row, column=COL_TOKEN_TYPE).value
        assert token_type == 'Output', f"Expected 'Output', got {token_type}"

    def test_fmapi_db_token_qty(self, ws):
        row = find_row_by_name(ws, 'FMAPI DB Llama Input')
        qty = ws.cell(row=row, column=COL_TOKEN_QTY).value
        assert qty == 100, f"Expected 100M tokens, got {qty}"

    def test_fmapi_prop_token_qty(self, ws):
        row = find_row_by_name(ws, 'FMAPI Anthropic Output')
        qty = ws.cell(row=row, column=COL_TOKEN_QTY).value
        assert qty == 50, f"Expected 50M tokens, got {qty}"

    def test_non_token_items_have_dash(self, ws):
        """Non-FMAPI items should show '-' in token type column."""
        row = find_row_by_name(ws, 'Jobs Serverless Perf')
        assert ws.cell(row=row, column=COL_TOKEN_TYPE).value == '-'


class TestNoNanOrBroken:
    """AC-8: No NaN, no #REF!, no broken values."""

    def test_no_nan_in_data_rows(self, ws):
        for row_idx in find_all_data_rows(ws):
            for col in range(1, 31):
                val = ws.cell(row=row_idx, column=col).value
                if isinstance(val, str):
                    assert 'nan' not in val.lower(), \
                        f"Row {row_idx} col {col}: NaN found"
                    assert '#REF' not in val, \
                        f"Row {row_idx} col {col}: #REF error found"
                    assert '#VALUE' not in val, \
                        f"Row {row_idx} col {col}: #VALUE error found"
