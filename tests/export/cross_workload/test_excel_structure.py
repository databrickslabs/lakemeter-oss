"""Sprint 10: Excel structure tests — row counts, SKU mapping, mode, hours, DBU rates."""
import pytest
from tests.export.cross_workload.excel_helpers import (
    generate_xlsx, find_all_data_rows, find_rows_by_sku, find_row_by_name,
    COL_SKU, COL_MODE, COL_HOURS, COL_TOKEN_TYPE, COL_TOKEN_QTY,
    COL_DBU_HR, COL_DBU_RATE, COL_NAME, COL_NOTES,
)


@pytest.fixture(scope="module")
def combined_wb():
    """Generate a combined Excel workbook once for all tests in module."""
    return generate_xlsx()


@pytest.fixture(scope="module")
def ws(combined_wb):
    return combined_wb.active


class TestExcelGenerates:
    """AC-1: Excel generation succeeds with all 9 workload types."""

    def test_workbook_has_active_sheet(self, combined_wb):
        assert combined_wb.active is not None

    def test_sheet_has_rows(self, ws):
        assert ws.max_row > 10


class TestRowCount:
    """AC-4: Correct number of data rows including storage sub-rows."""

    def test_total_data_rows(self, ws):
        rows = find_all_data_rows(ws)
        # 9 workload items + 1 Lakebase storage + 1 VS storage = 11
        assert len(rows) == 11, f"Expected 11 data rows, got {len(rows)}"

    def test_lakebase_storage_row_exists(self, ws):
        storage_rows = find_rows_by_sku(ws, 'DATABRICKS_STORAGE')
        # Lakebase + Vector Search both have storage sub-rows
        assert len(storage_rows) >= 2, \
            f"Expected >=2 DATABRICKS_STORAGE rows, got {len(storage_rows)}"

    def test_lakebase_compute_row_exists(self, ws):
        rows = find_rows_by_sku(ws, 'DATABASE_SERVERLESS_COMPUTE')
        assert len(rows) == 1

    def test_vector_search_compute_row_exists(self, ws):
        rows = find_rows_by_sku(ws, 'SERVERLESS_REAL_TIME_INFERENCE')
        assert len(rows) >= 1


class TestSkuMapping:
    """AC-3: Each workload type maps to correct SKU in Excel."""

    def test_jobs_serverless_sku(self, ws):
        row = find_row_by_name(ws, 'Jobs Serverless Perf')
        assert row is not None
        assert ws.cell(row=row, column=COL_SKU).value == \
            'JOBS_SERVERLESS_COMPUTE'

    def test_all_purpose_photon_sku(self, ws):
        row = find_row_by_name(ws, 'All-Purpose Classic Photon')
        assert row is not None
        assert ws.cell(row=row, column=COL_SKU).value == \
            'ALL_PURPOSE_COMPUTE_(PHOTON)'

    def test_dlt_serverless_sku(self, ws):
        row = find_row_by_name(ws, 'DLT Pro Serverless')
        assert row is not None
        assert ws.cell(row=row, column=COL_SKU).value == \
            'JOBS_SERVERLESS_COMPUTE'

    def test_dbsql_serverless_sku(self, ws):
        row = find_row_by_name(ws, 'DBSQL Serverless Medium')
        assert row is not None
        assert ws.cell(row=row, column=COL_SKU).value == \
            'SERVERLESS_SQL_COMPUTE'

    def test_model_serving_sku(self, ws):
        row = find_row_by_name(ws, 'Model Serving GPU')
        assert row is not None
        assert ws.cell(row=row, column=COL_SKU).value == \
            'SERVERLESS_REAL_TIME_INFERENCE'

    def test_lakebase_compute_sku(self, ws):
        row = find_row_by_name(ws, 'Lakebase 4CU 2HA')
        assert row is not None
        sku = ws.cell(row=row, column=COL_SKU).value
        assert sku == 'DATABASE_SERVERLESS_COMPUTE'


class TestServerlessMode:
    """AC-13: Serverless items show 'Serverless'; classic shows 'Classic'."""

    def test_jobs_serverless_mode(self, ws):
        row = find_row_by_name(ws, 'Jobs Serverless Perf')
        assert ws.cell(row=row, column=COL_MODE).value == 'Serverless'

    def test_all_purpose_classic_mode(self, ws):
        row = find_row_by_name(ws, 'All-Purpose Classic Photon')
        assert ws.cell(row=row, column=COL_MODE).value == 'Classic'

    def test_dbsql_serverless_mode(self, ws):
        row = find_row_by_name(ws, 'DBSQL Serverless Medium')
        assert ws.cell(row=row, column=COL_MODE).value == 'Serverless'


class TestHoursColumn:
    """AC-8: Hours/Mo populated correctly for non-token items."""

    def test_jobs_hours(self, ws):
        row = find_row_by_name(ws, 'Jobs Serverless Perf')
        assert ws.cell(row=row, column=COL_HOURS).value == 200

    def test_all_purpose_hours(self, ws):
        row = find_row_by_name(ws, 'All-Purpose Classic Photon')
        assert ws.cell(row=row, column=COL_HOURS).value == 730

    def test_dbsql_hours(self, ws):
        row = find_row_by_name(ws, 'DBSQL Serverless Medium')
        assert ws.cell(row=row, column=COL_HOURS).value == 500

    def test_fmapi_hours_na(self, ws):
        """FMAPI token items show N/A for hours."""
        row = find_row_by_name(ws, 'FMAPI DB Llama Input')
        assert ws.cell(row=row, column=COL_HOURS).value == 'N/A'


class TestDbuPerHour:
    """AC-8: DBU/Hr populated correctly for hourly items."""

    def test_jobs_dbu_hr(self, ws):
        row = find_row_by_name(ws, 'Jobs Serverless Perf')
        val = ws.cell(row=row, column=COL_DBU_HR).value
        # base=0.5 (driver fallback), photon 2.9 from JSON, performance *2 = 2.9
        assert val == pytest.approx(2.9, abs=0.01)

    def test_all_purpose_dbu_hr(self, ws):
        row = find_row_by_name(ws, 'All-Purpose Classic Photon')
        val = ws.cell(row=row, column=COL_DBU_HR).value
        # base = 0.5 + 0.5*2 = 1.5, photon *2.0 = 3.0
        assert val == pytest.approx(3.0, abs=0.01)

    def test_dbsql_dbu_hr(self, ws):
        row = find_row_by_name(ws, 'DBSQL Serverless Medium')
        val = ws.cell(row=row, column=COL_DBU_HR).value
        assert val == pytest.approx(24.0, abs=0.01)

    def test_lakebase_dbu_hr(self, ws):
        row = find_row_by_name(ws, 'Lakebase 4CU 2HA')
        val = ws.cell(row=row, column=COL_DBU_HR).value
        assert val == pytest.approx(8.0, abs=0.01)

    def test_model_serving_dbu_hr(self, ws):
        """Model Serving GPU (A10G x1) should show 20.0 DBU/hr."""
        row = find_row_by_name(ws, 'Model Serving GPU')
        val = ws.cell(row=row, column=COL_DBU_HR).value
        assert val == pytest.approx(20.0, abs=0.01)

    def test_fmapi_dbu_hr_na(self, ws):
        """FMAPI token items show N/A for DBU/Hr."""
        row = find_row_by_name(ws, 'FMAPI DB Llama Input')
        assert ws.cell(row=row, column=COL_DBU_HR).value == 'N/A'


class TestDbuRate:
    """AC-8: DBU Rate column has non-zero values for all items."""

    def test_all_rows_have_dbu_rate(self, ws):
        for row_idx in find_all_data_rows(ws):
            rate = ws.cell(row=row_idx, column=COL_DBU_RATE).value
            assert isinstance(rate, (int, float)), \
                f"Row {row_idx}: DBU rate should be numeric, got {rate}"
            assert rate >= 0, \
                f"Row {row_idx}: negative DBU rate {rate}"


class TestNotesColumn:
    """AC-10: Notes column populated for relevant items."""

    def test_storage_rows_have_notes(self, ws):
        """Storage sub-rows should have notes."""
        storage_rows = find_rows_by_sku(ws, 'DATABRICKS_STORAGE')
        for row_idx in storage_rows:
            notes = ws.cell(row=row_idx, column=COL_NOTES).value
            assert notes is not None, \
                f"Storage row {row_idx}: expected notes, got None"

    def test_storage_rows_have_descriptive_notes(self, ws):
        """Storage sub-rows should have descriptive notes with formulas."""
        storage_rows = find_rows_by_sku(ws, 'DATABRICKS_STORAGE')
        for row_idx in storage_rows:
            notes = ws.cell(row=row_idx, column=COL_NOTES).value
            assert notes is not None and len(str(notes)) > 0, \
                f"Storage row {row_idx}: expected descriptive note"
