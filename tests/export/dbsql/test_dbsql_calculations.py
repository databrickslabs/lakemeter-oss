"""
Sprint 4: DBSQL calculation verification tests.

Tests warehouse size → DBU/hr mapping, cluster multiplier, hours calculation,
and SKU determination for Classic, Pro, and Serverless DBSQL warehouses.
"""
import pytest
from tests.export.dbsql.dbsql_calc_helpers import (
    frontend_calc_dbsql, backend_calc_dbsql, DBSQL_SIZE_DBU,
)


class TestWarehouseSizeMapping:
    """All 9 warehouse sizes must map to correct DBU/hr rates."""

    @pytest.mark.parametrize("size,expected_dbu", [
        ('2X-Small', 4),
        ('X-Small', 6),
        ('Small', 12),
        ('Medium', 24),
        ('Large', 40),
        ('X-Large', 80),
        ('2X-Large', 144),
        ('3X-Large', 272),
        ('4X-Large', 528),
    ])
    def test_frontend_size_dbu(self, size, expected_dbu):
        result = frontend_calc_dbsql(warehouse_size=size, num_clusters=1)
        assert result['dbu_per_hour'] == expected_dbu

    @pytest.mark.parametrize("size,expected_dbu", [
        ('2X-Small', 4),
        ('X-Small', 6),
        ('Small', 12),
        ('Medium', 24),
        ('Large', 40),
        ('X-Large', 80),
        ('2X-Large', 144),
        ('3X-Large', 272),
        ('4X-Large', 528),
    ])
    def test_backend_size_dbu(self, size, expected_dbu):
        result = backend_calc_dbsql(warehouse_size=size, num_clusters=1)
        assert result['dbu_per_hour'] == expected_dbu


class TestClusterMultiplier:
    """DBU/hr = size_dbu × num_clusters."""

    @pytest.mark.parametrize("clusters", [1, 2, 3, 5, 10])
    def test_frontend_cluster_scaling(self, clusters):
        result = frontend_calc_dbsql(
            warehouse_size='Medium', num_clusters=clusters,
        )
        assert result['dbu_per_hour'] == pytest.approx(24 * clusters)

    @pytest.mark.parametrize("clusters", [1, 2, 3, 5, 10])
    def test_backend_cluster_scaling(self, clusters):
        result = backend_calc_dbsql(
            warehouse_size='Medium', num_clusters=clusters,
        )
        assert result['dbu_per_hour'] == pytest.approx(24 * clusters)

    def test_large_cluster_count(self):
        """DBSQL Pro Medium with 2 clusters, 200 hrs/month."""
        fe = frontend_calc_dbsql(
            warehouse_type='PRO', warehouse_size='Medium',
            num_clusters=2, hours_per_month=200,
        )
        assert fe['dbu_per_hour'] == pytest.approx(48)
        assert fe['monthly_dbus'] == pytest.approx(9600)

    def test_max_size_4xlarge(self):
        """4X-Large = 528 DBU/hr."""
        fe = frontend_calc_dbsql(
            warehouse_type='SERVERLESS', warehouse_size='4X-Large',
            num_clusters=1, hours_per_month=730,
        )
        assert fe['dbu_per_hour'] == pytest.approx(528)
        assert fe['monthly_dbus'] == pytest.approx(528 * 730)


class TestHoursCalculation:
    """Hours calculation for DBSQL (same logic as other workloads)."""

    def test_direct_hours(self):
        result = frontend_calc_dbsql(hours_per_month=100)
        assert result['hours_per_month'] == pytest.approx(100)

    def test_247_hours(self):
        result = frontend_calc_dbsql(hours_per_month=730)
        assert result['hours_per_month'] == pytest.approx(730)

    def test_zero_hours(self):
        result = frontend_calc_dbsql(hours_per_month=0)
        assert result['hours_per_month'] == 0
        assert result['monthly_dbus'] == 0

    def test_run_based_hours(self):
        """10 runs/day × 30 min / 60 × 22 days = 110 hrs."""
        result = frontend_calc_dbsql(
            runs_per_day=10, avg_runtime_minutes=30, days_per_month=22,
            hours_per_month=0,
        )
        assert result['hours_per_month'] == pytest.approx(110)

    def test_run_based_hours_backend(self):
        """Same run-based calculation via backend helper."""
        result = backend_calc_dbsql(
            runs_per_day=10, avg_runtime_minutes=30, days_per_month=22,
            hours_per_month=0,
        )
        assert result['hours_per_month'] == pytest.approx(110)


class TestSKUDetermination:
    """Classic→SQL_COMPUTE, Pro→SQL_PRO_COMPUTE, Serverless→SERVERLESS_SQL_COMPUTE."""

    def test_classic_sku(self):
        fe = frontend_calc_dbsql(warehouse_type='CLASSIC')
        be = backend_calc_dbsql(warehouse_type='CLASSIC')
        assert fe['sku'] == 'SQL_COMPUTE'
        assert be['sku'] == 'SQL_COMPUTE'

    def test_pro_sku(self):
        fe = frontend_calc_dbsql(warehouse_type='PRO')
        be = backend_calc_dbsql(warehouse_type='PRO')
        assert fe['sku'] == 'SQL_PRO_COMPUTE'
        assert be['sku'] == 'SQL_PRO_COMPUTE'

    def test_serverless_sku(self):
        fe = frontend_calc_dbsql(warehouse_type='SERVERLESS')
        be = backend_calc_dbsql(warehouse_type='SERVERLESS')
        assert fe['sku'] == 'SERVERLESS_SQL_COMPUTE'
        assert be['sku'] == 'SERVERLESS_SQL_COMPUTE'

    def test_default_type_is_serverless(self):
        """When warehouse_type is None, default to SERVERLESS."""
        fe = frontend_calc_dbsql(warehouse_type=None)
        assert fe['sku'] == 'SERVERLESS_SQL_COMPUTE'


class TestServerlessDetection:
    """DBSQL Serverless → is_serverless=True, Classic/Pro → False."""

    def test_serverless_is_serverless(self):
        assert frontend_calc_dbsql(warehouse_type='SERVERLESS')['is_serverless'] is True

    def test_classic_is_not_serverless(self):
        assert frontend_calc_dbsql(warehouse_type='CLASSIC')['is_serverless'] is False

    def test_pro_is_not_serverless(self):
        assert frontend_calc_dbsql(warehouse_type='PRO')['is_serverless'] is False


class TestDBUPricing:
    """Verify fallback $/DBU prices."""

    def test_classic_price(self):
        result = frontend_calc_dbsql(warehouse_type='CLASSIC')
        assert result['dbu_price'] == pytest.approx(0.22)

    def test_pro_price(self):
        result = frontend_calc_dbsql(warehouse_type='PRO')
        assert result['dbu_price'] == pytest.approx(0.55)

    def test_serverless_price(self):
        result = frontend_calc_dbsql(warehouse_type='SERVERLESS')
        assert result['dbu_price'] == pytest.approx(0.70)


class TestMonthlyDBUs:
    """monthly_dbus = dbu_per_hour × hours_per_month."""

    def test_small_100hrs(self):
        """Small warehouse, 100 hrs → 12 × 100 = 1200 DBUs."""
        result = frontend_calc_dbsql(
            warehouse_size='Small', num_clusters=1, hours_per_month=100,
        )
        assert result['monthly_dbus'] == pytest.approx(1200)

    def test_medium_2clusters_200hrs(self):
        """Medium 2 clusters, 200 hrs → 48 × 200 = 9600 DBUs."""
        result = frontend_calc_dbsql(
            warehouse_size='Medium', num_clusters=2, hours_per_month=200,
        )
        assert result['monthly_dbus'] == pytest.approx(9600)

    def test_large_730hrs(self):
        """Large 1 cluster, 730 hrs → 40 × 730 = 29200 DBUs."""
        result = frontend_calc_dbsql(
            warehouse_size='Large', num_clusters=1, hours_per_month=730,
        )
        assert result['monthly_dbus'] == pytest.approx(29200)
