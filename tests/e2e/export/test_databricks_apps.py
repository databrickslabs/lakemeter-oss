"""E2E tests: Databricks Apps — API calculation vs Excel export verification.

Tests:
  - 6 cloud/region configs
  - 2 sizes (medium, large)
  - default 730h always-on + custom hours
  = ~18 test cases

Run: pytest tests/e2e/export/test_databricks_apps.py -v
"""
import pytest
from tests.e2e.helpers.test_data import (
    ESTIMATE_CONFIGS, DATABRICKS_APPS_SIZES, config_id,
)
from tests.e2e.helpers.assertions import assert_costs_match, save_test_results
from tests.e2e.helpers.excel_parser import parse_estimate_excel

USAGE_CONFIGS = [
    {"hours_per_month": 730},  # always-on (default)
    {"hours_per_month": 200},  # partial usage
]


def _generate_params():
    params = []
    for cfg in ESTIMATE_CONFIGS:
        for size in DATABRICKS_APPS_SIZES:
            for usage in USAGE_CONFIGS:
                hrs = usage["hours_per_month"]
                test_id = f"{config_id(cfg)}-{size}-{hrs}h"
                params.append(pytest.param(cfg, size, usage, id=test_id))
    return params


@pytest.fixture(scope="module")
def results():
    data = []
    yield data
    save_test_results(data, "test_results/e2e_databricks_apps.json")


class TestDatabricksAppsCalculation:
    """Verify Databricks Apps API calculation returns valid results."""

    @pytest.mark.parametrize("cfg, size, usage", _generate_params())
    def test_calculation_succeeds(self, e2e_client, cfg, size, usage, results):
        result = e2e_client.calculate_databricks_apps(
            cloud=cfg["cloud"], region=cfg["region"], tier=cfg["tier"],
            size=size, usage=usage,
        )
        assert "dbu_calculation" in result
        assert "total_cost" in result
        dbu_calc = result["dbu_calculation"]
        assert dbu_calc["dbu_per_hour"] > 0
        assert dbu_calc["dbu_per_month"] >= 0
        assert result["total_cost"]["cost_per_month"] >= 0

        # Verify DBU rate matches size
        expected_rate = 0.5 if size == "medium" else 1.0
        assert dbu_calc["dbu_per_hour"] == expected_rate, \
            f"Expected {expected_rate} DBU/hr for {size}, got {dbu_calc['dbu_per_hour']}"

        results.append({
            "config": config_id(cfg), "size": size,
            "hours": usage["hours_per_month"],
            "dbu_per_month": dbu_calc["dbu_per_month"],
            "total_cost": result["total_cost"]["cost_per_month"],
            "status": "PASS",
        })


class TestDatabricksAppsExcelExport:
    """Create estimates with Databricks Apps workloads, export, verify."""

    @pytest.mark.parametrize("cfg", ESTIMATE_CONFIGS, ids=[config_id(c) for c in ESTIMATE_CONFIGS])
    def test_export_sizes(self, e2e_client, cfg):
        cloud, region, tier = cfg["cloud"], cfg["region"], cfg["tier"]

        estimate = e2e_client.create_estimate(
            name=f"E2E-DatabricksApps-{config_id(cfg)}",
            cloud=cloud, region=region, tier=tier,
        )
        eid = estimate["estimate_id"]

        calc_results = []
        for size in DATABRICKS_APPS_SIZES:
            api_result = e2e_client.calculate_databricks_apps(
                cloud=cloud, region=region, tier=tier, size=size,
                usage={"hours_per_month": 730},
            )
            e2e_client.add_line_item(eid, {
                "workload_name": f"DatabricksApps-{size}",
                "workload_type": "DATABRICKS_APPS",
                "databricks_apps_size": size,
                "hours_per_month": 730,
            })
            calc_results.append(api_result)

        # Export and verify
        excel_buf = e2e_client.export_excel(eid)
        rows = parse_estimate_excel(excel_buf)

        assert len(rows) >= len(DATABRICKS_APPS_SIZES), \
            f"Expected at least {len(DATABRICKS_APPS_SIZES)} rows, got {len(rows)}"

        for i, (api_res, row) in enumerate(zip(calc_results, rows)):
            assert_costs_match(api_res, row, f"DatabricksApps-{DATABRICKS_APPS_SIZES[i]}")
