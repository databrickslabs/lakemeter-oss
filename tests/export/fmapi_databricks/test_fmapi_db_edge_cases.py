"""Test FMAPI Databricks edge cases, NaN guards, and cross-cloud.

AC-29 to AC-34: Unknown model, zero quantity, NaN prevention, rate ordering.
"""
import math
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from app.routes.export.pricing import _get_fmapi_dbu_per_million
from .conftest import make_line_item
from .fmapi_db_calc_helpers import (
    FMAPI_DB_RATES, frontend_calc_fmapi_db, backend_calc_fmapi_db,
    get_dbu_rate, get_all_models, get_model_rate_types,
)


class TestUnknownModel:
    """AC-29: Unknown model returns (0, False) with no crash."""

    def test_unknown_model_returns_zero(self):
        item = make_line_item(fmapi_model='totally-fake-model', fmapi_rate_type='input_token')
        rate, found = _get_fmapi_dbu_per_million(item, 'aws')
        assert found is False
        assert rate == 0

    def test_empty_model_returns_zero(self):
        item = make_line_item(fmapi_model='', fmapi_rate_type='input_token')
        rate, found = _get_fmapi_dbu_per_million(item, 'aws')
        assert found is False
        assert rate == 0

    def test_none_model_returns_zero(self):
        item = make_line_item(fmapi_model=None, fmapi_rate_type='input_token')
        rate, found = _get_fmapi_dbu_per_million(item, 'aws')
        assert found is False
        assert rate == 0


class TestZeroQuantity:
    """AC-30: Zero quantity = zero DBUs/cost."""

    @pytest.mark.parametrize("rate_type", [
        "input_token", "output_token", "provisioned_scaling", "provisioned_entry",
    ])
    def test_zero_quantity_frontend(self, rate_type):
        result = frontend_calc_fmapi_db(
            model='llama-3-3-70b', rate_type=rate_type, quantity=0
        )
        assert result['monthly_dbus'] == 0
        assert result['dbu_cost'] == 0
        assert result['total_cost'] == 0

    @pytest.mark.parametrize("rate_type", [
        "input_token", "output_token", "provisioned_scaling", "provisioned_entry",
    ])
    def test_zero_quantity_backend(self, rate_type):
        result = backend_calc_fmapi_db(
            model='llama-3-3-70b', rate_type=rate_type, quantity=0
        )
        assert result['monthly_dbus'] == 0
        assert result['dbu_cost'] == 0
        assert result['total_cost'] == 0


class TestNaNGuards:
    """AC-31: No NaN for any valid model + rate_type combination."""

    @pytest.mark.parametrize("cloud", ["aws", "azure", "gcp"])
    def test_no_nan_all_entries(self, cloud):
        models = get_all_models(cloud)
        for model in models:
            for rt in get_model_rate_types(cloud, model):
                fe = frontend_calc_fmapi_db(model=model, rate_type=rt, quantity=100, cloud=cloud)
                be = backend_calc_fmapi_db(model=model, rate_type=rt, quantity=100, cloud=cloud)
                for calc_name, result in [('fe', fe), ('be', be)]:
                    for key, val in result.items():
                        if isinstance(val, (int, float)):
                            assert not math.isnan(val), (
                                f"NaN in {calc_name}.{key} for {cloud}:{model}:{rt}"
                            )
                            assert not math.isinf(val), (
                                f"Inf in {calc_name}.{key} for {cloud}:{model}:{rt}"
                            )


class TestOutputGTInput:
    """AC-32: Output rate > input rate for models with both types."""

    def test_output_gt_input_all_clouds(self):
        for cloud in ('aws', 'azure', 'gcp'):
            models = get_all_models(cloud)
            for model in models:
                rate_types = get_model_rate_types(cloud, model)
                if 'input_token' in rate_types and 'output_token' in rate_types:
                    i_rate = get_dbu_rate(cloud, model, 'input_token')
                    o_rate = get_dbu_rate(cloud, model, 'output_token')
                    assert o_rate > i_rate, (
                        f"{cloud}:{model} output({o_rate}) <= input({i_rate})"
                    )


class TestProvisionedEntryLEScaling:
    """AC-33: provisioned_entry <= provisioned_scaling for same model."""

    def test_entry_le_scaling_all_clouds(self):
        for cloud in ('aws', 'azure', 'gcp'):
            models = get_all_models(cloud)
            for model in models:
                rate_types = get_model_rate_types(cloud, model)
                if 'provisioned_entry' in rate_types and 'provisioned_scaling' in rate_types:
                    entry = get_dbu_rate(cloud, model, 'provisioned_entry')
                    scaling = get_dbu_rate(cloud, model, 'provisioned_scaling')
                    assert entry <= scaling, (
                        f"{cloud}:{model} entry({entry}) > scaling({scaling})"
                    )


class TestCaseInsensitiveFallback:
    """AC-34: Case-insensitive fallback lookup works."""

    def test_lowercase_key_still_found(self):
        item = make_line_item(
            fmapi_model='llama-3-3-70b', fmapi_rate_type='input_token'
        )
        rate, found = _get_fmapi_dbu_per_million(item, 'aws')
        assert found is True
        assert rate == 7.143


class TestCrossCloudFEBEAlignment:
    """Cross-cloud FE vs BE alignment."""

    @pytest.mark.parametrize("cloud", ["aws", "azure", "gcp"])
    def test_fe_be_match_per_cloud(self, cloud):
        models = get_all_models(cloud)
        for model in models:
            for rt in get_model_rate_types(cloud, model):
                fe = frontend_calc_fmapi_db(model=model, rate_type=rt, quantity=100, cloud=cloud)
                be = backend_calc_fmapi_db(model=model, rate_type=rt, quantity=100, cloud=cloud)
                assert abs(fe['monthly_dbus'] - be['monthly_dbus']) < 0.01, (
                    f"{cloud}:{model}:{rt} FE={fe['monthly_dbus']} BE={be['monthly_dbus']}"
                )
