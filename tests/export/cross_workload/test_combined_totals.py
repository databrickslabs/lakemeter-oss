"""Sprint 10: Grand total and cross-workload tests."""
import pytest
from xlsxwriter.utility import xl_col_to_name as _col
from tests.export.cross_workload.conftest import make_all_nine_items, make_line_item
from tests.export.cross_workload.excel_helpers import (
    generate_xlsx, find_all_data_rows, find_totals_row, find_rows_by_sku,
    COL_DBUS_MO, COL_DBU_COST_L, COL_DBU_COST_D,
    COL_DRIVER_VM_COST, COL_WORKER_VM_COST, COL_TOTAL_VM,
    COL_TOTAL_L, COL_TOTAL_D, COL_NOTES,
)


@pytest.fixture(scope="module")
def combined_wb():
    return generate_xlsx()


@pytest.fixture(scope="module")
def ws(combined_wb):
    return combined_wb.active


class TestTotalsRowExists:
    """AC-5: Totals row exists and spans all data rows."""

    def test_totals_row_found(self, ws):
        row = find_totals_row(ws)
        assert row is not None, "TOTALS row not found"

    def test_totals_row_after_data(self, ws):
        data_rows = find_all_data_rows(ws)
        totals_row = find_totals_row(ws)
        assert totals_row > max(data_rows), \
            "TOTALS row should come after all data rows"


class TestTotalsSumFormulas:
    """AC-5: Totals row uses SUM formulas spanning all data rows."""

    def _check_sum_formula(self, ws, col):
        totals_row = find_totals_row(ws)
        cell = ws.cell(row=totals_row, column=col)
        val = cell.value
        assert isinstance(val, str) and val.startswith('=SUM('), \
            f"Totals col {col}: expected SUM formula, got {val}"
        # Verify it spans from first to last data row
        data_rows = find_all_data_rows(ws)
        first_data = min(data_rows)   # openpyxl rows = Excel rows (1-indexed)
        last_data = max(data_rows)
        col_letter = _col(col - 1)  # Convert to 0-indexed for xl_col_to_name
        expected_range = f'{col_letter}{first_data}:{col_letter}{last_data}'
        assert expected_range in val, \
            f"Expected SUM range {expected_range} in formula {val}"

    def test_dbus_mo_sum(self, ws):
        self._check_sum_formula(ws, COL_DBUS_MO)

    def test_dbu_cost_list_sum(self, ws):
        self._check_sum_formula(ws, COL_DBU_COST_L)

    def test_dbu_cost_disc_sum(self, ws):
        self._check_sum_formula(ws, COL_DBU_COST_D)

    def test_driver_vm_cost_sum(self, ws):
        self._check_sum_formula(ws, COL_DRIVER_VM_COST)

    def test_worker_vm_cost_sum(self, ws):
        self._check_sum_formula(ws, COL_WORKER_VM_COST)

    def test_total_vm_sum(self, ws):
        self._check_sum_formula(ws, COL_TOTAL_VM)

    def test_total_list_sum(self, ws):
        self._check_sum_formula(ws, COL_TOTAL_L)

    def test_total_disc_sum(self, ws):
        self._check_sum_formula(ws, COL_TOTAL_D)


class TestStorageRowsInSum:
    """AC-7: Storage sub-rows are within the SUM range."""

    def test_storage_rows_in_totals_range(self, ws):
        data_rows = find_all_data_rows(ws)
        storage_rows = find_rows_by_sku(ws, 'DATABRICKS_STORAGE')
        first_data = min(data_rows)
        last_data = max(data_rows)
        for sr in storage_rows:
            assert first_data <= sr <= last_data, \
                f"Storage row {sr} outside data range [{first_data}, {last_data}]"


class TestMultiRowWorkloads:
    """AC-7: Lakebase and Vector Search have storage sub-rows."""

    def test_lakebase_has_storage_subrow(self, ws):
        storage_rows = find_rows_by_sku(ws, 'DATABRICKS_STORAGE')
        # Check at least one storage row is for Lakebase
        lakebase_storage = [r for r in storage_rows
                            if 'Lakebase' in str(ws.cell(row=r, column=3).value)
                            or 'Lakebase' in str(ws.cell(row=r, column=2).value)]
        assert len(lakebase_storage) >= 1, \
            "No Lakebase storage sub-row found"

    def test_vector_search_storage_subrow_emitted(self, ws):
        """Vector Search storage sub-row emitted when storage_gb > 0."""
        storage_rows = find_rows_by_sku(ws, 'DATABRICKS_STORAGE')
        vs_storage = [r for r in storage_rows
                      if 'Vector' in str(ws.cell(row=r, column=3).value)
                      or 'Vector' in str(ws.cell(row=r, column=2).value)]
        assert len(vs_storage) >= 1, \
            "Vector Search storage sub-row should be present when storage_gb > 0"

    def test_storage_rows_have_notes(self, ws):
        """Storage rows should have descriptive notes."""
        storage_rows = find_rows_by_sku(ws, 'DATABRICKS_STORAGE')
        for sr in storage_rows:
            notes = ws.cell(row=sr, column=COL_NOTES).value
            assert notes and len(str(notes)) > 0, \
                f"Storage row {sr} missing notes"


class TestNotesColumn:
    """AC-10: Notes column populated for relevant items."""

    def test_storage_rows_have_pricing_notes(self, ws):
        """Storage rows should show $/GB calculation in notes."""
        storage_rows = find_rows_by_sku(ws, 'DATABRICKS_STORAGE')
        for sr in storage_rows:
            notes = str(ws.cell(row=sr, column=COL_NOTES).value or '')
            assert '$' in notes or 'GB' in notes, \
                f"Storage row {sr}: expected pricing note, got '{notes}'"


class TestCrossWorkloadConsistency:
    """AC-14: Same pricing tier applied to all items."""

    def test_all_rows_have_discount_zero(self, ws):
        """Default discount is 0% for all rows."""
        from tests.export.cross_workload.excel_helpers import COL_DISCOUNT
        for row_idx in find_all_data_rows(ws):
            disc = ws.cell(row=row_idx, column=COL_DISCOUNT).value
            assert disc is not None and float(disc) == 0.0, \
                f"Row {row_idx}: expected 0% discount, got {disc}"


class TestEdgeCases:
    """Additional robustness checks for the combined estimate."""

    def test_empty_line_items(self):
        """Empty list produces a valid workbook with no data rows."""
        wb = generate_xlsx(line_items=[])
        ws = wb.active
        data_rows = find_all_data_rows(ws)
        assert len(data_rows) == 0

    def test_single_item_produces_valid_totals(self):
        """Single item still gets a totals row."""
        item = make_line_item(
            workload_type="DBSQL",
            workload_name="Solo DBSQL",
            dbsql_warehouse_type="SERVERLESS",
            dbsql_warehouse_size="Small",
            dbsql_num_clusters=1,
            hours_per_month=100,
        )
        wb = generate_xlsx(line_items=[item])
        ws = wb.active
        totals_row = find_totals_row(ws)
        assert totals_row is not None

    def test_duplicate_workload_types(self):
        """Multiple items of same type are all included."""
        items = [
            make_line_item(
                workload_type="DBSQL",
                workload_name=f"DBSQL #{i}",
                dbsql_warehouse_type="SERVERLESS",
                dbsql_warehouse_size="Small",
                hours_per_month=100,
            )
            for i in range(3)
        ]
        wb = generate_xlsx(line_items=items)
        ws = wb.active
        data_rows = find_all_data_rows(ws)
        assert len(data_rows) == 3

    def test_all_clouds(self):
        """Combined estimate works for aws, azure, gcp."""
        items = make_all_nine_items()
        for cloud in ['aws', 'azure', 'gcp']:
            wb = generate_xlsx(line_items=items, cloud=cloud)
            ws = wb.active
            data_rows = find_all_data_rows(ws)
            # 9 items + 1 Lakebase storage + 1 VS storage = 11
            assert len(data_rows) == 11, \
                f"{cloud}: expected 11 rows, got {len(data_rows)}"
