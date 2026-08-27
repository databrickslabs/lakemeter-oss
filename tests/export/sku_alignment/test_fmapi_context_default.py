import pytest

from app.routes.calculate.schemas import FMAPIProprietaryCalculationRequest
from app.routes.export.pricing import _get_fmapi_dbu_per_million
from .conftest import make_line_item


class TestFMAPIContextDefault:
    def _make_fmapi_prop_item(
        self,
        provider="anthropic",
        model="claude-opus-4-6",
        context_length=None,
    ):
        return make_line_item(
            workload_type='FMAPI_PROPRIETARY',
            fmapi_provider=provider,
            fmapi_model=model,
            fmapi_rate_type='input_token',
            fmapi_endpoint_type='global',
            fmapi_context_length=context_length,
        )

    def test_api_defaults_match_frontend_global_all_defaults(self):
        request = FMAPIProprietaryCalculationRequest(
            cloud="AWS",
            region="us-east-1",
            tier="ENTERPRISE",
            provider="anthropic",
            model="claude-opus-4-6",
            quantity=1,
            rate_type="input_token",
        )

        assert request.endpoint_type == "global"
        assert request.context_length == "all"

    def test_export_defaults_missing_context_to_exact_all_rate(self):
        item = self._make_fmapi_prop_item(context_length=None)
        rate, found = _get_fmapi_dbu_per_million(item, 'aws')

        assert found is True
        assert rate == pytest.approx(71.429)

    def test_explicit_context_uses_exact_published_matrix(self):
        item = self._make_fmapi_prop_item(
            provider="openai",
            model="gpt-5-6-sol",
            context_length="short",
        )
        rate, found = _get_fmapi_dbu_per_million(item, 'aws')

        assert found is True
        assert rate == pytest.approx(71.429)

    def test_export_does_not_fall_back_to_another_context(self):
        item = self._make_fmapi_prop_item(
            model="claude-sonnet-5",
            context_length="short",
        )
        rate, found = _get_fmapi_dbu_per_million(item, 'aws')

        assert found is False
        assert rate == 0
