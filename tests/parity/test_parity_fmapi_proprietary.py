"""Parity tests: FMAPI_PROPRIETARY workload — backend vs frontend equivalence.

Covers all 3 providers (OpenAI, Anthropic, Google) across input_token,
output_token, cache_read, cache_write, and batch_inference rate types,
with endpoint_type (global, in_geo) and context_length (all, short, long).
"""
import pytest
from .conftest import make_item
from .frontend_calc import fe_fmapi_token_cost, fe_fmapi_provisioned_cost

CLOUD = 'aws'
REGION = 'us-east-1'
TIER = 'PREMIUM'
TOL = 0.01


def _get_be_fmapi_results(item):
    from app.routes.export.calculations import _calculate_dbu_per_hour
    from app.routes.export.pricing import (
        _get_dbu_price, _get_sku_type, _get_fmapi_dbu_per_million, _is_fmapi_hourly,
    )
    from app.routes.export.excel_item_helpers import calc_item_values

    dbu_hr, _ = _calculate_dbu_per_hour(item, CLOUD)
    sku = _get_sku_type(item, CLOUD)
    dbu_price, _ = _get_dbu_price(CLOUD, REGION, TIER, sku)
    is_hourly = _is_fmapi_hourly(item, CLOUD)
    is_token = not is_hourly
    auto_notes = []
    hours, token_qty, dbu_per_m, total_dbus, token_type = calc_item_values(
        item, is_token, is_hourly, dbu_hr, CLOUD, auto_notes,
    )
    monthly_cost = total_dbus * dbu_price
    return dict(dbu_hr=dbu_hr, sku=sku, dbu_price=dbu_price,
                hours=hours, token_qty=token_qty, dbu_per_m=dbu_per_m,
                total_dbus=total_dbus, monthly_cost=monthly_cost,
                auto_notes=auto_notes)


# ── OpenAI tests ─────────────────────────────────────────────────────────

class TestFMAPIPropOpenAI:
    """OpenAI proprietary model token pricing."""

    def test_gpt5_1_input(self, pricing):
        key = 'aws:openai:gpt-5-1:global:all:input_token'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='openai',
            fmapi_model='gpt-5-1', fmapi_rate_type='input_token',
            fmapi_endpoint_type='global', fmapi_context_length='all',
            fmapi_quantity=20,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)
        assert be['sku'] == 'OPENAI_MODEL_SERVING'
        fe_cost = fe_fmapi_token_cost(
            quantity_millions=20, dbu_per_million=rate_info['dbu_rate'],
            dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_gpt5_1_output(self, pricing):
        key = 'aws:openai:gpt-5-1:global:all:output_token'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='openai',
            fmapi_model='gpt-5-1', fmapi_rate_type='output_token',
            fmapi_endpoint_type='global', fmapi_context_length='all',
            fmapi_quantity=5,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_gpt5_1_cache_read(self, pricing):
        key = 'aws:openai:gpt-5-1:global:all:cache_read'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='openai',
            fmapi_model='gpt-5-1', fmapi_rate_type='cache_read',
            fmapi_endpoint_type='global', fmapi_context_length='all',
            fmapi_quantity=200,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_gpt5_1_cache_write(self, pricing):
        key = 'aws:openai:gpt-5-1:global:all:cache_write'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='openai',
            fmapi_model='gpt-5-1', fmapi_rate_type='cache_write',
            fmapi_endpoint_type='global', fmapi_context_length='all',
            fmapi_quantity=30,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_gpt5_1_batch_inference(self, pricing):
        """batch_inference must be treated as token-based (not provisioned)."""
        key = 'aws:openai:gpt-5-1:global:all:batch_inference'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='openai',
            fmapi_model='gpt-5-1', fmapi_rate_type='batch_inference',
            fmapi_endpoint_type='global', fmapi_context_length='all',
            fmapi_quantity=10,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)
        # Token-based: total_dbus = quantity × dbu_per_1M_tokens
        assert be['total_dbus'] == pytest.approx(10 * rate_info['dbu_rate'], abs=TOL)
        fe_cost = fe_fmapi_token_cost(
            quantity_millions=10, dbu_per_million=rate_info['dbu_rate'],
            dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_gpt5_in_geo_input(self, pricing):
        """In-geo endpoint type should use in_geo pricing."""
        key = 'aws:openai:gpt-5:in_geo:all:input_token'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='openai',
            fmapi_model='gpt-5', fmapi_rate_type='input_token',
            fmapi_endpoint_type='in_geo', fmapi_context_length='all',
            fmapi_quantity=15,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_gpt5_in_geo_batch(self, pricing):
        """In-geo batch_inference."""
        key = 'aws:openai:gpt-5:in_geo:all:batch_inference'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='openai',
            fmapi_model='gpt-5', fmapi_rate_type='batch_inference',
            fmapi_endpoint_type='in_geo', fmapi_context_length='all',
            fmapi_quantity=25,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)
        assert be['total_dbus'] == pytest.approx(25 * rate_info['dbu_rate'], abs=TOL)

    def test_gpt5_mini_input(self, pricing):
        key = 'aws:openai:gpt-5-mini:global:all:input_token'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='openai',
            fmapi_model='gpt-5-mini', fmapi_rate_type='input_token',
            fmapi_endpoint_type='global', fmapi_context_length='all',
            fmapi_quantity=50,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_gpt5_nano_output(self, pricing):
        key = 'aws:openai:gpt-5-nano:global:all:output_token'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='openai',
            fmapi_model='gpt-5-nano', fmapi_rate_type='output_token',
            fmapi_endpoint_type='global', fmapi_context_length='all',
            fmapi_quantity=100,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)


# ── Anthropic tests ──────────────────────────────────────────────────────

class TestFMAPIPropAnthropic:
    """Anthropic proprietary model token pricing."""

    def test_claude_sonnet_output(self, pricing):
        key = 'aws:anthropic:claude-sonnet-4-5:global:long:output_token'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='anthropic',
            fmapi_model='claude-sonnet-4-5', fmapi_rate_type='output_token',
            fmapi_endpoint_type='global', fmapi_context_length='long',
            fmapi_quantity=8,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)
        assert be['sku'] == 'ANTHROPIC_MODEL_SERVING'
        fe_cost = fe_fmapi_token_cost(
            quantity_millions=8, dbu_per_million=rate_info['dbu_rate'],
            dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_claude_sonnet_cache_read(self, pricing):
        key = 'aws:anthropic:claude-sonnet-4-5:global:long:cache_read'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='anthropic',
            fmapi_model='claude-sonnet-4-5', fmapi_rate_type='cache_read',
            fmapi_endpoint_type='global', fmapi_context_length='long',
            fmapi_quantity=50,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_claude_sonnet_cache_write(self, pricing):
        key = 'aws:anthropic:claude-sonnet-4-5:global:long:cache_write'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='anthropic',
            fmapi_model='claude-sonnet-4-5', fmapi_rate_type='cache_write',
            fmapi_endpoint_type='global', fmapi_context_length='long',
            fmapi_quantity=20,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_claude_haiku_input(self, pricing):
        key = 'aws:anthropic:claude-haiku-4-5:global:all:input_token'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='anthropic',
            fmapi_model='claude-haiku-4-5', fmapi_rate_type='input_token',
            fmapi_endpoint_type='global', fmapi_context_length='all',
            fmapi_quantity=100,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_claude_haiku_output(self, pricing):
        key = 'aws:anthropic:claude-haiku-4-5:global:all:output_token'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='anthropic',
            fmapi_model='claude-haiku-4-5', fmapi_rate_type='output_token',
            fmapi_endpoint_type='global', fmapi_context_length='all',
            fmapi_quantity=30,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_claude_opus_4_batch_inference(self, pricing):
        """Anthropic batch_inference — treated as token-based."""
        key = 'aws:anthropic:claude-opus-4:global:all:batch_inference'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='anthropic',
            fmapi_model='claude-opus-4', fmapi_rate_type='batch_inference',
            fmapi_endpoint_type='global', fmapi_context_length='all',
            fmapi_quantity=5,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)
        assert be['total_dbus'] == pytest.approx(5 * rate_info['dbu_rate'], abs=TOL)

    def test_claude_opus_4_1_in_geo_batch(self, pricing):
        key = 'aws:anthropic:claude-opus-4-1:in_geo:all:batch_inference'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='anthropic',
            fmapi_model='claude-opus-4-1', fmapi_rate_type='batch_inference',
            fmapi_endpoint_type='in_geo', fmapi_context_length='all',
            fmapi_quantity=12,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_claude_sonnet_4_input_in_geo(self, pricing):
        key = 'aws:anthropic:claude-sonnet-4:in_geo:long:input_token'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='anthropic',
            fmapi_model='claude-sonnet-4', fmapi_rate_type='input_token',
            fmapi_endpoint_type='in_geo', fmapi_context_length='long',
            fmapi_quantity=40,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_claude_sonnet_3_7_short_context(self, pricing):
        key = 'aws:anthropic:claude-sonnet-3-7:global:short:input_token'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='anthropic',
            fmapi_model='claude-sonnet-3-7', fmapi_rate_type='input_token',
            fmapi_endpoint_type='global', fmapi_context_length='short',
            fmapi_quantity=60,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_claude_opus_4_5_output(self, pricing):
        """Opus 4.5 uses 'short' context (not 'long')."""
        key = 'aws:anthropic:claude-opus-4-5:global:short:output_token'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='anthropic',
            fmapi_model='claude-opus-4-5', fmapi_rate_type='output_token',
            fmapi_endpoint_type='global', fmapi_context_length='short',
            fmapi_quantity=3,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_claude_sonnet_4_1_cache_read(self, pricing):
        key = 'aws:anthropic:claude-sonnet-4-1:global:long:cache_read'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='anthropic',
            fmapi_model='claude-sonnet-4-1', fmapi_rate_type='cache_read',
            fmapi_endpoint_type='global', fmapi_context_length='long',
            fmapi_quantity=200,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)


# ── Google tests ─────────────────────────────────────────────────────────

class TestFMAPIPropGoogle:
    """Google proprietary model token pricing — uses GEMINI_MODEL_SERVING SKU."""

    def test_gemini_flash_input(self, pricing):
        key = 'aws:google:gemini-2-5-flash:global:long:input_token'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='google',
            fmapi_model='gemini-2-5-flash', fmapi_rate_type='input_token',
            fmapi_endpoint_type='global', fmapi_context_length='long',
            fmapi_quantity=100,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)
        assert be['sku'] == 'GEMINI_MODEL_SERVING'
        fe_cost = fe_fmapi_token_cost(
            quantity_millions=100, dbu_per_million=rate_info['dbu_rate'],
            dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_gemini_flash_output(self, pricing):
        key = 'aws:google:gemini-2-5-flash:global:long:output_token'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='google',
            fmapi_model='gemini-2-5-flash', fmapi_rate_type='output_token',
            fmapi_endpoint_type='global', fmapi_context_length='long',
            fmapi_quantity=50,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_gemini_flash_short_context(self, pricing):
        key = 'aws:google:gemini-2-5-flash:global:short:input_token'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='google',
            fmapi_model='gemini-2-5-flash', fmapi_rate_type='input_token',
            fmapi_endpoint_type='global', fmapi_context_length='short',
            fmapi_quantity=75,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_gemini_flash_in_geo(self, pricing):
        key = 'aws:google:gemini-2-5-flash:in_geo:long:input_token'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='google',
            fmapi_model='gemini-2-5-flash', fmapi_rate_type='input_token',
            fmapi_endpoint_type='in_geo', fmapi_context_length='long',
            fmapi_quantity=60,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_gemini_pro_input(self, pricing):
        key = 'aws:google:gemini-2-5-pro:global:long:input_token'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='google',
            fmapi_model='gemini-2-5-pro', fmapi_rate_type='input_token',
            fmapi_endpoint_type='global', fmapi_context_length='long',
            fmapi_quantity=20,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_gemini_pro_output(self, pricing):
        key = 'aws:google:gemini-2-5-pro:global:long:output_token'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='google',
            fmapi_model='gemini-2-5-pro', fmapi_rate_type='output_token',
            fmapi_endpoint_type='global', fmapi_context_length='long',
            fmapi_quantity=10,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)


# ── SKU assignment tests ─────────────────────────────────────────────────

class TestFMAPIPropSKU:
    """Verify correct provider-specific SKU assignment."""

    @pytest.mark.parametrize("provider,expected_sku", [
        ('openai', 'OPENAI_MODEL_SERVING'),
        ('anthropic', 'ANTHROPIC_MODEL_SERVING'),
        ('google', 'GEMINI_MODEL_SERVING'),
    ])
    def test_provider_sku_mapping(self, pricing, provider, expected_sku):
        model_map = {
            'openai': 'gpt-5', 'anthropic': 'claude-sonnet-4-5',
            'google': 'gemini-2-5-flash',
        }
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider=provider,
            fmapi_model=model_map[provider], fmapi_rate_type='input_token',
            fmapi_endpoint_type='global', fmapi_context_length='long',
            fmapi_quantity=1,
        )
        be = _get_be_fmapi_results(item)
        assert be['sku'] == expected_sku


# ── Edge case and fallback tests ─────────────────────────────────────────

class TestFMAPIPropEdgeCases:
    """Edge cases: zero quantity, unknown model/provider, fallback rates."""

    def test_zero_quantity(self, pricing):
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='openai',
            fmapi_model='gpt-5', fmapi_rate_type='input_token',
            fmapi_endpoint_type='global', fmapi_context_length='all',
            fmapi_quantity=0,
        )
        be = _get_be_fmapi_results(item)
        assert be['total_dbus'] == pytest.approx(0, abs=TOL)
        assert be['monthly_cost'] == pytest.approx(0, abs=TOL)

    def test_unknown_model_input_fallback(self, pricing):
        """Unknown model should use proprietary fallback rate (21.43 for input)."""
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='openai',
            fmapi_model='nonexistent-model', fmapi_rate_type='input_token',
            fmapi_endpoint_type='global', fmapi_context_length='all',
            fmapi_quantity=10,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(21.43, abs=TOL)

    def test_unknown_model_output_fallback(self, pricing):
        """Unknown model output should use proprietary fallback (321.43)."""
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='anthropic',
            fmapi_model='nonexistent-model', fmapi_rate_type='output_token',
            fmapi_endpoint_type='global', fmapi_context_length='long',
            fmapi_quantity=10,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(321.43, abs=TOL)

    def test_unknown_model_cache_read_fallback(self, pricing):
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='openai',
            fmapi_model='nonexistent-model', fmapi_rate_type='cache_read',
            fmapi_endpoint_type='global', fmapi_context_length='all',
            fmapi_quantity=10,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(8.57, abs=TOL)

    def test_unknown_model_cache_write_fallback(self, pricing):
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='openai',
            fmapi_model='nonexistent-model', fmapi_rate_type='cache_write',
            fmapi_endpoint_type='global', fmapi_context_length='all',
            fmapi_quantity=10,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(85.71, abs=TOL)

    def test_batch_inference_is_not_provisioned(self, pricing):
        """Regression: batch_inference must NOT be treated as provisioned/hourly."""
        from app.routes.export.pricing import _is_fmapi_hourly
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='openai',
            fmapi_model='gpt-5', fmapi_rate_type='batch_inference',
            fmapi_endpoint_type='global', fmapi_context_length='all',
            fmapi_quantity=10,
        )
        assert _is_fmapi_hourly(item, CLOUD) is False

    def test_context_length_fallback_to_all(self, pricing):
        """When 'long' context not found, backend falls back to 'all' context."""
        # claude-haiku-4-5 uses 'all' context, not 'long'
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='anthropic',
            fmapi_model='claude-haiku-4-5', fmapi_rate_type='input_token',
            fmapi_endpoint_type='global', fmapi_context_length='long',
            fmapi_quantity=10,
        )
        be = _get_be_fmapi_results(item)
        # Should fall back to 'all' context and find the rate
        expected_key = 'aws:anthropic:claude-haiku-4-5:global:all:input_token'
        expected_rate = pricing['fmapi_prop_rates'][expected_key]['dbu_rate']
        assert be['dbu_per_m'] == pytest.approx(expected_rate, abs=TOL)

    def test_large_quantity(self, pricing):
        key = 'aws:anthropic:claude-sonnet-4-5:global:long:input_token'
        rate_info = pricing['fmapi_prop_rates'][key]
        item = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='anthropic',
            fmapi_model='claude-sonnet-4-5', fmapi_rate_type='input_token',
            fmapi_endpoint_type='global', fmapi_context_length='long',
            fmapi_quantity=5000,
        )
        be = _get_be_fmapi_results(item)
        assert be['total_dbus'] == pytest.approx(5000 * rate_info['dbu_rate'], abs=1.0)


# ── Cross-provider comparison tests ──────────────────────────────────────

class TestFMAPIPropCrossProvider:
    """Verify different providers get different rates and SKUs."""

    def test_different_providers_different_prices(self, pricing):
        """Same rate type across providers should give different DBU rates."""
        providers = {
            'openai': ('gpt-5', 'global', 'all'),
            'anthropic': ('claude-sonnet-4-5', 'global', 'long'),
            'google': ('gemini-2-5-flash', 'global', 'long'),
        }
        results = {}
        for prov, (model, endpoint, context) in providers.items():
            item = make_item(
                workload_type='FMAPI_PROPRIETARY', fmapi_provider=prov,
                fmapi_model=model, fmapi_rate_type='input_token',
                fmapi_endpoint_type=endpoint, fmapi_context_length=context,
                fmapi_quantity=10,
            )
            results[prov] = _get_be_fmapi_results(item)
        # Each provider should have a different DBU/M rate
        rates = {p: r['dbu_per_m'] for p, r in results.items()}
        assert len(set(rates.values())) >= 2, f"Expected different rates: {rates}"

    def test_global_vs_in_geo_pricing(self, pricing):
        """In-geo pricing should differ from global for OpenAI."""
        item_global = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='openai',
            fmapi_model='gpt-5', fmapi_rate_type='input_token',
            fmapi_endpoint_type='global', fmapi_context_length='all',
            fmapi_quantity=10,
        )
        item_in_geo = make_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='openai',
            fmapi_model='gpt-5', fmapi_rate_type='input_token',
            fmapi_endpoint_type='in_geo', fmapi_context_length='all',
            fmapi_quantity=10,
        )
        be_global = _get_be_fmapi_results(item_global)
        be_in_geo = _get_be_fmapi_results(item_in_geo)
        assert be_in_geo['dbu_per_m'] > be_global['dbu_per_m'], \
            "In-geo should be more expensive than global"
