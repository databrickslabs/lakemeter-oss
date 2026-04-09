"""Test FMAPI Databricks SKU mapping and pricing lookups.

AC-9 to AC-12: SKU, fallback pricing, serverless detection, DBU/hr=0.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from app.routes.export.pricing import (
    _get_sku_type, _get_fmapi_sku, _get_fmapi_dbu_per_million,
    _is_fmapi_hourly, FALLBACK_DBU_PRICES,
)
from app.routes.export.calculations import (
    _calculate_dbu_per_hour, _is_serverless_workload,
)
from .conftest import make_line_item


class TestFMAPISKU:
    """AC-9: SKU = SERVERLESS_REAL_TIME_INFERENCE for FMAPI_DATABRICKS."""

    @pytest.mark.parametrize("model,rate_type", [
        ("llama-3-3-70b", "input_token"),
        ("llama-3-3-70b", "output_token"),
        ("llama-3-3-70b", "provisioned_scaling"),
        ("llama-3-3-70b", "provisioned_entry"),
        ("bge-large", "input_token"),
        ("gte", "input_token"),
    ])
    def test_sku_for_fmapi_databricks(self, model, rate_type):
        item = make_line_item(fmapi_model=model, fmapi_rate_type=rate_type)
        sku = _get_sku_type(item, 'aws')
        assert sku == 'SERVERLESS_REAL_TIME_INFERENCE'

    def test_sku_with_unknown_model(self):
        item = make_line_item(fmapi_model='nonexistent-model', fmapi_rate_type='input_token')
        sku = _get_sku_type(item, 'aws')
        assert sku == 'SERVERLESS_REAL_TIME_INFERENCE'


class TestFallbackPricing:
    """AC-10: Fallback $/DBU for SERVERLESS_REAL_TIME_INFERENCE."""

    def test_fallback_price_exists(self):
        assert 'SERVERLESS_REAL_TIME_INFERENCE' in FALLBACK_DBU_PRICES

    def test_fallback_price_is_007(self):
        assert FALLBACK_DBU_PRICES['SERVERLESS_REAL_TIME_INFERENCE'] == 0.07


class TestServerlessDetection:
    """AC-11: FMAPI_DATABRICKS is always serverless."""

    @pytest.mark.parametrize("rate_type", [
        "input_token", "output_token", "provisioned_scaling", "provisioned_entry",
    ])
    def test_is_serverless(self, rate_type):
        item = make_line_item(fmapi_rate_type=rate_type)
        assert _is_serverless_workload(item) is True

    def test_serverless_regardless_of_flag(self):
        item = make_line_item(serverless_enabled=False)
        assert _is_serverless_workload(item) is True


class TestDBUPerHourZero:
    """AC-12: _calculate_dbu_per_hour returns 0 for FMAPI."""

    @pytest.mark.parametrize("rate_type", [
        "input_token", "output_token", "provisioned_scaling", "provisioned_entry",
    ])
    def test_dbu_per_hour_zero(self, rate_type):
        item = make_line_item(fmapi_rate_type=rate_type)
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 0, f"FMAPI_DATABRICKS should have 0 DBU/hr, got {dbu}"
        assert len(warnings) == 0


class TestIsFMAPIHourly:
    """AC-17: _is_fmapi_hourly returns correct boolean."""

    @pytest.mark.parametrize("rate_type,expected", [
        ("input_token", False),
        ("output_token", False),
        ("provisioned_scaling", True),
        ("provisioned_entry", True),
    ])
    def test_is_hourly(self, rate_type, expected):
        item = make_line_item(fmapi_rate_type=rate_type)
        assert _is_fmapi_hourly(item, 'aws') is expected
