"""
Harness Test (ii): Add ~100 workload line items per estimate.

Generates a comprehensive matrix of workload combinations:
- Jobs Classic (3 instance combos x 2 photon) = 6
- Jobs Serverless (2 modes) = 2
- All-Purpose Classic (3 instance combos x 2 photon) = 6
- All-Purpose Serverless (2 modes) = 2
- DBSQL Classic (3 sizes) = 3
- DBSQL Pro (3 sizes) = 3
- DBSQL Serverless (6 sizes) = 6
- DLT Classic (3 editions x 2 photon) = 6
- DLT Serverless (3 editions) = 3
- Model Serving (3 GPU types x 3 scale-outs) = 9
- Vector Search (2 modes x 3 capacities) = 6
- FMAPI Databricks (6 models) = 6
- FMAPI Proprietary (6 provider/model combos) = 6
- Lakebase (7 CU sizes) = 7

Total per estimate: ~71 line items. We pad with extra variations to reach ~100.
"""
import pytest
from tests.harness.conftest import (
    ESTIMATE_CONFIGS, INSTANCE_TYPES, DBSQL_WAREHOUSE_SIZES,
    DLT_EDITIONS, VECTOR_SEARCH_MODES, LAKEBASE_CU_SIZES,
    GPU_TYPES, MODEL_SERVING_SCALE_OUTS,
)


def _cloud_instances(cloud):
    cloud_upper = cloud.upper()
    inst = INSTANCE_TYPES.get(cloud_upper, INSTANCE_TYPES["AWS"])
    return inst["driver"], inst["worker"]


def generate_workload_line_items(cloud, region, tier):
    """Generate ~100 line item payloads for a given cloud/region/tier."""
    items = []
    drivers, workers = _cloud_instances(cloud)
    counter = [0]

    def add(workload_type, name_suffix, **extra):
        counter[0] += 1
        item = {
            "workload_name": f"WL-{counter[0]:03d} {workload_type} {name_suffix}",
            "workload_type": workload_type,
            "cloud": cloud.upper(),
            **extra,
        }
        items.append(item)

    # ── Jobs Classic (6) ──────────────────────────────────────────────────
    for i, (drv, wrk) in enumerate(zip(drivers, workers)):
        for photon in [False, True]:
            add("JOBS", f"Classic {'Photon' if photon else 'Std'} {drv}",
                serverless_enabled=False, photon_enabled=photon,
                driver_node_type=drv, worker_node_type=wrk,
                num_workers=2 + i, runs_per_day=4, avg_runtime_minutes=30,
                days_per_month=22)

    # ── Jobs Serverless (2) ───────────────────────────────────────────────
    for mode in ["standard", "performance"]:
        add("JOBS", f"Serverless {mode}",
            serverless_enabled=True, serverless_mode=mode,
            runs_per_day=10, avg_runtime_minutes=15, days_per_month=30)

    # ── All-Purpose Classic (6) ───────────────────────────────────────────
    for i, (drv, wrk) in enumerate(zip(drivers, workers)):
        for photon in [False, True]:
            add("ALL_PURPOSE", f"Classic {'Photon' if photon else 'Std'} {drv}",
                serverless_enabled=False, photon_enabled=photon,
                driver_node_type=drv, worker_node_type=wrk,
                num_workers=1 + i, hours_per_month=160)

    # ── All-Purpose Serverless (2) ────────────────────────────────────────
    for mode in ["standard", "performance"]:
        add("ALL_PURPOSE", f"Serverless {mode}",
            serverless_enabled=True, serverless_mode=mode,
            hours_per_month=200)

    # ── DBSQL Classic (3) ─────────────────────────────────────────────────
    for size in DBSQL_WAREHOUSE_SIZES[:3]:
        add("DBSQL", f"Classic {size}",
            serverless_enabled=False,
            dbsql_warehouse_type="CLASSIC", dbsql_warehouse_size=size,
            hours_per_month=300)

    # ── DBSQL Pro (3) ─────────────────────────────────────────────────────
    for size in DBSQL_WAREHOUSE_SIZES[:3]:
        add("DBSQL", f"Pro {size}",
            serverless_enabled=False,
            dbsql_warehouse_type="PRO", dbsql_warehouse_size=size,
            hours_per_month=300)

    # ── DBSQL Serverless (6) ──────────────────────────────────────────────
    for size in DBSQL_WAREHOUSE_SIZES:
        add("DBSQL", f"Serverless {size}",
            serverless_enabled=True,
            dbsql_warehouse_type="SERVERLESS", dbsql_warehouse_size=size,
            hours_per_month=400)

    # ── DLT Classic (6) ───────────────────────────────────────────────────
    for edition in DLT_EDITIONS:
        for photon in [False, True]:
            add("DLT", f"Classic {edition} {'Photon' if photon else 'Std'}",
                serverless_enabled=False, dlt_edition=edition,
                photon_enabled=photon,
                driver_node_type=drivers[0], worker_node_type=workers[0],
                num_workers=2, runs_per_day=3, avg_runtime_minutes=45,
                days_per_month=22)

    # ── DLT Serverless (3) ────────────────────────────────────────────────
    for edition in DLT_EDITIONS:
        add("DLT", f"Serverless {edition}",
            serverless_enabled=True, dlt_edition=edition,
            runs_per_day=6, avg_runtime_minutes=20, days_per_month=30)

    # ── Model Serving (9) ─────────────────────────────────────────────────
    for gpu in GPU_TYPES:
        for scale in MODEL_SERVING_SCALE_OUTS:
            add("MODEL_SERVING", f"{gpu} {scale}",
                model_serving_gpu_type=gpu, hours_per_month=730,
                workload_config={"scale_out": scale})

    # ── Vector Search (6) ─────────────────────────────────────────────────
    for mode in VECTOR_SEARCH_MODES:
        for cap in [10, 50, 200]:
            add("VECTOR_SEARCH", f"{mode} {cap}M vectors",
                vector_search_mode=mode,
                vector_capacity_millions=cap, hours_per_month=730)

    # ── FMAPI Databricks (6) ──────────────────────────────────────────────
    fmapi_db_models = [
        "databricks-meta-llama-3-3-70b-instruct",
        "databricks-claude-sonnet-4",
        "databricks-dbrx-instruct",
        "databricks-mixtral-8x7b-instruct",
        "databricks-llama-2-70b-chat",
        "databricks-mpt-30b-instruct",
    ]
    for model in fmapi_db_models:
        add("FMAPI_DATABRICKS", f"DB {model.split('-')[-1]}",
            fmapi_model=model,
            workload_config={
                "input_tokens_per_month": 50_000_000,
                "output_tokens_per_month": 10_000_000,
            })

    # ── FMAPI Proprietary (6) ─────────────────────────────────────────────
    fmapi_prop = [
        ("anthropic", "claude-sonnet-4-20250514"),
        ("anthropic", "claude-3-5-haiku-20241022"),
        ("openai", "gpt-4o-2024-11-20"),
        ("openai", "gpt-4o-mini-2024-07-18"),
        ("google", "gemini-2.0-flash-001"),
        ("google", "gemini-1.5-pro-002"),
    ]
    for provider, model in fmapi_prop:
        add("FMAPI_PROPRIETARY", f"Prop {provider}/{model.split('-')[0]}",
            fmapi_provider=provider, fmapi_model=model,
            fmapi_endpoint_type="in_geo",
            workload_config={
                "input_tokens_per_month": 100_000_000,
                "output_tokens_per_month": 20_000_000,
            })

    # ── Lakebase (7) ──────────────────────────────────────────────────────
    for cu in LAKEBASE_CU_SIZES:
        replicas = 0 if cu <= 2 else min(2, int(cu / 8))
        add("LAKEBASE", f"CU {cu} ({replicas}R)",
            lakebase_cu=cu, lakebase_ha_nodes=replicas,
            hours_per_month=730)

    # ── Extra padding to reach ~100 ───────────────────────────────────────
    # Additional Jobs Serverless with different run patterns
    for rpd in [1, 5, 20, 50]:
        add("JOBS", f"Serverless heavy-{rpd}rpd",
            serverless_enabled=True, serverless_mode="standard",
            runs_per_day=rpd, avg_runtime_minutes=60, days_per_month=30)

    # Additional All-Purpose with varying hours
    for hrs in [40, 80, 160, 320, 500, 730]:
        add("ALL_PURPOSE", f"Serverless {hrs}h/mo",
            serverless_enabled=True, serverless_mode="standard",
            hours_per_month=hrs)

    return items


class TestAddWorkloads:
    """Add ~100 workload line items to each of the 6 estimates."""

    estimate_ids: list[str] = []
    items_per_estimate: dict[str, int] = {}

    @pytest.fixture(autouse=True, scope="class")
    def setup_workloads(self, client, test_user_id):
        """Create estimates and add workloads."""
        TestAddWorkloads.estimate_ids = []
        TestAddWorkloads.items_per_estimate = {}

        for cfg in ESTIMATE_CONFIGS:
            # Create estimate
            resp = client.post(
                "/api/v1/estimates",
                json={
                    "estimate_name": f"WL-Harness {cfg['name']}",
                    "customer_name": "Harness Workloads Corp",
                    "cloud": cfg["cloud"],
                    "region": cfg["region"],
                    "tier": cfg["tier"],
                },
                headers={"X-User-Id": test_user_id},
            )
            assert resp.status_code in (200, 201), f"Estimate creation failed: {resp.text}"
            data = resp.json()
            est_id = data.get("estimate_id") or data.get("data", {}).get("estimate_id")
            TestAddWorkloads.estimate_ids.append(est_id)

            # Generate and add workloads
            workloads = generate_workload_line_items(
                cfg["cloud"], cfg["region"], cfg["tier"]
            )
            success_count = 0
            for wl in workloads:
                wl["estimate_id"] = est_id
                resp = client.post(
                    "/api/v1/line-items",
                    json=wl,
                    headers={"X-User-Id": test_user_id},
                )
                if resp.status_code in (200, 201):
                    success_count += 1
            TestAddWorkloads.items_per_estimate[est_id] = success_count

    def test_six_estimates_exist(self):
        assert len(TestAddWorkloads.estimate_ids) == 6

    def test_minimum_workloads_per_estimate(self):
        """Each estimate should have at least 70 line items (some may fail on missing ref data)."""
        for est_id, count in TestAddWorkloads.items_per_estimate.items():
            assert count >= 70, (
                f"Estimate {est_id} only has {count} workloads (expected >= 70)"
            )

    def test_total_workloads_across_all(self):
        total = sum(TestAddWorkloads.items_per_estimate.values())
        assert total >= 420, f"Total workloads: {total} (expected >= 420 across 6 estimates)"

    @pytest.mark.parametrize("idx", range(6))
    def test_workload_types_coverage(self, client, test_user_id, idx):
        """Each estimate should contain at least 8 different workload types."""
        est_id = TestAddWorkloads.estimate_ids[idx]
        resp = client.get(
            f"/api/v1/line-items?estimate_id={est_id}",
            headers={"X-User-Id": test_user_id},
        )
        assert resp.status_code == 200
        items = resp.json()
        if isinstance(items, dict):
            items = items.get("data", items.get("line_items", []))
        types = set(item.get("workload_type", "") for item in items)
        expected_types = {
            "JOBS", "ALL_PURPOSE", "DBSQL", "DLT",
            "MODEL_SERVING", "VECTOR_SEARCH", "FMAPI_DATABRICKS",
            "FMAPI_PROPRIETARY", "LAKEBASE",
        }
        missing = expected_types - types
        assert len(missing) <= 2, (
            f"Estimate {idx} missing workload types: {missing}. Got: {types}"
        )
