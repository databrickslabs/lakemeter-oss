"""E2E tests: Shutterstock ImageAI — API calculation vs Excel export verification.

Tests:
  - 6 cloud/region configs
  - 4 image counts (100, 500, 1000, 5000)
  = ~24 test cases

Run: pytest tests/e2e/export/test_shutterstock.py -v
"""
import pytest
from tests.e2e.helpers.test_data import (
    ESTIMATE_CONFIGS, SHUTTERSTOCK_IMAGE_COUNTS, config_id,
)
from tests.e2e.helpers.assertions import assert_costs_match, save_test_results
from tests.e2e.helpers.excel_parser import parse_estimate_excel

DBU_PER_IMAGE = 0.857


def _generate_params():
    params = []
    for cfg in ESTIMATE_CONFIGS:
        for images in SHUTTERSTOCK_IMAGE_COUNTS:
            test_id = f"{config_id(cfg)}-{images}img"
            params.append(pytest.param(cfg, images, id=test_id))
    return params


@pytest.fixture(scope="module")
def results():
    data = []
    yield data
    save_test_results(data, "test_results/e2e_shutterstock.json")


class TestShutterstockCalculation:
    """Verify Shutterstock ImageAI API calculation returns valid results."""

    @pytest.mark.parametrize("cfg, images", _generate_params())
    def test_calculation_succeeds(self, e2e_client, cfg, images, results):
        result = e2e_client.calculate_shutterstock(
            cloud=cfg["cloud"], region=cfg["region"], tier=cfg["tier"],
            images_per_month=images,
        )
        assert "dbu_calculation" in result
        assert "total_cost" in result
        dbu_calc = result["dbu_calculation"]

        # Verify DBU = images × 0.857
        expected_dbu = images * DBU_PER_IMAGE
        assert abs(dbu_calc["dbu_per_month"] - expected_dbu) < 0.01, \
            f"Expected {expected_dbu:.2f} DBU, got {dbu_calc['dbu_per_month']}"

        assert dbu_calc["dbu_per_image"] == DBU_PER_IMAGE
        assert dbu_calc["images_per_month"] == images

        results.append({
            "config": config_id(cfg), "images": images,
            "dbu_per_month": dbu_calc["dbu_per_month"],
            "total_cost": result["total_cost"]["cost_per_month"],
            "status": "PASS",
        })

    def test_zero_images(self, e2e_client):
        """Verify 0 images returns 0 cost."""
        result = e2e_client.calculate_shutterstock(
            cloud="AWS", region="us-east-1", tier="PREMIUM",
            images_per_month=0,
        )
        assert result["dbu_calculation"]["dbu_per_month"] == 0
        assert result["total_cost"]["cost_per_month"] == 0


class TestShutterstockExcelExport:
    """Create estimates with Shutterstock workloads, export, verify."""

    @pytest.mark.parametrize("cfg", ESTIMATE_CONFIGS, ids=[config_id(c) for c in ESTIMATE_CONFIGS])
    def test_export_images(self, e2e_client, cfg):
        cloud, region, tier = cfg["cloud"], cfg["region"], cfg["tier"]

        estimate = e2e_client.create_estimate(
            name=f"E2E-Shutterstock-{config_id(cfg)}",
            cloud=cloud, region=region, tier=tier,
        )
        eid = estimate["estimate_id"]

        calc_results = []
        for images in SHUTTERSTOCK_IMAGE_COUNTS:
            api_result = e2e_client.calculate_shutterstock(
                cloud=cloud, region=region, tier=tier,
                images_per_month=images,
            )
            e2e_client.add_line_item(eid, {
                "workload_name": f"Shutterstock-{images}img",
                "workload_type": "SHUTTERSTOCK_IMAGEAI",
                "shutterstock_images": images,
            })
            calc_results.append(api_result)

        excel_buf = e2e_client.export_excel(eid)
        rows = parse_estimate_excel(excel_buf)

        assert len(rows) >= len(SHUTTERSTOCK_IMAGE_COUNTS), \
            f"Expected at least {len(SHUTTERSTOCK_IMAGE_COUNTS)} rows, got {len(rows)}"

        for i, (api_res, row) in enumerate(zip(calc_results, rows)):
            assert_costs_match(api_res, row, f"Shutterstock-{SHUTTERSTOCK_IMAGE_COUNTS[i]}img")
