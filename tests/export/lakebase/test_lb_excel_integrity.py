"""Test Lakebase Excel export — multi-item integrity and discount propagation.

Verifies:
- Multiple Lakebase items produce independent compute+storage row pairs
- Compute row discount columns are populated correctly
- Row ordering and adjacency rules hold with multiple items
"""
import pytest

from tests.export.lakebase.conftest import make_line_item
from tests.export.lakebase.excel_helpers import (
    generate_xlsx, find_compute_row, find_storage_row, find_data_rows,
    COL_SKU, COL_DBU_HR, COL_DISCOUNT, COL_DBU_RATE,
    COL_DBU_RATE_DISC, COL_DBU_COST_L, COL_DBU_COST_D,
)


class TestMultiItemExcel:
    """Verify multiple Lakebase items produce independent row pairs."""

    def test_two_items_produce_four_rows(self):
        items = [
            make_line_item(lakebase_cu=4, lakebase_ha_nodes=1,
                           lakebase_storage_gb=100, workload_name="DB-A"),
            make_line_item(lakebase_cu=16, lakebase_ha_nodes=2,
                           lakebase_storage_gb=500, workload_name="DB-B"),
        ]
        wb = generate_xlsx(items)
        ws = wb.active
        compute_rows = find_data_rows(ws, 'DATABASE_SERVERLESS_COMPUTE')
        storage_rows = find_data_rows(ws, 'DATABRICKS_STORAGE')
        assert len(compute_rows) == 2, (
            f"Expected 2 compute rows, got {len(compute_rows)}")
        assert len(storage_rows) == 2, (
            f"Expected 2 storage rows, got {len(storage_rows)}")

    def test_multi_item_row_pairing(self):
        """Each compute row is immediately followed by its storage row."""
        items = [
            make_line_item(lakebase_cu=4, lakebase_ha_nodes=1,
                           lakebase_storage_gb=100),
            make_line_item(lakebase_cu=16, lakebase_ha_nodes=2,
                           lakebase_storage_gb=500),
        ]
        wb = generate_xlsx(items)
        ws = wb.active
        compute_rows = find_data_rows(ws, 'DATABASE_SERVERLESS_COMPUTE')
        storage_rows = find_data_rows(ws, 'DATABRICKS_STORAGE')
        for c_row, s_row in zip(compute_rows, storage_rows):
            assert s_row == c_row + 1, (
                f"Storage row ({s_row}) not adjacent to compute ({c_row})")

    def test_multi_item_different_dbu_hr(self):
        """Each compute row has independent DBU/hr."""
        items = [
            make_line_item(lakebase_cu=4, lakebase_ha_nodes=1),
            make_line_item(lakebase_cu=16, lakebase_ha_nodes=2),
        ]
        wb = generate_xlsx(items)
        ws = wb.active
        compute_rows = find_data_rows(ws, 'DATABASE_SERVERLESS_COMPUTE')
        dbu_values = []
        for r in compute_rows:
            v = ws.cell(row=r, column=COL_DBU_HR).value
            if isinstance(v, (int, float)):
                dbu_values.append(v)
        assert len(dbu_values) == 2
        assert abs(dbu_values[0] - 4.0) < 0.01
        assert abs(dbu_values[1] - 32.0) < 0.01

    def test_three_items_produce_six_rows(self):
        """Three Lakebase items → 3 compute + 3 storage rows."""
        items = [
            make_line_item(lakebase_cu=0.5, lakebase_storage_gb=10),
            make_line_item(lakebase_cu=4, lakebase_storage_gb=100),
            make_line_item(lakebase_cu=32, lakebase_storage_gb=1000),
        ]
        wb = generate_xlsx(items)
        ws = wb.active
        compute_rows = find_data_rows(ws, 'DATABASE_SERVERLESS_COMPUTE')
        storage_rows = find_data_rows(ws, 'DATABRICKS_STORAGE')
        assert len(compute_rows) == 3
        assert len(storage_rows) == 3


class TestComputeDiscountPropagation:
    """Verify compute row discount columns are populated correctly."""

    def test_compute_discount_pct_present(self):
        items = [make_line_item(lakebase_cu=4, lakebase_ha_nodes=2)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None
        discount = ws.cell(row=row, column=COL_DISCOUNT).value
        assert discount is not None

    def test_compute_discounted_rate_present(self):
        items = [make_line_item(lakebase_cu=4, lakebase_ha_nodes=2)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None
        disc_rate = ws.cell(row=row, column=COL_DBU_RATE_DISC).value
        assert disc_rate is not None

    def test_compute_discounted_cost_present(self):
        items = [make_line_item(lakebase_cu=4, lakebase_ha_nodes=2)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None
        disc_cost = ws.cell(row=row, column=COL_DBU_COST_D).value
        assert disc_cost is not None

    def test_compute_at_zero_discount_list_equals_discounted(self):
        """At 0% discount, list cost == discounted cost."""
        items = [make_line_item(lakebase_cu=4, lakebase_ha_nodes=2)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None
        list_cost = ws.cell(row=row, column=COL_DBU_COST_L).value
        disc_cost = ws.cell(row=row, column=COL_DBU_COST_D).value
        if isinstance(list_cost, (int, float)) and isinstance(disc_cost, (int, float)):
            assert abs(disc_cost - list_cost) < 0.01

    def test_compute_discounted_rate_at_zero_discount(self):
        """At 0% discount, discounted rate == list rate."""
        items = [make_line_item(lakebase_cu=4, lakebase_ha_nodes=2)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None
        list_rate = ws.cell(row=row, column=COL_DBU_RATE).value
        disc_rate = ws.cell(row=row, column=COL_DBU_RATE_DISC).value
        if isinstance(list_rate, (int, float)) and isinstance(disc_rate, (int, float)):
            assert abs(disc_rate - list_rate) < 0.001
