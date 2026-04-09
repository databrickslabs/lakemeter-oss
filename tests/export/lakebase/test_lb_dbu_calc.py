"""Test Lakebase DBU/hr calculation logic.

AC-1: DBU/hr = CU × HA_nodes for all valid CU sizes.
AC-3: Monthly DBUs = DBU/hr × hours_per_month.
"""
import pytest

from tests.export.lakebase.conftest import make_line_item
from tests.export.lakebase.lb_calc_helpers import (
    calc_dbu_per_hour, calc_monthly_dbus,
)
from app.routes.export.calculations import _calculate_dbu_per_hour


class TestBasicDBUPerHour:
    """AC-1: DBU/hr = CU × HA_nodes."""

    @pytest.mark.parametrize("cu,nodes,expected", [
        (0.5, 1, 0.5),
        (1, 1, 1.0),
        (4, 1, 4.0),
        (4, 2, 8.0),
        (8, 1, 8.0),
        (16, 2, 32.0),
        (32, 3, 96.0),
    ])
    def test_basic_cu_times_nodes(self, cu, nodes, expected):
        item = make_line_item(lakebase_cu=cu, lakebase_ha_nodes=nodes)
        dbu_hr, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu_hr == pytest.approx(expected), (
            f"CU={cu}, nodes={nodes}: expected {expected}, got {dbu_hr}"
        )

    def test_half_cu_single_node(self):
        """Spec case: 0.5 CU × 1 node = 0.5 DBU/hr."""
        dbu = calc_dbu_per_hour(0.5, 1)
        assert dbu == pytest.approx(0.5)

    def test_4cu_2nodes(self):
        """Spec case: 4 CU × 2 HA nodes = 8 DBU/hr."""
        dbu = calc_dbu_per_hour(4, 2)
        assert dbu == pytest.approx(8.0)

    def test_32cu_3nodes(self):
        """Spec case: 32 CU × 3 HA nodes = 96 DBU/hr."""
        dbu = calc_dbu_per_hour(32, 3)
        assert dbu == pytest.approx(96.0)


class TestLargeCUSizes:
    """AC-1 extended: Fixed-size CU values (36-112)."""

    @pytest.mark.parametrize("cu", [36, 40, 44, 48, 52, 56, 60, 64,
                                     72, 80, 88, 96, 104, 112])
    def test_fixed_size_cu_single_node(self, cu):
        item = make_line_item(lakebase_cu=cu, lakebase_ha_nodes=1)
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        assert dbu_hr == pytest.approx(float(cu))

    @pytest.mark.parametrize("cu", [36, 64, 112])
    def test_fixed_size_cu_multi_node(self, cu):
        for nodes in (2, 3):
            item = make_line_item(lakebase_cu=cu, lakebase_ha_nodes=nodes)
            dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
            assert dbu_hr == pytest.approx(cu * nodes)

    def test_max_config_112cu_3nodes(self):
        """Max: 112 CU × 3 nodes = 336 DBU/hr."""
        item = make_line_item(lakebase_cu=112, lakebase_ha_nodes=3)
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        assert dbu_hr == pytest.approx(336.0)


class TestMonthlyDBUs:
    """AC-3: Monthly DBUs = DBU/hr × hours_per_month."""

    @pytest.mark.parametrize("cu,nodes,hours,expected_monthly", [
        (0.5, 1, 730, 365.0),
        (4, 2, 730, 5840.0),
        (32, 3, 730, 70080.0),
        (4, 1, 200, 800.0),
    ])
    def test_monthly_dbus(self, cu, nodes, hours, expected_monthly):
        monthly = calc_monthly_dbus(cu, nodes, hours)
        assert monthly == pytest.approx(expected_monthly)

    def test_always_on_730_hours(self):
        """Lakebase uses 730 hrs/month (always-on)."""
        monthly = calc_monthly_dbus(4, 2, 730)
        assert monthly == pytest.approx(5840.0)


class TestHelperMatchesBackend:
    """Verify calc helpers match backend _calculate_dbu_per_hour."""

    @pytest.mark.parametrize("cu,nodes", [
        (0.5, 1), (1, 1), (4, 2), (8, 1),
        (16, 2), (32, 3), (64, 1), (112, 3),
    ])
    def test_helper_matches_backend(self, cu, nodes):
        item = make_line_item(lakebase_cu=cu, lakebase_ha_nodes=nodes)
        be_dbu, _ = _calculate_dbu_per_hour(item, 'aws')
        helper_dbu = calc_dbu_per_hour(cu, nodes)
        assert be_dbu == pytest.approx(helper_dbu)


class TestAllClouds:
    """Verify same calculation across all clouds."""

    @pytest.mark.parametrize("cloud", ["aws", "azure", "gcp"])
    def test_lakebase_same_across_clouds(self, cloud):
        item = make_line_item(lakebase_cu=4, lakebase_ha_nodes=2)
        dbu_hr, _ = _calculate_dbu_per_hour(item, cloud)
        assert dbu_hr == pytest.approx(8.0)
