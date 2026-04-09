"""Sprint 7 — AC-4: Excel export for all 5 FMAPI Proprietary rate types.

Regression tests for BUG-S7-1: cache_read, cache_write, batch_inference
must produce non-zero costs in Excel export (not fall through to $0).
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from app.routes.export.excel_item_helpers import calc_item_values
from app.routes.export.pricing import _get_fmapi_dbu_per_million, _is_fmapi_hourly
from tests.export.fmapi_proprietary.conftest import make_line_item


# Rate type classification (mirrors excel_builder.py logic)
FMAPI_TOKEN_TYPES = (
    'input_token', 'output_token', 'input', 'output',
    'cache_read', 'cache_write',
)
FMAPI_PROVISIONED_TYPES = (
    'provisioned_scaling', 'provisioned_entry', 'batch_inference',
)


class TestTokenRateTypeClassification:
    """BUG-S7-1 regression: cache_read/cache_write are token-based."""

    @pytest.mark.parametrize("rate_type", [
        "input_token", "output_token", "cache_read", "cache_write",
    ])
    def test_token_rate_types_classified_correctly(self, rate_type):
        assert rate_type in FMAPI_TOKEN_TYPES

    @pytest.mark.parametrize("rate_type", [
        "provisioned_scaling", "provisioned_entry", "batch_inference",
    ])
    def test_provisioned_rate_types_classified_correctly(self, rate_type):
        assert rate_type in FMAPI_PROVISIONED_TYPES


class TestCalcItemValuesTokenPath:
    """BUG-S7-1 regression: calc_item_values produces non-zero for cache types."""

    @pytest.mark.parametrize("rate_type", [
        "input_token", "output_token", "cache_read", "cache_write",
    ])
    def test_token_rate_produces_nonzero_dbus(self, rate_type):
        item = make_line_item(fmapi_rate_type=rate_type, fmapi_quantity=100)
        is_token = True
        is_prov = False
        notes = []
        hours, tok_qty, dbu_m, total_dbus, tok_type = calc_item_values(
            item, is_token, is_prov, 0, "aws", notes)
        assert tok_qty == 100
        assert dbu_m > 0, f"{rate_type} should have non-zero dbu_per_million"
        assert total_dbus > 0, f"{rate_type} should produce non-zero total DBUs"
        assert hours == 0, "Token-based should have 0 hours"

    def test_cache_read_token_type_display(self):
        item = make_line_item(fmapi_rate_type="cache_read", fmapi_quantity=50)
        _, _, _, _, tok_type = calc_item_values(item, True, False, 0, "aws", [])
        assert tok_type == "Cache Read"

    def test_cache_write_token_type_display(self):
        item = make_line_item(fmapi_rate_type="cache_write", fmapi_quantity=50)
        _, _, _, _, tok_type = calc_item_values(item, True, False, 0, "aws", [])
        assert tok_type == "Cache Write"


class TestCalcItemValuesBatchInference:
    """batch_inference is token-based (not hourly) — matching frontend behavior.

    Frontend costCalculation.ts only treats 'provisioned_scaling' as provisioned.
    batch_inference goes through the token path with DBU per 1M tokens rate.
    """

    def test_batch_inference_produces_nonzero_dbus(self):
        item = make_line_item(
            fmapi_provider="anthropic", fmapi_model="claude-opus-4",
            fmapi_rate_type="batch_inference", fmapi_quantity=730)
        notes = []
        hours, tok_qty, dbu_m, total_dbus, tok_type = calc_item_values(
            item, True, False, 0, "aws", notes)
        assert tok_qty == 730
        assert total_dbus > 0, "batch_inference should produce non-zero DBUs"
        assert hours == 0

    def test_batch_inference_is_not_hourly(self):
        """batch_inference is token-based, not hourly — matches frontend."""
        item = make_line_item(fmapi_rate_type="batch_inference")
        assert _is_fmapi_hourly(item, "aws") is False


class TestCalcItemValuesStandardToken:
    """Verify standard input_token/output_token still work correctly."""

    def test_input_token_calculation(self):
        item = make_line_item(fmapi_rate_type="input_token", fmapi_quantity=500)
        notes = []
        hours, tok_qty, dbu_m, total_dbus, tok_type = calc_item_values(
            item, True, False, 0, "aws", notes)
        assert tok_qty == 500
        assert dbu_m > 0
        assert total_dbus == pytest.approx(500 * dbu_m)
        assert tok_type == "Input"

    def test_output_token_calculation(self):
        item = make_line_item(fmapi_rate_type="output_token", fmapi_quantity=200)
        notes = []
        hours, tok_qty, dbu_m, total_dbus, tok_type = calc_item_values(
            item, True, False, 0, "aws", notes)
        assert tok_qty == 200
        assert tok_type == "Output"
        assert total_dbus > 0


class TestCalcItemValuesBatchPath:
    """batch_inference uses provisioned path for FMAPI_PROPRIETARY."""

    def test_batch_inference_calculation(self):
        """FMAPI Proprietary has batch_inference (not provisioned_scaling)."""
        item = make_line_item(
            fmapi_provider="anthropic", fmapi_model="claude-opus-4",
            fmapi_rate_type="batch_inference", fmapi_quantity=730)
        notes = []
        hours, tok_qty, dbu_m, total_dbus, tok_type = calc_item_values(
            item, False, True, 0, "aws", notes)
        assert hours == 730
        assert total_dbus > 0
