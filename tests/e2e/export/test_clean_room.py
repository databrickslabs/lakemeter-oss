"""E2E tests: Clean Room — API calculation vs Excel export verification.

Tests:
  - 6 cloud/region configs
  - 4 collaborator counts (1, 3, 5, 10)
  - default 30 days/month
  = ~24 test cases

Run: pytest tests/e2e/export/test_clean_room.py -v
"""
import pytest
from tests.e2e.helpers.test_data import (
    ESTIMATE_CONFIGS, CLEAN_ROOM_COLLABORATORS, config_id,
)
from tests.e2e.helpers.assertions import assert_costs_match, save_test_results
from tests.e2e.helpers.excel_parser import parse_estimate_excel


def _generate_params():
    params = []
    for cfg in ESTIMATE_CONFIGS:
        for collab in CLEAN_ROOM_COLLABORATORS:
            test_id = f"{config_id(cfg)}-{collab}collab"
            params.append(pytest.param(cfg, collab, id=test_id))
    return params


@pytest.fixture(scope="module")
def results():
    data = []
    yield data
    save_test_results(data, "test_results/e2e_clean_room.json")


class TestCleanRoomCalculation:
    """Verify Clean Room API calculation returns valid results."""

    @pytest.mark.parametrize("cfg, collaborators", _generate_params())
    def test_calculation_succeeds(self, e2e_client, cfg, collaborators, results):
        result = e2e_client.calculate_clean_room(
            cloud=cfg["cloud"], region=cfg["region"], tier=cfg["tier"],
            collaborators=collaborators, days_per_month=30,
        )
        assert "dbu_calculation" in result
        assert "total_cost" in result
        dbu_calc = result["dbu_calculation"]
        assert dbu_calc["dbu_per_collaborator_per_day"] == 1.0
        assert dbu_calc["dbu_per_day"] == float(collaborators)
        assert dbu_calc["dbu_per_month"] == float(collaborators * 30)
        assert result["total_cost"]["cost_per_month"] >= 0

        results.append({
            "config": config_id(cfg), "collaborators": collaborators,
            "dbu_per_month": dbu_calc["dbu_per_month"],
            "total_cost": result["total_cost"]["cost_per_month"],
            "status": "PASS",
        })

    def test_validation_max_collaborators(self, e2e_client):
        """Verify that >10 collaborators is rejected."""
        from fastapi.testclient import TestClient
        resp = e2e_client.http.post("/api/v1/calculate/clean-room", json={
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
            "collaborators": 11,
        })
        assert resp.status_code == 422  # Pydantic validation

    def test_validation_zero_collaborators(self, e2e_client):
        """Verify that 0 collaborators is rejected."""
        resp = e2e_client.http.post("/api/v1/calculate/clean-room", json={
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
            "collaborators": 0,
        })
        assert resp.status_code == 422


class TestCleanRoomExcelExport:
    """Create estimates with Clean Room workloads, export, verify."""

    @pytest.mark.parametrize("cfg", ESTIMATE_CONFIGS, ids=[config_id(c) for c in ESTIMATE_CONFIGS])
    def test_export_collaborators(self, e2e_client, cfg):
        cloud, region, tier = cfg["cloud"], cfg["region"], cfg["tier"]

        estimate = e2e_client.create_estimate(
            name=f"E2E-CleanRoom-{config_id(cfg)}",
            cloud=cloud, region=region, tier=tier,
        )
        eid = estimate["estimate_id"]

        calc_results = []
        for collab in CLEAN_ROOM_COLLABORATORS:
            api_result = e2e_client.calculate_clean_room(
                cloud=cloud, region=region, tier=tier,
                collaborators=collab, days_per_month=30,
            )
            e2e_client.add_line_item(eid, {
                "workload_name": f"CleanRoom-{collab}collab",
                "workload_type": "CLEAN_ROOM",
                "clean_room_collaborators": collab,
                "days_per_month": 30,
            })
            calc_results.append(api_result)

        excel_buf = e2e_client.export_excel(eid)
        rows = parse_estimate_excel(excel_buf)

        assert len(rows) >= len(CLEAN_ROOM_COLLABORATORS), \
            f"Expected at least {len(CLEAN_ROOM_COLLABORATORS)} rows, got {len(rows)}"

        for i, (api_res, row) in enumerate(zip(calc_results, rows)):
            assert_costs_match(api_res, row, f"CleanRoom-{CLEAN_ROOM_COLLABORATORS[i]}collab")
