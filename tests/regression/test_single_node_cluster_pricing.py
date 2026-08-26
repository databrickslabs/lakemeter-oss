from pathlib import Path

import pytest
from pydantic import ValidationError

from app.routes.calculate.schemas import (
    AllPurposeClassicCalculationRequest,
    DLTClassicCalculationRequest,
    JobsClassicCalculationRequest,
)
from app.routes.export import _calculate_dbu_per_hour
from app.schemas.line_item import (
    LineItemUpdate,
    validate_compute_workload_config,
)
from tests.export.cross_workload.conftest import (
    make_line_item as make_export_line_item,
)
from tests.export.cross_workload.excel_helpers import (
    COL_DRIVER_TIER,
    COL_NUM_WORKERS,
    COL_WORKER,
    COL_WORKER_TIER,
    COL_WORKER_VM_HR,
    find_row_by_name,
    generate_xlsx,
)
from tests.regression.conftest import make_item


ROOT = Path(__file__).resolve().parents[2]
WORKLOAD_FORM = ROOT / "frontend" / "src" / "components" / "WorkloadForm.tsx"
COST_CALCULATION = ROOT / "frontend" / "src" / "utils" / "costCalculation.ts"
CALCULATOR = ROOT / "frontend" / "src" / "pages" / "Calculator.tsx"


def test_missing_worker_type_does_not_add_hidden_fallback_dbus():
    item = make_item(
        workload_type="JOBS",
        driver_node_type="i3.xlarge",
        worker_node_type=None,
        num_workers=2,
        serverless_enabled=False,
    )

    dbu_per_hour, warnings = _calculate_dbu_per_hour(item, "aws")

    assert dbu_per_hour == pytest.approx(1.0)
    assert warnings == []


def test_selected_unknown_worker_keeps_explicit_legacy_fallback():
    item = make_item(
        workload_type="JOBS",
        driver_node_type="i3.xlarge",
        worker_node_type="unknown.worker",
        num_workers=2,
        serverless_enabled=False,
    )

    dbu_per_hour, warnings = _calculate_dbu_per_hour(item, "aws")

    assert dbu_per_hour == pytest.approx(2.0)
    assert warnings == [
        "Worker DBU rate not found for unknown.worker, using 0.5"
    ]


@pytest.mark.parametrize(
    "workload_type",
    ["JOBS", "ALL_PURPOSE", "DLT"],
)
def test_compute_config_allows_true_single_node(workload_type):
    validate_compute_workload_config(
        workload_type,
        "i3.xlarge",
        None,
        0,
    )


def test_compute_config_requires_worker_type_when_workers_are_present():
    with pytest.raises(
        ValueError,
        match="worker_node_type is required when num_workers is greater than 0",
    ):
        validate_compute_workload_config(
            "JOBS",
            "i3.xlarge",
            None,
            2,
        )


@pytest.mark.parametrize(
    "request_model,extra",
    [
        (JobsClassicCalculationRequest, {}),
        (AllPurposeClassicCalculationRequest, {}),
        (DLTClassicCalculationRequest, {"dlt_edition": "CORE"}),
    ],
)
def test_classic_calculation_requests_allow_zero_workers(request_model, extra):
    request = request_model(
        cloud="AWS",
        region="us-east-1",
        tier="PREMIUM",
        driver_node_type="i3.xlarge",
        worker_node_type=None,
        num_workers=0,
        hours_per_month=10,
        **extra,
    )

    assert request.num_workers == 0
    assert request.worker_node_type is None


def test_classic_input_validation_skips_worker_lookup_for_single_node(
    monkeypatch,
):
    from app.routes.calculate import jobs

    checked_instances = []

    monkeypatch.setattr(jobs, "validate_cloud", lambda *_: None)
    monkeypatch.setattr(jobs, "validate_region", lambda *_: None)
    monkeypatch.setattr(jobs, "validate_tier", lambda *_: None)
    monkeypatch.setattr(jobs, "validate_pricing_tier", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(jobs, "validate_payment_option", lambda *_: None)
    monkeypatch.setattr(
        jobs,
        "validate_pricing_payment_combination",
        lambda *_: None,
    )
    monkeypatch.setattr(
        jobs,
        "validate_instance_type",
        lambda _cloud, instance_type, _db: checked_instances.append(
            instance_type
        ),
    )
    request = JobsClassicCalculationRequest(
        cloud="AWS",
        region="us-east-1",
        tier="PREMIUM",
        driver_node_type="i3.xlarge",
        worker_node_type=None,
        num_workers=0,
        hours_per_month=10,
    )

    jobs._validate_classic_inputs(request, object())

    assert checked_instances == ["i3.xlarge"]


@pytest.mark.parametrize(
    "request_model,extra",
    [
        (JobsClassicCalculationRequest, {}),
        (AllPurposeClassicCalculationRequest, {}),
        (DLTClassicCalculationRequest, {"dlt_edition": "CORE"}),
    ],
)
def test_classic_calculation_requests_reject_untyped_workers(
    request_model,
    extra,
):
    with pytest.raises(ValidationError, match="worker_node_type is required"):
        request_model(
            cloud="AWS",
            region="us-east-1",
            tier="PREMIUM",
            driver_node_type="i3.xlarge",
            worker_node_type=None,
            num_workers=2,
            hours_per_month=10,
            **extra,
        )


def test_line_item_schema_preserves_zero_workers():
    assert LineItemUpdate(num_workers=0).num_workers == 0


def test_single_node_excel_omits_worker_configuration():
    item = make_export_line_item(
        workload_type="JOBS",
        workload_name="Single Node Export",
        driver_node_type="i3.xlarge",
        worker_node_type="i3.xlarge",
        num_workers=0,
        driver_pricing_tier="on_demand",
        worker_pricing_tier="spot",
        hours_per_month=730,
    )

    worksheet = generate_xlsx(line_items=[item]).active
    row = find_row_by_name(worksheet, "Single Node Export")

    assert worksheet.cell(row=row, column=COL_NUM_WORKERS).value == 0
    assert worksheet.cell(row=row, column=COL_DRIVER_TIER).value == "On-Demand"
    assert worksheet.cell(row=row, column=COL_WORKER).value == "-"
    assert worksheet.cell(row=row, column=COL_WORKER_TIER).value == "-"
    assert worksheet.cell(row=row, column=COL_WORKER_VM_HR).value == 0


def test_frontend_preserves_and_accepts_zero_worker_count():
    source = WORKLOAD_FORM.read_text()

    assert source.count("lineItem.num_workers ?? 2") == 2
    assert "min={0}" in source
    assert "set worker count to 0 for single node" in source
    assert "form.num_workers === 0" in source


def test_frontend_only_falls_back_for_selected_instances():
    cost_source = COST_CALCULATION.read_text()
    calculator_source = CALCULATOR.read_text()

    assert (
        "let workerDBURate = item.worker_node_type ? 0.5 : 0"
        in cost_source
    )
    assert (
        "let workerDBURate = effectiveItem.worker_node_type ? 0.5 : 0"
        in calculator_source
    )
    assert calculator_source.count("Single node — driver only") == 2
