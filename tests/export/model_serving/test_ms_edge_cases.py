"""Test Model Serving edge cases, NaN guards, and cross-cloud consistency.

AC-29 to AC-32: Unknown GPU, zero hours, NaN prevention.
"""
import math
import pytest
from .conftest import make_line_item
from .ms_calc_helpers import (
    MODEL_SERVING_RATES, frontend_calc_model_serving,
    backend_calc_model_serving, get_gpu_dbu_rate,
)


class TestNaNGuards:
    """AC-32: No NaN for any valid GPU + hours combination."""

    @pytest.mark.parametrize("gpu_type", [
        "cpu", "gpu_small_t4", "gpu_medium_a10g_1x",
        "gpu_medium_a10g_4x", "gpu_medium_a10g_8x",
        "gpu_xlarge_a100_40gb_8x", "gpu_xlarge_a100_80gb_8x",
    ])
    def test_no_nan_aws_frontend(self, gpu_type):
        result = frontend_calc_model_serving(gpu_type=gpu_type, cloud='aws')
        for key, val in result.items():
            if isinstance(val, (int, float)):
                assert not math.isnan(val), f"NaN in fe {key} for {gpu_type}"
                assert not math.isinf(val), f"Inf in fe {key} for {gpu_type}"

    @pytest.mark.parametrize("gpu_type", [
        "cpu", "gpu_small_t4", "gpu_medium_a10g_1x",
        "gpu_medium_a10g_4x", "gpu_medium_a10g_8x",
        "gpu_xlarge_a100_40gb_8x", "gpu_xlarge_a100_80gb_8x",
    ])
    def test_no_nan_aws_backend(self, gpu_type):
        result = backend_calc_model_serving(gpu_type=gpu_type, cloud='aws')
        for key, val in result.items():
            if isinstance(val, (int, float)):
                assert not math.isnan(val), f"NaN in be {key} for {gpu_type}"
                assert not math.isinf(val), f"Inf in be {key} for {gpu_type}"

    @pytest.mark.parametrize("gpu_type", [
        "cpu", "gpu_small_t4", "gpu_xlarge_a100_80gb_1x",
        "gpu_2xlarge_a100_80gb_2x", "gpu_4xlarge_a100_80gb_4x",
    ])
    def test_no_nan_azure(self, gpu_type):
        fe = frontend_calc_model_serving(gpu_type=gpu_type, cloud='azure')
        be = backend_calc_model_serving(gpu_type=gpu_type, cloud='azure')
        for r in (fe, be):
            for key, val in r.items():
                if isinstance(val, (int, float)):
                    assert not math.isnan(val), f"NaN in {key} for azure:{gpu_type}"

    @pytest.mark.parametrize("gpu_type", ["cpu", "gpu_medium_g2_standard_8"])
    def test_no_nan_gcp(self, gpu_type):
        fe = frontend_calc_model_serving(gpu_type=gpu_type, cloud='gcp')
        be = backend_calc_model_serving(gpu_type=gpu_type, cloud='gcp')
        for r in (fe, be):
            for key, val in r.items():
                if isinstance(val, (int, float)):
                    assert not math.isnan(val), f"NaN in {key} for gcp:{gpu_type}"


class TestZeroHours:
    """AC-30: Zero hours = zero cost."""

    @pytest.mark.parametrize("gpu_type", [
        "cpu", "gpu_small_t4", "gpu_xlarge_a100_80gb_8x",
    ])
    def test_zero_hours_zero_cost_frontend(self, gpu_type):
        result = frontend_calc_model_serving(
            gpu_type=gpu_type, cloud='aws', hours_per_month=0
        )
        assert result['monthly_dbus'] == 0
        assert result['dbu_cost'] == 0
        assert result['total_cost'] == 0

    @pytest.mark.parametrize("gpu_type", [
        "cpu", "gpu_small_t4", "gpu_xlarge_a100_80gb_8x",
    ])
    def test_zero_hours_zero_cost_backend(self, gpu_type):
        result = backend_calc_model_serving(
            gpu_type=gpu_type, cloud='aws', hours_per_month=0
        )
        assert result['monthly_dbus'] == 0
        assert result['dbu_cost'] == 0
        assert result['total_cost'] == 0


class TestUnknownGPU:
    """AC-29: Unknown GPU type defaults to 0 (backend) or 2 (frontend)."""

    def test_unknown_gpu_frontend_fallback(self):
        """Frontend falls back to 2 DBU/hr for unknown GPU types."""
        result = frontend_calc_model_serving(
            gpu_type='nonexistent', cloud='aws', hours_per_month=100
        )
        assert result['dbu_per_hour'] == 2  # Frontend fallback

    def test_unknown_gpu_backend_zero(self):
        """Backend returns 0 for unknown GPU types."""
        result = backend_calc_model_serving(
            gpu_type='nonexistent', cloud='aws', hours_per_month=100
        )
        assert result['dbu_per_hour'] == 0


class TestCrossCloudConsistency:
    """Verify CPU rate is consistent across clouds."""

    def test_cpu_same_across_clouds(self):
        for cloud in ('aws', 'azure', 'gcp'):
            rate = get_gpu_dbu_rate(cloud, 'cpu')
            assert rate == 1.0, f"{cloud} CPU rate = {rate}, expected 1.0"

    def test_t4_same_aws_azure(self):
        """T4 GPU available on AWS and Azure at same rate."""
        aws_rate = get_gpu_dbu_rate('aws', 'gpu_small_t4')
        azure_rate = get_gpu_dbu_rate('azure', 'gpu_small_t4')
        assert aws_rate == azure_rate == 10.48


class TestFrontendBackendAlignment:
    """Verify FE and BE produce same results for known GPU types."""

    @pytest.mark.parametrize("gpu_type,cloud", [
        ("cpu", "aws"), ("gpu_small_t4", "aws"),
        ("gpu_medium_a10g_1x", "aws"), ("gpu_xlarge_a100_80gb_8x", "aws"),
        ("cpu", "azure"), ("gpu_xlarge_a100_80gb_1x", "azure"),
        ("cpu", "gcp"), ("gpu_medium_g2_standard_8", "gcp"),
    ])
    def test_fe_be_monthly_dbus_match(self, gpu_type, cloud):
        fe = frontend_calc_model_serving(
            gpu_type=gpu_type, cloud=cloud, hours_per_month=200
        )
        be = backend_calc_model_serving(
            gpu_type=gpu_type, cloud=cloud, hours_per_month=200
        )
        assert fe['monthly_dbus'] == be['monthly_dbus']
        assert fe['dbu_cost'] == be['dbu_cost']
