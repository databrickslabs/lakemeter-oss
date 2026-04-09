"""Test FMAPI Databricks config display helpers.

AC-19 to AC-22: Display name, config details, rate type labels.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from app.routes.export.helpers import (
    _get_workload_display_name, _get_workload_config_details,
    _fmapi_details,
)
from .conftest import make_line_item


class TestDisplayName:
    """AC-19: Display name = 'Foundation Models (Databricks)'."""

    def test_display_name(self):
        assert _get_workload_display_name('FMAPI_DATABRICKS') == 'Foundation Models (Databricks)'

    def test_proprietary_display_name(self):
        assert _get_workload_display_name('FMAPI_PROPRIETARY') == 'Foundation Models (Proprietary)'


class TestTokenConfigDetails:
    """AC-20: Config details for token-based items."""

    def test_input_token_details(self):
        item = make_line_item(
            fmapi_model='llama-3-3-70b', fmapi_rate_type='input_token',
            fmapi_quantity=100,
        )
        details = _fmapi_details(item)
        assert 'Model: llama-3-3-70b' in details
        assert 'Rate: Input Tokens' in details
        assert 'Tokens: 100.0M/mo' in details

    def test_output_token_details(self):
        item = make_line_item(
            fmapi_model='llama-3-3-70b', fmapi_rate_type='output_token',
            fmapi_quantity=50,
        )
        details = _fmapi_details(item)
        assert 'Rate: Output Tokens' in details
        assert 'Tokens: 50.0M/mo' in details


class TestProvisionedConfigDetails:
    """AC-21: Config details for provisioned items."""

    def test_provisioned_scaling_details(self):
        item = make_line_item(
            fmapi_model='llama-3-3-70b', fmapi_rate_type='provisioned_scaling',
            fmapi_quantity=730,
        )
        details = _fmapi_details(item)
        assert 'Model: llama-3-3-70b' in details
        assert 'Rate: Provisioned Scaling' in details
        assert 'Hours: 730' in details

    def test_provisioned_entry_details(self):
        item = make_line_item(
            fmapi_model='llama-3-3-70b', fmapi_rate_type='provisioned_entry',
            fmapi_quantity=200,
        )
        details = _fmapi_details(item)
        assert 'Rate: Provisioned Entry' in details
        assert 'Hours: 200' in details


class TestRateTypeLabels:
    """AC-22: Rate type display names correct."""

    @pytest.mark.parametrize("rate_type,expected_label", [
        ("input_token", "Input Tokens"),
        ("output_token", "Output Tokens"),
        ("provisioned_scaling", "Provisioned Scaling"),
        ("provisioned_entry", "Provisioned Entry"),
    ])
    def test_rate_type_display(self, rate_type, expected_label):
        item = make_line_item(fmapi_rate_type=rate_type, fmapi_quantity=100)
        details = _fmapi_details(item)
        assert f'Rate: {expected_label}' in details


class TestFullConfigString:
    """Integration: _get_workload_config_details for FMAPI_DATABRICKS."""

    def test_full_config_string(self):
        item = make_line_item(
            fmapi_model='llama-3-3-70b', fmapi_rate_type='input_token',
            fmapi_quantity=100,
        )
        config = _get_workload_config_details(item)
        assert 'llama-3-3-70b' in config
        assert 'Input Tokens' in config

    def test_no_model_details(self):
        item = make_line_item(fmapi_model=None, fmapi_rate_type=None, fmapi_quantity=None)
        details = _fmapi_details(item)
        assert details == []
