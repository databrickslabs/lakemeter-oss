"""E2E tests: AI Parse (Document AI) — API calculation vs Excel export verification.

Tests:
  - 6 cloud/region configs
  - 2 modes (pages, dbu)
  - 4 complexities × 3 page counts (pages mode)
  - 1 hours config (dbu mode)
  = ~84 test cases

Run: pytest tests/e2e/export/test_ai_parse.py -v
"""
import pytest
from tests.e2e.helpers.test_data import (
    ESTIMATE_CONFIGS, AI_PARSE_COMPLEXITIES, AI_PARSE_PAGES, config_id,
)
from tests.e2e.helpers.assertions import assert_costs_match, save_test_results
from tests.e2e.helpers.excel_parser import parse_estimate_excel

# Expected DBU per 1000 pages by complexity
COMPLEXITY_RATES = {
    "low_text": 12.5,
    "low_images": 22.5,
    "medium": 62.5,
    "high": 87.5,
}


def _generate_pages_params():
    params = []
    for cfg in ESTIMATE_CONFIGS:
        for complexity in AI_PARSE_COMPLEXITIES:
            for pages in AI_PARSE_PAGES:
                test_id = f"{config_id(cfg)}-pages-{complexity}-{pages}K"
                params.append(pytest.param(cfg, complexity, pages, id=test_id))
    return params


def _generate_dbu_params():
    params = []
    for cfg in ESTIMATE_CONFIGS:
        test_id = f"{config_id(cfg)}-dbu-100h"
        params.append(pytest.param(cfg, 100.0, id=test_id))
    return params


@pytest.fixture(scope="module")
def results():
    data = []
    yield data
    save_test_results(data, "test_results/e2e_ai_parse.json")


class TestAIParseCalculationPages:
    """Verify AI Parse pages mode calculation."""

    @pytest.mark.parametrize("cfg, complexity, pages", _generate_pages_params())
    def test_pages_mode(self, e2e_client, cfg, complexity, pages, results):
        result = e2e_client.calculate_ai_parse(
            cloud=cfg["cloud"], region=cfg["region"], tier=cfg["tier"],
            mode="pages", complexity=complexity, pages_thousands=pages,
        )
        assert "dbu_calculation" in result
        dbu_calc = result["dbu_calculation"]

        # Verify DBU matches: pages_thousands × complexity_rate
        expected_dbu = pages * COMPLEXITY_RATES[complexity]
        assert abs(dbu_calc["dbu_per_month"] - expected_dbu) < 0.01, \
            f"Expected {expected_dbu} DBU, got {dbu_calc['dbu_per_month']}"

        results.append({
            "config": config_id(cfg), "mode": "pages",
            "complexity": complexity, "pages_k": pages,
            "dbu_per_month": dbu_calc["dbu_per_month"],
            "total_cost": result["total_cost"]["cost_per_month"],
            "status": "PASS",
        })


class TestAIParseCalculationDBU:
    """Verify AI Parse DBU mode calculation."""

    @pytest.mark.parametrize("cfg, hours", _generate_dbu_params())
    def test_dbu_mode(self, e2e_client, cfg, hours, results):
        result = e2e_client.calculate_ai_parse(
            cloud=cfg["cloud"], region=cfg["region"], tier=cfg["tier"],
            mode="dbu", hours_per_month=hours,
        )
        assert "dbu_calculation" in result
        dbu_calc = result["dbu_calculation"]
        assert dbu_calc["dbu_per_month"] == hours

        results.append({
            "config": config_id(cfg), "mode": "dbu", "hours": hours,
            "dbu_per_month": dbu_calc["dbu_per_month"],
            "total_cost": result["total_cost"]["cost_per_month"],
            "status": "PASS",
        })


class TestAIParseValidation:
    """Verify input validation."""

    def test_invalid_mode(self, e2e_client):
        resp = e2e_client.http.post("/api/v1/calculate/ai-parse", json={
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
            "mode": "invalid",
        })
        assert resp.status_code == 400

    def test_invalid_complexity(self, e2e_client):
        resp = e2e_client.http.post("/api/v1/calculate/ai-parse", json={
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
            "mode": "pages", "complexity": "ultra", "pages_thousands": 10,
        })
        assert resp.status_code == 400


class TestAIParseExcelExport:
    """Create estimates with AI Parse workloads, export, verify."""

    @pytest.mark.parametrize("cfg", ESTIMATE_CONFIGS[:2], ids=[config_id(c) for c in ESTIMATE_CONFIGS[:2]])
    def test_export_pages_mode(self, e2e_client, cfg):
        cloud, region, tier = cfg["cloud"], cfg["region"], cfg["tier"]

        estimate = e2e_client.create_estimate(
            name=f"E2E-AIParse-{config_id(cfg)}",
            cloud=cloud, region=region, tier=tier,
        )
        eid = estimate["estimate_id"]

        calc_results = []
        for complexity in AI_PARSE_COMPLEXITIES:
            pages = 10.0
            api_result = e2e_client.calculate_ai_parse(
                cloud=cloud, region=region, tier=tier,
                mode="pages", complexity=complexity, pages_thousands=pages,
            )
            e2e_client.add_line_item(eid, {
                "workload_name": f"AIParse-{complexity}",
                "workload_type": "AI_PARSE",
                "ai_parse_mode": "pages",
                "ai_parse_complexity": complexity,
                "ai_parse_pages_thousands": pages,
            })
            calc_results.append(api_result)

        excel_buf = e2e_client.export_excel(eid)
        rows = parse_estimate_excel(excel_buf)

        assert len(rows) >= len(AI_PARSE_COMPLEXITIES), \
            f"Expected at least {len(AI_PARSE_COMPLEXITIES)} rows, got {len(rows)}"

        for i, (api_res, row) in enumerate(zip(calc_results, rows)):
            assert_costs_match(api_res, row, f"AIParse-{AI_PARSE_COMPLEXITIES[i]}")
