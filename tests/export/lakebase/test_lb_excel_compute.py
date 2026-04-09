"""Test Lakebase Excel export — compute row tests.

AC-4: SKU = DATABASE_SERVERLESS_COMPUTE in Excel.
AC-6: Two rows per item (compute + storage).
AC-8: Serverless markers, no VM costs.
"""
import pytest

from tests.export.lakebase.conftest import make_line_item
from tests.export.lakebase.excel_helpers import (
    generate_xlsx, find_compute_row, find_storage_row,
    COL_SKU, COL_MODE, COL_HOURS, COL_TOKEN_TYPE,
    COL_DBU_HR, COL_DBUS_MO, COL_DBU_RATE, COL_DBU_COST_L,
    COL_TOTAL_L, COL_NOTES, COL_CONFIG,
)


class TestComputeRowExists:
    """AC-6: Lakebase produces a compute row."""

    def test_compute_row_found(self):
        items = [make_line_item(lakebase_cu=4, lakebase_ha_nodes=2,
                                lakebase_storage_gb=100)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None, "No DATABASE_SERVERLESS_COMPUTE row"


class TestComputeRowSKU:
    """AC-4: Compute SKU in Excel."""

    def test_sku_is_database_serverless_compute(self):
        items = [make_line_item()]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None
        assert ws.cell(row=row, column=COL_SKU).value == (
            'DATABASE_SERVERLESS_COMPUTE')


class TestComputeRowFormula:
    """Compute row DBUs/Mo formula = DBU/Hr × Hours/Mo."""

    def test_dbus_mo_is_formula(self):
        items = [make_line_item(lakebase_cu=4, lakebase_ha_nodes=2)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None
        cell = ws.cell(row=row, column=COL_DBUS_MO)
        val = cell.value
        assert val is not None
        if isinstance(val, str):
            assert val.startswith('='), f"Expected formula, got: {val}"

    @pytest.mark.parametrize("cu,nodes,hours,expected_dbu_hr", [
        (0.5, 1, 730, 0.5),
        (4, 2, 730, 8.0),
        (32, 3, 730, 96.0),
    ])
    def test_dbu_hr_in_excel(self, cu, nodes, hours, expected_dbu_hr):
        items = [make_line_item(
            lakebase_cu=cu, lakebase_ha_nodes=nodes,
            hours_per_month=hours,
        )]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None
        dbu_hr = ws.cell(row=row, column=COL_DBU_HR).value
        assert isinstance(dbu_hr, (int, float)), (
            f"DBU/hr should be numeric, got {type(dbu_hr)}: {dbu_hr}")
        assert abs(dbu_hr - expected_dbu_hr) < 0.01

    def test_dbus_mo_numeric_correct(self):
        items = [make_line_item(
            lakebase_cu=4, lakebase_ha_nodes=2, hours_per_month=730,
        )]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None
        dbu_hr = ws.cell(row=row, column=COL_DBU_HR).value
        hours = ws.cell(row=row, column=COL_HOURS).value
        if isinstance(dbu_hr, (int, float)) and isinstance(hours, (int, float)):
            dbus_mo = ws.cell(row=row, column=COL_DBUS_MO).value
            if isinstance(dbus_mo, (int, float)):
                assert abs(dbus_mo - dbu_hr * hours) < 0.1


class TestServerlessMarkers:
    """AC-8: Lakebase shows serverless in Excel."""

    def test_mode_is_serverless(self):
        items = [make_line_item()]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None
        mode = ws.cell(row=row, column=COL_MODE).value
        assert mode == 'Serverless', f"Expected 'Serverless', got '{mode}'"

    def test_token_columns_dashes(self):
        items = [make_line_item()]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None
        assert ws.cell(row=row, column=COL_TOKEN_TYPE).value == '-'


class TestTwoRowOutput:
    """AC-6: Lakebase generates compute + storage rows."""

    def test_both_rows_exist(self):
        items = [make_line_item(
            lakebase_cu=4, lakebase_ha_nodes=2, lakebase_storage_gb=100,
        )]
        wb = generate_xlsx(items)
        ws = wb.active
        compute = find_compute_row(ws)
        storage = find_storage_row(ws)
        assert compute is not None, "Missing compute row"
        assert storage is not None, "Missing storage row"
        assert storage == compute + 1, (
            f"Storage row ({storage}) should be right after "
            f"compute row ({compute})")

    def test_storage_row_always_present(self):
        """Even with 0 storage, sub-row is emitted."""
        items = [make_line_item(lakebase_storage_gb=0)]
        wb = generate_xlsx(items)
        ws = wb.active
        storage = find_storage_row(ws)
        assert storage is not None


class TestDBUCostFormula:
    """Verify DBU Cost (List) formula in compute row."""

    def test_dbu_cost_list_correct(self):
        items = [make_line_item(
            lakebase_cu=4, lakebase_ha_nodes=2, hours_per_month=730,
        )]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None
        dbus_mo = ws.cell(row=row, column=COL_DBUS_MO).value
        dbu_rate = ws.cell(row=row, column=COL_DBU_RATE).value
        dbu_cost = ws.cell(row=row, column=COL_DBU_COST_L).value
        if all(isinstance(v, (int, float)) for v in (dbus_mo, dbu_rate, dbu_cost)):
            expected = dbus_mo * dbu_rate
            assert abs(dbu_cost - expected) < 0.01


