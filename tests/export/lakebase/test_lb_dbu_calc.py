"""Test Lakebase autoscaling DBU calculation logic."""
import pytest

from tests.export.lakebase.conftest import make_line_item
from tests.export.lakebase.lb_calc_helpers import calc_dbu_per_hour, calc_monthly_dbus
from app.routes.export.calculations import _calculate_dbu_per_hour, _calculate_hours_per_month


class TestBasicDBUPerHour:
    """Equivalent DBU/hr includes DBU/CU-hour and always-on discount."""

    @pytest.mark.parametrize("cu,nodes", [
        (0.5, 1),
        (1, 1),
        (4, 1),
        (4, 2),
        (8, 1),
        (16, 2),
        (32, 3),
        (32, 4),
    ])
    def test_basic_cu_times_nodes(self, cu, nodes):
        item = make_line_item(lakebase_cu=cu, lakebase_ha_nodes=nodes)
        dbu_hr, warnings = _calculate_dbu_per_hour(item, 'aws')
        expected = calc_dbu_per_hour(cu, nodes)
        assert warnings == []
        assert dbu_hr == pytest.approx(expected), (
            f"CU={cu}, nodes={nodes}: expected {expected}, got {dbu_hr}"
        )

    def test_half_cu_single_node(self):
        dbu = calc_dbu_per_hour(0.5, 1)
        assert dbu == pytest.approx(0.08625)

    def test_4cu_2nodes(self):
        dbu = calc_dbu_per_hour(4, 2)
        assert dbu == pytest.approx(1.38)

    def test_32cu_3nodes(self):
        dbu = calc_dbu_per_hour(32, 3)
        assert dbu == pytest.approx(16.56)


class TestLargeCUSizes:
    """Fixed-size legacy CU values still fall back to discounted always-on floor."""

    @pytest.mark.parametrize("cu", [36, 40, 44, 48, 52, 56, 60, 64,
                                     72, 80, 88, 96, 104, 112])
    def test_fixed_size_cu_single_node(self, cu):
        item = make_line_item(lakebase_cu=cu, lakebase_ha_nodes=1)
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        assert dbu_hr == pytest.approx(calc_dbu_per_hour(cu, 1))

    @pytest.mark.parametrize("cu", [36, 64, 112])
    def test_fixed_size_cu_multi_node(self, cu):
        for nodes in (2, 3):
            item = make_line_item(lakebase_cu=cu, lakebase_ha_nodes=nodes)
            dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
            assert dbu_hr == pytest.approx(calc_dbu_per_hour(cu, nodes))

    def test_max_config_112cu_3nodes(self):
        item = make_line_item(lakebase_cu=112, lakebase_ha_nodes=3)
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        assert dbu_hr == pytest.approx(calc_dbu_per_hour(112, 3))


class TestMonthlyDBUs:
    """Monthly DBUs use 730 always-on hours when scale-to-zero is disabled."""

    @pytest.mark.parametrize("cu,nodes,hours", [
        (0.5, 1, 730),
        (4, 2, 730),
        (32, 3, 730),
        (4, 1, 730),
    ])
    def test_monthly_dbus(self, cu, nodes, hours):
        monthly = calc_monthly_dbus(cu, nodes, hours)
        assert monthly == pytest.approx(calc_dbu_per_hour(cu, nodes) * hours)

    def test_always_on_730_hours(self):
        item = make_line_item(lakebase_cu=4, lakebase_ha_nodes=2, hours_per_month=200)
        assert _calculate_hours_per_month(item) == 730
        monthly = calc_monthly_dbus(4, 2, 730)
        assert monthly == pytest.approx(calc_dbu_per_hour(4, 2) * 730)


class TestHelperMatchesBackend:
    """Verify calc helpers match backend _calculate_dbu_per_hour."""

    @pytest.mark.parametrize("cu,nodes", [
        (0.5, 1), (1, 1), (4, 2), (8, 1),
        (16, 2), (32, 3), (64, 1), (112, 3),
        (32, 4),
    ])
    def test_helper_matches_backend(self, cu, nodes):
        item = make_line_item(lakebase_cu=cu, lakebase_ha_nodes=nodes)
        be_dbu, _ = _calculate_dbu_per_hour(item, 'aws')
        helper_dbu = calc_dbu_per_hour(cu, nodes)
        assert be_dbu == pytest.approx(helper_dbu)


class TestAutoscaleConfig:
    def test_scale_up_headroom_is_full_price(self):
        item = make_line_item(
            lakebase_cu=4,
            lakebase_ha_nodes=1,
            workload_config={
                "lakebase_min_cu": 4,
                "lakebase_max_cu": 8,
                "lakebase_scale_to_zero_enabled": False,
                "lakebase_scale_up_hours_per_month": 100,
                "lakebase_always_on_discount_pct": 25,
            },
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        expected_monthly = (4 * 0.230 * 630 * 0.75) + (8 * 0.230 * 100)
        assert dbu_hr == pytest.approx(expected_monthly / 730)

    def test_scale_to_zero_uses_active_hours_without_discount(self):
        item = make_line_item(
            lakebase_cu=4,
            lakebase_ha_nodes=1,
            hours_per_month=200,
            workload_config={
                "lakebase_min_cu": 4,
                "lakebase_max_cu": 8,
                "lakebase_scale_to_zero_enabled": True,
                "lakebase_active_hours_per_month": 200,
                "lakebase_scale_up_hours_per_month": 50,
            },
        )
        assert _calculate_hours_per_month(item) == 200
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        expected_monthly = (4 * 0.230 * 150) + (8 * 0.230 * 50)
        assert dbu_hr == pytest.approx(expected_monthly / 200)


class TestAllClouds:
    """Verify Lakebase rates by cloud use current DBU/CU-hour rates."""

    @pytest.mark.parametrize("cloud,dbu_per_cu_hour", [("aws", 0.230), ("azure", 0.213)])
    def test_lakebase_rates_by_cloud(self, cloud, dbu_per_cu_hour):
        item = make_line_item(lakebase_cu=4, lakebase_ha_nodes=4)
        dbu_hr, _ = _calculate_dbu_per_hour(item, cloud)
        assert dbu_hr == pytest.approx(4 * 4 * dbu_per_cu_hour * 0.75)
