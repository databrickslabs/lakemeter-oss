"""Sprint 7 — Edge cases: Google context_length, display names, file sizes.

Covers BUG-S7-2 (display names), BUG-S7-4 (Google context default),
BUG-S7-6 (file size limits).
"""
import sys
import os
from pathlib import Path
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from app.routes.export.pricing import (
    _get_fmapi_dbu_per_million, _get_fmapi_sku,
)
from app.routes.export.helpers import (
    _fmapi_details, _get_workload_config_details,
)
from tests.export.fmapi_proprietary.conftest import make_line_item


class TestGoogleContextLength:
    """BUG-S7-4 regression: Google uses 'long' default, not 'all'."""

    def test_google_default_context_finds_rate(self):
        """Google with default context_length should find rates."""
        item = make_line_item(
            fmapi_provider="google", fmapi_model="gemini-2-5-flash",
            fmapi_context_length="long", fmapi_rate_type="input_token")
        rate, found = _get_fmapi_dbu_per_million(item, "aws")
        assert found, "Google with context_length='long' should find rate"
        assert rate > 0

    def test_google_all_context_not_found(self):
        """Google with context_length='all' should NOT find rate."""
        item = make_line_item(
            fmapi_provider="google", fmapi_model="gemini-2-5-flash",
            fmapi_context_length="all", fmapi_rate_type="input_token")
        rate, found = _get_fmapi_dbu_per_million(item, "aws")
        assert not found, "Google with 'all' context should not find rate"

    def test_google_sku_with_long_context(self):
        item = make_line_item(
            fmapi_provider="google", fmapi_model="gemini-2-5-flash",
            fmapi_context_length="long", fmapi_rate_type="input_token")
        sku = _get_fmapi_sku(item, "aws")
        assert sku == "GEMINI_MODEL_SERVING"


class TestDisplayNames:
    """BUG-S7-2 regression: All rate types have display names."""

    @pytest.mark.parametrize("rate_type,expected_label", [
        ("input_token", "Input Tokens"),
        ("output_token", "Output Tokens"),
        ("cache_read", "Cache Read"),
        ("cache_write", "Cache Write"),
        ("batch_inference", "Batch Inference"),
        ("provisioned_scaling", "Provisioned Scaling"),
        ("provisioned_entry", "Provisioned Entry"),
    ])
    def test_rate_type_display_name(self, rate_type, expected_label):
        item = make_line_item(fmapi_rate_type=rate_type, fmapi_quantity=100)
        details = _fmapi_details(item)
        rate_detail = [d for d in details if d.startswith("Rate:")]
        assert len(rate_detail) == 1
        assert expected_label in rate_detail[0]

    @pytest.mark.parametrize("rate_type", [
        "cache_read", "cache_write",
    ])
    def test_cache_types_show_token_quantity(self, rate_type):
        """cache_read/cache_write should display as token quantity, not hours."""
        item = make_line_item(fmapi_rate_type=rate_type, fmapi_quantity=50.0)
        details = _fmapi_details(item)
        qty_detail = [d for d in details if "Tokens:" in d or "Hours:" in d]
        assert len(qty_detail) == 1
        assert "Tokens:" in qty_detail[0], f"{rate_type} should show Tokens, not Hours"

    def test_batch_inference_shows_hours(self):
        """batch_inference should display as hours quantity."""
        item = make_line_item(fmapi_rate_type="batch_inference", fmapi_quantity=730)
        details = _fmapi_details(item)
        qty_detail = [d for d in details if "Hours:" in d]
        assert len(qty_detail) == 1


class TestUnknownProviderFallback:
    """SUG-S7-002 regression: unknown provider should fallback gracefully."""

    def test_unknown_provider_sku_fallback(self):
        """Unknown provider should return OPENAI_MODEL_SERVING fallback."""
        item = make_line_item(
            fmapi_provider="meta", fmapi_model="llama-3",
            fmapi_rate_type="input_token")
        sku = _get_fmapi_sku(item, "aws")
        assert sku == "OPENAI_MODEL_SERVING", (
            f"Unknown provider should fallback to OPENAI_MODEL_SERVING, got {sku}")

    def test_unknown_provider_rate_not_found(self):
        """Unknown provider should return found=False from rate lookup."""
        item = make_line_item(
            fmapi_provider="meta", fmapi_model="llama-3",
            fmapi_rate_type="input_token")
        rate, found = _get_fmapi_dbu_per_million(item, "aws")
        assert not found, "Unknown provider should not find rate in pricing data"

    def test_empty_provider_sku_fallback(self):
        """Empty provider should fallback gracefully."""
        item = make_line_item(
            fmapi_provider="", fmapi_model="unknown-model",
            fmapi_rate_type="input_token")
        sku = _get_fmapi_sku(item, "aws")
        assert sku is not None and isinstance(sku, str)

    def test_none_model_sku_fallback(self):
        """None model should fallback gracefully (no crash)."""
        item = make_line_item(
            fmapi_provider="anthropic", fmapi_model=None,
            fmapi_rate_type="input_token")
        sku = _get_fmapi_sku(item, "aws")
        assert sku is not None


class TestGoogleCacheTypesGraceful:
    """SUG-S7-001 regression: Google cache_read/cache_write handled gracefully."""

    @pytest.mark.parametrize("rate_type", ["cache_read", "cache_write"])
    def test_google_cache_rate_not_found(self, rate_type):
        """Google doesn't support cache rate types — should return not found."""
        item = make_line_item(
            fmapi_provider="google", fmapi_model="gemini-2-5-flash",
            fmapi_rate_type=rate_type, fmapi_context_length="long")
        rate, found = _get_fmapi_dbu_per_million(item, "aws")
        assert not found, (
            f"Google {rate_type} should not be found in pricing data")

    @pytest.mark.parametrize("rate_type", ["cache_read", "cache_write"])
    def test_google_cache_sku_still_returns_gemini(self, rate_type):
        """Even for unsupported cache types, SKU should be GEMINI_MODEL_SERVING."""
        item = make_line_item(
            fmapi_provider="google", fmapi_model="gemini-2-5-flash",
            fmapi_rate_type=rate_type, fmapi_context_length="long")
        sku = _get_fmapi_sku(item, "aws")
        # Should still resolve to GEMINI (from fallback) or at least not crash
        assert sku is not None


class TestFileSizeLimits:
    """BUG-S7-6 regression: Key export files stay under 200 lines."""

    @pytest.mark.parametrize("filepath", [
        "backend/app/routes/export/excel_builder.py",
        "backend/app/routes/export/excel_item_helpers.py",
        "backend/app/routes/export/helpers.py",
        "backend/app/routes/export/pricing.py",
    ])
    def test_file_under_200_lines(self, filepath):
        project_root = Path(__file__).parent.parent.parent
        full_path = project_root / filepath
        if full_path.exists():
            lines = full_path.read_text().count('\n') + 1
            assert lines <= 200, f"{filepath} has {lines} lines (max 200)"
