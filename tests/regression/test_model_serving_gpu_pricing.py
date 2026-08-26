"""Regression coverage for Model Serving GPU replica pricing."""

from types import SimpleNamespace

import pytest

from app.routes.calculate.schemas import ModelServingCalculationRequest
from app.routes.export.calculations import _calculate_dbu_per_hour
from app.services.model_serving_pricing import (
    calculate_model_serving_dbu_per_hour,
    get_billing_capacity_units,
)


class _Result:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _PricingDb:
    def execute(self, query, params):
        query_text = str(query)
        if "sync_product_serverless_rates" in query_text:
            rate = 1.0 if params["gpu_type"].lower().startswith("cpu") else 20.0
            return _Result(SimpleNamespace(dbu_rate=rate))
        if "sync_pricing_dbu_rates" in query_text:
            return _Result(SimpleNamespace(price_per_dbu=0.1))
        raise AssertionError(f"Unexpected query: {query_text}")


def _request(**overrides):
    data = {
        "cloud": "aws",
        "region": "us-east-1",
        "tier": "PREMIUM",
        "gpu_type": "gpu_medium_a10g_1x",
        "scale_out": "small",
        "hours_per_month": 10,
    }
    data.update(overrides)
    return ModelServingCalculationRequest(**data)


def _patch_validators(monkeypatch):
    from app.routes.calculate import model_serving_calc

    monkeypatch.setattr(model_serving_calc, "validate_cloud", lambda *_: None)
    monkeypatch.setattr(model_serving_calc, "validate_region", lambda *_: None)
    monkeypatch.setattr(model_serving_calc, "validate_tier", lambda *_: None)
    monkeypatch.setattr(
        model_serving_calc,
        "get_product_type_for_pricing",
        lambda *_: "SERVERLESS_REAL_TIME_INFERENCE",
    )
    return model_serving_calc


@pytest.mark.parametrize(
    ("scale_out", "custom_concurrency", "expected_replicas", "expected_dbu_hr"),
    [
        ("small", None, 1, 20),
        ("medium", None, 3, 60),
        ("large", None, 10, 200),
        ("custom", 20, 5, 100),
    ],
)
def test_gpu_api_bills_one_replica_per_four_concurrency(
    monkeypatch,
    scale_out,
    custom_concurrency,
    expected_replicas,
    expected_dbu_hr,
):
    model_serving_calc = _patch_validators(monkeypatch)
    data = model_serving_calc.calculate_model_serving_cost(
        _request(
            scale_out=scale_out,
            custom_concurrency=custom_concurrency,
        ),
        db=_PricingDb(),
    )["data"]

    assert data["dbu_calculation"]["gpu_replicas"] == expected_replicas
    assert data["dbu_calculation"]["concurrency_per_gpu_replica"] == 4
    assert data["dbu_calculation"]["dbu_per_hour"] == expected_dbu_hr
    assert data["dbu_calculation"]["dbu_per_month"] == expected_dbu_hr * 10
    assert data["total_cost"]["cost_per_month"] == expected_dbu_hr
    assert (
        f"= {expected_replicas:g} GPU replicas"
        in data["dbu_calculation"]["calculation"]
    )


def test_cpu_api_keeps_per_concurrency_pricing(monkeypatch):
    model_serving_calc = _patch_validators(monkeypatch)
    data = model_serving_calc.calculate_model_serving_cost(
        _request(gpu_type="cpu"),
        db=_PricingDb(),
    )["data"]

    assert data["dbu_calculation"]["gpu_replicas"] is None
    assert data["dbu_calculation"]["concurrency_per_gpu_replica"] is None
    assert data["dbu_calculation"]["billing_capacity_units"] == 4
    assert data["dbu_calculation"]["dbu_per_hour"] == 4


def test_shared_capacity_conversion_handles_current_and_future_cpu_types():
    assert get_billing_capacity_units("gpu_medium_a10g_1x", 12) == 3
    assert get_billing_capacity_units("MULTIGPU_MEDIUM", 12) == 3
    assert get_billing_capacity_units("cpu", 12) == 12
    assert get_billing_capacity_units("CPU_LARGE", 12) == 12
    assert calculate_model_serving_dbu_per_hour(20, "GPU_MEDIUM", 12) == 60


def test_excel_export_uses_gpu_replicas_but_keeps_cpu_concurrency():
    common = {
        "workload_type": "MODEL_SERVING",
        "model_serving_concurrency": 12,
        "workload_config": {},
    }
    gpu_item = SimpleNamespace(
        **common,
        model_serving_gpu_type="gpu_medium_a10g_1x",
    )
    cpu_item = SimpleNamespace(
        **common,
        model_serving_gpu_type="cpu",
    )

    gpu_dbu_per_hour, gpu_warnings = _calculate_dbu_per_hour(
        gpu_item, "aws"
    )
    cpu_dbu_per_hour, cpu_warnings = _calculate_dbu_per_hour(
        cpu_item, "aws"
    )

    assert gpu_dbu_per_hour == 60
    assert cpu_dbu_per_hour == 12
    assert gpu_warnings == []
    assert cpu_warnings == []
