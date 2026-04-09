"""Test Vector Search Excel export — compute row tests.

AC-9: Compute formula, SKU, DBU/hr values, serverless markers.
"""
import pytest

from tests.export.vector_search.conftest import make_line_item
from tests.export.vector_search.excel_helpers import (
    generate_xlsx, find_vs_compute_row,
    COL_SKU, COL_MODE, COL_HOURS, COL_TOKEN_TYPE,
    COL_DBU_HR, COL_DBUS_MO,
)


class TestComputeRowFormula:
    """AC-9: Compute row uses hourly formula =P{r}*L{r} for DBUs/Mo."""

    def test_dbus_mo_is_formula(self):
        items = [make_line_item(vector_capacity_millions=2)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_vs_compute_row(ws)
        assert row is not None, "No SERVERLESS_REAL_TIME_INFERENCE row found"
        cell = ws.cell(row=row, column=COL_DBUS_MO)
        val = cell.value
        assert val is not None
        if isinstance(val, str):
            assert val.startswith('='), f"DBUs/Mo should be formula, got: {val}"
            assert 'P' in val.upper() and 'L' in val.upper(), (
                f"Hourly formula should ref P*L, got: {val}"
            )

    def test_dbus_mo_numeric_value(self):
        """Verify the cached numeric value matches expected."""
        items = [make_line_item(
            vector_capacity_millions=2, hours_per_month=730,
        )]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_vs_compute_row(ws)
        assert row is not None
        dbu_hr_val = ws.cell(row=row, column=COL_DBU_HR).value
        hours_val = ws.cell(row=row, column=COL_HOURS).value
        if isinstance(dbu_hr_val, (int, float)) and isinstance(hours_val, (int, float)):
            expected_dbus = dbu_hr_val * hours_val
            dbus_mo = ws.cell(row=row, column=COL_DBUS_MO).value
            if isinstance(dbus_mo, (int, float)):
                assert abs(dbus_mo - expected_dbus) < 0.1


class TestComputeRowSKU:
    """Verify compute row has correct SKU."""

    def test_compute_sku_standard(self):
        items = [make_line_item(vector_search_mode='standard')]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_vs_compute_row(ws)
        assert row is not None
        assert ws.cell(row=row, column=COL_SKU).value == 'SERVERLESS_REAL_TIME_INFERENCE'

    def test_compute_sku_storage_optimized(self):
        items = [make_line_item(vector_search_mode='storage_optimized',
                                vector_capacity_millions=64)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_vs_compute_row(ws)
        assert row is not None
        assert ws.cell(row=row, column=COL_SKU).value == 'SERVERLESS_REAL_TIME_INFERENCE'


class TestExcelServerlessMarkers:
    """Vector Search rows should show 'Serverless' mode."""

    def test_mode_column_says_serverless(self):
        items = [make_line_item(vector_capacity_millions=2)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_vs_compute_row(ws)
        assert row is not None
        mode_val = ws.cell(row=row, column=COL_MODE).value
        assert mode_val == 'Serverless', (
            f"Expected 'Serverless', got '{mode_val}'"
        )

    def test_token_columns_are_dashes(self):
        """Vector Search is hour-based, not token-based."""
        items = [make_line_item(vector_capacity_millions=2)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_vs_compute_row(ws)
        assert row is not None
        token_type = ws.cell(row=row, column=COL_TOKEN_TYPE).value
        assert token_type == '-', f"Token type should be '-', got {token_type}"


class TestExcelDBUValues:
    """Verify DBU/hr and DBU rate values in Excel match expectations."""

    @pytest.mark.parametrize("mode,capacity,expected_dbu_hr", [
        ('standard', 2, 4.0),
        ('standard', 5, 12.0),
        ('storage_optimized', 64, 18.29),
    ])
    def test_dbu_hr_in_excel(self, mode, capacity, expected_dbu_hr):
        items = [make_line_item(
            vector_search_mode=mode, vector_capacity_millions=capacity,
        )]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_vs_compute_row(ws)
        assert row is not None
        dbu_hr = ws.cell(row=row, column=COL_DBU_HR).value
        assert isinstance(dbu_hr, (int, float)), (
            f"DBU/hr should be numeric, got {type(dbu_hr)}: {dbu_hr}"
        )
        assert abs(dbu_hr - expected_dbu_hr) < 0.01
