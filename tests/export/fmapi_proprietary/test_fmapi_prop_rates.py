"""Sprint 7 — AC-3, AC-5: Rate type verification for FMAPI Proprietary.

Verifies cache_read/cache_write have distinct rates, and global vs in_geo
endpoint types produce different rates where applicable.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from app.routes.export.pricing import _get_fmapi_dbu_per_million
from tests.export.fmapi_proprietary.conftest import make_line_item
from tests.export.fmapi_proprietary.fmapi_prop_calc_helpers import (
    FMAPI_PROP_RATES, get_dbu_rate, get_all_providers,
    get_provider_models, get_model_rate_types,
)


class TestCacheRateTypes:
    """AC-3: cache_read, cache_write rate types have distinct rates."""

    def test_cache_read_vs_cache_write_anthropic(self):
        cr = get_dbu_rate("aws", "anthropic", "claude-haiku-4-5",
                          "global", "all", "cache_read")
        cw = get_dbu_rate("aws", "anthropic", "claude-haiku-4-5",
                          "global", "all", "cache_write")
        assert cr > 0, "cache_read rate should be > 0"
        assert cw > 0, "cache_write rate should be > 0"
        assert cr != cw, "cache_read and cache_write should differ"
        assert cw > cr, "cache_write should be more expensive than cache_read"

    def test_cache_read_less_than_input_token(self):
        """Cache reads should be cheaper than full input tokens."""
        cr = get_dbu_rate("aws", "anthropic", "claude-haiku-4-5",
                          "global", "all", "cache_read")
        it = get_dbu_rate("aws", "anthropic", "claude-haiku-4-5",
                          "global", "all", "input_token")
        assert cr < it, "cache_read should be cheaper than input_token"

    def test_cache_rates_via_backend_lookup(self):
        """Verify _get_fmapi_dbu_per_million works for cache rate types."""
        item_cr = make_line_item(fmapi_rate_type="cache_read")
        item_cw = make_line_item(fmapi_rate_type="cache_write")
        rate_cr, found_cr = _get_fmapi_dbu_per_million(item_cr, "aws")
        rate_cw, found_cw = _get_fmapi_dbu_per_million(item_cw, "aws")
        assert found_cr, "cache_read should be found in pricing"
        assert found_cw, "cache_write should be found in pricing"
        assert rate_cr > 0
        assert rate_cw > 0
        assert rate_cr != rate_cw


class TestBatchInferenceRateType:
    """batch_inference pricing data and rate lookup tests."""

    def test_batch_inference_is_hourly_in_pricing(self):
        key = "aws:anthropic:claude-opus-4:global:all:batch_inference"
        info = FMAPI_PROP_RATES.get(key, {})
        assert info.get("is_hourly") is True

    def test_batch_inference_has_positive_rate(self):
        rate = get_dbu_rate("aws", "anthropic", "claude-opus-4",
                            "global", "all", "batch_inference")
        assert rate > 0

    def test_batch_inference_via_backend_lookup(self):
        item = make_line_item(
            fmapi_provider="anthropic", fmapi_model="claude-opus-4",
            fmapi_rate_type="batch_inference", fmapi_quantity=730)
        rate, found = _get_fmapi_dbu_per_million(item, "aws")
        assert found, "batch_inference should be found in pricing"
        assert rate > 0


class TestEndpointTypeVariations:
    """AC-5: Different endpoint types (global/in_geo) show different rates."""

    def test_global_vs_in_geo_anthropic(self):
        global_rate = get_dbu_rate("aws", "anthropic", "claude-haiku-4-5",
                                   "global", "all", "input_token")
        in_geo_rate = get_dbu_rate("aws", "anthropic", "claude-haiku-4-5",
                                   "in_geo", "all", "input_token")
        assert global_rate > 0, "global rate should exist"
        assert in_geo_rate > 0, "in_geo rate should exist"
        assert in_geo_rate > global_rate, "in_geo should be more expensive"

    def test_endpoint_type_via_backend_lookup(self):
        item_global = make_line_item(fmapi_endpoint_type="global")
        item_in_geo = make_line_item(fmapi_endpoint_type="in_geo")
        rate_g, _ = _get_fmapi_dbu_per_million(item_global, "aws")
        rate_i, _ = _get_fmapi_dbu_per_million(item_in_geo, "aws")
        assert rate_g > 0
        assert rate_i > 0
        assert rate_i != rate_g


class TestAllProvidersHaveRates:
    """Verify all 3 providers have at least input_token rates across clouds."""

    @pytest.mark.parametrize("provider,model", [
        ("anthropic", "claude-haiku-4-5"),
        ("openai", "gpt-5-mini"),
        ("google", "gemini-2-5-flash"),
    ])
    @pytest.mark.parametrize("cloud", ["aws", "azure", "gcp"])
    def test_provider_has_input_rates(self, provider, model, cloud):
        ctx = "long" if provider == "google" else "all"
        rate = get_dbu_rate(cloud, provider, model,
                            "global", ctx, "input_token")
        assert rate > 0, f"{provider}/{model} on {cloud} should have input_token rate"
