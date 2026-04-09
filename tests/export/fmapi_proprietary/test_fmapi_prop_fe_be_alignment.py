"""Sprint 7 — AC-6: Frontend/backend cost alignment for FMAPI Proprietary.

Verifies that backend calc_item_values produces the same monthly DBUs
as the expected formula for all rate types across all 3 providers.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from app.routes.export.excel_item_helpers import calc_item_values
from tests.export.fmapi_proprietary.conftest import make_line_item
from tests.export.fmapi_proprietary.fmapi_prop_calc_helpers import (
    FMAPI_PROP_RATES, get_dbu_rate, get_all_providers,
    get_provider_models, get_model_rate_types,
    is_token_based, is_provisioned,
)


def _all_provider_model_rate_combos(cloud='aws'):
    """Generate (provider, model, rate_type, context) tuples from pricing JSON."""
    combos = []
    for key in FMAPI_PROP_RATES:
        parts = key.split(':')
        if len(parts) == 6 and parts[0] == cloud:
            provider, model = parts[1], parts[2]
            endpoint, context, rate_type = parts[3], parts[4], parts[5]
            combos.append((provider, model, endpoint, context, rate_type))
    return combos


class TestFrontendBackendAlignment:
    """Verify backend produces correct monthly DBUs for each rate type."""

    @pytest.mark.parametrize("rate_type,quantity", [
        ("input_token", 100),
        ("output_token", 50),
        ("cache_read", 200),
        ("cache_write", 30),
    ])
    def test_token_based_alignment_anthropic(self, rate_type, quantity):
        """Token-based: monthly_dbus = quantity × dbu_per_1M."""
        item = make_line_item(
            fmapi_provider="anthropic", fmapi_model="claude-haiku-4-5",
            fmapi_rate_type=rate_type, fmapi_quantity=quantity)
        expected_rate = get_dbu_rate(
            "aws", "anthropic", "claude-haiku-4-5", "global", "all", rate_type)
        notes = []
        _, tok_qty, dbu_m, total_dbus, _ = calc_item_values(
            item, True, False, 0, "aws", notes)
        assert tok_qty == quantity
        assert dbu_m == pytest.approx(expected_rate, rel=1e-3)
        assert total_dbus == pytest.approx(quantity * expected_rate, rel=1e-3)

    def test_batch_inference_alignment(self):
        """batch_inference: monthly_dbus = hours × dbu_per_hour."""
        item = make_line_item(
            fmapi_provider="anthropic", fmapi_model="claude-opus-4",
            fmapi_rate_type="batch_inference", fmapi_quantity=730)
        expected_rate = get_dbu_rate(
            "aws", "anthropic", "claude-opus-4", "global", "all",
            "batch_inference")
        notes = []
        hours, _, _, total_dbus, _ = calc_item_values(
            item, False, True, 0, "aws", notes)
        assert hours == 730
        assert total_dbus == pytest.approx(730 * expected_rate, rel=1e-3)

    @pytest.mark.parametrize("provider,model,context", [
        ("anthropic", "claude-haiku-4-5", "all"),
        ("openai", "gpt-5-mini", "all"),
        ("google", "gemini-2-5-flash", "long"),
    ])
    def test_input_token_all_providers(self, provider, model, context):
        """Input token calculation works for all 3 providers."""
        item = make_line_item(
            fmapi_provider=provider, fmapi_model=model,
            fmapi_rate_type="input_token", fmapi_quantity=100,
            fmapi_context_length=context)
        expected = get_dbu_rate("aws", provider, model,
                                "global", context, "input_token")
        notes = []
        _, _, dbu_m, total_dbus, _ = calc_item_values(
            item, True, False, 0, "aws", notes)
        assert dbu_m == pytest.approx(expected, rel=1e-3)
        assert total_dbus == pytest.approx(100 * expected, rel=1e-3)

    @pytest.mark.parametrize("provider,model,context", [
        ("anthropic", "claude-haiku-4-5", "all"),
        ("openai", "gpt-5-mini", "all"),
        ("google", "gemini-2-5-flash", "long"),
    ])
    def test_output_token_all_providers(self, provider, model, context):
        """Output token calculation works for all 3 providers."""
        item = make_line_item(
            fmapi_provider=provider, fmapi_model=model,
            fmapi_rate_type="output_token", fmapi_quantity=50,
            fmapi_context_length=context)
        expected = get_dbu_rate("aws", provider, model,
                                "global", context, "output_token")
        notes = []
        _, _, dbu_m, total_dbus, _ = calc_item_values(
            item, True, False, 0, "aws", notes)
        assert dbu_m == pytest.approx(expected, rel=1e-3)
        assert total_dbus == pytest.approx(50 * expected, rel=1e-3)


class TestOutputMoreExpensiveThanInput:
    """Output tokens should generally cost more than input tokens."""

    @pytest.mark.parametrize("provider,model,context", [
        ("anthropic", "claude-haiku-4-5", "all"),
        ("openai", "gpt-5-mini", "all"),
        ("google", "gemini-2-5-flash", "long"),
    ])
    def test_output_gt_input(self, provider, model, context):
        input_rate = get_dbu_rate("aws", provider, model,
                                  "global", context, "input_token")
        output_rate = get_dbu_rate("aws", provider, model,
                                   "global", context, "output_token")
        if input_rate > 0 and output_rate > 0:
            assert output_rate > input_rate, (
                f"{provider}/{model}: output ({output_rate}) should > "
                f"input ({input_rate})")
