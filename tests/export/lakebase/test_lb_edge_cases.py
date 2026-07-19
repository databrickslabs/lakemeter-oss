"""Test Lakebase edge cases and boundary conditions."""
import pytest

from tests.export.lakebase.conftest import make_line_item
from tests.export.lakebase.lb_calc_helpers import calc_dbu_per_hour, calc_storage_cost, calc_total_monthly_cost
from app.routes.export.calculations import _calculate_dbu_per_hour


class TestZeroCU:
    """Zero CU should return 0 DBU/hr with warning."""

    def test_zero_cu_returns_zero(self):
        item = make_line_item(lakebase_cu=0)
        dbu_hr, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu_hr == 0

    def test_zero_cu_has_warning(self):
        item = make_line_item(lakebase_cu=0)
        _, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert any("cu" in w.lower() or "not specified" in w.lower() for w in warnings)


class TestNegativeCU:
    """Negative CU values are warned on and clamped to zero for billing."""

    @pytest.mark.parametrize("neg_cu", [-1, -0.5, -112])
    def test_negative_cu_returns_zero_dbu(self, neg_cu):
        item = make_line_item(lakebase_cu=neg_cu, lakebase_ha_nodes=1)
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        assert dbu_hr == 0

    @pytest.mark.parametrize("neg_cu", [-1, -0.5, -112])
    def test_negative_cu_emits_warning(self, neg_cu):
        item = make_line_item(lakebase_cu=neg_cu, lakebase_ha_nodes=1)
        _, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert any("negative" in w.lower() for w in warnings), (
            f"Expected 'negative' warning for CU={neg_cu}, got: {warnings}")

    def test_negative_cu_warning_includes_value(self):
        item = make_line_item(lakebase_cu=-4, lakebase_ha_nodes=1)
        _, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert any("-4" in w for w in warnings), (
            f"Warning should include CU value -4, got: {warnings}")


class TestNoneDefaults:
    """None values should default gracefully."""

    def test_none_cu_treated_as_zero(self):
        item = make_line_item(lakebase_cu=None)
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        assert dbu_hr == 0

    def test_none_nodes_treated_as_one(self):
        item = make_line_item(lakebase_cu=4, lakebase_ha_nodes=None)
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        assert dbu_hr == pytest.approx(calc_dbu_per_hour(4, 1))

    def test_none_storage_gb(self):
        cost = calc_storage_cost(0, 0.023)
        assert cost == 0


class TestStorageCost:
    """Storage cost = GB x rate."""

    @pytest.mark.parametrize("gb,rate,expected", [
        (10, 0.023, 0.23),
        (100, 0.023, 2.30),
        (1000, 0.023, 23.00),
        (8192, 0.023, 188.416),
    ])
    def test_storage_cost_formula(self, gb, rate, expected):
        cost = calc_storage_cost(gb, rate)
        assert cost == pytest.approx(expected, rel=1e-3)

    def test_zero_storage(self):
        cost = calc_storage_cost(0, 0.023)
        assert cost == 0


class TestTotalMonthlyCost:
    """End-to-end helper cost calculation verification."""

    def test_spec_case_1(self):
        total = calc_total_monthly_cost(cu=0.5, ha_nodes=1, hours=730, dbu_rate=0.40, storage_gb=10)
        compute = calc_dbu_per_hour(0.5, 1) * 730 * 0.40
        storage = 10 * 0.023
        assert total == pytest.approx(compute + storage)

    def test_spec_case_2(self):
        total = calc_total_monthly_cost(cu=4, ha_nodes=2, hours=730, dbu_rate=0.40, storage_gb=100)
        compute = calc_dbu_per_hour(4, 2) * 730 * 0.40
        storage = 100 * 0.023
        assert total == pytest.approx(compute + storage)

    def test_spec_case_3(self):
        total = calc_total_monthly_cost(cu=32, ha_nodes=3, hours=730, dbu_rate=0.40, storage_gb=1000)
        compute = calc_dbu_per_hour(32, 3) * 730 * 0.40
        storage = 1000 * 0.023
        assert total == pytest.approx(compute + storage)

    def test_with_discount(self):
        total = calc_total_monthly_cost(cu=4, ha_nodes=2, hours=730, dbu_rate=0.40, storage_gb=100, discount_pct=0.20)
        compute = calc_dbu_per_hour(4, 2) * 730 * 0.40 * 0.80
        storage = 100 * 0.023
        assert total == pytest.approx(compute + storage)


class TestMaxConfig:
    """Maximum configuration (112 CU, 3 nodes, 8192 GB)."""

    def test_max_dbu_per_hour(self):
        item = make_line_item(lakebase_cu=112, lakebase_ha_nodes=3)
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        assert dbu_hr == pytest.approx(calc_dbu_per_hour(112, 3))

    def test_max_monthly_cost(self):
        total = calc_total_monthly_cost(cu=112, ha_nodes=3, hours=730, dbu_rate=0.40, storage_gb=8192)
        compute = calc_dbu_per_hour(112, 3) * 730 * 0.40
        storage = 8192 * 0.023
        assert total == pytest.approx(compute + storage)
