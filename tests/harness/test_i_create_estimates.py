"""
Harness Test (i): Create 6 estimates — 2 from each cloud (AWS, Azure, GCP).

Verifies:
- POST /api/v1/estimates creates estimates with correct cloud/region/tier
- GET /api/v1/estimates returns all 6
- Each estimate has correct metadata
"""
import pytest
from tests.harness.conftest import ESTIMATE_CONFIGS


class TestCreateEstimates:
    """Create 6 estimates: 2 AWS, 2 Azure, 2 GCP."""

    created_ids: list[str] = []

    @pytest.fixture(autouse=True, scope="class")
    def setup_estimates(self, client, test_user_id):
        """Create all 6 estimates before tests run."""
        TestCreateEstimates.created_ids = []
        for cfg in ESTIMATE_CONFIGS:
            resp = client.post(
                "/api/v1/estimates",
                json={
                    "estimate_name": f"Harness - {cfg['name']}",
                    "customer_name": "Harness Test Corp",
                    "cloud": cfg["cloud"],
                    "region": cfg["region"],
                    "tier": cfg["tier"],
                },
                headers={"X-User-Id": test_user_id},
            )
            assert resp.status_code == 200 or resp.status_code == 201, (
                f"Failed to create estimate {cfg['name']}: {resp.status_code} {resp.text}"
            )
            data = resp.json()
            est_id = data.get("estimate_id") or data.get("data", {}).get("estimate_id")
            assert est_id, f"No estimate_id in response: {data}"
            TestCreateEstimates.created_ids.append(est_id)

    def test_six_estimates_created(self):
        assert len(TestCreateEstimates.created_ids) == 6

    def test_two_per_cloud(self, client, test_user_id):
        resp = client.get(
            "/api/v1/estimates",
            headers={"X-User-Id": test_user_id},
        )
        assert resp.status_code == 200
        estimates = resp.json()
        if isinstance(estimates, dict):
            estimates = estimates.get("data", estimates.get("estimates", []))

        harness_estimates = [
            e for e in estimates
            if e.get("estimate_name", "").startswith("Harness - ")
        ]
        clouds = [e.get("cloud", "").upper() for e in harness_estimates]
        assert clouds.count("AWS") >= 2, f"Expected 2 AWS estimates, got {clouds.count('AWS')}"
        assert clouds.count("AZURE") >= 2, f"Expected 2 Azure estimates, got {clouds.count('AZURE')}"
        assert clouds.count("GCP") >= 2, f"Expected 2 GCP estimates, got {clouds.count('GCP')}"

    @pytest.mark.parametrize("idx,cfg", list(enumerate(ESTIMATE_CONFIGS)))
    def test_estimate_metadata(self, client, test_user_id, idx, cfg):
        est_id = TestCreateEstimates.created_ids[idx]
        resp = client.get(
            f"/api/v1/estimates/{est_id}",
            headers={"X-User-Id": test_user_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        if "data" in data:
            data = data["data"]
        assert data["cloud"].upper() == cfg["cloud"].upper()
        assert data["tier"].upper() == cfg["tier"].upper()
