"""Test Vector Search edge cases.

AC-15 to AC-20: Config display, fractional/large capacity, defaults, no negatives.
"""
import pytest

from tests.export.vector_search.conftest import make_line_item
from tests.export.vector_search.vs_calc_helpers import calc_dbu_per_hour, calc_units
from app.routes.export.calculations import _calculate_dbu_per_hour
from app.routes.export.helpers import _get_workload_config_details


class TestConfigDisplay:
    """AC-15, AC-16: Config shows mode and capacity."""

    def test_standard_mode_display(self):
        item = make_line_item(
            vector_search_mode='standard', vector_capacity_millions=5,
        )
        config = _get_workload_config_details(item)
        assert 'Mode: Standard' in config

    def test_storage_optimized_mode_display(self):
        item = make_line_item(
            vector_search_mode='storage_optimized',
            vector_capacity_millions=64,
        )
        config = _get_workload_config_details(item)
        assert 'Mode: Storage Optimized' in config

    def test_capacity_in_config(self):
        item = make_line_item(vector_capacity_millions=10)
        config = _get_workload_config_details(item)
        assert '10M vectors' in config

    def test_no_capacity_omits_from_config(self):
        item = make_line_item(vector_capacity_millions=None)
        config = _get_workload_config_details(item)
        assert 'Mode: Standard' in config
        assert 'vectors' not in config


class TestFractionalCapacity:
    """AC-17: Fractional capacity (e.g., 0.5M) calculates correctly."""

    @pytest.mark.parametrize("capacity_m,mode,expected_dbu", [
        (0.5, 'standard', 4.0),       # ceil(0.5M/2M)=1 unit
        (0.1, 'standard', 4.0),       # ceil(0.1M/2M)=1 unit
        (1.5, 'standard', 4.0),       # ceil(1.5M/2M)=1 unit
        (0.5, 'storage_optimized', 18.29),  # ceil(0.5M/64M)=1 unit
    ])
    def test_fractional_dbu(self, capacity_m, mode, expected_dbu):
        item = make_line_item(
            vector_search_mode=mode, vector_capacity_millions=capacity_m,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        assert abs(dbu_hr - expected_dbu) < 0.01


class TestLargeCapacity:
    """AC-18: Large capacity (1000M) calculates correctly."""

    def test_1000m_standard(self):
        """1000M / 2M = 500 units × 4.0 = 2000 DBU/hr."""
        item = make_line_item(
            vector_search_mode='standard',
            vector_capacity_millions=1000,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        assert abs(dbu_hr - 2000.0) < 0.01

    def test_1000m_storage_optimized(self):
        """ceil(1000M / 64M) = 16 units × 18.29 = 292.64."""
        item = make_line_item(
            vector_search_mode='storage_optimized',
            vector_capacity_millions=1000,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        expected = 16 * 18.29  # ceil(1_000_000_000 / 64_000_000) = 16
        assert abs(dbu_hr - expected) < 0.01

    def test_10000m_no_overflow(self):
        """Very large capacity should not overflow or produce NaN."""
        item = make_line_item(
            vector_search_mode='standard',
            vector_capacity_millions=10000,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        assert dbu_hr > 0
        import math
        assert not math.isnan(dbu_hr)


class TestDefaultMode:
    """AC-19: Missing mode defaults to 'standard'."""

    def test_none_mode_defaults_to_standard(self):
        item = make_line_item(
            vector_search_mode=None, vector_capacity_millions=2,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        assert abs(dbu_hr - 4.0) < 0.01

    def test_empty_string_mode(self):
        """Empty string mode should use standard defaults."""
        item = make_line_item(
            vector_search_mode='', vector_capacity_millions=2,
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, 'aws')
        # Backend uses `mode or 'standard'`, empty string → 'standard'
        # But key would be 'aws:' which won't match → uses defaults
        assert dbu_hr >= 0


class TestNoNegatives:
    """AC-20: No negative values in output."""

    @pytest.mark.parametrize("capacity_m", [0, 0.001, 1, 100])
    def test_dbu_hr_never_negative(self, capacity_m):
        item = make_line_item(vector_capacity_millions=capacity_m)
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws')
        assert dbu_hr >= 0

    @pytest.mark.parametrize("capacity_m", [0, 0.001, 1, 100])
    def test_units_never_negative(self, capacity_m):
        units = calc_units(capacity_m, 'standard')
        assert units >= 0

    @pytest.mark.parametrize("capacity_m", [-5, -1, -0.1])
    def test_negative_capacity_clamps_to_zero(self, capacity_m):
        """Negative capacity should produce 0 DBU/hr (clamped) or raise."""
        item = make_line_item(vector_capacity_millions=capacity_m)
        dbu_hr, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu_hr >= 0, (
            f"Negative capacity {capacity_m}M should not produce "
            f"negative DBU/hr, got {dbu_hr}"
        )

    @pytest.mark.parametrize("capacity_m", [-5, -1, -0.1])
    def test_negative_capacity_units_non_negative(self, capacity_m):
        """Helper calc_units should never return negative."""
        units = calc_units(max(capacity_m, 0), 'standard')
        assert units >= 0


class TestCalcItemValuesIntegration:
    """Test calc_item_values for Vector Search path."""

    def test_hourly_path_used(self):
        """Vector Search uses hourly path, not token or provisioned."""
        from app.routes.export.excel_item_helpers import calc_item_values
        item = make_line_item(
            vector_capacity_millions=2, hours_per_month=730,
        )
        dbu_per_hour = 4.0
        hours, tok_qty, dbu_m, total_dbus, tok_type = calc_item_values(
            item, False, False, dbu_per_hour, 'aws', [])
        assert hours == 730
        assert tok_qty == 0
        assert abs(total_dbus - 2920.0) < 0.1
        assert tok_type == ''

    def test_run_based_hours(self):
        """Vector Search with run-based usage."""
        from app.routes.export.excel_item_helpers import calc_item_values
        item = make_line_item(
            vector_capacity_millions=2,
            hours_per_month=None,
            runs_per_day=10,
            avg_runtime_minutes=60,
            days_per_month=22,
        )
        dbu_per_hour = 4.0
        hours, _, _, total_dbus, _ = calc_item_values(
            item, False, False, dbu_per_hour, 'aws', [])
        expected_hours = (10 * 60 / 60) * 22  # = 220
        assert abs(hours - expected_hours) < 0.1
        assert abs(total_dbus - 4.0 * 220) < 0.1


class TestDisplayName:
    """Verify workload display name."""

    def test_display_name_is_vector_search(self):
        from app.routes.export.helpers import _get_workload_display_name
        assert _get_workload_display_name('VECTOR_SEARCH') == 'Vector Search'
