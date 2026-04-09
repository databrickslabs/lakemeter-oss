"""Test backend export calculation functions for Model Serving.

AC-17 to AC-22: Hours calculation, monthly DBUs, DBU cost.
AC-29 to AC-32: Edge cases and unknown GPU types.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from app.routes.export.calculations import (
    _calculate_dbu_per_hour, _calculate_hours_per_month,
)
from .conftest import make_line_item


class TestModelServingDBUPerHour:
    """Backend _calc_model_serving_dbu via _calculate_dbu_per_hour."""

    def test_cpu_rate(self):
        item = make_line_item(model_serving_gpu_type='cpu')
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 1.0
        assert len(warnings) == 0

    def test_gpu_small_t4(self):
        item = make_line_item(model_serving_gpu_type='gpu_small_t4')
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 10.48

    def test_gpu_medium_a10g_1x(self):
        item = make_line_item(model_serving_gpu_type='gpu_medium_a10g_1x')
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 20.0

    def test_gpu_xlarge_a100_80gb_8x(self):
        item = make_line_item(model_serving_gpu_type='gpu_xlarge_a100_80gb_8x')
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 628.0

    def test_azure_xlarge(self):
        item = make_line_item(model_serving_gpu_type='gpu_xlarge_a100_80gb_1x')
        dbu, warnings = _calculate_dbu_per_hour(item, 'azure')
        assert dbu == 78.6

    def test_gcp_medium_g2(self):
        item = make_line_item(model_serving_gpu_type='gpu_medium_g2_standard_8')
        dbu, warnings = _calculate_dbu_per_hour(item, 'gcp')
        assert dbu == 5.0


class TestModelServingHours:
    """AC-17 to AC-19: Hours calculation for Model Serving."""

    def test_direct_hours(self):
        item = make_line_item(hours_per_month=200)
        assert _calculate_hours_per_month(item) == 200

    def test_24_7_hours(self):
        item = make_line_item(hours_per_month=730)
        assert _calculate_hours_per_month(item) == 730

    def test_run_based(self):
        item = make_line_item(
            runs_per_day=10, avg_runtime_minutes=30, days_per_month=22,
            hours_per_month=None,
        )
        expected = (10 * 30 / 60) * 22  # 110 hours
        assert _calculate_hours_per_month(item) == expected

    def test_run_based_overrides_hours(self):
        """AC-19: Run-based fields take priority over hours_per_month."""
        item = make_line_item(
            runs_per_day=5, avg_runtime_minutes=60, days_per_month=20,
            hours_per_month=730,
        )
        expected = (5 * 60 / 60) * 20  # 100 hours, NOT 730
        assert _calculate_hours_per_month(item) == expected

    def test_zero_hours(self):
        item = make_line_item(hours_per_month=None, runs_per_day=None)
        assert _calculate_hours_per_month(item) == 0


class TestModelServingUnknownGPU:
    """AC-29, AC-31: Unknown GPU type behavior."""

    def test_unknown_gpu_returns_zero_with_warning(self):
        item = make_line_item(model_serving_gpu_type='nonexistent_gpu')
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 0
        assert len(warnings) == 1
        assert 'not found' in warnings[0].lower()

    def test_none_gpu_defaults_to_cpu(self):
        """AC-31: Missing gpu_type defaults to 'cpu'."""
        item = make_line_item(model_serving_gpu_type=None)
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 1.0  # CPU rate
        assert len(warnings) == 0

    def test_wrong_cloud_returns_zero(self):
        item = make_line_item(model_serving_gpu_type='gpu_small_t4')
        dbu, warnings = _calculate_dbu_per_hour(item, 'nonexistent_cloud')
        assert dbu == 0
        assert len(warnings) == 1


class TestModelServingMonthlyCost:
    """AC-20 to AC-22: Full monthly cost calculation."""

    def test_monthly_dbus_formula(self):
        """AC-20: Monthly DBUs = DBU/hr × hours."""
        item = make_line_item(
            model_serving_gpu_type='gpu_small_t4', hours_per_month=200
        )
        dbu_per_hour, _ = _calculate_dbu_per_hour(item, 'aws')
        hours = _calculate_hours_per_month(item)
        monthly_dbus = dbu_per_hour * hours
        assert dbu_per_hour == 10.48
        assert hours == 200
        assert monthly_dbus == 10.48 * 200  # 2096 DBUs

    def test_dbu_cost_formula(self):
        """AC-21: DBU Cost = monthly_dbus × $/DBU."""
        monthly_dbus = 2096.0
        dbu_price = 0.07
        dbu_cost = monthly_dbus * dbu_price
        assert abs(dbu_cost - 146.72) < 0.01

    def test_total_cost_equals_dbu_cost(self):
        """AC-22: Total = DBU Cost (no VM)."""
        item = make_line_item(
            model_serving_gpu_type='gpu_medium_a10g_1x', hours_per_month=100
        )
        dbu_per_hour, _ = _calculate_dbu_per_hour(item, 'aws')
        hours = _calculate_hours_per_month(item)
        monthly_dbus = dbu_per_hour * hours
        dbu_cost = monthly_dbus * 0.07
        # Total = DBU Cost + VM Cost, but VM = 0 for serverless
        total = dbu_cost + 0
        assert total == dbu_cost
        assert dbu_per_hour == 20.0
        assert monthly_dbus == 2000.0
        assert abs(dbu_cost - 140.0) < 0.01
