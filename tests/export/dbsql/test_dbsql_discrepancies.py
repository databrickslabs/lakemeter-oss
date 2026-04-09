"""
Sprint 4: Frontend vs backend discrepancy tests for DBSQL.

Verifies that frontend costCalculation.ts and backend calculations.py
agree on all DBSQL calculations.
"""
import pytest
from tests.export.dbsql.dbsql_calc_helpers import (
    frontend_calc_dbsql, backend_calc_dbsql, DBSQL_SIZE_DBU,
)


class TestFEBEWarehouseSizeAlignment:
    """Frontend and backend must agree on DBU/hr for all 9 sizes."""

    @pytest.mark.parametrize("size", list(DBSQL_SIZE_DBU.keys()))
    def test_size_dbu_match(self, size):
        fe = frontend_calc_dbsql(warehouse_size=size, num_clusters=1, hours_per_month=100)
        be = backend_calc_dbsql(warehouse_size=size, num_clusters=1, hours_per_month=100)
        assert fe['dbu_per_hour'] == pytest.approx(be['dbu_per_hour']), \
            f"FE/BE mismatch for {size}: FE={fe['dbu_per_hour']}, BE={be['dbu_per_hour']}"


class TestFEBESKUAlignment:
    """Frontend and backend must agree on SKU mapping."""

    @pytest.mark.parametrize("wh_type,expected_sku", [
        ('CLASSIC', 'SQL_COMPUTE'),
        ('PRO', 'SQL_PRO_COMPUTE'),
        ('SERVERLESS', 'SERVERLESS_SQL_COMPUTE'),
    ])
    def test_sku_match(self, wh_type, expected_sku):
        fe = frontend_calc_dbsql(warehouse_type=wh_type)
        be = backend_calc_dbsql(warehouse_type=wh_type)
        assert fe['sku'] == expected_sku
        assert be['sku'] == expected_sku


class TestFEBEMonthlyDBUsAlignment:
    """Frontend and backend must produce identical monthly DBUs."""

    @pytest.mark.parametrize("size,clusters,hours", [
        ('Small', 1, 100),
        ('Medium', 2, 200),
        ('Large', 1, 730),
        ('4X-Large', 1, 730),
        ('2X-Small', 3, 50),
    ])
    def test_monthly_dbus_match(self, size, clusters, hours):
        fe = frontend_calc_dbsql(
            warehouse_size=size, num_clusters=clusters, hours_per_month=hours,
        )
        be = backend_calc_dbsql(
            warehouse_size=size, num_clusters=clusters, hours_per_month=hours,
        )
        assert fe['monthly_dbus'] == pytest.approx(be['monthly_dbus']), \
            f"FE/BE monthly DBUs mismatch: FE={fe['monthly_dbus']}, BE={be['monthly_dbus']}"


class TestFEBEServerlessAlignment:
    """Frontend and backend must agree on serverless detection."""

    @pytest.mark.parametrize("wh_type,expected", [
        ('SERVERLESS', True),
        ('CLASSIC', False),
        ('PRO', False),
    ])
    def test_serverless_detection(self, wh_type, expected):
        fe = frontend_calc_dbsql(warehouse_type=wh_type)
        be = backend_calc_dbsql(warehouse_type=wh_type)
        assert fe['is_serverless'] == expected
        assert be['is_serverless'] == expected


class TestFEBEPricingAlignment:
    """Frontend and backend fallback $/DBU must match."""

    @pytest.mark.parametrize("wh_type", ['CLASSIC', 'PRO', 'SERVERLESS'])
    def test_fallback_price_match(self, wh_type):
        fe = frontend_calc_dbsql(warehouse_type=wh_type)
        be = backend_calc_dbsql(warehouse_type=wh_type)
        assert fe['dbu_price'] == pytest.approx(be['dbu_price']), \
            f"FE/BE price mismatch for {wh_type}: FE={fe['dbu_price']}, BE={be['dbu_price']}"


class TestFEBECostAlignment:
    """Frontend and backend total DBU costs must match."""

    @pytest.mark.parametrize("wh_type,size,clusters,hours", [
        ('CLASSIC', 'Small', 1, 100),
        ('PRO', 'Medium', 2, 200),
        ('SERVERLESS', 'Large', 1, 730),
        ('SERVERLESS', '4X-Large', 1, 730),
    ])
    def test_dbu_cost_match(self, wh_type, size, clusters, hours):
        fe = frontend_calc_dbsql(
            warehouse_type=wh_type, warehouse_size=size,
            num_clusters=clusters, hours_per_month=hours,
        )
        be = backend_calc_dbsql(
            warehouse_type=wh_type, warehouse_size=size,
            num_clusters=clusters, hours_per_month=hours,
        )
        assert fe['dbu_cost'] == pytest.approx(be['dbu_cost'], rel=1e-6), \
            f"FE/BE cost mismatch: FE=${fe['dbu_cost']:.2f}, BE=${be['dbu_cost']:.2f}"
