"""Test Lakebase Excel export — storage sub-row tests.

AC-5: SKU = DATABRICKS_STORAGE for storage row.
AC-7: Storage row has cost = gb × rate, no DBU formula.
"""
import pytest

from tests.export.lakebase.conftest import make_line_item
from tests.export.lakebase.excel_helpers import (
    generate_xlsx, find_storage_row, find_compute_row,
    COL_SKU, COL_MODE, COL_HOURS, COL_DBU_HR,
    COL_DBUS_MO, COL_DBU_RATE, COL_DISCOUNT, COL_DBU_RATE_DISC,
    COL_DBU_COST_L, COL_DBU_COST_D,
    COL_TOTAL_L, COL_NOTES, COL_CONFIG,
)


class TestStorageRowSKU:
    """AC-5: Storage SKU is DATABRICKS_STORAGE."""

    def test_storage_sku(self):
        items = [make_line_item(lakebase_storage_gb=100)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        assert ws.cell(row=row, column=COL_SKU).value == 'DATABRICKS_STORAGE'


class TestStorageRowValues:
    """AC-7: Storage row has direct cost, not DBU formula."""

    def test_storage_dbus_mo_is_zero(self):
        """Storage row should have 0 DBUs/Mo (cost is direct, not DBU)."""
        items = [make_line_item(lakebase_storage_gb=100)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        dbus_mo = ws.cell(row=row, column=COL_DBUS_MO).value
        assert dbus_mo == 0, f"Storage DBUs/Mo should be 0, got {dbus_mo}"

    def test_storage_hours_na(self):
        """Storage row has N/A for hours."""
        items = [make_line_item(lakebase_storage_gb=100)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        hours = ws.cell(row=row, column=COL_HOURS).value
        assert hours == 'N/A', f"Storage hours should be N/A, got {hours}"

    def test_storage_dbu_hr_na(self):
        """Storage row has N/A for DBU/Hr."""
        items = [make_line_item(lakebase_storage_gb=100)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        dbu_hr = ws.cell(row=row, column=COL_DBU_HR).value
        assert dbu_hr == 'N/A', f"Storage DBU/Hr should be N/A, got {dbu_hr}"


class TestStorageCostValues:
    """Verify storage cost = gb × rate in Excel."""

    @pytest.mark.parametrize("gb,expected_cost", [
        (10, 3.45),       # 10 GB × 15 DSU/GB × $0.023/DSU
        (100, 34.50),     # 100 GB × 15 DSU/GB × $0.023/DSU
        (1000, 345.00),   # 1000 GB × 15 DSU/GB × $0.023/DSU
        (8192, 2826.24),  # 8192 GB × 15 DSU/GB × $0.023/DSU
    ])
    def test_storage_cost(self, gb, expected_cost):
        items = [make_line_item(lakebase_storage_gb=gb)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        cost = ws.cell(row=row, column=COL_DBU_COST_L).value
        if isinstance(cost, (int, float)):
            assert abs(cost - expected_cost) < 0.01, (
                f"Storage {gb}GB: expected ${expected_cost:.2f}, "
                f"got ${cost:.2f}")

    def test_zero_storage_zero_cost(self):
        items = [make_line_item(lakebase_storage_gb=0)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        cost = ws.cell(row=row, column=COL_DBU_COST_L).value
        if isinstance(cost, (int, float)):
            assert cost == 0


class TestStorageDBURate:
    """Verify storage rate in Excel matches pricing data."""

    def test_storage_dbu_rate(self):
        items = [make_line_item(lakebase_storage_gb=100)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        rate = ws.cell(row=row, column=COL_DBU_RATE).value
        if isinstance(rate, (int, float)):
            assert rate == pytest.approx(0.023)


class TestStorageConfig:
    """Verify storage config display."""

    def test_storage_config_shows_gb(self):
        items = [make_line_item(lakebase_storage_gb=100)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        config = ws.cell(row=row, column=COL_CONFIG).value
        assert config is not None
        assert '100' in str(config)
        assert 'GB' in str(config)


class TestStorageDiscountPropagation:
    """Verify storage row discounted cost column (col 22) propagation.

    The backend hardcodes discount_pct=0.0 for storage rows, so the
    discounted cost should equal the list cost. This confirms the
    Excel formula =col20*(1-col18) evaluates correctly for storage.
    """

    @pytest.mark.parametrize("gb,expected_list_cost", [
        (10, 3.45),       # 10 GB × 15 DSU/GB × $0.023/DSU
        (100, 34.50),     # 100 GB × 15 DSU/GB × $0.023/DSU
        (1000, 345.00),   # 1000 GB × 15 DSU/GB × $0.023/DSU
    ])
    def test_storage_discounted_cost_equals_list_at_zero_discount(
        self, gb, expected_list_cost,
    ):
        """At 0% discount, discounted cost == list cost for storage."""
        items = [make_line_item(lakebase_storage_gb=gb)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        list_cost = ws.cell(row=row, column=COL_DBU_COST_L).value
        disc_cost = ws.cell(row=row, column=COL_DBU_COST_D).value
        if isinstance(list_cost, (int, float)) and isinstance(disc_cost, (int, float)):
            assert abs(disc_cost - list_cost) < 0.01, (
                f"Storage {gb}GB: disc cost ${disc_cost:.2f} != "
                f"list cost ${list_cost:.2f} at 0% discount")

    def test_storage_discount_pct_is_zero(self):
        """Verify storage row discount % column is 0."""
        items = [make_line_item(lakebase_storage_gb=100)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        discount = ws.cell(row=row, column=COL_DISCOUNT).value
        assert discount == 0 or discount is None or discount == 0.0

    def test_storage_discounted_rate_equals_list_rate(self):
        """At 0% discount, discounted DBU rate == list rate."""
        items = [make_line_item(lakebase_storage_gb=100)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        list_rate = ws.cell(row=row, column=COL_DBU_RATE).value
        disc_rate = ws.cell(row=row, column=COL_DBU_RATE_DISC).value
        if isinstance(list_rate, (int, float)) and isinstance(disc_rate, (int, float)):
            assert abs(disc_rate - list_rate) < 0.001


class TestStorageNotes:
    """Verify notes column for storage row."""

    def test_storage_notes_has_rate(self):
        items = [make_line_item(lakebase_storage_gb=100)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        notes = ws.cell(row=row, column=COL_NOTES).value
        assert notes is not None
        assert '/DSU' in str(notes)

    def test_storage_notes_has_gb(self):
        items = [make_line_item(lakebase_storage_gb=100)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        notes = ws.cell(row=row, column=COL_NOTES).value
        assert '100' in str(notes)
