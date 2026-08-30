from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.routes.calculate import databricks_apps_calc
from app.routes.calculate.databricks_apps_calc import (
    DATABRICKS_APPS_SKU,
    calculate_databricks_apps_cost,
)
from app.routes.calculate.helpers import get_sku_type as get_calculation_sku_type
from app.routes.calculate.schemas import DatabricksAppsCalculationRequest
from app.routes.export.calculations import (
    _calculate_dbu_per_hour,
    _calculate_hours_per_month,
)
from app.routes.export.helpers import _get_workload_config_details
from app.routes.export.pricing import _get_sku_type as get_export_sku_type
from app.schemas.line_item import LineItemUpdate
from app.services.lakebase_queries import get_sku_type as get_service_sku_type


class _Result:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _PricingDb:
    PRICES = {
        "JOBS_COMPUTE": 0.15,
        DATABRICKS_APPS_SKU: 0.75,
    }

    def __init__(self):
        self.product_types = []

    def execute(self, statement, params):
        sql = str(statement)
        if "get_product_type_for_pricing" in sql:
            return _Result(SimpleNamespace(product_type="JOBS_COMPUTE"))

        product_type = params["pt"]
        self.product_types.append(product_type)
        return _Result(
            SimpleNamespace(price_per_dbu=self.PRICES[product_type])
        )


@pytest.fixture(autouse=True)
def _patch_validation(monkeypatch):
    monkeypatch.setattr(
        databricks_apps_calc, "validate_cloud", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        databricks_apps_calc, "validate_region", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        databricks_apps_calc, "validate_tier", lambda *_args, **_kwargs: None
    )


@pytest.mark.parametrize(
    ("size", "expected_dbu_per_app_hour"),
    [("medium", 0.5), ("large", 1.0)],
)
@pytest.mark.parametrize("num_apps", [1, 6])
def test_calculate_and_export_use_apps_serverless_sku(
    size, expected_dbu_per_app_hour, num_apps
):
    db = _PricingDb()
    hours_per_month = 730
    expected_dbu_per_hour = expected_dbu_per_app_hour * num_apps

    response = calculate_databricks_apps_cost(
        DatabricksAppsCalculationRequest(
            cloud="AWS",
            region="us-east-1",
            tier="PREMIUM",
            size=size,
            num_apps=num_apps,
            hours_per_month=hours_per_month,
        ),
        db=db,
    )
    api_data = response["data"]

    export_item = SimpleNamespace(
        workload_type="DATABRICKS_APPS",
        databricks_apps_size=size,
        databricks_apps_num_apps=num_apps,
        runs_per_day=None,
        avg_runtime_minutes=None,
        hours_per_month=hours_per_month,
    )
    export_sku = get_export_sku_type(export_item, "aws")
    export_dbu_per_hour, warnings = _calculate_dbu_per_hour(
        export_item, "aws", "PREMIUM"
    )
    export_hours = _calculate_hours_per_month(export_item)
    export_cost = export_dbu_per_hour * export_hours * 0.75

    assert api_data["sku_type"] == DATABRICKS_APPS_SKU
    assert export_sku == DATABRICKS_APPS_SKU
    assert db.product_types == [DATABRICKS_APPS_SKU]
    assert api_data["configuration"]["num_apps"] == num_apps
    assert (
        api_data["dbu_calculation"]["dbu_per_app_hour"]
        == expected_dbu_per_app_hour
    )
    assert api_data["dbu_calculation"]["dbu_per_hour"] == expected_dbu_per_hour
    assert export_dbu_per_hour == expected_dbu_per_hour
    assert f"Apps: {num_apps}" in _get_workload_config_details(export_item)
    assert warnings == []
    assert api_data["total_cost"]["cost_per_month"] == pytest.approx(
        export_cost
    )


def test_apps_count_must_be_at_least_one():
    with pytest.raises(ValidationError):
        DatabricksAppsCalculationRequest(
            cloud="AWS",
            region="us-east-1",
            tier="PREMIUM",
            num_apps=0,
        )
    with pytest.raises(ValidationError):
        LineItemUpdate(databricks_apps_num_apps=0)


def test_frontend_sends_and_calculates_apps_count():
    repository_root = Path(__file__).parents[2]
    cost_source = (
        repository_root / "frontend/src/utils/costCalculation.ts"
    ).read_text()
    store_source = (
        repository_root / "frontend/src/store/useStore.ts"
    ).read_text()
    form_source = (
        repository_root / "frontend/src/components/WorkloadForm.tsx"
    ).read_text()

    assert "calculateDatabricksAppsUsage" in cost_source
    assert "num_apps: lineItem.databricks_apps_num_apps ?? 1" in store_source
    assert "Number of Apps" in form_source
    assert "data.databricks_apps_num_apps" in form_source


@pytest.mark.parametrize(
    "resolver",
    [get_calculation_sku_type, get_service_sku_type],
)
def test_python_sku_resolvers_reject_unknown_workloads(resolver):
    with pytest.raises(ValueError, match="Unsupported workload type"):
        resolver("NOT_A_WORKLOAD")


@pytest.mark.parametrize(
    "relative_path",
    [
        "scripts/functions/01_Utility_Functions.py",
        "etl/lakebase_setup/functions/01_Utility_Functions.py",
    ],
)
def test_sql_sku_resolvers_map_apps_and_reject_unknown_workloads(
    relative_path,
):
    repository_root = Path(__file__).parents[2]
    source = (repository_root / relative_path).read_text()

    assert "WHEN 'DATABRICKS_APPS' THEN" in source
    assert "v_product_type := 'ALL_PURPOSE_SERVERLESS_COMPUTE';" in source
    assert "RAISE EXCEPTION 'Unsupported workload type: %'" in source
