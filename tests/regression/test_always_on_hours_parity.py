"""Regression coverage for always-on monthly-hours defaults."""
from pathlib import Path

import pytest

from app.routes.export.calculations import _calculate_hours_per_month
from tests.parity.frontend_calc import fe_hours_per_month
from tests.regression.conftest import make_item


ROOT = Path(__file__).resolve().parents[2]
ALWAYS_ON_WORKLOADS = (
    "VECTOR_SEARCH",
    "MODEL_SERVING",
    "LAKEBASE",
    "DATABRICKS_APPS",
    "LAKEFLOW_CONNECT",
)


@pytest.mark.parametrize("workload_type", ALWAYS_ON_WORKLOADS)
def test_missing_usage_defaults_to_730_hours_everywhere(workload_type):
    item = make_item(workload_type=workload_type, workload_config={})
    assert _calculate_hours_per_month(item) == 730
    assert fe_hours_per_month(workload_type=workload_type) == 730


@pytest.mark.parametrize(
    "workload_type",
    ("VECTOR_SEARCH", "MODEL_SERVING", "DATABRICKS_APPS", "LAKEFLOW_CONNECT"),
)
@pytest.mark.parametrize("hours_per_month", (0, 160))
def test_explicit_hours_override_always_on_default(
    workload_type,
    hours_per_month,
):
    item = make_item(
        workload_type=workload_type,
        hours_per_month=hours_per_month,
    )
    assert _calculate_hours_per_month(item) == hours_per_month
    assert fe_hours_per_month(
        workload_type=workload_type,
        hours_per_month=hours_per_month,
    ) == hours_per_month


def test_run_based_usage_precedes_legacy_stored_default():
    item = make_item(
        workload_type="MODEL_SERVING",
        runs_per_day=2,
        avg_runtime_minutes=60,
        days_per_month=10,
        hours_per_month=730,
    )
    assert _calculate_hours_per_month(item) == 20
    assert fe_hours_per_month(
        workload_type=item.workload_type,
        runs_per_day=item.runs_per_day,
        avg_runtime_minutes=item.avg_runtime_minutes,
        days_per_month=item.days_per_month,
        hours_per_month=item.hours_per_month,
    ) == 20


def test_frontend_cost_paths_use_shared_hours_resolver():
    utility = (
        ROOT / "frontend/src/utils/costCalculation.ts"
    ).read_text(encoding="utf-8")
    calculator = (
        ROOT / "frontend/src/pages/Calculator.tsx"
    ).read_text(encoding="utf-8")
    store = (
        ROOT / "frontend/src/store/useStore.ts"
    ).read_text(encoding="utf-8")

    assert "export function calculateHoursPerMonth" in utility
    assert "const hoursPerMonth = calculateHoursPerMonth(item)" in utility
    assert calculator.count("calculateHoursPerMonth(effectiveItem)") == 2
    assert "const hoursPerMonth = calculateHoursPerMonth(item)" in calculator
    assert store.count("hours_per_month: calculateHoursPerMonth(lineItem)") == 4
