"""Test Lakebase edge cases and boundary conditions.

AC-10: Zero CU warns, None defaults, max config.
"""
import pytest

from tests.export.lakebase.conftest import make_line_item
from tests.export.lakebase.lb_calc_helpers import (
    calc_dbu_per_hour, calc_storage_cost, calc_total_monthly_cost,
)
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
        assert any("cu" in w.lower() or "not specified" in w.lower()
                    for w in warnings)


class TestNegativeCU:
    """Negative CU should emit a warning and still compute correctly."""

    @pytest.mark.parametrize("neg_cu", [-1, -0.5, -112])
    def test_negative_cu_returns_negative_dbu(self, neg_cu):
        """Backend computes CU × nodes — negative CU yields negative DBU/hr."""
        item = make_line_item(lakebase_cu=neg_cu, lakebase_ha_nodes=1)
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        assert dbu_hr < 0, f"Negative CU ({neg_cu}) should yield negative DBU/hr"

    @pytest.mark.parametrize("neg_cu", [-1, -0.5, -112])
    def test_negative_cu_emits_warning(self, neg_cu):
        """Backend should warn when CU is negative."""
        item = make_line_item(lakebase_cu=neg_cu, lakebase_ha_nodes=1)
        _, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert any("negative" in w.lower() for w in warnings), (
            f"Expected 'negative' warning for CU={neg_cu}, got: {warnings}")

    def test_negative_cu_with_ha_nodes(self):
        """Negative CU with HA nodes still returns negative product."""
        item = make_line_item(lakebase_cu=-4, lakebase_ha_nodes=3)
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        assert dbu_hr == pytest.approx(-12.0)

    def test_negative_cu_warning_includes_value(self):
        """Warning message should include the actual negative CU value."""
        item = make_line_item(lakebase_cu=-4, lakebase_ha_nodes=1)
        _, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert any("-4" in w for w in warnings), (
            f"Warning should include CU value -4, got: {warnings}")

    def test_negative_cu_helper_matches_backend(self):
        """Verify helper mirrors backend for negative inputs."""
        item = make_line_item(lakebase_cu=-2, lakebase_ha_nodes=2)
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        expected = calc_dbu_per_hour(-2, 2)
        assert dbu_hr == pytest.approx(expected)


class TestNoneDefaults:
    """None values should default gracefully."""

    def test_none_cu_treated_as_zero(self):
        item = make_line_item(lakebase_cu=None)
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        assert dbu_hr == 0

    def test_none_nodes_treated_as_one(self):
        """HA nodes default to 1 if not specified."""
        item = make_line_item(lakebase_cu=4, lakebase_ha_nodes=None)
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        assert dbu_hr == pytest.approx(4.0)

    def test_none_storage_gb(self):
        """Storage GB of None → 0 cost."""
        cost = calc_storage_cost(0, 0.023)
        assert cost == 0


class TestStorageCost:
    """AC-2: Storage cost = GB × $0.023/GB/month."""

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

    def test_max_storage_8192gb(self):
        """Spec: max storage = 8192 GB."""
        cost = calc_storage_cost(8192, 0.023)
        assert cost == pytest.approx(188.416, rel=1e-3)


class TestTotalMonthlyCost:
    """End-to-end cost calculation verification."""

    def test_spec_case_1(self):
        """0.5 CU, 1 node, 10GB, 730 hrs, $0.40/DBU."""
        total = calc_total_monthly_cost(
            cu=0.5, ha_nodes=1, hours=730,
            dbu_rate=0.40, storage_gb=10,
        )
        compute = 0.5 * 730 * 0.40  # 146.0
        storage = 10 * 0.023  # 0.23
        assert total == pytest.approx(compute + storage)

    def test_spec_case_2(self):
        """4 CU, 2 nodes, 100GB, 730 hrs, $0.40/DBU."""
        total = calc_total_monthly_cost(
            cu=4, ha_nodes=2, hours=730,
            dbu_rate=0.40, storage_gb=100,
        )
        compute = 8.0 * 730 * 0.40  # 2336.0
        storage = 100 * 0.023  # 2.30
        assert total == pytest.approx(compute + storage)

    def test_spec_case_3(self):
        """32 CU, 3 nodes, 1000GB, 730 hrs, $0.40/DBU."""
        total = calc_total_monthly_cost(
            cu=32, ha_nodes=3, hours=730,
            dbu_rate=0.40, storage_gb=1000,
        )
        compute = 96.0 * 730 * 0.40  # 28032.0
        storage = 1000 * 0.023  # 23.0
        assert total == pytest.approx(compute + storage)

    def test_with_discount(self):
        """4 CU, 2 nodes, 100GB, 730 hrs, 20% discount."""
        total = calc_total_monthly_cost(
            cu=4, ha_nodes=2, hours=730,
            dbu_rate=0.40, storage_gb=100,
            discount_pct=0.20,
        )
        compute = 8.0 * 730 * 0.40 * 0.80  # 1868.8
        storage = 100 * 0.023  # 2.30
        assert total == pytest.approx(compute + storage)


class TestMaxConfig:
    """AC-10: Maximum configuration (112 CU, 3 nodes, 8192 GB)."""

    def test_max_dbu_per_hour(self):
        item = make_line_item(lakebase_cu=112, lakebase_ha_nodes=3)
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        assert dbu_hr == pytest.approx(336.0)

    def test_max_monthly_cost(self):
        total = calc_total_monthly_cost(
            cu=112, ha_nodes=3, hours=730,
            dbu_rate=0.40, storage_gb=8192,
        )
        compute = 336.0 * 730 * 0.40  # 98112.0
        storage = 8192 * 0.023  # 188.416
        assert total == pytest.approx(compute + storage)
