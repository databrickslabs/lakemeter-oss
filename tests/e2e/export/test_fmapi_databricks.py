"""E2E tests: FMAPI Databricks — API calculation vs Excel export verification.

Tests every combination of:
  - 6 cloud/region configs
  - 3 Databricks foundation models
  - token-based pricing (input + output tokens)
  = ~18 test cases

Run: pytest tests/e2e/export/test_fmapi_databricks.py -v
"""
import pytest
from tests.e2e.helpers.test_data import (
    ESTIMATE_CONFIGS, config_id,
)
from tests.e2e.helpers.assertions import assert_costs_match, save_test_results
from tests.e2e.helpers.excel_parser import parse_estimate_excel

FMAPI_DATABRICKS_MODELS = [
    "llama-3-3-70b",
    "llama-4-maverick",
    "gemma-3-12b",
]

INPUT_TOKENS = 10   # millions per month
OUTPUT_TOKENS = 5   # millions per month


def _generate_params():
    params = []
    for cfg in ESTIMATE_CONFIGS:
        for model in FMAPI_DATABRICKS_MODELS:
            test_id = f"{config_id(cfg)}-{model}"
            params.append(pytest.param(cfg, model, id=test_id))
    return params


@pytest.fixture(scope="module")
def results():
    data = []
    yield data
    save_test_results(data, "test_results/e2e_fmapi_databricks.json")


class TestFMAPIDatabricksCalculation:
    """Verify FMAPI Databricks API calculation returns valid token-based results."""

    @pytest.mark.parametrize("cfg, model", _generate_params())
    def test_calculation_succeeds(self, e2e_client, cfg, model, results):
        result = e2e_client.calculate_fmapi_databricks(
            cloud=cfg["cloud"], region=cfg["region"], tier=cfg["tier"],
            model=model,
            input_tokens=INPUT_TOKENS,
            output_tokens=OUTPUT_TOKENS,
        )
        assert "line_items" in result or "dbu_calculation" in result
        assert "total_cost" in result
        assert result["total_cost"]["cost_per_month"] >= 0

        results.append({
            "config": config_id(cfg), "model": model,
            "total_cost": result["total_cost"]["cost_per_month"],
            "status": "PASS",
        })


class TestFMAPIDatabricksExcelExport:
    """Create estimates with FMAPI Databricks workloads, export, verify."""

    @pytest.mark.parametrize("cfg", ESTIMATE_CONFIGS, ids=[config_id(c) for c in ESTIMATE_CONFIGS])
    def test_export_all_models(self, e2e_client, cfg):
        cloud, region, tier = cfg["cloud"], cfg["region"], cfg["tier"]

        estimate = e2e_client.create_estimate(
            name=f"E2E-FMAPI-DB-{config_id(cfg)}",
            cloud=cloud, region=region, tier=tier,
        )
        eid = estimate["estimate_id"]

        calc_results = []
        for model in FMAPI_DATABRICKS_MODELS:
            api_result = e2e_client.calculate_fmapi_databricks(
                cloud=cloud, region=region, tier=tier,
                model=model,
                input_tokens=INPUT_TOKENS,
                output_tokens=OUTPUT_TOKENS,
            )
            # Each model produces two line items: input_token and output_token
            calc_results.append(api_result)

            e2e_client.add_line_item(eid, {
                "workload_name": f"FMAPI-DB-{model}-input",
                "workload_type": "FMAPI_DATABRICKS",
                "serverless_enabled": True,
                "fmapi_model": model,
                "fmapi_rate_type": "input_token",
                "fmapi_quantity": INPUT_TOKENS,
            })
            e2e_client.add_line_item(eid, {
                "workload_name": f"FMAPI-DB-{model}-output",
                "workload_type": "FMAPI_DATABRICKS",
                "serverless_enabled": True,
                "fmapi_model": model,
                "fmapi_rate_type": "output_token",
                "fmapi_quantity": OUTPUT_TOKENS,
            })

        excel_bytes = e2e_client.export_excel(eid)
        parsed = parse_estimate_excel(excel_bytes)

        # Each model has 2 rows (input + output), so total rows = models * 2
        expected_rows = len(FMAPI_DATABRICKS_MODELS) * 2
        assert len(parsed["rows"]) == expected_rows, (
            f"Expected {expected_rows} rows, got {len(parsed['rows'])}"
        )

        # Verify each row is a valid FMAPI token row
        for row in parsed["rows"]:
            assert row.is_fmapi_token, f"Row '{row.name}' should be a token-based FMAPI row"

        e2e_client.delete_estimate(eid)
