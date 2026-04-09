"""Test Model Serving GPU type → DBU/hr rate mappings across all clouds.

AC-1 through AC-12: Verify each GPU type maps to correct DBU/hr from
model-serving-rates.json for AWS, Azure, and GCP.
"""
import pytest
from .ms_calc_helpers import (
    MODEL_SERVING_RATES, get_gpu_dbu_rate,
    frontend_calc_model_serving, backend_calc_model_serving,
)


class TestAWSGPURates:
    """AC-1 to AC-7: AWS GPU types and their DBU/hr rates."""

    @pytest.mark.parametrize("gpu_type,expected_dbu", [
        ("cpu", 1.0),
        ("gpu_small_t4", 10.48),
        ("gpu_medium_a10g_1x", 20.0),
        ("gpu_medium_a10g_4x", 112.0),
        ("gpu_medium_a10g_8x", 290.8),
        ("gpu_xlarge_a100_40gb_8x", 538.4),
        ("gpu_xlarge_a100_80gb_8x", 628.0),
    ])
    def test_aws_gpu_dbu_rate(self, gpu_type, expected_dbu):
        rate = get_gpu_dbu_rate("aws", gpu_type)
        assert rate == expected_dbu, f"aws:{gpu_type} → {rate}, expected {expected_dbu}"

    @pytest.mark.parametrize("gpu_type,expected_dbu", [
        ("cpu", 1.0),
        ("gpu_small_t4", 10.48),
        ("gpu_medium_a10g_1x", 20.0),
        ("gpu_medium_a10g_4x", 112.0),
        ("gpu_medium_a10g_8x", 290.8),
        ("gpu_xlarge_a100_40gb_8x", 538.4),
        ("gpu_xlarge_a100_80gb_8x", 628.0),
    ])
    def test_aws_frontend_matches_backend(self, gpu_type, expected_dbu):
        fe = frontend_calc_model_serving(gpu_type=gpu_type, cloud="aws", hours_per_month=100)
        be = backend_calc_model_serving(gpu_type=gpu_type, cloud="aws", hours_per_month=100)
        assert fe['dbu_per_hour'] == be['dbu_per_hour']
        assert fe['monthly_dbus'] == be['monthly_dbus']


class TestAzureGPURates:
    """AC-8 to AC-10: Azure GPU types."""

    @pytest.mark.parametrize("gpu_type,expected_dbu", [
        ("cpu", 1.0),
        ("gpu_small_t4", 10.48),
        ("gpu_xlarge_a100_80gb_1x", 78.6),
        ("gpu_2xlarge_a100_80gb_2x", 157.2),
        ("gpu_4xlarge_a100_80gb_4x", 314.4),
    ])
    def test_azure_gpu_dbu_rate(self, gpu_type, expected_dbu):
        rate = get_gpu_dbu_rate("azure", gpu_type)
        assert rate == expected_dbu


class TestGCPGPURates:
    """AC-11 to AC-12: GCP GPU types."""

    @pytest.mark.parametrize("gpu_type,expected_dbu", [
        ("cpu", 1.0),
        ("gpu_medium_g2_standard_8", 5.0),
    ])
    def test_gcp_gpu_dbu_rate(self, gpu_type, expected_dbu):
        rate = get_gpu_dbu_rate("gcp", gpu_type)
        assert rate == expected_dbu


class TestAllRatesInJSON:
    """Verify every entry in model-serving-rates.json has required fields."""

    def test_all_entries_have_dbu_rate(self):
        for key, info in MODEL_SERVING_RATES.items():
            assert 'dbu_rate' in info, f"{key} missing dbu_rate"
            assert info['dbu_rate'] > 0, f"{key} dbu_rate must be positive"

    def test_all_entries_have_correct_sku(self):
        for key, info in MODEL_SERVING_RATES.items():
            assert info.get('sku_product_type') == 'SERVERLESS_REAL_TIME_INFERENCE', (
                f"{key} has wrong SKU: {info.get('sku_product_type')}"
            )

    def test_cpu_cheapest_per_cloud(self):
        """CPU should be cheapest option on each cloud."""
        for cloud in ('aws', 'azure', 'gcp'):
            cpu_rate = get_gpu_dbu_rate(cloud, 'cpu')
            if cpu_rate == 0:
                continue
            for key, info in MODEL_SERVING_RATES.items():
                if key.startswith(f"{cloud}:"):
                    assert info['dbu_rate'] >= cpu_rate, (
                        f"{key} ({info['dbu_rate']}) cheaper than CPU ({cpu_rate})"
                    )

    def test_aws_has_7_entries(self):
        aws_keys = [k for k in MODEL_SERVING_RATES if k.startswith("aws:")]
        assert len(aws_keys) == 7

    def test_azure_has_5_entries(self):
        azure_keys = [k for k in MODEL_SERVING_RATES if k.startswith("azure:")]
        assert len(azure_keys) == 5

    def test_gcp_has_2_entries(self):
        gcp_keys = [k for k in MODEL_SERVING_RATES if k.startswith("gcp:")]
        assert len(gcp_keys) == 2
