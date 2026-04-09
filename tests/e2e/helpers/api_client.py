"""E2E API client: wraps TestClient with convenience methods for
creating estimates, adding line items, calculating costs, and exporting Excel.
"""
import uuid
from io import BytesIO
from typing import Optional

AUTH_EMAIL = "e2e-test@databricks.com"
AUTH_HEADERS = {"X-Forwarded-Email": AUTH_EMAIL}


class E2EClient:
    """Stateful E2E test client wrapping FastAPI TestClient."""

    def __init__(self, http_client):
        self.http = http_client
        self._created_estimates = []

    # ── Estimates ──────────────────────────────────────────────────────────

    def create_estimate(self, name: str, cloud: str, region: str, tier: str) -> dict:
        resp = self.http.post("/api/v1/estimates/", json={
            "estimate_name": name,
            "cloud": cloud,
            "region": region,
            "tier": tier,
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 201, f"Create estimate failed: {resp.text}"
        data = resp.json()
        self._created_estimates.append(data["estimate_id"])
        return data

    def delete_estimate(self, estimate_id: str):
        self.http.delete(f"/api/v1/estimates/{estimate_id}", headers=AUTH_HEADERS)

    def cleanup(self):
        for eid in self._created_estimates:
            try:
                self.delete_estimate(eid)
            except Exception:
                pass
        self._created_estimates.clear()

    # ── Line Items ────────────────────────────────────────────────────────

    def add_line_item(self, estimate_id: str, payload: dict) -> dict:
        payload["estimate_id"] = estimate_id
        resp = self.http.post("/api/v1/line-items/", json=payload, headers=AUTH_HEADERS)
        assert resp.status_code == 201, f"Add line item failed: {resp.text}"
        return resp.json()

    def get_line_items(self, estimate_id: str) -> list:
        resp = self.http.get(
            f"/api/v1/line-items/estimate/{estimate_id}", headers=AUTH_HEADERS
        )
        assert resp.status_code == 200, f"Get line items failed: {resp.text}"
        return resp.json()

    # ── Calculation ───────────────────────────────────────────────────────

    def calculate(self, endpoint: str, payload: dict) -> dict:
        resp = self.http.post(f"/api/v1{endpoint}", json=payload)
        assert resp.status_code == 200, f"Calculate failed ({endpoint}): {resp.text}"
        result = resp.json()
        assert result.get("success"), f"Calculation returned success=false: {result}"
        return result["data"]

    def calculate_jobs_classic(self, cloud: str, region: str, tier: str,
                               driver: str, worker: str, num_workers: int,
                               photon: bool = False,
                               usage: Optional[dict] = None,
                               pricing_tier: str = "on_demand",
                               discount_config: Optional[dict] = None) -> dict:
        payload = {
            "cloud": cloud, "region": region, "tier": tier,
            "driver_node_type": driver, "worker_node_type": worker,
            "num_workers": num_workers, "photon_enabled": photon,
            "driver_pricing_tier": pricing_tier, "worker_pricing_tier": pricing_tier,
        }
        if usage:
            payload.update(usage)
        if discount_config:
            payload["discount_config"] = discount_config
        return self.calculate("/calculate/jobs-classic", payload)

    def calculate_jobs_serverless(self, cloud: str, region: str, tier: str,
                                   mode: str = "standard",
                                   usage: Optional[dict] = None,
                                   discount_config: Optional[dict] = None) -> dict:
        payload = {
            "cloud": cloud, "region": region, "tier": tier,
            "serverless_mode": mode,
        }
        if usage:
            payload.update(usage)
        if discount_config:
            payload["discount_config"] = discount_config
        return self.calculate("/calculate/jobs-serverless", payload)

    def calculate_dbsql_classic_pro(self, cloud: str, region: str, tier: str,
                                     warehouse_type: str, warehouse_size: str,
                                     usage: Optional[dict] = None,
                                     pricing_tier: str = "on_demand",
                                     discount_config: Optional[dict] = None) -> dict:
        payload = {
            "cloud": cloud, "region": region, "tier": tier,
            "warehouse_type": warehouse_type, "warehouse_size": warehouse_size,
            "driver_pricing_tier": pricing_tier, "worker_pricing_tier": pricing_tier,
        }
        if usage:
            payload.update(usage)
        if discount_config:
            payload["discount_config"] = discount_config
        return self.calculate("/calculate/dbsql-classic-pro", payload)

    def calculate_dbsql_serverless(self, cloud: str, region: str, tier: str,
                                    warehouse_size: str,
                                    usage: Optional[dict] = None,
                                    discount_config: Optional[dict] = None) -> dict:
        payload = {
            "cloud": cloud, "region": region, "tier": tier,
            "warehouse_size": warehouse_size,
        }
        if usage:
            payload.update(usage)
        if discount_config:
            payload["discount_config"] = discount_config
        return self.calculate("/calculate/dbsql-serverless", payload)

    def calculate_allpurpose_classic(self, cloud: str, region: str, tier: str,
                                      driver: str, worker: str, num_workers: int,
                                      photon: bool = False,
                                      usage: Optional[dict] = None,
                                      pricing_tier: str = "on_demand",
                                      discount_config: Optional[dict] = None) -> dict:
        payload = {
            "cloud": cloud, "region": region, "tier": tier,
            "driver_node_type": driver, "worker_node_type": worker,
            "num_workers": num_workers, "photon_enabled": photon,
            "driver_pricing_tier": pricing_tier, "worker_pricing_tier": pricing_tier,
        }
        if usage:
            payload.update(usage)
        if discount_config:
            payload["discount_config"] = discount_config
        return self.calculate("/calculate/all-purpose-classic", payload)

    def calculate_allpurpose_serverless(self, cloud: str, region: str, tier: str,
                                         mode: str = "standard",
                                         usage: Optional[dict] = None,
                                         discount_config: Optional[dict] = None) -> dict:
        payload = {
            "cloud": cloud, "region": region, "tier": tier,
            "serverless_mode": mode,
        }
        if usage:
            payload.update(usage)
        if discount_config:
            payload["discount_config"] = discount_config
        return self.calculate("/calculate/all-purpose-serverless", payload)

    def calculate_dlt_classic(self, cloud: str, region: str, tier: str,
                               edition: str, driver: str, worker: str,
                               num_workers: int, photon: bool = False,
                               usage: Optional[dict] = None,
                               pricing_tier: str = "on_demand",
                               discount_config: Optional[dict] = None) -> dict:
        payload = {
            "cloud": cloud, "region": region, "tier": tier,
            "dlt_edition": edition,
            "driver_node_type": driver, "worker_node_type": worker,
            "num_workers": num_workers, "photon_enabled": photon,
            "driver_pricing_tier": pricing_tier, "worker_pricing_tier": pricing_tier,
        }
        if usage:
            payload.update(usage)
        if discount_config:
            payload["discount_config"] = discount_config
        return self.calculate("/calculate/dlt-classic", payload)

    def calculate_dlt_serverless(self, cloud: str, region: str, tier: str,
                                  edition: str, mode: str = "standard",
                                  usage: Optional[dict] = None,
                                  discount_config: Optional[dict] = None) -> dict:
        payload = {
            "cloud": cloud, "region": region, "tier": tier,
            "dlt_edition": edition, "serverless_mode": mode,
        }
        if usage:
            payload.update(usage)
        if discount_config:
            payload["discount_config"] = discount_config
        return self.calculate("/calculate/dlt-serverless", payload)

    def calculate_vector_search(self, cloud: str, region: str, tier: str,
                                 mode: str, num_vectors_millions: float,
                                 usage: Optional[dict] = None,
                                 discount_config: Optional[dict] = None) -> dict:
        payload = {
            "cloud": cloud, "region": region, "tier": tier,
            "mode": mode, "num_vectors_millions": num_vectors_millions,
        }
        if usage:
            payload.update(usage)
        if discount_config:
            payload["discount_config"] = discount_config
        return self.calculate("/calculate/vector-search", payload)

    def calculate_model_serving(self, cloud: str, region: str, tier: str,
                                 gpu_type: str, scale_out: str = "small",
                                 usage: Optional[dict] = None,
                                 discount_config: Optional[dict] = None) -> dict:
        payload = {
            "cloud": cloud, "region": region, "tier": tier,
            "gpu_type": gpu_type, "scale_out": scale_out,
        }
        if usage:
            payload.update(usage)
        if discount_config:
            payload["discount_config"] = discount_config
        return self.calculate("/calculate/model-serving", payload)

    def calculate_fmapi_databricks(self, cloud: str, region: str, tier: str,
                                    model: str,
                                    input_tokens: float = 0,
                                    output_tokens: float = 0,
                                    discount_config: Optional[dict] = None) -> dict:
        payload = {
            "cloud": cloud, "region": region, "tier": tier,
            "model": model,
            "input_tokens_per_month": input_tokens,
            "output_tokens_per_month": output_tokens,
        }
        if discount_config:
            payload["discount_config"] = discount_config
        return self.calculate("/calculate/fmapi-databricks", payload)

    def calculate_fmapi_proprietary(self, cloud: str, region: str, tier: str,
                                     provider: str, model: str,
                                     input_tokens: float = 0,
                                     output_tokens: float = 0,
                                     discount_config: Optional[dict] = None) -> dict:
        payload = {
            "cloud": cloud, "region": region, "tier": tier,
            "provider": provider, "model": model,
            "input_tokens_per_month": input_tokens,
            "output_tokens_per_month": output_tokens,
        }
        if discount_config:
            payload["discount_config"] = discount_config
        return self.calculate("/calculate/fmapi-proprietary", payload)

    def calculate_lakebase(self, cloud: str, region: str, tier: str,
                            cu_size: float, read_replicas: int = 0,
                            usage: Optional[dict] = None,
                            discount_config: Optional[dict] = None) -> dict:
        payload = {
            "cloud": cloud, "region": region, "tier": tier,
            "cu_size": cu_size, "read_replicas": read_replicas,
        }
        if usage:
            payload.update(usage)
        if discount_config:
            payload["discount_config"] = discount_config
        return self.calculate("/calculate/lakebase", payload)

    # ── New Workload Types ─────────────────────────────────────────────────

    def calculate_databricks_apps(self, cloud: str, region: str, tier: str,
                                   size: str = "medium",
                                   usage: Optional[dict] = None,
                                   discount_config: Optional[dict] = None) -> dict:
        payload = {
            "cloud": cloud, "region": region, "tier": tier,
            "size": size,
        }
        if usage:
            payload.update(usage)
        if discount_config:
            payload["discount_config"] = discount_config
        return self.calculate("/calculate/databricks-apps", payload)

    def calculate_clean_room(self, cloud: str, region: str, tier: str,
                              collaborators: int,
                              days_per_month: int = 30,
                              discount_config: Optional[dict] = None) -> dict:
        payload = {
            "cloud": cloud, "region": region, "tier": tier,
            "collaborators": collaborators, "days_per_month": days_per_month,
        }
        if discount_config:
            payload["discount_config"] = discount_config
        return self.calculate("/calculate/clean-room", payload)

    def calculate_ai_parse(self, cloud: str, region: str, tier: str,
                            mode: str = "pages",
                            complexity: Optional[str] = None,
                            pages_thousands: Optional[float] = None,
                            hours_per_month: Optional[float] = None,
                            discount_config: Optional[dict] = None) -> dict:
        payload: dict = {
            "cloud": cloud, "region": region, "tier": tier,
            "mode": mode,
        }
        if complexity:
            payload["complexity"] = complexity
        if pages_thousands is not None:
            payload["pages_thousands"] = pages_thousands
        if hours_per_month is not None:
            payload["hours_per_month"] = hours_per_month
        if discount_config:
            payload["discount_config"] = discount_config
        return self.calculate("/calculate/ai-parse", payload)

    def calculate_shutterstock(self, cloud: str, region: str, tier: str,
                                images_per_month: int,
                                discount_config: Optional[dict] = None) -> dict:
        payload = {
            "cloud": cloud, "region": region, "tier": tier,
            "images_per_month": images_per_month,
        }
        if discount_config:
            payload["discount_config"] = discount_config
        return self.calculate("/calculate/shutterstock-imageai", payload)

    def calculate_lakeflow_connect(self, cloud: str, region: str, tier: str,
                                    dlt_edition: str = "ADVANCED",
                                    gateway_enabled: bool = False,
                                    gateway_instance_type: Optional[str] = None,
                                    usage: Optional[dict] = None,
                                    discount_config: Optional[dict] = None) -> dict:
        payload: dict = {
            "cloud": cloud, "region": region, "tier": tier,
            "dlt_edition": dlt_edition, "gateway_enabled": gateway_enabled,
        }
        if gateway_instance_type:
            payload["gateway_instance_type"] = gateway_instance_type
        if usage:
            payload.update(usage)
        if discount_config:
            payload["discount_config"] = discount_config
        return self.calculate("/calculate/lakeflow-connect", payload)

    # ── Export ─────────────────────────────────────────────────────────────

    def export_excel(self, estimate_id: str) -> BytesIO:
        resp = self.http.get(
            f"/api/v1/export/estimate/{estimate_id}/excel", headers=AUTH_HEADERS
        )
        assert resp.status_code == 200, f"Export failed: {resp.text[:200]}"
        return BytesIO(resp.content)
