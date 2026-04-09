"""Parity tests: DBSQL workload — backend vs frontend equivalence.

Tests all 27 DBSQL configurations: 3 warehouse types (Classic/Pro/Serverless)
× 9 warehouse sizes (2X-Small through 4X-Large). Plus multi-cluster and edge cases.
"""
import pytest
from .conftest import make_item
from .frontend_calc import fe_dbsql_dbu_per_hour, fe_monthly_dbu_cost

CLOUD = 'aws'
REGION = 'us-east-1'
TIER = 'PREMIUM'
TOL = 0.01

# Expected DBU/hr per warehouse size (must match both frontend and backend)
EXPECTED_DBU = {
    '2X-Small': 4, 'X-Small': 6, 'Small': 12, 'Medium': 24,
    'Large': 40, 'X-Large': 80, '2X-Large': 144, '3X-Large': 272, '4X-Large': 528,
}

# SKU expected per warehouse type
EXPECTED_SKU = {
    'CLASSIC': 'SQL_COMPUTE',
    'PRO': 'SQL_PRO_COMPUTE',
    'SERVERLESS': 'SERVERLESS_SQL_COMPUTE',
}


def _get_be_results(item):
    from app.routes.export.calculations import _calculate_dbu_per_hour, _calculate_hours_per_month
    from app.routes.export.pricing import _get_dbu_price, _get_sku_type

    dbu_hr, _ = _calculate_dbu_per_hour(item, CLOUD)
    hours = _calculate_hours_per_month(item)
    sku = _get_sku_type(item, CLOUD)
    dbu_price, _ = _get_dbu_price(CLOUD, REGION, TIER, sku)
    monthly_dbus = dbu_hr * hours
    return dict(dbu_hr=dbu_hr, hours=hours, sku=sku, dbu_price=dbu_price,
                monthly_dbus=monthly_dbus, monthly_cost=monthly_dbus * dbu_price)


# ============================================================
# Parametrized: All Sizes × All Types
# ============================================================

ALL_SIZES = list(EXPECTED_DBU.keys())
ALL_TYPES = ['CLASSIC', 'PRO', 'SERVERLESS']


@pytest.mark.parametrize("wh_type", ALL_TYPES)
@pytest.mark.parametrize("wh_size", ALL_SIZES)
class TestDBSQLAllSizesAllTypes:
    """Verify DBU/hr and SKU for every size × type combination."""

    def test_dbu_per_hour(self, pricing, wh_type, wh_size):
        item = make_item(
            workload_type='DBSQL', dbsql_warehouse_type=wh_type,
            dbsql_warehouse_size=wh_size, dbsql_num_clusters=1,
            hours_per_month=100,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_dbsql_dbu_per_hour(warehouse_size=wh_size, num_clusters=1)
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(float(EXPECTED_DBU[wh_size]), abs=TOL)
        assert be['sku'] == EXPECTED_SKU[wh_type]

    def test_monthly_cost(self, pricing, wh_type, wh_size):
        item = make_item(
            workload_type='DBSQL', dbsql_warehouse_type=wh_type,
            dbsql_warehouse_size=wh_size, dbsql_num_clusters=1,
            hours_per_month=500,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_dbsql_dbu_per_hour(warehouse_size=wh_size, num_clusters=1)
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=500, dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)


# ============================================================
# Multi-Cluster Tests
# ============================================================

class TestDBSQLMultiCluster:
    """Multi-cluster: DBU/hr = base_dbu × num_clusters."""

    @pytest.mark.parametrize("num_clusters", [1, 2, 3, 5])
    def test_classic_medium_clusters(self, pricing, num_clusters):
        item = make_item(
            workload_type='DBSQL', dbsql_warehouse_type='CLASSIC',
            dbsql_warehouse_size='Medium', dbsql_num_clusters=num_clusters,
            hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_dbsql_dbu_per_hour(
            warehouse_size='Medium', num_clusters=num_clusters,
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(24.0 * num_clusters, abs=TOL)

    @pytest.mark.parametrize("num_clusters", [1, 2, 4])
    def test_serverless_xlarge_clusters(self, pricing, num_clusters):
        item = make_item(
            workload_type='DBSQL', dbsql_warehouse_type='SERVERLESS',
            dbsql_warehouse_size='X-Large', dbsql_num_clusters=num_clusters,
            hours_per_month=200,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_dbsql_dbu_per_hour(
            warehouse_size='X-Large', num_clusters=num_clusters,
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(80.0 * num_clusters, abs=TOL)

    @pytest.mark.parametrize("num_clusters", [1, 3])
    def test_pro_large_clusters(self, pricing, num_clusters):
        item = make_item(
            workload_type='DBSQL', dbsql_warehouse_type='PRO',
            dbsql_warehouse_size='Large', dbsql_num_clusters=num_clusters,
            hours_per_month=500,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_dbsql_dbu_per_hour(
            warehouse_size='Large', num_clusters=num_clusters,
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=500, dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)


# ============================================================
# Edge Cases
# ============================================================

class TestDBSQLEdgeCases:
    """Edge cases: default warehouse type, missing size, run-based hours."""

    def test_default_type_is_serverless(self, pricing):
        """Missing dbsql_warehouse_type defaults to SERVERLESS."""
        item = make_item(
            workload_type='DBSQL', dbsql_warehouse_type=None,
            dbsql_warehouse_size='Small', dbsql_num_clusters=1,
            hours_per_month=100,
        )
        be = _get_be_results(item)
        assert be['sku'] == 'SERVERLESS_SQL_COMPUTE'

    def test_default_size_is_small(self, pricing):
        """Missing dbsql_warehouse_size defaults to Small (12 DBU)."""
        item = make_item(
            workload_type='DBSQL', dbsql_warehouse_type='SERVERLESS',
            dbsql_warehouse_size=None, dbsql_num_clusters=1,
            hours_per_month=100,
        )
        be = _get_be_results(item)
        assert be['dbu_hr'] == pytest.approx(12.0, abs=TOL)

    def test_empty_size_defaults_to_small(self, pricing):
        """Empty string size defaults to Small."""
        item = make_item(
            workload_type='DBSQL', dbsql_warehouse_type='CLASSIC',
            dbsql_warehouse_size='', dbsql_num_clusters=1,
            hours_per_month=100,
        )
        be = _get_be_results(item)
        assert be['dbu_hr'] == pytest.approx(12.0, abs=TOL)

    def test_run_based_hours(self, pricing):
        """DBSQL with run-based hours."""
        item = make_item(
            workload_type='DBSQL', dbsql_warehouse_type='PRO',
            dbsql_warehouse_size='Medium', dbsql_num_clusters=2,
            runs_per_day=8, avg_runtime_minutes=15, days_per_month=22,
        )
        be = _get_be_results(item)
        # 8 runs * 15min/60 * 22 days = 44 hours
        assert be['hours'] == pytest.approx(44.0, abs=TOL)
        fe_dbu_hr = fe_dbsql_dbu_per_hour(warehouse_size='Medium', num_clusters=2)
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=44.0, dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_null_clusters_defaults_to_1(self, pricing):
        """Null num_clusters defaults to 1."""
        item = make_item(
            workload_type='DBSQL', dbsql_warehouse_type='SERVERLESS',
            dbsql_warehouse_size='Large', dbsql_num_clusters=None,
            hours_per_month=200,
        )
        be = _get_be_results(item)
        assert be['dbu_hr'] == pytest.approx(40.0, abs=TOL)
