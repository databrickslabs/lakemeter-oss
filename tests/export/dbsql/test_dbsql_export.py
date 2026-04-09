"""
Sprint 4: Backend export function tests for DBSQL workloads.

Tests _calc_dbsql_dbu, _get_sku_type, _is_serverless_workload, and
_calculate_hours_per_month using the real backend functions.
"""
import os
import sys
import pytest

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, BACKEND_DIR)

from app.routes.export.calculations import (
    _calc_dbsql_dbu, _calculate_dbu_per_hour,
    _calculate_hours_per_month, _is_serverless_workload,
)
from app.routes.export.pricing import _get_sku_type, FALLBACK_DBU_PRICES
from tests.export.dbsql.conftest import make_line_item


class TestCalcDbsqlDbu:
    """Test _calc_dbsql_dbu for all warehouse sizes and clusters."""

    @pytest.mark.parametrize("size,expected", [
        ('2X-Small', 4), ('X-Small', 6), ('Small', 12), ('Medium', 24),
        ('Large', 40), ('X-Large', 80), ('2X-Large', 144),
        ('3X-Large', 272), ('4X-Large', 528),
    ])
    def test_all_sizes_single_cluster(self, size, expected):
        item = make_line_item(dbsql_warehouse_size=size, dbsql_num_clusters=1)
        dbu, warnings = _calc_dbsql_dbu(item, [])
        assert dbu == pytest.approx(expected)
        assert len(warnings) == 0

    def test_medium_2_clusters(self):
        item = make_line_item(dbsql_warehouse_size='Medium', dbsql_num_clusters=2)
        dbu, warnings = _calc_dbsql_dbu(item, [])
        assert dbu == pytest.approx(48)

    def test_large_3_clusters(self):
        item = make_line_item(dbsql_warehouse_size='Large', dbsql_num_clusters=3)
        dbu, warnings = _calc_dbsql_dbu(item, [])
        assert dbu == pytest.approx(120)

    def test_unknown_size_falls_back_to_small(self):
        item = make_line_item(dbsql_warehouse_size='Tiny', dbsql_num_clusters=1)
        dbu, warnings = _calc_dbsql_dbu(item, [])
        assert dbu == pytest.approx(12)
        assert any("Unknown DBSQL warehouse size" in w for w in warnings)

    def test_none_size_defaults_to_small(self):
        item = make_line_item(dbsql_warehouse_size=None, dbsql_num_clusters=1)
        dbu, warnings = _calc_dbsql_dbu(item, [])
        assert dbu == pytest.approx(12)

    def test_none_clusters_defaults_to_1(self):
        item = make_line_item(dbsql_warehouse_size='Medium', dbsql_num_clusters=None)
        dbu, warnings = _calc_dbsql_dbu(item, [])
        assert dbu == pytest.approx(24)


class TestCalculateDBUPerHour:
    """Test _calculate_dbu_per_hour dispatches to DBSQL correctly."""

    def test_dbsql_routes_to_calc_dbsql_dbu(self):
        item = make_line_item(dbsql_warehouse_size='Small')
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == pytest.approx(12)

    def test_dbsql_4xlarge(self):
        item = make_line_item(dbsql_warehouse_size='4X-Large')
        dbu, _ = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == pytest.approx(528)


class TestGetSKUType:
    """Test _get_sku_type for DBSQL warehouse types."""

    def test_serverless(self):
        item = make_line_item(dbsql_warehouse_type='SERVERLESS')
        assert _get_sku_type(item) == 'SERVERLESS_SQL_COMPUTE'

    def test_pro(self):
        item = make_line_item(dbsql_warehouse_type='PRO')
        assert _get_sku_type(item) == 'SQL_PRO_COMPUTE'

    def test_classic(self):
        item = make_line_item(dbsql_warehouse_type='CLASSIC')
        assert _get_sku_type(item) == 'SQL_COMPUTE'

    def test_none_defaults_serverless(self):
        item = make_line_item(dbsql_warehouse_type=None)
        assert _get_sku_type(item) == 'SERVERLESS_SQL_COMPUTE'

    def test_lowercase_serverless(self):
        """Backend uppercases the warehouse type."""
        item = make_line_item(dbsql_warehouse_type='serverless')
        assert _get_sku_type(item) == 'SERVERLESS_SQL_COMPUTE'

    def test_lowercase_pro(self):
        item = make_line_item(dbsql_warehouse_type='pro')
        assert _get_sku_type(item) == 'SQL_PRO_COMPUTE'


class TestIsServerlessWorkload:
    """Test _is_serverless_workload for DBSQL."""

    def test_serverless_is_true(self):
        item = make_line_item(dbsql_warehouse_type='SERVERLESS')
        assert _is_serverless_workload(item) is True

    def test_classic_is_false(self):
        item = make_line_item(dbsql_warehouse_type='CLASSIC')
        assert _is_serverless_workload(item) is False

    def test_pro_is_false(self):
        item = make_line_item(dbsql_warehouse_type='PRO')
        assert _is_serverless_workload(item) is False

    def test_lowercase_serverless(self):
        item = make_line_item(dbsql_warehouse_type='serverless')
        assert _is_serverless_workload(item) is True


class TestCalculateHoursPerMonth:
    """Test _calculate_hours_per_month for DBSQL items."""

    def test_direct_hours(self):
        item = make_line_item(hours_per_month=100)
        assert _calculate_hours_per_month(item) == pytest.approx(100)

    def test_247(self):
        item = make_line_item(hours_per_month=730)
        assert _calculate_hours_per_month(item) == pytest.approx(730)

    def test_no_hours_returns_zero(self):
        item = make_line_item(hours_per_month=None)
        assert _calculate_hours_per_month(item) == 0


class TestFallbackPrices:
    """Verify fallback $/DBU prices match expected values."""

    def test_classic_fallback(self):
        assert FALLBACK_DBU_PRICES['SQL_COMPUTE'] == pytest.approx(0.22)

    def test_pro_fallback(self):
        assert FALLBACK_DBU_PRICES['SQL_PRO_COMPUTE'] == pytest.approx(0.55)

    def test_serverless_fallback(self):
        assert FALLBACK_DBU_PRICES['SERVERLESS_SQL_COMPUTE'] == pytest.approx(0.70)
