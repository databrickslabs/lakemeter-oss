"""E2E tests: DLT Serverless — API calculation vs Excel export verification.

Tests every combination of:
  - 6 cloud/region configs
  - 3 DLT editions (CORE, PRO, ADVANCED)
  - standard vs performance mode
  - run-based vs hourly usage
  = ~72 test cases

Run: pytest tests/e2e/export/test_dlt_serverless.py -v --timeout=600
"""
import pytest
from tests.e2e.helpers.test_data import (
    ESTIMATE_CONFIGS, DLT_EDITIONS, SERVERLESS_MODES,
    USAGE_RUN_BASED, USAGE_HOURLY, config_id,
)
from tests.e2e.helpers.assertions import assert_costs_match, save_test_results
from tests.e2e.helpers.excel_parser import parse_estimate_excel


def _generate_params():
    params = []
    for cfg in ESTIMATE_CONFIGS:
        for edition in DLT_EDITIONS:
            for mode in SERVERLESS_MODES:
                for usage_label, usage in [("run_based", USAGE_RUN_BASED), ("hourly", USAGE_HOURLY)]:
                    test_id = f"{config_id(cfg)}-{edition}-{mode}-{usage_label}"
                    params.append(pytest.param(
                        cfg, edition, mode, usage_label, usage,
                        id=test_id,
                    ))
    return params


@pytest.fixture(scope="module")
def results():
    data = []
    yield data
    save_test_results(data, "test_results/e2e_dlt_serverless.json")


class TestDLTServerlessCalculation:
    """Verify DLT Serverless API calculation returns valid results."""

    @pytest.mark.parametrize("cfg, edition, mode, usage_label, usage", _generate_params())
    def test_calculation_succeeds(self, e2e_client, cfg, edition, mode,
                                   usage_label, usage, results):
        result = e2e_client.calculate_dlt_serverless(
            cloud=cfg["cloud"], region=cfg["region"], tier=cfg["tier"],
            edition=edition, mode=mode, usage=usage,
        )
        assert "dbu_calculation" in result
        assert "total_cost" in result
        assert result["dbu_calculation"]["dbu_per_month"] > 0
        assert result["total_cost"]["cost_per_month"] > 0

        results.append({
            "config": config_id(cfg), "edition": edition, "mode": mode,
            "usage": usage_label,
            "total_cost": result["total_cost"]["cost_per_month"],
            "status": "PASS",
        })


class TestDLTServerlessExcelExport:
    """Create estimates with DLT Serverless workloads, export, verify."""

    @pytest.mark.parametrize("cfg", ESTIMATE_CONFIGS, ids=[config_id(c) for c in ESTIMATE_CONFIGS])
    def test_export_all_combos(self, e2e_client, cfg):
        cloud, region, tier = cfg["cloud"], cfg["region"], cfg["tier"]

        estimate = e2e_client.create_estimate(
            name=f"E2E-DLT-Serverless-{config_id(cfg)}",
            cloud=cloud, region=region, tier=tier,
        )
        eid = estimate["estimate_id"]

        calc_results = []
        for edition in DLT_EDITIONS:
            for mode in SERVERLESS_MODES:
                for usage_label, usage in [("run_based", USAGE_RUN_BASED), ("hourly", USAGE_HOURLY)]:
                    api_result = e2e_client.calculate_dlt_serverless(
                        cloud=cloud, region=region, tier=tier,
                        edition=edition, mode=mode, usage=usage,
                    )
                    calc_results.append(api_result)

                    line_item_payload = {
                        "workload_name": f"DLT-SL-{edition}-{mode}-{usage_label}",
                        "workload_type": "DLT",
                        "serverless_enabled": True,
                        "dlt_edition": edition,
                        "serverless_mode": mode,
                    }
                    if usage_label == "run_based":
                        line_item_payload["runs_per_day"] = usage["runs_per_day"]
                        line_item_payload["avg_runtime_minutes"] = usage["avg_runtime_minutes"]
                        line_item_payload["days_per_month"] = usage["days_per_month"]
                    else:
                        line_item_payload["hours_per_month"] = usage["hours_per_month"]

                    e2e_client.add_line_item(eid, line_item_payload)

        excel_bytes = e2e_client.export_excel(eid)
        parsed = parse_estimate_excel(excel_bytes)

        assert len(parsed["rows"]) == len(calc_results), (
            f"Expected {len(calc_results)} rows, got {len(parsed['rows'])}"
        )
        for row, api_result in zip(parsed["rows"], calc_results):
            assert row.is_serverless, f"Row '{row.name}' should be Serverless mode"
            assert_costs_match(api_result, row, workload_label=row.name)

        e2e_client.delete_estimate(eid)
