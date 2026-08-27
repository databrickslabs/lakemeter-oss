"""Parity tests for proprietary Foundation Model API catalog entries."""

import json
from pathlib import Path

import pytest

from app.services.fmapi_pricing import get_effective_dbu_rate
from .conftest import make_item


CLOUD = "aws"
TOL = 0.01
CATALOG_PATH = (
    Path(__file__).resolve().parents[2]
    / "backend/static/pricing/fmapi-proprietary-rates.json"
)
CATALOG = json.loads(CATALOG_PATH.read_text())
ACTIVE_AWS_KEYS = [
    key
    for key, rate in CATALOG.items()
    if key.startswith("aws:") and rate.get("status") != "retired"
]


def _get_backend_results(item):
    from app.routes.export.calculations import _calculate_dbu_per_hour
    from app.routes.export.excel_item_helpers import calc_item_values
    from app.routes.export.pricing import _is_fmapi_hourly

    dbu_per_hour, _ = _calculate_dbu_per_hour(item, CLOUD)
    is_hourly = _is_fmapi_hourly(item, CLOUD)
    hours, token_quantity, dbu_per_million, total_dbus, _ = calc_item_values(
        item,
        not is_hourly,
        is_hourly,
        dbu_per_hour,
        CLOUD,
        [],
    )
    return {
        "hours": hours,
        "token_quantity": token_quantity,
        "dbu_per_million": dbu_per_million,
        "total_dbus": total_dbus,
        "is_hourly": is_hourly,
    }


@pytest.mark.parametrize("key", ACTIVE_AWS_KEYS)
def test_every_active_aws_rate_matches_export_calculation(key):
    cloud, provider, model, endpoint, context, rate_type = key.split(":")
    rate = CATALOG[key]
    quantity = 3.5
    item = make_item(
        workload_type="FMAPI_PROPRIETARY",
        fmapi_provider=provider,
        fmapi_model=model,
        fmapi_rate_type=rate_type,
        fmapi_endpoint_type=endpoint,
        fmapi_context_length=context,
        fmapi_quantity=quantity,
    )

    result = _get_backend_results(item)
    effective_rate = get_effective_dbu_rate(rate)

    assert cloud == CLOUD
    assert result["is_hourly"] is rate["is_hourly"]
    assert result["total_dbus"] == pytest.approx(
        quantity * effective_rate,
        abs=TOL,
    )
    if rate["is_hourly"]:
        assert result["hours"] == pytest.approx(quantity, abs=TOL)
        assert result["token_quantity"] == 0
        assert result["dbu_per_million"] == 0
    else:
        assert result["hours"] == 0
        assert result["token_quantity"] == pytest.approx(quantity, abs=TOL)
        assert result["dbu_per_million"] == pytest.approx(
            effective_rate,
            abs=TOL,
        )


@pytest.mark.parametrize(
    "provider,expected_sku",
    [
        ("openai", "OPENAI_MODEL_SERVING"),
        ("anthropic", "ANTHROPIC_MODEL_SERVING"),
        ("google", "GEMINI_MODEL_SERVING"),
        ("moonshot", "MOONSHOT_MODEL_SERVING"),
        ("zhipu", "ZHIPU_MODEL_SERVING"),
        ("deepseek", "DEEPSEEK_MODEL_SERVING"),
        ("qwen", "QWEN_MODEL_SERVING"),
    ],
)
def test_provider_sku_mapping(provider, expected_sku):
    from app.routes.export.pricing import _get_fmapi_sku

    item = make_item(
        workload_type="FMAPI_PROPRIETARY",
        fmapi_provider=provider,
        fmapi_model="model",
        fmapi_rate_type="input_token",
        fmapi_endpoint_type="global",
        fmapi_context_length="all",
    )

    assert _get_fmapi_sku(item, CLOUD) == expected_sku


def test_unknown_model_has_no_fabricated_rate():
    from app.routes.export.pricing import _get_fmapi_dbu_per_million

    item = make_item(
        workload_type="FMAPI_PROPRIETARY",
        fmapi_provider="openai",
        fmapi_model="nonexistent-model",
        fmapi_rate_type="input_token",
        fmapi_endpoint_type="global",
        fmapi_context_length="all",
        fmapi_quantity=10,
    )

    rate, found = _get_fmapi_dbu_per_million(item, CLOUD)
    result = _get_backend_results(item)

    assert found is False
    assert rate == 0
    assert result["total_dbus"] == 0


def test_unpublished_context_does_not_fall_back():
    from app.routes.export.pricing import _get_fmapi_dbu_per_million

    item = make_item(
        workload_type="FMAPI_PROPRIETARY",
        fmapi_provider="anthropic",
        fmapi_model="claude-sonnet-5",
        fmapi_rate_type="input_token",
        fmapi_endpoint_type="global",
        fmapi_context_length="short",
        fmapi_quantity=10,
    )

    rate, found = _get_fmapi_dbu_per_million(item, CLOUD)

    assert found is False
    assert rate == 0
