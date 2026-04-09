"""
Sprint 4: DBSQL VM costs, notes, and edge case tests.

Tests that Classic/Pro warehouses can have VM costs, Serverless has zero,
and various edge cases are handled correctly.
"""
import os
import sys
import pytest

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, BACKEND_DIR)

from app.routes.export.calculations import (
    _calc_dbsql_dbu, _is_serverless_workload,
)
from app.routes.export.pricing import _get_sku_type
from app.routes.export.helpers import (
    _get_workload_display_name, _get_workload_config_details,
)
from tests.export.dbsql.conftest import make_line_item


class TestDBSQLVMCosts:
    """Classic/Pro have VM costs; Serverless does not."""

    def test_serverless_no_vm(self):
        item = make_line_item(dbsql_warehouse_type='SERVERLESS')
        assert _is_serverless_workload(item) is True

    def test_classic_has_vm_potential(self):
        item = make_line_item(dbsql_warehouse_type='CLASSIC')
        assert _is_serverless_workload(item) is False

    def test_pro_has_vm_potential(self):
        item = make_line_item(dbsql_warehouse_type='PRO')
        assert _is_serverless_workload(item) is False


class TestDBSQLDisplayName:
    """DBSQL workload display name should be 'Databricks SQL'."""

    def test_display_name(self):
        assert _get_workload_display_name('DBSQL') == 'Databricks SQL'


class TestDBSQLConfigDetails:
    """Config details should show warehouse type, size, and clusters."""

    def test_serverless_small(self):
        item = make_line_item(
            dbsql_warehouse_type='SERVERLESS',
            dbsql_warehouse_size='Small',
            dbsql_num_clusters=1,
        )
        config = _get_workload_config_details(item)
        assert 'SERVERLESS' in config
        assert 'Small' in config

    def test_pro_medium_2_clusters(self):
        item = make_line_item(
            dbsql_warehouse_type='PRO',
            dbsql_warehouse_size='Medium',
            dbsql_num_clusters=2,
        )
        config = _get_workload_config_details(item)
        assert 'PRO' in config
        assert 'Medium' in config
        assert 'Clusters: 2' in config

    def test_single_cluster_no_cluster_text(self):
        """Single cluster should not show cluster count."""
        item = make_line_item(
            dbsql_warehouse_type='CLASSIC',
            dbsql_warehouse_size='Large',
            dbsql_num_clusters=1,
        )
        config = _get_workload_config_details(item)
        assert 'Clusters' not in config


class TestDBSQLEdgeCases:
    """Edge cases: unknown size, zero clusters, missing fields."""

    def test_unknown_size_warning(self):
        item = make_line_item(dbsql_warehouse_size='Micro')
        dbu, warnings = _calc_dbsql_dbu(item, [])
        assert dbu == pytest.approx(12)  # Falls back to Small
        assert any("Unknown DBSQL warehouse size" in w for w in warnings)

    def test_empty_string_size(self):
        """Empty string defaults to Small with warning (BUG-S4-2 fix)."""
        item = make_line_item(dbsql_warehouse_size='')
        dbu, warnings = _calc_dbsql_dbu(item, [])
        assert dbu == pytest.approx(12)
        assert any("Empty warehouse size" in w for w in warnings)

    def test_zero_clusters_treated_as_1(self):
        """0 clusters → int(0 or 1) = 1."""
        item = make_line_item(dbsql_warehouse_size='Medium', dbsql_num_clusters=0)
        dbu, _ = _calc_dbsql_dbu(item, [])
        # int(0 or 1) = int(1) = 1 because 0 is falsy
        assert dbu == pytest.approx(24)

    def test_negative_clusters(self):
        """Negative clusters clamped to 1 (BUG-S4-1 fix)."""
        item = make_line_item(dbsql_warehouse_size='Small', dbsql_num_clusters=-1)
        dbu, _ = _calc_dbsql_dbu(item, [])
        assert dbu == pytest.approx(12)  # max(1, -1) = 1, so 12 * 1 = 12

    def test_none_warehouse_type_sku(self):
        item = make_line_item(dbsql_warehouse_type=None)
        sku = _get_sku_type(item)
        assert sku == 'SERVERLESS_SQL_COMPUTE'


class TestDBSQLAllSizesFullCycle:
    """Full cycle test: size → DBU/hr → monthly DBUs for all sizes."""

    @pytest.mark.parametrize("size,dbu_hr", [
        ('2X-Small', 4), ('X-Small', 6), ('Small', 12), ('Medium', 24),
        ('Large', 40), ('X-Large', 80), ('2X-Large', 144),
        ('3X-Large', 272), ('4X-Large', 528),
    ])
    def test_full_cycle_100hrs(self, size, dbu_hr):
        item = make_line_item(
            dbsql_warehouse_size=size, dbsql_num_clusters=1, hours_per_month=100,
        )
        actual_dbu, _ = _calc_dbsql_dbu(item, [])
        assert actual_dbu == pytest.approx(dbu_hr)
