"""Sprint 5: Totals row, cost summary, and DBU summary verification.

Verifies that the totals SUM formulas span all data rows, the cost summary
references the totals row correctly, and annual = monthly × 12.
"""
import pytest
from xlsxwriter.utility import xl_col_to_name as _col

from tests.regression.excel_helpers import (
    generate_xlsx, find_all_data_rows, find_totals_row,
    find_cost_summary_header, find_dbu_summary_row, find_rows_by_sku,
    COL_DBUS_MO, COL_DBU_COST_L, COL_DBU_COST_D,
    COL_DRIVER_VM_COST, COL_WORKER_VM_COST, COL_TOTAL_VM,
    COL_TOTAL_L, COL_TOTAL_D,
)
from tests.regression.conftest import make_all_regression_items


@pytest.fixture(scope="module")
def ws():
    return generate_xlsx().active


class TestTotalsRowIntegrity:
    """Totals row exists and its SUM formulas span the full data range."""

    def test_totals_row_exists(self, ws):
        assert find_totals_row(ws) is not None

    def test_totals_after_all_data(self, ws):
        data_rows = find_all_data_rows(ws)
        totals = find_totals_row(ws)
        assert totals > max(data_rows)

    @pytest.mark.parametrize("col", [
        COL_DBUS_MO, COL_DBU_COST_L, COL_DBU_COST_D,
        COL_DRIVER_VM_COST, COL_WORKER_VM_COST, COL_TOTAL_VM,
        COL_TOTAL_L, COL_TOTAL_D,
    ])
    def test_sum_formula_spans_all_data(self, ws, col):
        """Each totals column has =SUM() spanning first to last data row."""
        totals = find_totals_row(ws)
        cell = ws.cell(row=totals, column=col)
        val = cell.value
        assert isinstance(val, str) and val.startswith('=SUM('), \
            f"Totals col {col}: expected SUM, got {val}"
        data_rows = find_all_data_rows(ws)
        first = min(data_rows)
        last = max(data_rows)
        col_letter = _col(col - 1)  # 0-indexed for xl_col_to_name
        expected = f'{col_letter}{first}:{col_letter}{last}'
        assert expected in val, \
            f"Col {col}: expected range {expected} in {val}"

    def test_storage_rows_inside_sum_range(self, ws):
        """Storage sub-rows are within the SUM range."""
        data_rows = find_all_data_rows(ws)
        storage = find_rows_by_sku(ws, 'DATABRICKS_STORAGE')
        first = min(data_rows)
        last = max(data_rows)
        for sr in storage:
            assert first <= sr <= last, \
                f"Storage row {sr} outside range [{first}, {last}]"


class TestCostSummarySection:
    """Cost summary references totals row correctly, annual = monthly × 12."""

    def test_cost_summary_exists(self, ws):
        header = find_cost_summary_header(ws)
        assert header is not None, "COST SUMMARY section not found"

    def test_monthly_row_references_totals(self, ws):
        """Monthly row formulas reference the totals row."""
        header = find_cost_summary_header(ws)
        totals = find_totals_row(ws)
        # Monthly row is header + 2 (after sub-headers)
        monthly_row = header + 2
        monthly_val = ws.cell(row=monthly_row, column=1).value
        assert monthly_val == 'Monthly', \
            f"Expected 'Monthly' at row {monthly_row}, got {monthly_val}"

        totals_1idx = totals  # already 1-indexed
        # Check that at least the first value column references the totals row
        for c in range(2, 9):
            cell_val = ws.cell(row=monthly_row, column=c).value
            if isinstance(cell_val, str) and cell_val.startswith('='):
                assert str(totals_1idx) in cell_val, \
                    f"Monthly col {c}: formula {cell_val} doesn't ref totals row {totals_1idx}"

    def test_annual_is_monthly_times_12(self, ws):
        """Annual row formulas multiply the monthly row by 12."""
        header = find_cost_summary_header(ws)
        monthly_row = header + 2
        annual_row = header + 3
        annual_val = ws.cell(row=annual_row, column=1).value
        assert annual_val == 'Annual', \
            f"Expected 'Annual' at row {annual_row}, got {annual_val}"
        for c in range(2, 9):
            cell_val = ws.cell(row=annual_row, column=c).value
            if isinstance(cell_val, str) and cell_val.startswith('='):
                assert '*12' in cell_val, \
                    f"Annual col {c}: formula {cell_val} missing *12"
                assert str(monthly_row) in cell_val, \
                    f"Annual col {c}: formula {cell_val} doesn't ref monthly row"


class TestDbuSummary:
    """DBU summary total matches the totals row DBUs/Mo."""

    def test_dbu_summary_exists(self, ws):
        assert find_dbu_summary_row(ws) is not None

    def test_dbu_summary_formula(self, ws):
        """DBU summary uses SUM over the same data range as totals."""
        dbu_row = find_dbu_summary_row(ws)
        # The summary value is in column 3 (C)
        cell = ws.cell(row=dbu_row, column=3)
        val = cell.value
        assert isinstance(val, str) and val.startswith('=SUM('), \
            f"DBU summary: expected SUM formula, got {val}"
        data_rows = find_all_data_rows(ws)
        first = min(data_rows)
        last = max(data_rows)
        col_letter = _col(COL_DBUS_MO - 1)
        expected = f'{col_letter}{first}:{col_letter}{last}'
        assert expected in val, \
            f"DBU summary: expected range {expected} in {val}"


class TestCrossCloudExcelGeneration:
    """Excel generation works for all 3 clouds with all 26 items."""

    @pytest.mark.parametrize("cloud", ["aws", "azure", "gcp"])
    def test_generates_all_rows(self, cloud):
        wb = generate_xlsx(cloud=cloud)
        ws = wb.active
        data_rows = find_all_data_rows(ws)
        # 26 items + storage sub-rows for 2 Lakebase + 1 VS (with storage) = 29
        assert len(data_rows) >= 26, \
            f"{cloud}: expected >= 26 data rows, got {len(data_rows)}"

    @pytest.mark.parametrize("cloud", ["aws", "azure", "gcp"])
    def test_totals_row_exists(self, cloud):
        wb = generate_xlsx(cloud=cloud)
        ws = wb.active
        assert find_totals_row(ws) is not None

    @pytest.mark.parametrize("cloud", ["aws", "azure", "gcp"])
    def test_no_nan_in_totals(self, cloud):
        wb = generate_xlsx(cloud=cloud)
        ws = wb.active
        totals = find_totals_row(ws)
        for c in range(1, 31):
            v = ws.cell(row=totals, column=c).value
            if isinstance(v, str):
                assert 'nan' not in v.lower(), \
                    f"{cloud} totals col {c}: NaN"


class TestEdgeCases:
    """Empty estimates and single-item estimates produce valid structure."""

    def test_empty_estimate(self):
        wb = generate_xlsx(line_items=[])
        ws = wb.active
        assert len(find_all_data_rows(ws)) == 0
        # Totals row should still exist
        assert find_totals_row(ws) is not None

    def test_single_item(self):
        from tests.regression.conftest import make_jobs_classic
        wb = generate_xlsx(line_items=[make_jobs_classic()])
        ws = wb.active
        assert len(find_all_data_rows(ws)) == 1
        assert find_totals_row(ws) is not None
        assert find_cost_summary_header(ws) is not None
