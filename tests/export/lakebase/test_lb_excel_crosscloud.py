"""Test Lakebase Excel export — cross-cloud and boundary CU sizes.

Verifies:
- Excel output (compute + storage rows) is consistent across AWS, Azure, GCP
- Half-CU (0.5) smallest valid size produces correct Excel output
"""
import pytest

from tests.export.lakebase.conftest import make_line_item
from tests.export.lakebase.excel_helpers import (
    generate_xlsx, find_compute_row, find_storage_row,
    COL_SKU, COL_DBU_HR,
)


class TestCrossCloudExcel:
    """Verify Excel output is consistent across AWS, Azure, GCP."""

    @pytest.mark.parametrize("cloud,region", [
        ("aws", "us-east-1"),
        ("azure", "eastus"),
        ("gcp", "us-central1"),
    ])
    def test_compute_row_present_all_clouds(self, cloud, region):
        items = [make_line_item(lakebase_cu=4, lakebase_ha_nodes=2)]
        wb = generate_xlsx(items, cloud=cloud, region=region)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None, (
            f"No compute row for cloud={cloud}, region={region}")

    @pytest.mark.parametrize("cloud,region", [
        ("aws", "us-east-1"),
        ("azure", "eastus"),
        ("gcp", "us-central1"),
    ])
    def test_storage_row_present_all_clouds(self, cloud, region):
        items = [make_line_item(lakebase_storage_gb=100)]
        wb = generate_xlsx(items, cloud=cloud, region=region)
        ws = wb.active
        row = find_storage_row(ws)
        assert row is not None, (
            f"No storage row for cloud={cloud}, region={region}")

    @pytest.mark.parametrize("cloud,region", [
        ("aws", "us-east-1"),
        ("azure", "eastus"),
        ("gcp", "us-central1"),
    ])
    def test_sku_consistent_all_clouds(self, cloud, region):
        """SKU should be DATABASE_SERVERLESS_COMPUTE on all clouds."""
        items = [make_line_item(lakebase_cu=4)]
        wb = generate_xlsx(items, cloud=cloud, region=region)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None
        assert ws.cell(row=row, column=COL_SKU).value == (
            'DATABASE_SERVERLESS_COMPUTE')


class TestHalfCUExcel:
    """Verify 0.5 CU (smallest valid size) works in Excel output."""

    def test_half_cu_dbu_hr(self):
        items = [make_line_item(lakebase_cu=0.5, lakebase_ha_nodes=1)]
        wb = generate_xlsx(items)
        ws = wb.active
        row = find_compute_row(ws)
        assert row is not None
        dbu_hr = ws.cell(row=row, column=COL_DBU_HR).value
        assert isinstance(dbu_hr, (int, float))
        assert abs(dbu_hr - 0.5) < 0.01

    def test_half_cu_with_storage(self):
        """Half CU + storage: both rows present and correct."""
        items = [make_line_item(
            lakebase_cu=0.5, lakebase_ha_nodes=1,
            lakebase_storage_gb=10,
        )]
        wb = generate_xlsx(items)
        ws = wb.active
        compute = find_compute_row(ws)
        storage = find_storage_row(ws)
        assert compute is not None
        assert storage is not None
        assert storage == compute + 1
