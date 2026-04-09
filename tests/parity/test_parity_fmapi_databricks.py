"""Parity tests: FMAPI_DATABRICKS workload — backend vs frontend equivalence.

Covers all 10 Databricks OSS models across input_token, output_token,
provisioned_scaling, and provisioned_entry rate types.
"""
import pytest
from .conftest import make_item
from .frontend_calc import fe_fmapi_token_cost, fe_fmapi_provisioned_cost

CLOUD = 'aws'
REGION = 'us-east-1'
TIER = 'PREMIUM'
TOL = 0.01


def _get_be_fmapi_results(item):
    """Run backend FMAPI calculation path."""
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


# ── Token-based tests (input_token) ──────────────────────────────────────

class TestFMAPIDbInputToken:
    """FMAPI Databricks token-based (input) across multiple models."""

    def test_bge_large_input(self, pricing):
        rate_info = pricing['fmapi_db_rates']['aws:bge-large:input_token']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='bge-large',
            fmapi_rate_type='input_token', fmapi_quantity=10,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)
        assert be['total_dbus'] == pytest.approx(10 * rate_info['dbu_rate'], abs=TOL)
        fe_cost = fe_fmapi_token_cost(
            quantity_millions=10, dbu_per_million=rate_info['dbu_rate'],
            dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)
        assert be['sku'] == 'SERVERLESS_REAL_TIME_INFERENCE'

    def test_gte_embedding_input(self, pricing):
        """GTE is an embedding model — input_token only, no output."""
        rate_info = pricing['fmapi_db_rates']['aws:gte:input_token']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='gte',
            fmapi_rate_type='input_token', fmapi_quantity=25,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)
        fe_cost = fe_fmapi_token_cost(
            quantity_millions=25, dbu_per_million=rate_info['dbu_rate'],
            dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_llama_3_3_70b_input(self, pricing):
        """Large model — higher DBU rate."""
        rate_info = pricing['fmapi_db_rates']['aws:llama-3-3-70b:input_token']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='llama-3-3-70b',
            fmapi_rate_type='input_token', fmapi_quantity=15,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)
        assert be['total_dbus'] == pytest.approx(15 * rate_info['dbu_rate'], abs=TOL)
        fe_cost = fe_fmapi_token_cost(
            quantity_millions=15, dbu_per_million=rate_info['dbu_rate'],
            dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_llama_4_maverick_input(self, pricing):
        rate_info = pricing['fmapi_db_rates']['aws:llama-4-maverick:input_token']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='llama-4-maverick',
            fmapi_rate_type='input_token', fmapi_quantity=50,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)
        fe_cost = fe_fmapi_token_cost(
            quantity_millions=50, dbu_per_million=rate_info['dbu_rate'],
            dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_gpt_oss_20b_input(self, pricing):
        """Lowest input rate model."""
        rate_info = pricing['fmapi_db_rates']['aws:gpt-oss-20b:input_token']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='gpt-oss-20b',
            fmapi_rate_type='input_token', fmapi_quantity=100,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)
        assert be['total_dbus'] == pytest.approx(100 * rate_info['dbu_rate'], abs=TOL)

    def test_gpt_oss_120b_input(self, pricing):
        rate_info = pricing['fmapi_db_rates']['aws:gpt-oss-120b:input_token']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='gpt-oss-120b',
            fmapi_rate_type='input_token', fmapi_quantity=30,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_gemma_input(self, pricing):
        rate_info = pricing['fmapi_db_rates']['aws:gemma-3-12b:input_token']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='gemma-3-12b',
            fmapi_rate_type='input_token', fmapi_quantity=20,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_llama_3_1_8b_input(self, pricing):
        rate_info = pricing['fmapi_db_rates']['aws:llama-3-1-8b:input_token']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='llama-3-1-8b',
            fmapi_rate_type='input_token', fmapi_quantity=40,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)


# ── Token-based tests (output_token) ─────────────────────────────────────

class TestFMAPIDbOutputToken:
    """FMAPI Databricks token-based (output) — only LLMs, not embeddings."""

    def test_gemma_output(self, pricing):
        rate_info = pricing['fmapi_db_rates']['aws:gemma-3-12b:output_token']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='gemma-3-12b',
            fmapi_rate_type='output_token', fmapi_quantity=5,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)
        fe_cost = fe_fmapi_token_cost(
            quantity_millions=5, dbu_per_million=rate_info['dbu_rate'],
            dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_llama_3_3_70b_output(self, pricing):
        rate_info = pricing['fmapi_db_rates']['aws:llama-3-3-70b:output_token']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='llama-3-3-70b',
            fmapi_rate_type='output_token', fmapi_quantity=8,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)
        assert be['total_dbus'] == pytest.approx(8 * rate_info['dbu_rate'], abs=TOL)

    def test_gpt_oss_20b_output(self, pricing):
        rate_info = pricing['fmapi_db_rates']['aws:gpt-oss-20b:output_token']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='gpt-oss-20b',
            fmapi_rate_type='output_token', fmapi_quantity=12,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_gpt_oss_120b_output(self, pricing):
        rate_info = pricing['fmapi_db_rates']['aws:gpt-oss-120b:output_token']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='gpt-oss-120b',
            fmapi_rate_type='output_token', fmapi_quantity=7,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_llama_4_maverick_output(self, pricing):
        rate_info = pricing['fmapi_db_rates']['aws:llama-4-maverick:output_token']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='llama-4-maverick',
            fmapi_rate_type='output_token', fmapi_quantity=18,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)

    def test_llama_3_1_8b_output(self, pricing):
        rate_info = pricing['fmapi_db_rates']['aws:llama-3-1-8b:output_token']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='llama-3-1-8b',
            fmapi_rate_type='output_token', fmapi_quantity=22,
        )
        be = _get_be_fmapi_results(item)
        assert be['dbu_per_m'] == pytest.approx(rate_info['dbu_rate'], abs=TOL)


# ── Provisioned tests ────────────────────────────────────────────────────

class TestFMAPIDbProvisioned:
    """FMAPI Databricks provisioned (hourly) — scaling and entry modes."""

    def test_gemma_provisioned_scaling(self, pricing):
        rate_info = pricing['fmapi_db_rates']['aws:gemma-3-12b:provisioned_scaling']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='gemma-3-12b',
            fmapi_rate_type='provisioned_scaling', fmapi_quantity=100,
        )
        be = _get_be_fmapi_results(item)
        assert be['hours'] == pytest.approx(100, abs=TOL)
        assert be['total_dbus'] == pytest.approx(100 * rate_info['dbu_rate'], abs=TOL)
        fe_cost = fe_fmapi_provisioned_cost(
            hours=100, dbu_per_hour=rate_info['dbu_rate'],
            dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_gemma_provisioned_entry(self, pricing):
        rate_info = pricing['fmapi_db_rates']['aws:gemma-3-12b:provisioned_entry']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='gemma-3-12b',
            fmapi_rate_type='provisioned_entry', fmapi_quantity=200,
        )
        be = _get_be_fmapi_results(item)
        assert be['hours'] == pytest.approx(200, abs=TOL)
        assert be['total_dbus'] == pytest.approx(200 * rate_info['dbu_rate'], abs=TOL)

    def test_bge_large_provisioned_scaling(self, pricing):
        """Embedding model — provisioned scaling."""
        rate_info = pricing['fmapi_db_rates']['aws:bge-large:provisioned_scaling']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='bge-large',
            fmapi_rate_type='provisioned_scaling', fmapi_quantity=730,
        )
        be = _get_be_fmapi_results(item)
        assert be['total_dbus'] == pytest.approx(730 * rate_info['dbu_rate'], abs=TOL)

    def test_bge_large_provisioned_entry(self, pricing):
        rate_info = pricing['fmapi_db_rates']['aws:bge-large:provisioned_entry']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='bge-large',
            fmapi_rate_type='provisioned_entry', fmapi_quantity=500,
        )
        be = _get_be_fmapi_results(item)
        assert be['total_dbus'] == pytest.approx(500 * rate_info['dbu_rate'], abs=TOL)

    def test_llama_3_3_70b_provisioned_scaling(self, pricing):
        """Highest provisioned_scaling rate model."""
        rate_info = pricing['fmapi_db_rates']['aws:llama-3-3-70b:provisioned_scaling']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='llama-3-3-70b',
            fmapi_rate_type='provisioned_scaling', fmapi_quantity=50,
        )
        be = _get_be_fmapi_results(item)
        assert be['total_dbus'] == pytest.approx(50 * rate_info['dbu_rate'], abs=TOL)
        fe_cost = fe_fmapi_provisioned_cost(
            hours=50, dbu_per_hour=rate_info['dbu_rate'],
            dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_llama_3_1_8b_asymmetric_provisioned(self, pricing):
        """Model where scaling != entry rate."""
        scaling = pricing['fmapi_db_rates']['aws:llama-3-1-8b:provisioned_scaling']
        entry = pricing['fmapi_db_rates']['aws:llama-3-1-8b:provisioned_entry']
        assert scaling['dbu_rate'] != entry['dbu_rate'], "Expect asymmetric rates"

        item_s = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='llama-3-1-8b',
            fmapi_rate_type='provisioned_scaling', fmapi_quantity=100,
        )
        item_e = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='llama-3-1-8b',
            fmapi_rate_type='provisioned_entry', fmapi_quantity=100,
        )
        be_s = _get_be_fmapi_results(item_s)
        be_e = _get_be_fmapi_results(item_e)
        assert be_s['total_dbus'] == pytest.approx(100 * scaling['dbu_rate'], abs=TOL)
        assert be_e['total_dbus'] == pytest.approx(100 * entry['dbu_rate'], abs=TOL)
        assert be_s['total_dbus'] != be_e['total_dbus']

    def test_provisioned_only_model_llama_3_2_1b(self, pricing):
        """Model with provisioned rates only (no token-based)."""
        rate_info = pricing['fmapi_db_rates']['aws:llama-3-2-1b:provisioned_scaling']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='llama-3-2-1b',
            fmapi_rate_type='provisioned_scaling', fmapi_quantity=730,
        )
        be = _get_be_fmapi_results(item)
        assert be['total_dbus'] == pytest.approx(730 * rate_info['dbu_rate'], abs=TOL)

    def test_provisioned_only_model_llama_3_2_3b(self, pricing):
        rate_info = pricing['fmapi_db_rates']['aws:llama-3-2-3b:provisioned_entry']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='llama-3-2-3b',
            fmapi_rate_type='provisioned_entry', fmapi_quantity=365,
        )
        be = _get_be_fmapi_results(item)
        assert be['total_dbus'] == pytest.approx(365 * rate_info['dbu_rate'], abs=TOL)


# ── SKU assignment tests ─────────────────────────────────────────────────

class TestFMAPIDbSKU:
    """Verify SKU is always SERVERLESS_REAL_TIME_INFERENCE for Databricks FMAPI."""

    @pytest.mark.parametrize("model,rate_type", [
        ('bge-large', 'input_token'),
        ('gemma-3-12b', 'output_token'),
        ('llama-3-3-70b', 'provisioned_scaling'),
        ('llama-3-2-1b', 'provisioned_entry'),
        ('gte', 'input_token'),
        ('llama-4-maverick', 'input_token'),
    ])
    def test_sku_is_serverless_rti(self, pricing, model, rate_type):
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model=model,
            fmapi_rate_type=rate_type, fmapi_quantity=1,
        )
        be = _get_be_fmapi_results(item)
        assert be['sku'] == 'SERVERLESS_REAL_TIME_INFERENCE'


# ── Edge case and fallback tests ─────────────────────────────────────────

class TestFMAPIDbEdgeCases:
    """Edge cases: zero quantity, unknown model, fallback rates."""

    def test_zero_quantity_token(self, pricing):
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='gemma-3-12b',
            fmapi_rate_type='input_token', fmapi_quantity=0,
        )
        be = _get_be_fmapi_results(item)
        assert be['total_dbus'] == pytest.approx(0, abs=TOL)
        assert be['monthly_cost'] == pytest.approx(0, abs=TOL)

    def test_zero_quantity_provisioned(self, pricing):
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='gemma-3-12b',
            fmapi_rate_type='provisioned_scaling', fmapi_quantity=0,
        )
        be = _get_be_fmapi_results(item)
        assert be['total_dbus'] == pytest.approx(0, abs=TOL)

    def test_unknown_model_token_fallback(self, pricing):
        """Unknown model should use Databricks fallback rate (1.0 for input)."""
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='nonexistent-model',
            fmapi_rate_type='input_token', fmapi_quantity=10,
        )
        be = _get_be_fmapi_results(item)
        # Frontend fallback: input_token = 1.0 for Databricks
        assert be['dbu_per_m'] == pytest.approx(1.0, abs=TOL)
        assert be['total_dbus'] == pytest.approx(10 * 1.0, abs=TOL)

    def test_unknown_model_output_fallback(self, pricing):
        """Unknown model output should use Databricks fallback rate (3.0)."""
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='nonexistent-model',
            fmapi_rate_type='output_token', fmapi_quantity=10,
        )
        be = _get_be_fmapi_results(item)
        # Frontend fallback: output_token = 3.0 for Databricks
        assert be['dbu_per_m'] == pytest.approx(3.0, abs=TOL)
        assert be['total_dbus'] == pytest.approx(10 * 3.0, abs=TOL)

    def test_unknown_model_provisioned_scaling_fallback(self, pricing):
        """Unknown model provisioned_scaling should fallback to 200 DBU/hr."""
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='nonexistent-model',
            fmapi_rate_type='provisioned_scaling', fmapi_quantity=10,
        )
        be = _get_be_fmapi_results(item)
        assert be['total_dbus'] == pytest.approx(10 * 200, abs=TOL)

    def test_unknown_model_provisioned_entry_fallback(self, pricing):
        """Unknown model provisioned_entry should fallback to 50 DBU/hr."""
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='nonexistent-model',
            fmapi_rate_type='provisioned_entry', fmapi_quantity=10,
        )
        be = _get_be_fmapi_results(item)
        assert be['total_dbus'] == pytest.approx(10 * 50, abs=TOL)

    def test_large_quantity(self, pricing):
        """Large token quantity should calculate correctly."""
        rate_info = pricing['fmapi_db_rates']['aws:llama-3-3-70b:input_token']
        item = make_item(
            workload_type='FMAPI_DATABRICKS', fmapi_model='llama-3-3-70b',
            fmapi_rate_type='input_token', fmapi_quantity=10000,
        )
        be = _get_be_fmapi_results(item)
        assert be['total_dbus'] == pytest.approx(10000 * rate_info['dbu_rate'], abs=1.0)
