"""Test Lakebase config display string generation.

AC-9: Config display shows "CU: X | Nodes: Y".
"""
import pytest

from tests.export.lakebase.conftest import make_line_item
from app.routes.export.helpers import (
    _get_workload_display_name, _get_workload_config_details,
)


class TestDisplayName:
    """Workload display name for LAKEBASE."""

    def test_display_name(self):
        assert _get_workload_display_name('LAKEBASE') == 'Lakebase'


class TestConfigDetails:
    """AC-9: Config string shows CU and nodes."""

    def test_basic_config(self):
        item = make_line_item(lakebase_cu=4, lakebase_ha_nodes=2)
        config = _get_workload_config_details(item)
        assert 'CU: 4' in config
        assert 'Nodes: 2' in config

    def test_half_cu(self):
        item = make_line_item(lakebase_cu=0.5, lakebase_ha_nodes=1)
        config = _get_workload_config_details(item)
        assert 'CU: 0.5' in config
        assert 'Nodes: 1' in config

    def test_large_cu(self):
        item = make_line_item(lakebase_cu=112, lakebase_ha_nodes=3)
        config = _get_workload_config_details(item)
        assert '112' in config
        assert '3' in config

    def test_config_uses_pipe_separator(self):
        item = make_line_item(lakebase_cu=4, lakebase_ha_nodes=2)
        config = _get_workload_config_details(item)
        assert '|' in config

    def test_no_cu_returns_partial(self):
        """If CU is None, only nodes should appear."""
        item = make_line_item(lakebase_cu=None, lakebase_ha_nodes=2)
        config = _get_workload_config_details(item)
        assert 'Nodes: 2' in config

    def test_no_nodes_returns_partial(self):
        """If nodes is None, only CU should appear."""
        item = make_line_item(lakebase_cu=4, lakebase_ha_nodes=None)
        config = _get_workload_config_details(item)
        assert 'CU: 4' in config
