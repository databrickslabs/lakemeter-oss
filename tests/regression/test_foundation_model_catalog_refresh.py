import importlib.util
import csv
import io
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routes.calculate.fmapi_calc import _build_fmapi_line_items_direct
from app.routes.export import _get_fmapi_dbu_per_million, _is_fmapi_hourly
from app.services.fmapi_pricing import (
    FMAPIRateNotFound,
    active_databricks_models,
    active_proprietary_models,
    get_databricks_rate,
    get_effective_dbu_rate,
    get_proprietary_rate,
)


ROOT = Path(__file__).resolve().parents[2]
CATALOG_SCRIPT = ROOT / "scripts" / "foundation_model_catalog.py"
WORKLOAD_FORM = ROOT / "frontend" / "src" / "components" / "WorkloadForm.tsx"
CALCULATOR = ROOT / "frontend" / "src" / "pages" / "Calculator.tsx"
FRONTEND_STORE = ROOT / "frontend" / "src" / "store" / "useStore.ts"


def _load_catalog_script():
    spec = importlib.util.spec_from_file_location(
        "foundation_model_catalog",
        CATALOG_SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "model,rate_type,expected",
    [
        ("kimi-k3", "input_token", 42.857),
        ("kimi-k2-7", "cache_read", 2.714),
        ("glm-5-2", "output_token", 62.857),
        ("glm-5-2-priority", "input_token", 35.0),
        ("inkling", "output_token", 57.857),
        ("deepseek-v4-pro-0813", "cache_read", 1.886),
        ("deepseek-v4-flash-0731", "output_token", 4.0),
        ("qwen35-122b-a10b-priority", "output_token", 62.858),
    ],
)
def test_current_databricks_hosted_rates(model, rate_type, expected):
    rate = get_databricks_rate("aws", model, rate_type)
    assert rate["dbu_rate"] == pytest.approx(expected)
    assert rate["status"] == "active"


def test_glm_reservation_durations_are_explicit():
    one_month = get_databricks_rate(
        "aws",
        "glm-5-2",
        "provisioned_scaling_1_month",
    )
    three_month = get_databricks_rate(
        "aws",
        "glm-5-2",
        "provisioned_scaling_3_month",
    )

    assert one_month["dbu_rate"] == pytest.approx(142.857)
    assert one_month["reservation_months"] == 1
    assert three_month["dbu_rate"] == pytest.approx(121.429)
    assert three_month["reservation_months"] == 3


def test_gcp_does_not_offer_provisioned_entry_capacity():
    with pytest.raises(FMAPIRateNotFound):
        get_databricks_rate(
            "gcp",
            "qwen35-122b-a10b",
            "provisioned_entry",
        )

    scaling = get_databricks_rate(
        "gcp",
        "qwen35-122b-a10b",
        "provisioned_scaling",
    )
    assert scaling["dbu_rate"] == pytest.approx(85.714)


def test_kimi_k3_regional_uplift_is_explicit():
    global_rate = get_databricks_rate(
        "azure",
        "kimi-k3",
        "input_token",
        processing_type="global",
    )
    regional_rate = get_databricks_rate(
        "azure",
        "kimi-k3",
        "input_token",
        processing_type="regional",
    )

    assert global_rate["dbu_rate"] == pytest.approx(42.857)
    assert regional_rate["regional_uplift_percent"] == 10
    assert regional_rate["regional_uplift_applied"] is True
    assert regional_rate["dbu_rate"] == pytest.approx(47.1427)


def test_regional_processing_is_rejected_when_not_published():
    with pytest.raises(FMAPIRateNotFound):
        get_databricks_rate(
            "aws",
            "llama-4-maverick",
            "input_token",
            processing_type="regional",
        )


def test_provisioned_entry_is_limited_to_americas_regions():
    supported = get_databricks_rate(
        "aws",
        "qwen35-122b-a10b",
        "provisioned_entry",
        region="us-east-1",
    )
    assert supported["dbu_rate"] == pytest.approx(85.714)

    with pytest.raises(FMAPIRateNotFound):
        get_databricks_rate(
            "aws",
            "qwen35-122b-a10b",
            "provisioned_entry",
            region="ap-southeast-1",
        )


def test_retired_aliases_are_hidden_but_remain_priceable_for_saved_estimates():
    with pytest.raises(FMAPIRateNotFound):
        get_databricks_rate("aws", "bge-large-en", "input_token")

    historical = get_databricks_rate(
        "aws",
        "bge-large-en",
        "input_token",
        allow_retired=True,
    )
    assert historical["status"] == "retired"
    assert historical["dbu_rate"] == pytest.approx(1.429)
    assert "bge-large-en" not in {
        model["id"] for model in active_databricks_models()
    }


@pytest.mark.parametrize(
    "provider,model,endpoint,context,rate_type,expected",
    [
        ("openai", "gpt-5-6-sol", "global", "long", "output_token", 642.857),
        ("openai", "gpt-5-4-pro", "global", "long", "batch_inference", 1142.857),
        ("anthropic", "claude-opus-4-6", "global", "all", "input_token", 71.429),
        ("google", "gemini-3-5-flash", "in_geo", "all", "batch_inference", 172.8568),
    ],
)
def test_current_proprietary_rates(
    provider,
    model,
    endpoint,
    context,
    rate_type,
    expected,
):
    rate = get_proprietary_rate(
        "aws",
        provider,
        model,
        endpoint,
        context,
        rate_type,
    )
    assert rate["dbu_rate"] == pytest.approx(expected)


def test_retired_context_matrix_is_not_used_as_fallback():
    with pytest.raises(FMAPIRateNotFound):
        get_proprietary_rate(
            "aws",
            "anthropic",
            "claude-opus-4-6",
            "global",
            "short",
            "input_token",
        )


def test_retired_context_remains_exactly_priceable_for_saved_estimates():
    historical = get_proprietary_rate(
        "aws",
        "anthropic",
        "claude-opus-4-6",
        "global",
        "long",
        "input_token",
        allow_retired=True,
    )

    assert historical["status"] == "retired"
    assert historical["dbu_rate"] > 0


def test_unpublished_batch_rate_is_rejected():
    with pytest.raises(FMAPIRateNotFound):
        get_proprietary_rate(
            "aws",
            "google",
            "gemini-3-6-flash",
            "global",
            "all",
            "batch_inference",
        )


def test_sonnet_launch_promotion_expires_to_standard_rate():
    raw_rate = {
        "dbu_rate": 42.857,
        "promotional_dbu_rate": 28.571,
        "promotion_end_date": "2026-08-31",
    }
    assert get_effective_dbu_rate(
        raw_rate,
        as_of=date(2026, 8, 31),
    ) == pytest.approx(28.571)
    assert get_effective_dbu_rate(
        raw_rate,
        as_of=date(2026, 9, 1),
    ) == pytest.approx(42.857)


def test_google_twenty_percent_promotion_is_applied():
    rate = get_proprietary_rate(
        "aws",
        "google",
        "gemini-3-6-flash",
        "global",
        "all",
        "input_token",
    )
    assert rate["list_dbu_rate"] == pytest.approx(26.786)
    assert rate["dbu_rate"] == pytest.approx(21.4288)
    assert rate["promotion_end_date"] == "2027-01-31"


def test_active_proprietary_selector_excludes_retired_models():
    providers = active_proprietary_models()
    anthropic = {model["id"] for model in providers["anthropic"]}

    assert "claude-sonnet-5" in anthropic
    assert "claude-sonnet-3-7" not in anthropic


def test_calculation_api_rejects_unsupported_combinations():
    request = SimpleNamespace(
        model="gemini-3-6-flash",
        rate_type="batch_inference",
        quantity=10,
        input_tokens_per_month=None,
        output_tokens_per_month=None,
        provisioned_hours_per_month=None,
    )

    with pytest.raises(HTTPException, match="Unsupported Foundation Model"):
        _build_fmapi_line_items_direct(
            request,
            "FMAPI_PROPRIETARY",
            "AWS",
            "us-east-1",
            "ENTERPRISE",
            provider="google",
            endpoint_type="global",
            context_length="all",
        )


def test_calculation_api_applies_databricks_regional_uplift():
    request = SimpleNamespace(
        model="kimi-k3",
        endpoint_type="regional",
        rate_type="input_token",
        quantity=2,
        input_tokens_per_month=None,
        output_tokens_per_month=None,
        provisioned_hours_per_month=None,
    )

    line_items = _build_fmapi_line_items_direct(
        request,
        "FMAPI_DATABRICKS",
        "AWS",
        "us-east-1",
        "ENTERPRISE",
    )

    assert line_items[0]["dbu_quantity"] == pytest.approx(94.2854)
    assert line_items[0]["regional_uplift_percent"] == 10


def test_calculation_api_rejects_entry_capacity_outside_americas():
    request = SimpleNamespace(
        model="qwen35-122b-a10b",
        endpoint_type="global",
        rate_type="provisioned_entry",
        quantity=10,
        input_tokens_per_month=None,
        output_tokens_per_month=None,
        provisioned_hours_per_month=None,
    )

    with pytest.raises(HTTPException, match="Provisioned Entry"):
        _build_fmapi_line_items_direct(
            request,
            "FMAPI_DATABRICKS",
            "AWS",
            "ap-southeast-1",
            "ENTERPRISE",
        )


def test_export_uses_exact_hourly_batch_rate_without_token_fallback():
    item = SimpleNamespace(
        workload_type="FMAPI_PROPRIETARY",
        fmapi_provider="openai",
        fmapi_model="gpt-5-6-sol",
        fmapi_endpoint_type="global",
        fmapi_context_length="short",
        fmapi_rate_type="batch_inference",
    )

    rate, found = _get_fmapi_dbu_per_million(item, "aws")
    assert found is True
    assert rate == pytest.approx(214.286)
    assert _is_fmapi_hourly(item, "aws") is True


def test_export_applies_regional_uplift_and_region_eligibility():
    regional_item = SimpleNamespace(
        workload_type="FMAPI_DATABRICKS",
        fmapi_model="kimi-k3",
        fmapi_endpoint_type="regional",
        fmapi_rate_type="input_token",
    )
    rate, found = _get_fmapi_dbu_per_million(
        regional_item,
        "aws",
        "us-east-1",
    )
    assert found is True
    assert rate == pytest.approx(47.1427)

    unsupported_entry = SimpleNamespace(
        workload_type="FMAPI_DATABRICKS",
        fmapi_model="qwen35-122b-a10b",
        fmapi_endpoint_type="global",
        fmapi_rate_type="provisioned_entry",
    )
    rate, found = _get_fmapi_dbu_per_million(
        unsupported_entry,
        "aws",
        "ap-southeast-1",
    )
    assert found is False
    assert rate == 0


def test_generated_catalogs_match_canonical_source():
    catalog = _load_catalog_script()
    outputs = catalog.generate(date(2026, 8, 27))

    for path, expected in outputs.items():
        assert path.read_text() == expected


def test_csv_contains_only_active_list_prices():
    catalog = _load_catalog_script()
    outputs = catalog.generate(date(2026, 8, 27))
    databricks_rows = list(csv.DictReader(io.StringIO(outputs[catalog.DB_CSV])))
    rows = list(csv.DictReader(io.StringIO(outputs[catalog.PROP_CSV])))

    assert all(row["model"] != "bge-large-en" for row in databricks_rows)
    assert all(row["model"] != "claude-sonnet-3-7" for row in rows)
    sonnet_input = next(
        row for row in rows
        if row["cloud"] == "AWS"
        and row["model"] == "claude-sonnet-5"
        and row["endpoint_type"] == "global"
        and row["context_length"] == "all"
        and row["rate_type"] == "input_token"
    )
    assert float(sonnet_input["dbu_rate"]) == pytest.approx(42.857)


def test_frontend_uses_dynamic_exact_rate_options_and_no_fallback_prices():
    form_source = WORKLOAD_FORM.read_text()
    calculator_source = CALCULATOR.read_text()
    store_source = FRONTEND_STORE.read_text()

    assert "getAvailableDatabricksRateTypes" in form_source
    assert "rate.status !== 'retired'" in form_source
    assert "Regional processing (+" in form_source
    assert "promotion_label" in form_source
    assert "fmapiPropRateType === 'batch_inference'" in calculator_source
    assert "if (dbxDbuRate === null) dbxDbuRate = 0" in calculator_source
    assert "if (propDbuRate === null) propDbuRate = 0" in calculator_source
    assert "const provider = wType === 'FMAPI_PROPRIETARY'" in calculator_source
    assert "endpoint_type: lineItem.fmapi_endpoint_type || 'global'" in store_source
