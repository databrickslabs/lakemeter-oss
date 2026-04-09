"""Test FMAPI Databricks rate lookups across models, rate types, and clouds.

AC-1 to AC-8: Token-based, provisioned, cross-cloud rate verification.
"""
import pytest
from .fmapi_db_calc_helpers import (
    FMAPI_DB_RATES, get_dbu_rate, get_all_models, get_model_rate_types,
)


class TestAWSTokenRates:
    """AC-1: Token-based input rates match pricing JSON for AWS models."""

    @pytest.mark.parametrize("model,rate_type,expected", [
        ("llama-3-3-70b", "input_token", 7.143),
        ("llama-3-3-70b", "output_token", 21.429),
        ("llama-3-1-8b", "input_token", 2.143),
        ("llama-3-1-8b", "output_token", 6.429),
        ("bge-large", "input_token", 1.429),
        ("gte", "input_token", 1.857),
        ("gpt-oss-20b", "input_token", 1.0),
        ("gpt-oss-20b", "output_token", 4.286),
        ("gpt-oss-120b", "input_token", 2.143),
        ("gpt-oss-120b", "output_token", 8.571),
        ("gemma-3-12b", "input_token", 2.143),
        ("gemma-3-12b", "output_token", 7.143),
        ("llama-4-maverick", "input_token", 7.143),
        ("llama-4-maverick", "output_token", 21.429),
    ])
    def test_aws_token_rate(self, model, rate_type, expected):
        rate = get_dbu_rate("aws", model, rate_type)
        assert rate == expected, f"aws:{model}:{rate_type} = {rate}, expected {expected}"


class TestAWSProvisionedRates:
    """AC-3, AC-4: Provisioned rates match pricing JSON for AWS."""

    @pytest.mark.parametrize("model,rate_type,expected", [
        ("llama-3-3-70b", "provisioned_scaling", 342.857),
        ("llama-3-3-70b", "provisioned_entry", 85.714),
        ("llama-3-1-8b", "provisioned_scaling", 106.0),
        ("llama-3-1-8b", "provisioned_entry", 53.571),
        ("bge-large", "provisioned_scaling", 24.0),
        ("bge-large", "provisioned_entry", 24.0),
        ("gte", "provisioned_scaling", 20.0),
        ("gte", "provisioned_entry", 20.0),
        ("gpt-oss-20b", "provisioned_scaling", 53.571),
        ("gpt-oss-20b", "provisioned_entry", 53.571),
        ("gpt-oss-120b", "provisioned_scaling", 71.429),
        ("gpt-oss-120b", "provisioned_entry", 71.429),
        ("llama-3-2-1b", "provisioned_scaling", 85.714),
        ("llama-3-2-1b", "provisioned_entry", 42.857),
        ("llama-3-2-3b", "provisioned_scaling", 92.857),
        ("llama-3-2-3b", "provisioned_entry", 46.429),
    ])
    def test_aws_provisioned_rate(self, model, rate_type, expected):
        rate = get_dbu_rate("aws", model, rate_type)
        assert rate == expected, f"aws:{model}:{rate_type} = {rate}, expected {expected}"


class TestOutputGTInput:
    """AC-2: Output token rate > input token rate for models with both."""

    @pytest.mark.parametrize("cloud", ["aws", "azure", "gcp"])
    def test_output_gt_input_per_cloud(self, cloud):
        models = get_all_models(cloud)
        for model in models:
            rate_types = get_model_rate_types(cloud, model)
            if 'input_token' in rate_types and 'output_token' in rate_types:
                input_rate = get_dbu_rate(cloud, model, 'input_token')
                output_rate = get_dbu_rate(cloud, model, 'output_token')
                assert output_rate > input_rate, (
                    f"{cloud}:{model} output({output_rate}) <= input({input_rate})"
                )


class TestCrossCloudConsistency:
    """AC-7: Same model/rate_type has same rate across clouds."""

    @pytest.mark.parametrize("model,rate_type", [
        ("llama-3-3-70b", "input_token"),
        ("llama-3-3-70b", "output_token"),
        ("bge-large", "input_token"),
        ("gte", "input_token"),
        ("gpt-oss-20b", "input_token"),
    ])
    def test_rate_same_across_clouds(self, model, rate_type):
        aws_rate = get_dbu_rate("aws", model, rate_type)
        azure_rate = get_dbu_rate("azure", model, rate_type)
        gcp_rate = get_dbu_rate("gcp", model, rate_type)
        assert aws_rate == azure_rate == gcp_rate, (
            f"{model}:{rate_type} aws={aws_rate} azure={azure_rate} gcp={gcp_rate}"
        )


class TestAllEntriesValid:
    """AC-8: All JSON entries have required fields."""

    def test_all_entries_have_dbu_rate(self):
        for key, info in FMAPI_DB_RATES.items():
            assert 'dbu_rate' in info, f"{key} missing dbu_rate"
            assert info['dbu_rate'] > 0, f"{key} dbu_rate must be positive"

    def test_all_entries_have_sku(self):
        for key, info in FMAPI_DB_RATES.items():
            assert 'sku_product_type' in info, f"{key} missing sku_product_type"
            assert info['sku_product_type'] == 'SERVERLESS_REAL_TIME_INFERENCE'

    def test_all_entries_have_is_hourly(self):
        for key, info in FMAPI_DB_RATES.items():
            assert 'is_hourly' in info, f"{key} missing is_hourly"

    def test_token_entries_not_hourly(self):
        for key, info in FMAPI_DB_RATES.items():
            if key.endswith(':input_token') or key.endswith(':output_token'):
                assert info['is_hourly'] is False, f"{key} token should not be hourly"

    def test_provisioned_entries_are_hourly(self):
        for key, info in FMAPI_DB_RATES.items():
            if 'provisioned' in key:
                assert info['is_hourly'] is True, f"{key} provisioned should be hourly"

    def test_all_entries_have_input_divisor(self):
        for key, info in FMAPI_DB_RATES.items():
            assert 'input_divisor' in info, f"{key} missing input_divisor"

    def test_aws_model_count(self):
        aws_keys = [k for k in FMAPI_DB_RATES if k.startswith("aws:")]
        assert len(aws_keys) >= 20, f"Expected >= 20 AWS entries, got {len(aws_keys)}"

    def test_azure_model_count(self):
        azure_keys = [k for k in FMAPI_DB_RATES if k.startswith("azure:")]
        assert len(azure_keys) >= 20, f"Expected >= 20 Azure entries, got {len(azure_keys)}"

    def test_gcp_model_count(self):
        gcp_keys = [k for k in FMAPI_DB_RATES if k.startswith("gcp:")]
        assert len(gcp_keys) >= 20, f"Expected >= 20 GCP entries, got {len(gcp_keys)}"
