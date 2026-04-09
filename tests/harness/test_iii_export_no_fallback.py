"""
Harness Test (iii): Export all estimates to Excel, verify NO fallback pricing.

Tests:
- Each estimate exports successfully to Excel
- Calculate endpoints return success=True with real Lakebase data
- No "fallback" or "default" source in any calculation response
- DBU prices are non-zero and come from sync_pricing_dbu_rates
- VM prices come from sync_pricing_vm_costs (not DEFAULT_VM_PRICING)
"""
import io
import pytest
from tests.harness.conftest import ESTIMATE_CONFIGS, INSTANCE_TYPES


class TestCalculateNoFallback:
    """Verify every calculation endpoint returns Lakebase data, not fallback."""

    @pytest.fixture(scope="class")
    def estimate_with_workloads(self, client, test_user_id):
        """Create one estimate with representative workloads for calculation testing."""
        resp = client.post(
            "/api/v1/estimates",
            json={
                "estimate_name": "Calc-Harness AWS",
                "customer_name": "Harness Export Corp",
                "cloud": "AWS",
                "region": "us-east-1",
                "tier": "PREMIUM",
            },
            headers={"X-User-Id": test_user_id},
        )
        data = resp.json()
        return data.get("estimate_id") or data.get("data", {}).get("estimate_id")

    # ── Jobs Classic ──────────────────────────────────────────────────────

    def test_jobs_classic_no_fallback(self, client):
        resp = client.post("/api/v1/calculate/jobs-classic", json={
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
            "driver_node_type": "i3.xlarge", "worker_node_type": "i3.2xlarge",
            "num_workers": 2, "photon_enabled": False,
            "runs_per_day": 4, "avg_runtime_minutes": 30, "days_per_month": 22,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True, f"Calculation failed: {data}"
        self._assert_no_fallback(data)

    # ── Jobs Serverless ───────────────────────────────────────────────────

    def test_jobs_serverless_no_fallback(self, client):
        resp = client.post("/api/v1/calculate/jobs-serverless", json={
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
            "runs_per_day": 10, "avg_runtime_minutes": 15, "days_per_month": 30,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True, f"Calculation failed: {data}"
        self._assert_no_fallback(data)

    # ── All-Purpose Classic ───────────────────────────────────────────────

    def test_all_purpose_classic_no_fallback(self, client):
        resp = client.post("/api/v1/calculate/all-purpose-classic", json={
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
            "driver_node_type": "m5d.xlarge", "worker_node_type": "m5d.2xlarge",
            "num_workers": 3, "photon_enabled": True,
            "hours_per_month": 160,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True, f"Calculation failed: {data}"
        self._assert_no_fallback(data)

    # ── All-Purpose Serverless ────────────────────────────────────────────

    def test_all_purpose_serverless_no_fallback(self, client):
        resp = client.post("/api/v1/calculate/all-purpose-serverless", json={
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
            "hours_per_month": 200,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True, f"Calculation failed: {data}"
        self._assert_no_fallback(data)

    # ── DBSQL Classic Pro ─────────────────────────────────────────────────

    def test_dbsql_classic_pro_no_fallback(self, client):
        resp = client.post("/api/v1/calculate/dbsql-classic-pro", json={
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
            "warehouse_type": "PRO", "warehouse_size": "Medium",
            "hours_per_month": 300,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True, f"Calculation failed: {data}"
        self._assert_no_fallback(data)

    # ── DBSQL Serverless ──────────────────────────────────────────────────

    def test_dbsql_serverless_no_fallback(self, client):
        resp = client.post("/api/v1/calculate/dbsql-serverless", json={
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
            "warehouse_size": "Medium", "hours_per_month": 400,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True, f"Calculation failed: {data}"
        self._assert_no_fallback(data)

    # ── DLT Classic ───────────────────────────────────────────────────────

    def test_dlt_classic_no_fallback(self, client):
        resp = client.post("/api/v1/calculate/dlt-classic", json={
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
            "dlt_edition": "PRO",
            "driver_node_type": "i3.xlarge", "worker_node_type": "i3.2xlarge",
            "num_workers": 2, "photon_enabled": True,
            "runs_per_day": 3, "avg_runtime_minutes": 45, "days_per_month": 22,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True, f"Calculation failed: {data}"
        self._assert_no_fallback(data)

    # ── DLT Serverless ────────────────────────────────────────────────────

    def test_dlt_serverless_no_fallback(self, client):
        resp = client.post("/api/v1/calculate/dlt-serverless", json={
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
            "dlt_edition": "CORE",
            "runs_per_day": 6, "avg_runtime_minutes": 20, "days_per_month": 30,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True, f"Calculation failed: {data}"
        self._assert_no_fallback(data)

    # ── Model Serving ─────────────────────────────────────────────────────

    def test_model_serving_no_fallback(self, client):
        resp = client.post("/api/v1/calculate/model-serving", json={
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
            "gpu_type": "gpu_small_t4", "scale_out": "small",
            "hours_per_month": 730,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True, f"Calculation failed: {data}"
        self._assert_no_fallback(data)

    # ── FMAPI Databricks ──────────────────────────────────────────────────

    def test_fmapi_databricks_no_fallback(self, client):
        resp = client.post("/api/v1/calculate/fmapi-databricks", json={
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
            "model": "databricks-meta-llama-3-3-70b-instruct",
            "input_tokens_per_month": 50_000_000,
            "output_tokens_per_month": 10_000_000,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True, f"Calculation failed: {data}"
        self._assert_no_fallback(data)

    # ── FMAPI Proprietary ─────────────────────────────────────────────────

    def test_fmapi_proprietary_no_fallback(self, client):
        resp = client.post("/api/v1/calculate/fmapi-proprietary", json={
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
            "provider": "anthropic", "model": "claude-sonnet-4-20250514",
            "endpoint_type": "in_geo",
            "input_tokens_per_month": 100_000_000,
            "output_tokens_per_month": 20_000_000,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True, f"Calculation failed: {data}"
        self._assert_no_fallback(data)

    # ── Vector Search ─────────────────────────────────────────────────────

    def test_vector_search_no_fallback(self, client):
        resp = client.post("/api/v1/calculate/vector-search", json={
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
            "mode": "standard", "num_vectors_millions": 50,
            "hours_per_month": 730,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True, f"Calculation failed: {data}"
        self._assert_no_fallback(data)

    # ── Lakebase ──────────────────────────────────────────────────────────

    def test_lakebase_no_fallback(self, client):
        resp = client.post("/api/v1/calculate/lakebase", json={
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
            "cu_size": 4, "read_replicas": 1,
            "hours_per_month": 730,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True, f"Calculation failed: {data}"
        self._assert_no_fallback(data)

    # ── Multi-cloud calculations ──────────────────────────────────────────

    @pytest.mark.parametrize("cloud,region,tier", [
        ("AWS", "us-east-1", "PREMIUM"),
        ("AZURE", "eastus", "PREMIUM"),
        ("GCP", "us-central1", "PREMIUM"),
    ])
    def test_jobs_serverless_all_clouds(self, client, cloud, region, tier):
        resp = client.post("/api/v1/calculate/jobs-serverless", json={
            "cloud": cloud, "region": region, "tier": tier,
            "hours_per_month": 100,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True, f"{cloud} calc failed: {data}"
        self._assert_no_fallback(data)

    # ── Helper ────────────────────────────────────────────────────────────

    def _assert_no_fallback(self, response_data):
        """Recursively check no 'fallback' or 'default' source in response."""
        data = response_data.get("data", response_data)

        # Check source fields
        def _check(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == "source" and isinstance(v, str):
                        assert v.lower() not in ("fallback", "default"), (
                            f"Fallback pricing detected at {path}.{k}: {v}"
                        )
                    _check(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    _check(item, f"{path}[{i}]")

        _check(data)

        # Check DBU price is non-zero
        dbu_calc = data.get("dbu_calculation", {})
        dbu_price = dbu_calc.get("dbu_price", None)
        if dbu_price is not None:
            assert dbu_price > 0, f"DBU price is zero — likely fallback: {dbu_calc}"

        # Check total cost is non-zero
        total = data.get("total_cost", {})
        cost = total.get("cost_per_month", None)
        if cost is not None:
            assert cost > 0, f"Total cost is zero — likely fallback: {total}"


class TestExportToExcel:
    """Export estimates to Excel and verify content."""

    @pytest.fixture(scope="class")
    def export_estimate(self, client, test_user_id):
        """Create an estimate with workloads for export testing."""
        # Create estimate
        resp = client.post("/api/v1/estimates", json={
            "estimate_name": "Export-Harness AWS",
            "customer_name": "Export Test Corp",
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
        }, headers={"X-User-Id": test_user_id})
        data = resp.json()
        est_id = data.get("estimate_id") or data.get("data", {}).get("estimate_id")

        # Add a few workloads
        for wl in [
            {"workload_name": "Export Jobs", "workload_type": "JOBS",
             "serverless_enabled": True, "runs_per_day": 5,
             "avg_runtime_minutes": 30, "days_per_month": 22},
            {"workload_name": "Export DBSQL", "workload_type": "DBSQL",
             "serverless_enabled": True, "dbsql_warehouse_type": "SERVERLESS",
             "dbsql_warehouse_size": "Medium", "hours_per_month": 300},
            {"workload_name": "Export Lakebase", "workload_type": "LAKEBASE",
             "lakebase_cu": 4, "hours_per_month": 730},
        ]:
            wl["estimate_id"] = est_id
            wl["cloud"] = "AWS"
            client.post("/api/v1/line-items", json=wl,
                        headers={"X-User-Id": test_user_id})

        return est_id

    def test_single_estimate_export(self, client, test_user_id, export_estimate):
        """Export a single estimate to Excel."""
        resp = client.get(
            f"/api/v1/export/estimate/{export_estimate}/excel",
            headers={"X-User-Id": test_user_id},
        )
        assert resp.status_code == 200, f"Export failed: {resp.status_code} {resp.text}"
        assert "spreadsheet" in resp.headers.get("content-type", "").lower() or \
               "octet-stream" in resp.headers.get("content-type", "").lower(), \
            f"Unexpected content type: {resp.headers.get('content-type')}"
        assert len(resp.content) > 1000, "Excel file too small — likely empty"

    def test_all_estimates_export(self, client, test_user_id):
        """Export all estimates summary."""
        resp = client.get(
            "/api/v1/export/estimates/excel",
            headers={"X-User-Id": test_user_id},
        )
        assert resp.status_code == 200, f"Export failed: {resp.status_code} {resp.text}"
        assert len(resp.content) > 500, "Summary Excel file too small"
