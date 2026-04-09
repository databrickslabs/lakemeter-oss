"""
Regression tests for bugs found during Sprint 4 evaluation.

BUG-S4-1: Negative cluster count produced negative DBU values.
BUG-S4-2: Empty string warehouse size silently defaulted without warning.
"""
import os
import sys
import pytest

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, BACKEND_DIR)

from app.routes.export.calculations import _calc_dbsql_dbu
from tests.export.dbsql.conftest import make_line_item


class TestBugS4_1_NegativeClusters:
    """BUG-S4-1: Negative cluster count must be clamped to 1."""

    def test_negative_one_cluster(self):
        item = make_line_item(dbsql_warehouse_size='Small', dbsql_num_clusters=-1)
        dbu, _ = _calc_dbsql_dbu(item, [])
        assert dbu == pytest.approx(12)  # 12 * max(1, -1) = 12

    def test_negative_ten_clusters(self):
        item = make_line_item(dbsql_warehouse_size='Medium', dbsql_num_clusters=-10)
        dbu, _ = _calc_dbsql_dbu(item, [])
        assert dbu == pytest.approx(24)  # 24 * max(1, -10) = 24

    def test_zero_clusters_still_defaults_to_1(self):
        item = make_line_item(dbsql_warehouse_size='Large', dbsql_num_clusters=0)
        dbu, _ = _calc_dbsql_dbu(item, [])
        assert dbu == pytest.approx(40)  # 40 * max(1, 0→1) = 40

    def test_positive_clusters_unaffected(self):
        item = make_line_item(dbsql_warehouse_size='Small', dbsql_num_clusters=3)
        dbu, _ = _calc_dbsql_dbu(item, [])
        assert dbu == pytest.approx(36)  # 12 * 3 = 36


class TestBugS4_2_EmptyWarehouseSize:
    """BUG-S4-2: Empty string warehouse size must warn and default to Small."""

    def test_empty_string_warns(self):
        item = make_line_item(dbsql_warehouse_size='')
        dbu, warnings = _calc_dbsql_dbu(item, [])
        assert dbu == pytest.approx(12)
        assert any("Empty warehouse size" in w for w in warnings)

    def test_whitespace_only_warns(self):
        item = make_line_item(dbsql_warehouse_size='   ')
        dbu, warnings = _calc_dbsql_dbu(item, [])
        assert dbu == pytest.approx(12)
        assert any("Empty warehouse size" in w for w in warnings)

    def test_none_defaults_without_empty_warning(self):
        item = make_line_item(dbsql_warehouse_size=None)
        dbu, warnings = _calc_dbsql_dbu(item, [])
        assert dbu == pytest.approx(12)
        assert any("Empty warehouse size" in w for w in warnings)

    def test_valid_size_no_warning(self):
        item = make_line_item(dbsql_warehouse_size='Medium')
        dbu, warnings = _calc_dbsql_dbu(item, [])
        assert dbu == pytest.approx(24)
        assert len(warnings) == 0
