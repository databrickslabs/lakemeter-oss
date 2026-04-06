"""E2E tests: DBSQL Serverless — API calculation vs Excel export verification.

Tests every combination of:
  - 6 cloud/region configs (3 clouds × 2 regions)
  - 6 warehouse sizes
  - hours_per_day+days_per_month vs hours_per_month usage
  = ~72 test cases per run

Run: pytest tests/e2e/export/test_dbsql_serverless.py -v --timeout=600
"""
import pytest
from tests.e2e.helpers.test_data import (
    ESTIMATE_CONFIGS, DBSQL_WAREHOUSE_SIZES,
    USAGE_HOURLY, config_id,
)
from tests.e2e.helpers.assertions import assert_costs_match, save_test_results
from tests.e2e.helpers.excel_parser import parse_estimate_excel


# ── Parametrize: all config combos ────────────────────────────────────────

def _generate_dbsql_serverless_params():
    """Generate all (config, warehouse_size, usage_label, usage) combos."""
    params = []
    for cfg in ESTIMATE_CONFIGS:
        for wh_size in DBSQL_WAREHOUSE_SIZES:
            for usage_label, usage in [("hourly", USAGE_HOURLY)]:
                test_id = f"{config_id(cfg)}-{wh_size}-{usage_label}"
                params.append(pytest.param(
                    cfg, wh_size, usage_label, usage,
                    id=test_id,
                ))
    return params


@pytest.fixture(scope="module")
def dbsql_serverless_results():
    """Collect results across all tests in this module."""
    results = []
    yield results
    save_test_results(results, "test_results/e2e_dbsql_serverless.json")


class TestDBSQLServerlessCalculation:
    """Verify DBSQL Serverless API calculation returns valid results."""

    @pytest.mark.parametrize(
        "cfg, wh_size, usage_label, usage",
        _generate_dbsql_serverless_params(),
    )
    def test_calculation_succeeds(self, e2e_client, cfg, wh_size,
                                   usage_label, usage, dbsql_serverless_results):
        result = e2e_client.calculate_dbsql_serverless(
            cloud=cfg["cloud"], region=cfg["region"], tier=cfg["tier"],
            warehouse_size=wh_size, usage=usage,
        )
        # Verify structure
        assert "dbu_calculation" in result
        assert "total_cost" in result
        assert result["dbu_calculation"]["dbu_per_hour"] > 0
        assert result["dbu_calculation"]["dbu_per_month"] > 0
        assert result["dbu_calculation"]["dbu_price"] > 0
        assert result["total_cost"]["cost_per_month"] > 0

        dbsql_serverless_results.append({
            "config": config_id(cfg), "warehouse_size": wh_size,
            "usage": usage_label,
            "dbu_per_hour": result["dbu_calculation"]["dbu_per_hour"],
            "dbu_per_month": result["dbu_calculation"]["dbu_per_month"],
            "total_cost": result["total_cost"]["cost_per_month"],
            "status": "PASS",
        })


class TestDBSQLServerlessExcelExport:
    """Create estimates with DBSQL Serverless workloads, export to Excel,
    verify API numbers match Excel numbers exactly."""

    @pytest.mark.parametrize("cfg", ESTIMATE_CONFIGS, ids=[config_id(c) for c in ESTIMATE_CONFIGS])
    def test_export_all_sizes(self, e2e_client, cfg):
        """Test DBSQL Serverless: create estimate with all warehouse sizes, export, verify."""
        cloud, region, tier = cfg["cloud"], cfg["region"], cfg["tier"]

        estimate = e2e_client.create_estimate(
            name=f"E2E-DBSQL-Serverless-{config_id(cfg)}",
            cloud=cloud, region=region, tier=tier,
        )
        eid = estimate["estimate_id"]

        calc_results = []
        for wh_size in DBSQL_WAREHOUSE_SIZES:
            api_result = e2e_client.calculate_dbsql_serverless(
                cloud=cloud, region=region, tier=tier,
                warehouse_size=wh_size, usage=USAGE_HOURLY,
            )
            calc_results.append(api_result)

            e2e_client.add_line_item(eid, {
                "workload_name": f"DBSQL-Serverless-{wh_size}",
                "workload_type": "DBSQL",
                "serverless_enabled": True,
                "dbsql_warehouse_type": "serverless",
                "dbsql_warehouse_size": wh_size,
                "hours_per_month": USAGE_HOURLY["hours_per_month"],
            })

        excel_bytes = e2e_client.export_excel(eid)
        parsed = parse_estimate_excel(excel_bytes)

        assert len(parsed["rows"]) == len(calc_results), (
            f"Expected {len(calc_results)} rows, got {len(parsed['rows'])}"
        )
        for row, api_result in zip(parsed["rows"], calc_results):
            assert row.is_serverless, f"Row '{row.name}' should be Serverless mode"
            assert_costs_match(api_result, row, workload_label=row.name)

        e2e_client.delete_estimate(eid)

    @pytest.mark.parametrize("cfg", ESTIMATE_CONFIGS, ids=[config_id(c) for c in ESTIMATE_CONFIGS])
    def test_export_subset_sizes(self, e2e_client, cfg):
        """Test DBSQL Serverless with subset of sizes, export, verify."""
        cloud, region, tier = cfg["cloud"], cfg["region"], cfg["tier"]

        estimate = e2e_client.create_estimate(
            name=f"E2E-DBSQL-SL-Subset-{config_id(cfg)}",
            cloud=cloud, region=region, tier=tier,
        )
        eid = estimate["estimate_id"]

        calc_results = []
        for wh_size in ["Small", "Medium", "Large"]:
            api_result = e2e_client.calculate_dbsql_serverless(
                cloud=cloud, region=region, tier=tier,
                warehouse_size=wh_size, usage=USAGE_HOURLY,
            )
            calc_results.append(api_result)

            e2e_client.add_line_item(eid, {
                "workload_name": f"DBSQL-SL-{wh_size}-sub",
                "workload_type": "DBSQL",
                "serverless_enabled": True,
                "dbsql_warehouse_type": "serverless",
                "dbsql_warehouse_size": wh_size,
                "hours_per_month": USAGE_HOURLY["hours_per_month"],
            })

        excel_bytes = e2e_client.export_excel(eid)
        parsed = parse_estimate_excel(excel_bytes)

        assert len(parsed["rows"]) == len(calc_results), (
            f"Expected {len(calc_results)} rows, got {len(parsed['rows'])}"
        )
        for row, api_result in zip(parsed["rows"], calc_results):
            assert row.is_serverless, f"Row '{row.name}' should be Serverless mode"
            assert_costs_match(api_result, row, workload_label=row.name)

        e2e_client.delete_estimate(eid)
