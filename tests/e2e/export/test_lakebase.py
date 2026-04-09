"""E2E tests: Lakebase — API calculation vs Excel export verification.

Tests every combination of:
  - 6 cloud/region configs
  - 7 CU sizes (0.5, 1, 2, 4, 8, 16, 32)
  - hourly usage (100 hours/month)
  = ~42 test cases

Run: pytest tests/e2e/export/test_lakebase.py -v
"""
import pytest
from tests.e2e.helpers.test_data import (
    ESTIMATE_CONFIGS, LAKEBASE_CU_SIZES, USAGE_HOURLY, config_id,
)
from tests.e2e.helpers.assertions import assert_costs_match, save_test_results
from tests.e2e.helpers.excel_parser import parse_estimate_excel


def _generate_params():
    params = []
    for cfg in ESTIMATE_CONFIGS:
        for cu_size in LAKEBASE_CU_SIZES:
            test_id = f"{config_id(cfg)}-{cu_size}CU"
            params.append(pytest.param(cfg, cu_size, id=test_id))
    return params


@pytest.fixture(scope="module")
def results():
    data = []
    yield data
    save_test_results(data, "test_results/e2e_lakebase.json")


class TestLakebaseCalculation:
    """Verify Lakebase API calculation returns valid CU-based results."""

    @pytest.mark.parametrize("cfg, cu_size", _generate_params())
    def test_calculation_succeeds(self, e2e_client, cfg, cu_size, results):
        result = e2e_client.calculate_lakebase(
            cloud=cfg["cloud"], region=cfg["region"], tier=cfg["tier"],
            cu_size=cu_size, read_replicas=0,
            usage=USAGE_HOURLY,
        )
        assert "dbu_calculation" in result
        assert "total_cost" in result
        assert result["dbu_calculation"]["dbu_per_month"] >= 0
        assert result["total_cost"]["cost_per_month"] >= 0

        results.append({
            "config": config_id(cfg), "cu_size": cu_size,
            "total_cost": result["total_cost"]["cost_per_month"],
            "status": "PASS",
        })


class TestLakebaseExcelExport:
    """Create estimates with Lakebase workloads, export, verify."""

    @pytest.mark.parametrize("cfg", ESTIMATE_CONFIGS, ids=[config_id(c) for c in ESTIMATE_CONFIGS])
    def test_export_all_cu_sizes(self, e2e_client, cfg):
        cloud, region, tier = cfg["cloud"], cfg["region"], cfg["tier"]

        estimate = e2e_client.create_estimate(
            name=f"E2E-Lakebase-{config_id(cfg)}",
            cloud=cloud, region=region, tier=tier,
        )
        eid = estimate["estimate_id"]

        calc_results = []
        for cu_size in LAKEBASE_CU_SIZES:
            api_result = e2e_client.calculate_lakebase(
                cloud=cloud, region=region, tier=tier,
                cu_size=cu_size, read_replicas=0,
                usage=USAGE_HOURLY,
            )
            calc_results.append(api_result)

            e2e_client.add_line_item(eid, {
                "workload_name": f"Lakebase-{cu_size}CU",
                "workload_type": "LAKEBASE",
                "serverless_enabled": True,
                "lakebase_cu": cu_size,
                "lakebase_ha_nodes": 1,
                "hours_per_month": USAGE_HOURLY["hours_per_month"],
            })

        excel_bytes = e2e_client.export_excel(eid)
        parsed = parse_estimate_excel(excel_bytes)

        assert len(parsed["rows"]) == len(calc_results), (
            f"Expected {len(calc_results)} rows, got {len(parsed['rows'])}"
        )
        for row, api_result in zip(parsed["rows"], calc_results):
            assert_costs_match(api_result, row, workload_label=row.name)

        e2e_client.delete_estimate(eid)
