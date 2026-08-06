from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routes.calculate import (
    all_purpose,
    dbsql_calc,
    dlt_calc,
    jobs,
    lakeflow_connect_calc,
    vector_search_calc,
)
from app.routes.calculate.jobs import normalize_usage_params
from app.routes.calculate.schemas import (
    AllPurposeClassicCalculationRequest,
    AllPurposeServerlessCalculationRequest,
    DBSQLClassicProCalculationRequest,
    DBSQLServerlessCalculationRequest,
    DLTServerlessCalculationRequest,
    JobsServerlessCalculationRequest,
    LakeflowConnectCalculationRequest,
    VectorSearchCalculationRequest,
)


def _calculation_row(params):
    hours = params["p16"]
    if hours is None:
        hours = (
            params["p13"]
            * params["p14"]
            / 60
            * params["p15"]
        )
    dbu_per_hour = 2.0
    dbu_per_month = dbu_per_hour * hours
    dbu_price = 0.5
    dbu_cost = dbu_per_month * dbu_price
    return SimpleNamespace(
        hours_per_month=hours,
        dbu_per_hour=dbu_per_hour,
        dbu_per_month=dbu_per_month,
        dbu_price=dbu_price,
        dbu_cost_per_month=dbu_cost,
        driver_vm_cost_per_month=0,
        total_worker_vm_cost_per_month=0,
        driver_vm_cost_per_hour=0,
        worker_vm_cost_per_hour=0,
        total_vm_cost_per_hour=0,
        vm_cost_per_month=0,
        cost_per_month=dbu_cost,
    )


@pytest.fixture(autouse=True)
def _patch_route_dependencies(monkeypatch):
    for module in (
        all_purpose,
        dbsql_calc,
        dlt_calc,
        jobs,
        lakeflow_connect_calc,
        vector_search_calc,
    ):
        monkeypatch.setattr(
            module,
            "call_calculate_line_item_costs",
            lambda _db, params: _calculation_row(params),
        )
        monkeypatch.setattr(
            module,
            "get_product_type_for_pricing",
            lambda *_args, **_kwargs: "TEST_SKU",
        )

    monkeypatch.setattr(
        all_purpose,
        "_validate_classic_inputs",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        all_purpose,
        "_validate_serverless_inputs",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        dlt_calc,
        "_validate_serverless_inputs",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        jobs,
        "_validate_serverless_inputs",
        lambda *_args, **_kwargs: None,
    )

    for module in (dbsql_calc, lakeflow_connect_calc, vector_search_calc):
        monkeypatch.setattr(
            module, "validate_cloud", lambda *_args, **_kwargs: None
        )
        monkeypatch.setattr(
            module, "validate_region", lambda *_args, **_kwargs: None
        )
        monkeypatch.setattr(
            module, "validate_tier", lambda *_args, **_kwargs: None
        )

    monkeypatch.setattr(
        dbsql_calc,
        "validate_warehouse_type",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        dbsql_calc,
        "validate_warehouse_size",
        lambda *_args, **_kwargs: None,
    )


DAILY_MONTHLY_CASES = [
    pytest.param(
        all_purpose.calculate_all_purpose_classic_cost,
        AllPurposeClassicCalculationRequest,
        {
            "cloud": "AWS",
            "region": "us-east-1",
            "tier": "PREMIUM",
            "driver_node_type": "i3.xlarge",
            "worker_node_type": "i3.xlarge",
            "num_workers": 2,
        },
        id="all-purpose-classic",
    ),
    pytest.param(
        all_purpose.calculate_all_purpose_serverless_cost,
        AllPurposeServerlessCalculationRequest,
        {
            "cloud": "AWS",
            "region": "us-east-1",
            "tier": "PREMIUM",
        },
        id="all-purpose-serverless",
    ),
    pytest.param(
        dbsql_calc.calculate_dbsql_classic_pro_cost,
        DBSQLClassicProCalculationRequest,
        {
            "cloud": "AWS",
            "region": "us-east-1",
            "tier": "PREMIUM",
            "warehouse_type": "PRO",
            "warehouse_size": "Medium",
        },
        id="dbsql-classic-pro",
    ),
    pytest.param(
        dbsql_calc.calculate_dbsql_serverless_cost,
        DBSQLServerlessCalculationRequest,
        {
            "cloud": "AWS",
            "region": "us-east-1",
            "tier": "PREMIUM",
            "warehouse_size": "Medium",
        },
        id="dbsql-serverless",
    ),
    pytest.param(
        vector_search_calc.calculate_vector_search_cost,
        VectorSearchCalculationRequest,
        {
            "cloud": "AWS",
            "region": "us-east-1",
            "tier": "PREMIUM",
            "mode": "standard",
            "num_vectors_millions": 2,
        },
        id="vector-search",
    ),
]


@pytest.mark.parametrize(
    ("calculate", "request_type", "base_payload"),
    DAILY_MONTHLY_CASES,
)
def test_hours_per_day_matches_equivalent_hours_per_month(
    calculate,
    request_type,
    base_payload,
):
    daily_request = request_type(
        **base_payload,
        hours_per_day=8,
        days_per_month=30,
    )
    monthly_request = request_type(
        **base_payload,
        hours_per_month=240,
    )

    daily_result = calculate(daily_request, db=object())
    monthly_result = calculate(monthly_request, db=object())

    assert daily_result["success"] is True
    assert monthly_result["success"] is True
    assert daily_result["data"]["usage"]["hours_per_month"] == 240
    assert monthly_result["data"]["usage"]["hours_per_month"] == 240
    assert daily_result["data"]["total_cost"] == monthly_result["data"]["total_cost"]
    assert daily_request.hours_per_month is None


RUN_USAGE_CASES = [
    pytest.param(
        jobs.calculate_jobs_serverless_cost,
        JobsServerlessCalculationRequest,
        {},
        lambda result: result["data"]["usage"]["hours_per_month"],
        id="jobs-serverless",
    ),
    pytest.param(
        dlt_calc.calculate_dlt_serverless_cost,
        DLTServerlessCalculationRequest,
        {"dlt_edition": "ADVANCED"},
        lambda result: result["data"]["usage"]["hours_per_month"],
        id="dlt-serverless",
    ),
    pytest.param(
        lakeflow_connect_calc.calculate_lakeflow_connect_cost,
        LakeflowConnectCalculationRequest,
        {},
        lambda result: result["data"]["pipeline"]["hours_per_month"],
        id="lakeflow-connect",
    ),
]


@pytest.mark.parametrize(
    ("calculate", "request_type", "extra_payload", "get_hours"),
    RUN_USAGE_CASES,
)
def test_run_usage_matches_equivalent_monthly_hours(
    calculate,
    request_type,
    extra_payload,
    get_hours,
):
    base_payload = {
        "cloud": "AWS",
        "region": "us-east-1",
        "tier": "PREMIUM",
        **extra_payload,
    }
    run_request = request_type(
        **base_payload,
        runs_per_day=2,
        avg_runtime_minutes=30,
        days_per_month=20,
    )
    monthly_request = request_type(
        **base_payload,
        hours_per_month=20,
    )

    run_result = calculate(run_request, db=object())
    monthly_result = calculate(monthly_request, db=object())

    assert run_result["success"] is True
    assert monthly_result["success"] is True
    assert get_hours(run_result) == 20
    assert get_hours(monthly_result) == 20
    assert run_result["data"]["total_cost"] == monthly_result["data"]["total_cost"]


def test_daily_and_monthly_inputs_conflict_before_normalization():
    request = SimpleNamespace(
        hours_per_day=8,
        days_per_month=30,
        hours_per_month=240,
    )

    with pytest.raises(HTTPException) as exc_info:
        normalize_usage_params(request, mode="daily_or_monthly")

    assert exc_info.value.detail["code"] == "CONFLICTING_USAGE_PARAMETERS"


def test_partial_run_inputs_are_rejected():
    request = SimpleNamespace(
        runs_per_day=2,
        avg_runtime_minutes=None,
        days_per_month=30,
        hours_per_month=None,
    )

    with pytest.raises(HTTPException) as exc_info:
        normalize_usage_params(request, mode="runs_or_monthly")

    assert exc_info.value.detail["code"] == "INCOMPLETE_USAGE_PARAMETERS"
