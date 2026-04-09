"""Test Model Serving config display helpers.

AC-23, AC-24: GPU name label mapping and config details format.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from app.routes.export.helpers import (
    MODEL_SERVING_GPU_NAMES, _model_serving_details,
    _get_workload_display_name, _get_workload_config_details,
)
from .conftest import make_line_item


class TestGPUDisplayNames:
    """AC-23: GPU display name mapping."""

    @pytest.mark.parametrize("gpu_type,expected_label", [
        ("cpu", "CPU"),
        ("gpu_small_t4", "Small (T4)"),
        ("gpu_medium_a10g_1x", "Medium (A10G 1x)"),
        ("gpu_medium_a10g_4x", "Medium (A10G 4x)"),
        ("gpu_medium_a10g_8x", "Medium (A10G 8x)"),
        ("gpu_xlarge_a100_40gb_8x", "XLarge (A100 40GB 8x)"),
        ("gpu_xlarge_a100_80gb_8x", "XLarge (A100 80GB 8x)"),
        ("gpu_xlarge_a100_80gb_1x", "XLarge (A100 80GB 1x)"),
        ("gpu_2xlarge_a100_80gb_2x", "2XLarge (A100 80GB 2x)"),
        ("gpu_4xlarge_a100_80gb_4x", "4XLarge (A100 80GB 4x)"),
    ])
    def test_gpu_display_name(self, gpu_type, expected_label):
        assert MODEL_SERVING_GPU_NAMES[gpu_type] == expected_label

    def test_all_json_gpu_types_have_names(self):
        """Every gpu_type that appears in pricing JSON should have a display name."""
        from .ms_calc_helpers import MODEL_SERVING_RATES
        for key in MODEL_SERVING_RATES:
            gpu_type = key.split(":", 1)[1]
            assert gpu_type in MODEL_SERVING_GPU_NAMES, (
                f"GPU type '{gpu_type}' in pricing JSON but no display name"
            )


class TestModelServingDetails:
    """AC-24: Config details show "GPU: {label}" format."""

    def test_cpu_details(self):
        item = make_line_item(model_serving_gpu_type='cpu')
        details = _model_serving_details(item)
        assert details == ["GPU: CPU"]

    def test_t4_details(self):
        item = make_line_item(model_serving_gpu_type='gpu_small_t4')
        details = _model_serving_details(item)
        assert details == ["GPU: Small (T4)"]

    def test_a100_details(self):
        item = make_line_item(model_serving_gpu_type='gpu_xlarge_a100_80gb_8x')
        details = _model_serving_details(item)
        assert details == ["GPU: XLarge (A100 80GB 8x)"]

    def test_none_gpu_no_details(self):
        item = make_line_item(model_serving_gpu_type=None)
        details = _model_serving_details(item)
        assert details == []

    def test_unknown_gpu_uses_raw_name(self):
        item = make_line_item(model_serving_gpu_type='some_new_gpu')
        details = _model_serving_details(item)
        assert details == ["GPU: some_new_gpu"]


class TestWorkloadDisplayName:
    """Verify Model Serving display name."""

    def test_display_name(self):
        assert _get_workload_display_name('MODEL_SERVING') == 'Model Serving'


class TestWorkloadConfigDetails:
    """Integration test: _get_workload_config_details for Model Serving."""

    def test_config_details_integration(self):
        item = make_line_item(model_serving_gpu_type='gpu_medium_a10g_1x')
        config = _get_workload_config_details(item)
        assert 'GPU: Medium (A10G 1x)' in config

    def test_config_no_gpu(self):
        item = make_line_item(model_serving_gpu_type=None)
        config = _get_workload_config_details(item)
        assert config == '-'
