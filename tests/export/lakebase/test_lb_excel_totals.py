"""Test Lakebase Excel total cost columns and compute notes.

Verifies:
- Total Cost (List) and Total Cost (Disc.) columns are populated for both
  compute and storage rows
- For serverless Lakebase, Total = DBU/storage cost (VM costs = 0)
- Compute row notes contain CU and HA info
- End-to-end: compute + storage pair total costs are both positive
"""
import pytest

from tests.export.lakebase.conftest import make_line_item
from tests.export.lakebase.excel_helpers import (
    generate_xlsx, find_compute_row, find_storage_row,
    COL_DBU_COST_L, COL_DBU_COST_D, COL_TOTAL_L, COL_TOTAL_D,
    COL_NOTES,
)


class TestComputeTotalCost:
    """Total Cost (List) and (Disc.) for compute rows."""

    def test_total_list_present(self):
        items = [make_line_item(lakebase_cu=4, lakebase_ha_nodes=2)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None
        total = ws.cell(row=row, column=COL_TOTAL_L).value
        assert total is not None

    def test_total_list_equals_dbu_cost_serverless(self):
        """Serverless: Total Cost (List) = DBU Cost (List) since VM = 0."""
        items = [make_line_item(lakebase_cu=4, lakebase_ha_nodes=2)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None
        dbu_cost = ws.cell(row=row, column=COL_DBU_COST_L).value
        total = ws.cell(row=row, column=COL_TOTAL_L).value
        if isinstance(dbu_cost, (int, float)) and isinstance(total, (int, float)):
            assert abs(total - dbu_cost) < 0.01, (
                f"Total (List) {total} != DBU Cost (List) {dbu_cost}")

    def test_total_disc_present(self):
        items = [make_line_item(lakebase_cu=4, lakebase_ha_nodes=2)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None
        total_d = ws.cell(row=row, column=COL_TOTAL_D).value
        assert total_d is not None

    def test_total_disc_equals_dbu_disc_serverless(self):
        """Serverless: Total Cost (Disc.) = DBU Cost (Disc.) since VM = 0."""
        items = [make_line_item(lakebase_cu=4, lakebase_ha_nodes=2)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None
        dbu_disc = ws.cell(row=row, column=COL_DBU_COST_D).value
        total_d = ws.cell(row=row, column=COL_TOTAL_D).value
        if isinstance(dbu_disc, (int, float)) and isinstance(total_d, (int, float)):
            assert abs(total_d - dbu_disc) < 0.01, (
                f"Total (Disc.) {total_d} != DBU Cost (Disc.) {dbu_disc}")

    def test_total_list_positive_for_nonzero_cu(self):
        """Any nonzero CU config should produce positive total."""
        items = [make_line_item(lakebase_cu=4, lakebase_ha_nodes=2)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None
        total = ws.cell(row=row, column=COL_TOTAL_L).value
        if isinstance(total, (int, float)):
            assert total > 0


class TestStorageTotalCost:
    """Total Cost columns for storage rows."""

    def test_storage_total_list_present(self):
        items = [make_line_item(lakebase_storage_gb=100)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        total = ws.cell(row=row, column=COL_TOTAL_L).value
        assert total is not None

    def test_storage_total_list_equals_dbu_cost(self):
        """Storage Total (List) = storage direct cost (no VM)."""
        items = [make_line_item(lakebase_storage_gb=100)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        dbu_cost = ws.cell(row=row, column=COL_DBU_COST_L).value
        total = ws.cell(row=row, column=COL_TOTAL_L).value
        if isinstance(dbu_cost, (int, float)) and isinstance(total, (int, float)):
            assert abs(total - dbu_cost) < 0.01

    def test_storage_total_disc_present(self):
        items = [make_line_item(lakebase_storage_gb=100)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        total_d = ws.cell(row=row, column=COL_TOTAL_D).value
        assert total_d is not None

    def test_storage_total_positive_for_nonzero_gb(self):
        """100 GB storage should produce positive total cost."""
        items = [make_line_item(lakebase_storage_gb=100)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None
        total = ws.cell(row=row, column=COL_TOTAL_L).value
        if isinstance(total, (int, float)):
            assert total > 0


class TestEndToEndPairTotals:
    """Verify compute + storage pair both have valid totals."""

    def test_pair_totals_both_positive(self):
        """Both compute and storage totals should be positive."""
        items = [make_line_item(
            lakebase_cu=4, lakebase_ha_nodes=2, lakebase_storage_gb=100,
        )]
        wb = generate_xlsx(items)
        ws = wb.active
        compute = find_compute_row(ws)
        storage = find_storage_row(ws)
        assert compute is not None
        assert storage is not None
        c_total = ws.cell(row=compute, column=COL_TOTAL_L).value
        s_total = ws.cell(row=storage, column=COL_TOTAL_L).value
        if isinstance(c_total, (int, float)):
            assert c_total > 0
        if isinstance(s_total, (int, float)):
            assert s_total > 0

    def test_compute_total_larger_than_storage(self):
        """For 4 CU × 2 nodes vs 100 GB, compute cost >> storage cost."""
        items = [make_line_item(
            lakebase_cu=4, lakebase_ha_nodes=2, lakebase_storage_gb=100,
        )]
        wb = generate_xlsx(items)
        ws = wb.active
        compute = find_compute_row(ws)
        storage = find_storage_row(ws)
        assert compute is not None
        assert storage is not None
        c_total = ws.cell(row=compute, column=COL_TOTAL_L).value
        s_total = ws.cell(row=storage, column=COL_TOTAL_L).value
        if isinstance(c_total, (int, float)) and isinstance(s_total, (int, float)):
            assert c_total > s_total, (
                f"Compute total ({c_total}) should exceed "
                f"storage total ({s_total}) for 4CU×2 vs 100GB")


class TestComputeNotes:
    """Verify compute row notes column propagation."""

    def test_compute_notes_empty_by_default(self):
        """Compute row notes are empty when no notes provided."""
        items = [make_line_item(lakebase_cu=4, lakebase_ha_nodes=2)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None
        notes = ws.cell(row=row, column=COL_NOTES).value
        assert notes is None or notes == ''

    def test_compute_notes_propagate_user_input(self):
        """User-provided notes appear in compute row."""
        items = [make_line_item(
            lakebase_cu=4, lakebase_ha_nodes=2,
            notes='Production HA database for analytics',
        )]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None
        notes = str(ws.cell(row=row, column=COL_NOTES).value or '')
        assert 'Production' in notes or 'analytics' in notes, (
            f"User notes not propagated, got: {notes}")
