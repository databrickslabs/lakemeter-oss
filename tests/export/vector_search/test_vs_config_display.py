"""Test Vector Search configuration display and workload type config.

Verifies the workload type definition and config detail output.
"""
import pytest

from tests.export.vector_search.conftest import make_line_item
from app.routes.export.helpers import (
    _get_workload_config_details, _get_workload_display_name,
)


class TestModeDisplayVariations:
    """All mode string variations display correctly."""

    def test_standard_lowercase(self):
        item = make_line_item(vector_search_mode='standard')
        config = _get_workload_config_details(item)
        assert 'Standard' in config

    def test_storage_optimized(self):
        item = make_line_item(vector_search_mode='storage_optimized')
        config = _get_workload_config_details(item)
        assert 'Storage Optimized' in config

    def test_none_mode_shows_standard(self):
        item = make_line_item(vector_search_mode=None)
        config = _get_workload_config_details(item)
        assert 'Standard' in config


class TestCapacityDisplay:
    """Capacity shown in config details."""

    @pytest.mark.parametrize("cap,expected_text", [
        (1, '1M vectors'),
        (2, '2M vectors'),
        (10, '10M vectors'),
        (64, '64M vectors'),
        (100, '100M vectors'),
    ])
    def test_capacity_text(self, cap, expected_text):
        item = make_line_item(vector_capacity_millions=cap)
        config = _get_workload_config_details(item)
        assert expected_text in config

    def test_zero_capacity_omitted(self):
        item = make_line_item(vector_capacity_millions=0)
        config = _get_workload_config_details(item)
        # 0 is falsy, so capacity line should be omitted
        assert 'vectors' not in config

    def test_none_capacity_omitted(self):
        item = make_line_item(vector_capacity_millions=None)
        config = _get_workload_config_details(item)
        assert 'vectors' not in config


class TestConfigSeparator:
    """Config parts joined with ' | '."""

    def test_mode_and_capacity_joined(self):
        item = make_line_item(
            vector_search_mode='standard', vector_capacity_millions=5,
        )
        config = _get_workload_config_details(item)
        assert ' | ' in config
        parts = config.split(' | ')
        assert len(parts) == 2

    def test_mode_only_no_separator(self):
        item = make_line_item(
            vector_search_mode='standard', vector_capacity_millions=None,
        )
        config = _get_workload_config_details(item)
        assert ' | ' not in config


class TestFullPipeline:
    """End-to-end: mode + capacity → config string."""

    @pytest.mark.parametrize("mode,cap,expected_parts", [
        ('standard', 2, ['Mode: Standard', 'Capacity: 2M vectors']),
        ('storage_optimized', 64,
         ['Mode: Storage Optimized', 'Capacity: 64M vectors']),
        ('standard', None, ['Mode: Standard']),
    ])
    def test_full_config(self, mode, cap, expected_parts):
        item = make_line_item(
            vector_search_mode=mode, vector_capacity_millions=cap,
        )
        config = _get_workload_config_details(item)
        for part in expected_parts:
            assert part in config, f"Missing '{part}' in config: {config}"
