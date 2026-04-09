"""Sprint 7 — FMAPI_DATABRICKS backend pricing: SKU, rates, calc paths."""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

from app.routes.export.pricing import (
    _get_sku_type, _get_fmapi_sku, _get_fmapi_dbu_per_million, _is_fmapi_hourly,
)
from app.routes.export.excel_item_helpers import calc_item_values
from tests.export.fmapi_proprietary.conftest import make_line_item

# Load FMAPI Databricks pricing data
_PRICING_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', 'backend', 'static', 'pricing'
)
with open(os.path.join(_PRICING_DIR, 'fmapi-databricks-rates.json')) as f:
    FMAPI_DB_RATES = json.load(f)


def _make_db_item(**kwargs):
    """Create a mock line item with defaults for FMAPI_DATABRICKS workloads."""
    defaults = {
        "workload_type": "FMAPI_DATABRICKS",
        "fmapi_provider": "databricks",
        "fmapi_model": "llama-4-maverick",
        "fmapi_endpoint_type": "global",
        "fmapi_context_length": None,
        "fmapi_rate_type": "input_token",
        "fmapi_quantity": 10,
    }
    defaults.update(kwargs)
    return make_line_item(**defaults)


class TestFmapiDbSkuMapping:
    """FMAPI_DATABRICKS should map to SERVERLESS_REAL_TIME_INFERENCE."""

    @pytest.mark.parametrize("model", [
        "llama-4-maverick", "llama-3-3-70b", "bge-large", "gte",
    ])
    def test_all_models_map_to_serverless_inference(self, model):
        item = _make_db_item(fmapi_model=model)
        sku = _get_sku_type(item, "aws")
        assert sku == "SERVERLESS_REAL_TIME_INFERENCE", (
            f"{model} should map to SERVERLESS_REAL_TIME_INFERENCE, got {sku}")

    def test_unknown_model_fallback_sku(self):
        """Unknown model should still return SERVERLESS_REAL_TIME_INFERENCE."""
        item = _make_db_item(fmapi_model="nonexistent-model-xyz")
        sku = _get_fmapi_sku(item, "aws")
        assert sku == "SERVERLESS_REAL_TIME_INFERENCE"

    def test_empty_model_fallback(self):
        item = _make_db_item(fmapi_model="")
        sku = _get_fmapi_sku(item, "aws")
        assert sku is not None


class TestFmapiDbRateLookup:
    """Rate lookup for FMAPI_DATABRICKS models."""

    @pytest.mark.parametrize("model,rate_type", [
        ("llama-4-maverick", "input_token"),
        ("llama-4-maverick", "output_token"),
        ("bge-large", "input_token"),
        ("gte", "input_token"),
        ("llama-3-3-70b", "input_token"),
        ("llama-3-3-70b", "output_token"),
    ])
    def test_known_models_have_rates(self, model, rate_type):
        item = _make_db_item(fmapi_model=model, fmapi_rate_type=rate_type)
        rate, found = _get_fmapi_dbu_per_million(item, "aws")
        assert found, f"{model}/{rate_type} should be found in pricing"
        assert rate > 0, f"{model}/{rate_type} rate should be > 0"

    def test_unknown_model_rate_not_found(self):
        item = _make_db_item(fmapi_model="nonexistent-model")
        rate, found = _get_fmapi_dbu_per_million(item, "aws")
        assert not found, "Unknown model should not be found"

    def test_output_more_expensive_than_input(self):
        """Output tokens should cost more than input tokens for Llama."""
        item_in = _make_db_item(
            fmapi_model="llama-4-maverick", fmapi_rate_type="input_token")
        item_out = _make_db_item(
            fmapi_model="llama-4-maverick", fmapi_rate_type="output_token")
        rate_in, _ = _get_fmapi_dbu_per_million(item_in, "aws")
        rate_out, _ = _get_fmapi_dbu_per_million(item_out, "aws")
        assert rate_out > rate_in, (
            f"Output ({rate_out}) should be > input ({rate_in})")

    @pytest.mark.parametrize("model", ["bge-large", "gte"])
    def test_embeddings_models_input_only(self, model):
        """Embeddings models should have input_token rates."""
        item = _make_db_item(fmapi_model=model, fmapi_rate_type="input_token")
        rate, found = _get_fmapi_dbu_per_million(item, "aws")
        assert found and rate > 0


class TestFmapiDbHourlyClassification:
    """Provisioned types are hourly, token types are not."""

    @pytest.mark.parametrize("rate_type,expected_hourly", [
        ("input_token", False),
        ("output_token", False),
        ("provisioned_scaling", True),
        ("provisioned_entry", True),
    ])
    def test_hourly_classification(self, rate_type, expected_hourly):
        item = _make_db_item(fmapi_rate_type=rate_type)
        assert _is_fmapi_hourly(item, "aws") is expected_hourly


class TestFmapiDbCalcItemValues:
    """calc_item_values for FMAPI_DATABRICKS workloads."""

    def test_token_based_produces_nonzero_dbus(self):
        item = _make_db_item(
            fmapi_model="llama-4-maverick",
            fmapi_rate_type="input_token", fmapi_quantity=10)
        notes = []
        hours, tok_qty, dbu_m, total_dbus, tok_type = calc_item_values(
            item, True, False, 0, "aws", notes)
        assert tok_qty == 10
        assert dbu_m > 0
        assert total_dbus > 0
        assert hours == 0

    def test_provisioned_produces_nonzero_dbus(self):
        item = _make_db_item(
            fmapi_model="llama-4-maverick",
            fmapi_rate_type="provisioned_scaling", fmapi_quantity=730)
        notes = []
        hours, tok_qty, dbu_m, total_dbus, tok_type = calc_item_values(
            item, False, True, 0, "aws", notes)
        assert hours == 730
        assert total_dbus > 0
        assert tok_qty == 0

    def test_token_calculation_matches_formula(self):
        """monthly_dbus = quantity × dbu_per_1M."""
        model = "llama-4-maverick"
        item = _make_db_item(
            fmapi_model=model, fmapi_rate_type="input_token", fmapi_quantity=100)
        expected_rate = FMAPI_DB_RATES.get(
            f"aws:{model}:input_token", {}).get("dbu_rate", 0)
        notes = []
        _, tok_qty, dbu_m, total_dbus, _ = calc_item_values(
            item, True, False, 0, "aws", notes)
        assert tok_qty == 100
        assert dbu_m == pytest.approx(expected_rate, rel=1e-3)
        assert total_dbus == pytest.approx(100 * expected_rate, rel=1e-3)

    def test_embeddings_calculation(self):
        """BGE-Large embeddings calculation."""
        item = _make_db_item(
            fmapi_model="bge-large", fmapi_rate_type="input_token",
            fmapi_quantity=20)
        expected_rate = FMAPI_DB_RATES.get(
            "aws:bge-large:input_token", {}).get("dbu_rate", 0)
        notes = []
        _, tok_qty, dbu_m, total_dbus, _ = calc_item_values(
            item, True, False, 0, "aws", notes)
        assert tok_qty == 20
        assert dbu_m == pytest.approx(expected_rate, rel=1e-3)
        assert total_dbus == pytest.approx(20 * expected_rate, rel=1e-3)


class TestFmapiDbPricingDataIntegrity:
    """Verify pricing data has expected structure for all entries."""

    def test_all_entries_have_required_fields(self):
        required = {"dbu_rate", "is_hourly", "sku_product_type"}
        for key, info in FMAPI_DB_RATES.items():
            for field in required:
                assert field in info, (
                    f"Entry {key} missing required field '{field}'")

    def test_all_dbu_rates_positive(self):
        for key, info in FMAPI_DB_RATES.items():
            assert info["dbu_rate"] > 0, (
                f"Entry {key} has non-positive dbu_rate: {info['dbu_rate']}")

    def test_token_types_not_hourly(self):
        for key, info in FMAPI_DB_RATES.items():
            if key.endswith(":input_token") or key.endswith(":output_token"):
                assert info["is_hourly"] is False, (
                    f"Token type {key} should not be hourly")

    def test_provisioned_types_are_hourly(self):
        for key, info in FMAPI_DB_RATES.items():
            if "provisioned" in key:
                assert info["is_hourly"] is True, (
                    f"Provisioned type {key} should be hourly")
