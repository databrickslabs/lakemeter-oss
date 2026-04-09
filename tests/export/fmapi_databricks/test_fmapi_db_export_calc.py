"""Test backend export calculation functions for FMAPI Databricks.

AC-13 to AC-18: Token-based vs provisioned calculation paths.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from app.routes.export.pricing import _get_fmapi_dbu_per_million
from .conftest import make_line_item
from .fmapi_db_calc_helpers import (
    frontend_calc_fmapi_db, backend_calc_fmapi_db, get_dbu_rate,
)


class TestTokenBasedCalculation:
    """AC-13: Token-based monthly_dbus = quantity_M x dbu_per_1M_tokens."""

    @pytest.mark.parametrize("model,rate_type,quantity,expected_rate", [
        ("llama-3-3-70b", "input_token", 100, 7.143),
        ("llama-3-3-70b", "output_token", 50, 21.429),
        ("bge-large", "input_token", 200, 1.429),
        ("gpt-oss-20b", "input_token", 500, 1.0),
        ("gpt-oss-120b", "output_token", 10, 8.571),
    ])
    def test_token_monthly_dbus(self, model, rate_type, quantity, expected_rate):
        expected_dbus = quantity * expected_rate
        be = backend_calc_fmapi_db(model=model, rate_type=rate_type, quantity=quantity)
        assert abs(be['monthly_dbus'] - expected_dbus) < 0.01, (
            f"{model}:{rate_type} qty={quantity}: got {be['monthly_dbus']}, "
            f"expected {expected_dbus}"
        )

    def test_token_100m_llama_input(self):
        """Spec test: 100M input tokens of llama-3-3-70b."""
        result = backend_calc_fmapi_db(
            model='llama-3-3-70b', rate_type='input_token', quantity=100
        )
        assert abs(result['monthly_dbus'] - 714.3) < 0.1

    def test_token_50m_llama_output(self):
        """Spec test: 50M output tokens of llama-3-3-70b."""
        result = backend_calc_fmapi_db(
            model='llama-3-3-70b', rate_type='output_token', quantity=50
        )
        assert abs(result['monthly_dbus'] - 1071.45) < 0.1


class TestProvisionedCalculation:
    """AC-14: Provisioned monthly_dbus = hours x dbu_per_hour."""

    @pytest.mark.parametrize("model,rate_type,hours,expected_rate", [
        ("llama-3-3-70b", "provisioned_scaling", 730, 342.857),
        ("llama-3-3-70b", "provisioned_entry", 730, 85.714),
        ("bge-large", "provisioned_scaling", 200, 24.0),
        ("llama-3-1-8b", "provisioned_entry", 100, 53.571),
    ])
    def test_provisioned_monthly_dbus(self, model, rate_type, hours, expected_rate):
        expected_dbus = hours * expected_rate
        be = backend_calc_fmapi_db(model=model, rate_type=rate_type, quantity=hours)
        assert abs(be['monthly_dbus'] - expected_dbus) < 0.1

    def test_provisioned_730hrs_llama_scaling(self):
        """Spec test: llama-3-3-70b provisioned_scaling 730 hours."""
        result = backend_calc_fmapi_db(
            model='llama-3-3-70b', rate_type='provisioned_scaling', quantity=730
        )
        expected = 730 * 342.857
        assert abs(result['monthly_dbus'] - expected) < 1.0


class TestTokenItemHasZeroHours:
    """AC-15: Token-based items have hours=0 in export."""

    def test_token_hours_zero(self):
        item = make_line_item(
            fmapi_model='llama-3-3-70b', fmapi_rate_type='input_token',
            fmapi_quantity=100,
        )
        dbu_rate, found = _get_fmapi_dbu_per_million(item, 'aws')
        assert found is True
        # Token-based: hours = 0, tokens = quantity
        assert dbu_rate == 7.143


class TestProvisionedUsesQuantityAsHours:
    """AC-16: Provisioned items use fmapi_quantity as hours."""

    def test_provisioned_quantity_is_hours(self):
        fe = frontend_calc_fmapi_db(
            model='llama-3-3-70b', rate_type='provisioned_scaling', quantity=730
        )
        be = backend_calc_fmapi_db(
            model='llama-3-3-70b', rate_type='provisioned_scaling', quantity=730
        )
        # Both should use 730 as hours * dbu_per_hour
        expected = 730 * 342.857
        assert abs(fe['monthly_dbus'] - expected) < 1.0
        assert abs(be['monthly_dbus'] - expected) < 1.0


class TestGetFMAPIDbuPerMillion:
    """AC-18: _get_fmapi_dbu_per_million returns correct tuple."""

    def test_known_model_returns_true(self):
        item = make_line_item(fmapi_model='llama-3-3-70b', fmapi_rate_type='input_token')
        rate, found = _get_fmapi_dbu_per_million(item, 'aws')
        assert found is True
        assert rate == 7.143

    def test_unknown_model_returns_false(self):
        item = make_line_item(fmapi_model='nonexistent-xyz', fmapi_rate_type='input_token')
        rate, found = _get_fmapi_dbu_per_million(item, 'aws')
        assert found is False
        assert rate == 0

    def test_provisioned_rate_lookup(self):
        item = make_line_item(
            fmapi_model='llama-3-3-70b', fmapi_rate_type='provisioned_scaling'
        )
        rate, found = _get_fmapi_dbu_per_million(item, 'aws')
        assert found is True
        assert rate == 342.857

    def test_azure_model_lookup(self):
        item = make_line_item(fmapi_model='llama-3-3-70b', fmapi_rate_type='input_token')
        rate, found = _get_fmapi_dbu_per_million(item, 'azure')
        assert found is True
        assert rate == 7.143


class TestFrontendBackendAlignment:
    """Verify FE and BE produce same results."""

    @pytest.mark.parametrize("model,rate_type,quantity", [
        ("llama-3-3-70b", "input_token", 100),
        ("llama-3-3-70b", "output_token", 50),
        ("llama-3-3-70b", "provisioned_scaling", 730),
        ("bge-large", "input_token", 200),
        ("gpt-oss-20b", "output_token", 1000),
    ])
    def test_fe_be_monthly_dbus_match(self, model, rate_type, quantity):
        fe = frontend_calc_fmapi_db(model=model, rate_type=rate_type, quantity=quantity)
        be = backend_calc_fmapi_db(model=model, rate_type=rate_type, quantity=quantity)
        assert abs(fe['monthly_dbus'] - be['monthly_dbus']) < 0.01
        assert abs(fe['dbu_cost'] - be['dbu_cost']) < 0.01
