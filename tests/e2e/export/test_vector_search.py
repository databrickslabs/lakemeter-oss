"""E2E tests: Vector Search — API calculation vs Excel export verification.

Tests every combination of:
  - 6 cloud/region configs
  - 2 modes (standard, storage_optimized)
  - 3 vector capacities (1M, 10M, 100M)
  - hourly usage
  = ~36 test cases

Run: pytest tests/e2e/export/test_vector_search.py -v
"""
import pytest
from tests.e2e.helpers.test_data import (
    ESTIMATE_CONFIGS, VECTOR_SEARCH_MODES, USAGE_HOURLY, config_id,
)
from tests.e2e.helpers.assertions import assert_costs_match, save_test_results
from tests.e2e.helpers.excel_parser import parse_estimate_excel

VECTOR_CAPACITIES = [1.0, 10.0, 100.0]  # millions of vectors


def _generate_params():
    params = []
    for cfg in ESTIMATE_CONFIGS:
        for mode in VECTOR_SEARCH_MODES:
            for cap in VECTOR_CAPACITIES:
                test_id = f"{config_id(cfg)}-{mode}-{cap}M"
                params.append(pytest.param(cfg, mode, cap, id=test_id))
    return params


@pytest.fixture(scope="module")
def results():
    data = []
    yield data
    save_test_results(data, "test_results/e2e_vector_search.json")


class TestVectorSearchCalculation:
    """Verify Vector Search API calculation returns valid results."""

    @pytest.mark.parametrize("cfg, mode, capacity", _generate_params())
    def test_calculation_succeeds(self, e2e_client, cfg, mode, capacity, results):
        result = e2e_client.calculate_vector_search(
            cloud=cfg["cloud"], region=cfg["region"], tier=cfg["tier"],
            mode=mode, num_vectors_millions=capacity,
            usage=USAGE_HOURLY,
        )
        assert "dbu_calculation" in result
        assert "total_cost" in result
        assert result["dbu_calculation"]["dbu_per_month"] >= 0
        assert result["total_cost"]["cost_per_month"] >= 0

        results.append({
            "config": config_id(cfg), "mode": mode, "capacity_m": capacity,
            "total_cost": result["total_cost"]["cost_per_month"],
            "status": "PASS",
        })


class TestVectorSearchExcelExport:
    """Create estimates with Vector Search workloads, export, verify."""

    @pytest.mark.parametrize("cfg", ESTIMATE_CONFIGS, ids=[config_id(c) for c in ESTIMATE_CONFIGS])
    def test_export_all_modes(self, e2e_client, cfg):
        cloud, region, tier = cfg["cloud"], cfg["region"], cfg["tier"]

        estimate = e2e_client.create_estimate(
            name=f"E2E-VectorSearch-{config_id(cfg)}",
            cloud=cloud, region=region, tier=tier,
        )
        eid = estimate["estimate_id"]

        calc_results = []
        for mode in VECTOR_SEARCH_MODES:
            for cap in VECTOR_CAPACITIES:
                api_result = e2e_client.calculate_vector_search(
                    cloud=cloud, region=region, tier=tier,
                    mode=mode, num_vectors_millions=cap,
                    usage=USAGE_HOURLY,
                )
                calc_results.append(api_result)

                e2e_client.add_line_item(eid, {
                    "workload_name": f"VS-{mode}-{cap}M",
                    "workload_type": "VECTOR_SEARCH",
                    "serverless_enabled": True,
                    "vector_search_mode": mode,
                    "vector_capacity_millions": cap,
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
