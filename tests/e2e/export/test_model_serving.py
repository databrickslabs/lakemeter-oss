"""E2E tests: Model Serving — API calculation vs Excel export verification.

Tests every combination of:
  - 6 cloud/region configs
  - GPU types per cloud
  - scale-out sizes (small, medium, large)
  - hourly usage
  = ~54 test cases

Run: pytest tests/e2e/export/test_model_serving.py -v
"""
import pytest
from tests.e2e.helpers.test_data import (
    ESTIMATE_CONFIGS, GPU_TYPES, MODEL_SERVING_SCALE_OUTS, USAGE_HOURLY, config_id,
)
from tests.e2e.helpers.assertions import assert_costs_match, save_test_results
from tests.e2e.helpers.excel_parser import parse_estimate_excel

# Map scale_out presets to concurrency (must match API's SCALE_OUT_PRESETS)
SCALE_OUT_CONCURRENCY = {"small": 4, "medium": 12, "large": 40}


def _generate_params():
    params = []
    for cfg in ESTIMATE_CONFIGS:
        cloud = cfg["cloud"]
        for gpu in GPU_TYPES.get(cloud, []):
            for scale_out in MODEL_SERVING_SCALE_OUTS:
                test_id = f"{config_id(cfg)}-{gpu}-{scale_out}"
                params.append(pytest.param(cfg, gpu, scale_out, id=test_id))
    return params


@pytest.fixture(scope="module")
def results():
    data = []
    yield data
    save_test_results(data, "test_results/e2e_model_serving.json")


class TestModelServingCalculation:
    """Verify Model Serving API calculation returns valid results."""

    @pytest.mark.parametrize("cfg, gpu, scale_out", _generate_params())
    def test_calculation_succeeds(self, e2e_client, cfg, gpu, scale_out, results):
        result = e2e_client.calculate_model_serving(
            cloud=cfg["cloud"], region=cfg["region"], tier=cfg["tier"],
            gpu_type=gpu, scale_out=scale_out,
            usage=USAGE_HOURLY,
        )
        assert "dbu_calculation" in result
        assert "total_cost" in result
        assert result["dbu_calculation"]["dbu_per_month"] >= 0
        assert result["total_cost"]["cost_per_month"] >= 0

        results.append({
            "config": config_id(cfg), "gpu": gpu, "scale_out": scale_out,
            "total_cost": result["total_cost"]["cost_per_month"],
            "status": "PASS",
        })


class TestModelServingExcelExport:
    """Create estimates with Model Serving workloads, export, verify."""

    @pytest.mark.parametrize("cfg", ESTIMATE_CONFIGS, ids=[config_id(c) for c in ESTIMATE_CONFIGS])
    def test_export_all_gpus(self, e2e_client, cfg):
        cloud, region, tier = cfg["cloud"], cfg["region"], cfg["tier"]

        estimate = e2e_client.create_estimate(
            name=f"E2E-ModelServing-{config_id(cfg)}",
            cloud=cloud, region=region, tier=tier,
        )
        eid = estimate["estimate_id"]

        calc_results = []
        for gpu in GPU_TYPES.get(cloud, []):
            for scale_out in MODEL_SERVING_SCALE_OUTS:
                api_result = e2e_client.calculate_model_serving(
                    cloud=cloud, region=region, tier=tier,
                    gpu_type=gpu, scale_out=scale_out,
                    usage=USAGE_HOURLY,
                )
                calc_results.append(api_result)

                e2e_client.add_line_item(eid, {
                    "workload_name": f"MS-{gpu}-{scale_out}",
                    "workload_type": "MODEL_SERVING",
                    "serverless_enabled": True,
                    "model_serving_gpu_type": gpu,
                    "hours_per_month": USAGE_HOURLY["hours_per_month"],
                    "workload_config": {"model_serving_concurrency": SCALE_OUT_CONCURRENCY[scale_out]},
                })

        excel_bytes = e2e_client.export_excel(eid)
        parsed = parse_estimate_excel(excel_bytes)

        assert len(parsed["rows"]) == len(calc_results), (
            f"Expected {len(calc_results)} rows, got {len(parsed['rows'])}"
        )
        for row, api_result in zip(parsed["rows"], calc_results):
            assert_costs_match(api_result, row, workload_label=row.name)

        e2e_client.delete_estimate(eid)
