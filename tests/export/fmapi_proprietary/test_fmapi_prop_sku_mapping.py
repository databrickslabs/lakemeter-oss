"""Sprint 7 — AC-1, AC-2: Provider → SKU mapping for FMAPI Proprietary.

Verifies that each provider maps to the correct {PROVIDER}_MODEL_SERVING SKU
and that Google correctly maps to GEMINI_MODEL_SERVING (not GOOGLE_).
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from app.routes.export.pricing import _get_sku_type, _get_fmapi_sku
from tests.export.fmapi_proprietary.conftest import make_line_item
from tests.export.fmapi_proprietary.fmapi_prop_calc_helpers import PROVIDER_SKU_MAP


class TestProviderSkuMapping:
    """AC-1: Each provider maps to correct SKU ({PROVIDER}_MODEL_SERVING)."""

    @pytest.mark.parametrize("provider,expected_sku", [
        ("anthropic", "ANTHROPIC_MODEL_SERVING"),
        ("openai", "OPENAI_MODEL_SERVING"),
        ("google", "GEMINI_MODEL_SERVING"),
    ])
    def test_provider_to_sku_input_token(self, provider, expected_sku):
        models = {"anthropic": "claude-haiku-4-5", "openai": "gpt-5-mini",
                  "google": "gemini-2-5-flash"}
        ctx = "long" if provider == "google" else "all"
        item = make_line_item(
            fmapi_provider=provider, fmapi_model=models[provider],
            fmapi_rate_type="input_token", fmapi_context_length=ctx)
        sku = _get_sku_type(item, "aws")
        assert sku == expected_sku

    @pytest.mark.parametrize("provider,expected_sku", [
        ("anthropic", "ANTHROPIC_MODEL_SERVING"),
        ("openai", "OPENAI_MODEL_SERVING"),
        ("google", "GEMINI_MODEL_SERVING"),
    ])
    def test_provider_to_sku_output_token(self, provider, expected_sku):
        models = {"anthropic": "claude-haiku-4-5", "openai": "gpt-5-mini",
                  "google": "gemini-2-5-flash"}
        ctx = "long" if provider == "google" else "all"
        item = make_line_item(
            fmapi_provider=provider, fmapi_model=models[provider],
            fmapi_rate_type="output_token", fmapi_context_length=ctx)
        sku = _get_sku_type(item, "aws")
        assert sku == expected_sku


class TestGoogleGeminiMapping:
    """AC-2: Google correctly maps to GEMINI_MODEL_SERVING."""

    def test_google_gemini_flash(self):
        item = make_line_item(
            fmapi_provider="google", fmapi_model="gemini-2-5-flash",
            fmapi_context_length="long")
        sku = _get_sku_type(item, "aws")
        assert sku == "GEMINI_MODEL_SERVING"
        assert "GOOGLE" not in sku

    def test_google_gemini_pro(self):
        item = make_line_item(
            fmapi_provider="google", fmapi_model="gemini-2-5-pro",
            fmapi_context_length="long")
        sku = _get_sku_type(item, "aws")
        assert sku == "GEMINI_MODEL_SERVING"

    @pytest.mark.parametrize("rate_type", [
        "input_token", "output_token",
    ])
    def test_google_sku_across_rate_types(self, rate_type):
        """Google has input_token/output_token; cache types not in pricing."""
        item = make_line_item(
            fmapi_provider="google", fmapi_model="gemini-2-5-flash",
            fmapi_rate_type=rate_type, fmapi_context_length="long")
        sku = _get_sku_type(item, "aws")
        assert sku == "GEMINI_MODEL_SERVING"

    def test_google_cache_types_fallback_sku(self):
        """Google has no cache_read/cache_write — verify graceful fallback."""
        for rt in ("cache_read", "cache_write"):
            item = make_line_item(
                fmapi_provider="google", fmapi_model="gemini-2-5-flash",
                fmapi_rate_type=rt, fmapi_context_length="long")
            sku = _get_sku_type(item, "aws")
            assert sku is not None, f"SKU should not be None for {rt}"


class TestSkuAcrossClouds:
    """Verify SKU mapping works across all 3 clouds."""

    @pytest.mark.parametrize("cloud", ["aws", "azure", "gcp"])
    def test_anthropic_sku_all_clouds(self, cloud):
        item = make_line_item(
            fmapi_provider="anthropic", fmapi_model="claude-haiku-4-5",
            fmapi_rate_type="input_token")
        sku = _get_sku_type(item, cloud)
        assert sku == "ANTHROPIC_MODEL_SERVING"
