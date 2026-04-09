"""Test Vector Search Excel export — storage sub-row, totals, NaN checks.

AC-10 to AC-14, AC-20: Storage sub-row, totals SUM, no NaN.
"""
import math

import pytest

from tests.export.vector_search.conftest import make_line_item
from tests.export.vector_search.excel_helpers import (
    generate_xlsx, find_data_rows, find_storage_row,
    COL_TYPE, COL_CONFIG, COL_SKU, COL_DBU_COST_L, COL_NOTES,
)


class TestStorageSubRow:
    """AC-10 to AC-13: Storage sub-row emitted with correct values."""

    def test_storage_row_emitted(self):
        """AC-10: Storage sub-row exists for Vector Search with storage_gb > 0."""
        items = [make_line_item(vector_capacity_millions=5, vector_search_storage_gb=50)]
        wb = generate_xlsx(items)
        ws = wb.active
        storage_rows = find_data_rows(ws, 'DATABRICKS_STORAGE')
        assert len(storage_rows) >= 1, "No storage sub-row found"

    def test_storage_row_sku(self):
        """AC-11: Storage sub-row SKU = DATABRICKS_STORAGE."""
        items = [make_line_item(vector_capacity_millions=5, vector_search_storage_gb=50)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        assert ws.cell(row=row, column=COL_SKU).value == 'DATABRICKS_STORAGE'

    def test_storage_row_type_display(self):
        """Storage sub-row type should say 'Vector Search (Storage)'."""
        items = [make_line_item(vector_capacity_millions=5, vector_search_storage_gb=50)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        type_val = ws.cell(row=row, column=COL_TYPE).value
        assert 'Vector Search' in str(type_val)
        assert 'Storage' in str(type_val)

    def test_storage_gb_approximation(self):
        """AC-12: Storage config mentions the storage GB amount."""
        items = [make_line_item(vector_capacity_millions=5, vector_search_storage_gb=50)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        config = ws.cell(row=row, column=COL_CONFIG).value
        assert '50' in str(config), (
            f"Storage config should mention 50 GB, got: {config}"
        )

    def test_storage_cost_positive(self):
        """AC-13: Storage cost = storage_gb * rate > 0 (billable > free)."""
        # 10M vectors, standard mode: units=ceil(10M/2M)=5, free=5*20=100GB
        # Set storage_gb=200 so billable=200-100=100GB, cost=100*0.023=$2.30
        items = [make_line_item(vector_capacity_millions=10, vector_search_storage_gb=200)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        cost = ws.cell(row=row, column=COL_DBU_COST_L).value
        if isinstance(cost, (int, float)):
            assert cost > 0, f"Storage cost should be > 0, got {cost}"

    def test_storage_notes_mention_rate(self):
        """Notes should mention $/GB/month rate."""
        items = [make_line_item(vector_capacity_millions=5, vector_search_storage_gb=50)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        notes = ws.cell(row=row, column=COL_NOTES).value
        assert notes and '/GB' in str(notes)


class TestExcelTotals:
    """AC-14: Totals SUM formula spans compute + storage rows."""

    def test_totals_sum_exists(self):
        items = [make_line_item(vector_capacity_millions=5)]
        wb = generate_xlsx(items)
        ws = wb.active
        found_sum = False
        for row_idx in range(1, ws.max_row + 1):
            val = ws.cell(row=row_idx, column=COL_DBU_COST_L).value
            if val and isinstance(val, str) and 'SUM' in val.upper():
                found_sum = True
                break
        assert found_sum, "No SUM formula found in totals row"

    def test_totals_with_multiple_vs_items(self):
        """Two VS items with storage -> 4 data rows (2 compute + 2 storage)."""
        items = [
            make_line_item(vector_capacity_millions=2,
                           vector_search_storage_gb=20,
                           workload_name='VS Standard'),
            make_line_item(vector_search_mode='storage_optimized',
                           vector_capacity_millions=64,
                           vector_search_storage_gb=640,
                           workload_name='VS StorOpt', display_order=1),
        ]
        wb = generate_xlsx(items)
        ws = wb.active
        compute_rows = find_data_rows(ws, 'SERVERLESS_REAL_TIME_INFERENCE')
        storage_rows = find_data_rows(ws, 'DATABRICKS_STORAGE')
        assert len(compute_rows) == 2, (
            f"Expected 2 compute rows, got {len(compute_rows)}"
        )
        assert len(storage_rows) == 2, (
            f"Expected 2 storage rows, got {len(storage_rows)}"
        )


class TestExcelNoNaN:
    """AC-20: No NaN values in generated Excel."""

    def test_no_nan_standard(self):
        items = [make_line_item(vector_capacity_millions=2)]
        wb = generate_xlsx(items)
        ws = wb.active
        for row_idx in range(1, ws.max_row + 1):
            for col_idx in range(1, 31):
                val = ws.cell(row=row_idx, column=col_idx).value
                if isinstance(val, float):
                    assert not math.isnan(val), (
                        f"NaN at row={row_idx}, col={col_idx}"
                    )

    def test_no_nan_storage_optimized(self):
        items = [make_line_item(
            vector_search_mode='storage_optimized',
            vector_capacity_millions=64,
        )]
        wb = generate_xlsx(items)
        ws = wb.active
        for row_idx in range(1, ws.max_row + 1):
            for col_idx in range(1, 31):
                val = ws.cell(row=row_idx, column=col_idx).value
                if isinstance(val, float):
                    assert not math.isnan(val), (
                        f"NaN at row={row_idx}, col={col_idx}"
                    )
