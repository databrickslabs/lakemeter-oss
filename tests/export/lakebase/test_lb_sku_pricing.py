"""Test Lakebase SKU determination and pricing lookups.

AC-4: SKU = DATABASE_SERVERLESS_COMPUTE for compute.
AC-5: SKU = DATABRICKS_STORAGE for storage sub-row.
AC-8: Lakebase is always serverless (no VM costs).
"""
import pytest

from tests.export.lakebase.conftest import make_line_item
from app.routes.export.pricing import (
    _get_sku_type, _get_dbu_price, FALLBACK_DBU_PRICES,
)
from app.routes.export.calculations import _is_serverless_workload


class TestSKUDetermination:
    """AC-4: Compute SKU is DATABASE_SERVERLESS_COMPUTE."""

    def test_lakebase_sku(self):
        item = make_line_item()
        assert _get_sku_type(item, 'aws') == 'DATABASE_SERVERLESS_COMPUTE'

    @pytest.mark.parametrize("cu,nodes", [
        (0.5, 1), (4, 2), (32, 3), (112, 1),
    ])
    def test_sku_independent_of_config(self, cu, nodes):
        item = make_line_item(lakebase_cu=cu, lakebase_ha_nodes=nodes)
        assert _get_sku_type(item, 'aws') == 'DATABASE_SERVERLESS_COMPUTE'

    @pytest.mark.parametrize("cloud", ["aws", "azure", "gcp"])
    def test_sku_same_all_clouds(self, cloud):
        item = make_line_item()
        assert _get_sku_type(item, cloud) == 'DATABASE_SERVERLESS_COMPUTE'


class TestStorageSKU:
    """AC-5: Storage sub-row uses DATABRICKS_STORAGE SKU."""

    def test_storage_rate_lookup_from_pricing_json(self):
        """DATABRICKS_STORAGE rate from dbu-rates.json (not fallback)."""
        rate, found = _get_dbu_price('aws', 'us-east-1', 'PREMIUM',
                                     'DATABRICKS_STORAGE')
        assert rate == pytest.approx(0.023)
        assert found is True

    def test_storage_not_in_fallback(self):
        """DATABRICKS_STORAGE is NOT in fallback dict — only in JSON."""
        assert 'DATABRICKS_STORAGE' not in FALLBACK_DBU_PRICES

    def test_compute_sku_in_fallback(self):
        """DATABASE_SERVERLESS_COMPUTE IS in fallback."""
        assert 'DATABASE_SERVERLESS_COMPUTE' in FALLBACK_DBU_PRICES


class TestComputePricing:
    """Verify DATABASE_SERVERLESS_COMPUTE pricing lookup."""

    def test_compute_rate_aws_us_east_1(self):
        rate, found = _get_dbu_price('aws', 'us-east-1', 'PREMIUM',
                                     'DATABASE_SERVERLESS_COMPUTE')
        assert rate == pytest.approx(0.40)

    def test_compute_fallback_rate(self):
        fallback = FALLBACK_DBU_PRICES['DATABASE_SERVERLESS_COMPUTE']
        assert fallback == pytest.approx(0.48)


class TestServerlessClassification:
    """AC-8: Lakebase is always serverless — no VM costs."""

    def test_lakebase_is_serverless(self):
        item = make_line_item()
        assert _is_serverless_workload(item) is True

    @pytest.mark.parametrize("cu,nodes", [
        (0.5, 1), (4, 2), (112, 3),
    ])
    def test_always_serverless_regardless_of_config(self, cu, nodes):
        item = make_line_item(lakebase_cu=cu, lakebase_ha_nodes=nodes)
        assert _is_serverless_workload(item) is True

    def test_lakebase_not_serverless_flag_but_still_serverless(self):
        """Even without serverless_enabled=True, Lakebase is serverless."""
        item = make_line_item(serverless_enabled=False)
        assert _is_serverless_workload(item) is True
