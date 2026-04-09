#!/usr/bin/env python3
"""
Populate All Workload Combinations

Creates an estimate with every workload type and configuration variant,
covering ALL DBSQL sizes, DLT editions, serverless/classic modes,
run-based/hourly usage, vector search modes, model serving GPUs,
FMAPI providers, and Lakebase configs.

Usage:
    python scripts/populate_all_workloads.py --url https://lakemeter-e2e-v2-335310294452632.aws.databricksapps.com
    python scripts/populate_all_workloads.py --url http://localhost:8000
"""
import argparse
import json
import sys
import requests

# ---------------------------------------------------------------------------
# Workload definitions: every combination
# ---------------------------------------------------------------------------

# A few representative VM instance types (not exhaustive — user said "a few")
VM_INSTANCES = {
    "aws": [
        ("i3.xlarge", "i3.xlarge"),
        ("m5d.2xlarge", "m5d.4xlarge"),
        ("r5d.xlarge", "r5d.2xlarge"),
    ],
    "azure": [
        ("Standard_DS3_v2", "Standard_DS4_v2"),
    ],
    "gcp": [
        ("n2-highmem-4", "n2-highmem-8"),
    ],
}

DBSQL_SIZES = [
    "2X-Small", "X-Small", "Small", "Medium",
    "Large", "X-Large", "2X-Large", "3X-Large", "4X-Large",
]

DBSQL_TYPES = ["SERVERLESS", "PRO", "CLASSIC"]

DLT_EDITIONS = ["CORE", "PRO", "ADVANCED"]

MODEL_SERVING_GPUS = [
    # GPU type IDs must match keys in model-serving-rates.json
    "cpu", "gpu_small_t4", "gpu_medium_a10g_1x",
    "gpu_medium_a10g_4x", "gpu_xlarge_a100_40gb_8x",
]

FMAPI_PROPRIETARY_CONFIGS = [
    # (provider, model, endpoint, context, rate_type)
    # Model names must match keys in fmapi-proprietary-rates.json
    ("anthropic", "claude-sonnet-3-7", "global", "long", "input_token"),
    ("anthropic", "claude-sonnet-3-7", "global", "long", "output_token"),
    ("openai", "gpt-5", "global", "all", "input_token"),
    ("openai", "gpt-5", "global", "all", "output_token"),
    ("google", "gemini-2-5-flash", "global", "long", "input_token"),
    ("google", "gemini-2-5-flash", "global", "long", "output_token"),
    ("anthropic", "claude-sonnet-3-7", "global", "long", "cache_read"),
    ("anthropic", "claude-sonnet-3-7", "global", "long", "cache_write"),
]

FMAPI_DATABRICKS_CONFIGS = [
    ("llama-3-3-70b", "input_token"),
    ("llama-3-3-70b", "output_token"),
    ("llama-3-1-8b", "input_token"),
    ("llama-3-1-8b", "output_token"),
    ("gemma-3-12b", "input_token"),
]

LAKEBASE_CONFIGS = [
    (0.5, 100, 1, 7),   # Small: 0.5 CU, 100GB, 1 node
    (2, 500, 1, 14),     # Medium: 2 CU, 500GB
    (4, 1000, 2, 30),    # Large: 4 CU, 1TB, 2 HA nodes
    (8, 2000, 3, 35),    # XL: 8 CU, 2TB, 3 HA nodes
]


def build_workloads(cloud: str) -> list[dict]:
    """Build the full list of line items for every workload combination."""
    items = []
    order = 0
    driver, worker = VM_INSTANCES.get(cloud, VM_INSTANCES["aws"])[0]

    # =========================================================================
    # 1. JOBS — Classic (Photon on/off) × (run-based / hourly) + Serverless
    # =========================================================================
    for photon in [False, True]:
        label = "Photon" if photon else "Classic"
        # Run-based usage
        items.append({
            "workload_name": f"Jobs {label} (Run-based)",
            "workload_type": "JOBS",
            "display_order": (order := order + 1),
            "photon_enabled": photon,
            "serverless_enabled": False,
            "driver_node_type": driver,
            "worker_node_type": worker,
            "num_workers": 4,
            "runs_per_day": 6,
            "avg_runtime_minutes": 45,
            "days_per_month": 22,
            "driver_pricing_tier": "on_demand",
            "worker_pricing_tier": "on_demand",
        })
        # Hourly usage
        items.append({
            "workload_name": f"Jobs {label} (Hourly)",
            "workload_type": "JOBS",
            "display_order": (order := order + 1),
            "photon_enabled": photon,
            "serverless_enabled": False,
            "driver_node_type": driver,
            "worker_node_type": worker,
            "num_workers": 2,
            "hours_per_month": 160,
            "driver_pricing_tier": "on_demand",
            "worker_pricing_tier": "on_demand",
        })

    # Jobs Serverless (standard + performance)
    for mode in ["standard", "performance"]:
        items.append({
            "workload_name": f"Jobs Serverless ({mode.title()})",
            "workload_type": "JOBS",
            "display_order": (order := order + 1),
            "serverless_enabled": True,
            "serverless_mode": mode,
            "driver_node_type": driver,
            "worker_node_type": worker,
            "num_workers": 4,
            "runs_per_day": 10,
            "avg_runtime_minutes": 30,
            "days_per_month": 22,
        })

    # =========================================================================
    # 2. ALL PURPOSE — Classic (Photon on/off) + Serverless
    # =========================================================================
    for photon in [False, True]:
        label = "Photon" if photon else "Classic"
        items.append({
            "workload_name": f"All-Purpose {label}",
            "workload_type": "ALL_PURPOSE",
            "display_order": (order := order + 1),
            "photon_enabled": photon,
            "serverless_enabled": False,
            "driver_node_type": driver,
            "worker_node_type": worker,
            "num_workers": 3,
            "hours_per_month": 200,
            "driver_pricing_tier": "on_demand",
            "worker_pricing_tier": "on_demand",
        })

    items.append({
        "workload_name": "All-Purpose Serverless",
        "workload_type": "ALL_PURPOSE",
        "display_order": (order := order + 1),
        "serverless_enabled": True,
        "driver_node_type": driver,
        "worker_node_type": worker,
        "num_workers": 2,
        "hours_per_month": 160,
    })

    # =========================================================================
    # 3. DLT — Every edition × (Classic/Photon/Serverless)
    # =========================================================================
    for edition in DLT_EDITIONS:
        # Classic
        items.append({
            "workload_name": f"DLT {edition} Classic",
            "workload_type": "DLT",
            "display_order": (order := order + 1),
            "dlt_edition": edition,
            "photon_enabled": False,
            "serverless_enabled": False,
            "driver_node_type": driver,
            "worker_node_type": worker,
            "num_workers": 4,
            "runs_per_day": 4,
            "avg_runtime_minutes": 60,
            "days_per_month": 30,
        })
        # Photon
        items.append({
            "workload_name": f"DLT {edition} Photon",
            "workload_type": "DLT",
            "display_order": (order := order + 1),
            "dlt_edition": edition,
            "photon_enabled": True,
            "serverless_enabled": False,
            "driver_node_type": driver,
            "worker_node_type": worker,
            "num_workers": 4,
            "runs_per_day": 4,
            "avg_runtime_minutes": 60,
            "days_per_month": 30,
        })
        # Serverless
        items.append({
            "workload_name": f"DLT {edition} Serverless",
            "workload_type": "DLT",
            "display_order": (order := order + 1),
            "dlt_edition": edition,
            "serverless_enabled": True,
            "driver_node_type": driver,
            "worker_node_type": worker,
            "num_workers": 4,
            "runs_per_day": 4,
            "avg_runtime_minutes": 60,
            "days_per_month": 30,
        })

    # =========================================================================
    # 4. DBSQL — Every warehouse type × every size
    # =========================================================================
    for wh_type in DBSQL_TYPES:
        for size in DBSQL_SIZES:
            items.append({
                "workload_name": f"DBSQL {wh_type} {size}",
                "workload_type": "DBSQL",
                "display_order": (order := order + 1),
                "dbsql_warehouse_type": wh_type,
                "dbsql_warehouse_size": size,
                "dbsql_num_clusters": 1,
                "hours_per_month": 160,
                "notes": f"{wh_type} warehouse, {size}",
            })

    # DBSQL multi-cluster examples
    for clusters in [2, 4, 8]:
        items.append({
            "workload_name": f"DBSQL Serverless Medium ×{clusters}",
            "workload_type": "DBSQL",
            "display_order": (order := order + 1),
            "dbsql_warehouse_type": "SERVERLESS",
            "dbsql_warehouse_size": "Medium",
            "dbsql_num_clusters": clusters,
            "hours_per_month": 200,
            "notes": f"Multi-cluster: {clusters} clusters",
        })

    # =========================================================================
    # 5. VECTOR SEARCH — Standard + Storage Optimized, with storage
    # =========================================================================
    for mode, capacity in [("standard", 5), ("standard", 50), ("storage_optimized", 50), ("storage_optimized", 200)]:
        storage = capacity * 2  # Rough storage estimate
        items.append({
            "workload_name": f"Vector Search {mode.replace('_', ' ').title()} {capacity}M",
            "workload_type": "VECTOR_SEARCH",
            "display_order": (order := order + 1),
            "vector_search_mode": mode,
            "vector_capacity_millions": capacity,
            "vector_search_storage_gb": storage,
            "hours_per_month": 730,
            "notes": f"{capacity}M vectors, {storage}GB storage",
        })

    # =========================================================================
    # 6. MODEL SERVING — Every GPU type
    # =========================================================================
    for gpu in MODEL_SERVING_GPUS:
        items.append({
            "workload_name": f"Model Serving ({gpu})",
            "workload_type": "MODEL_SERVING",
            "display_order": (order := order + 1),
            "model_serving_gpu_type": gpu,
            "hours_per_month": 730,
            "notes": f"GPU type: {gpu}",
        })

    # =========================================================================
    # 7. FMAPI PROPRIETARY — Every provider × rate type
    # =========================================================================
    for provider, model, endpoint, context, rate_type in FMAPI_PROPRIETARY_CONFIGS:
        items.append({
            "workload_name": f"FMAPI {provider.title()} {model} ({rate_type})",
            "workload_type": "FMAPI_PROPRIETARY",
            "display_order": (order := order + 1),
            "fmapi_provider": provider,
            "fmapi_model": model,
            "fmapi_endpoint_type": endpoint,
            "fmapi_context_length": context,
            "fmapi_rate_type": rate_type,
            "fmapi_quantity": 50,
            "notes": f"{provider}/{model} — {rate_type}",
        })

    # =========================================================================
    # 8. FMAPI DATABRICKS — Databricks OSS models
    # =========================================================================
    for model, rate_type in FMAPI_DATABRICKS_CONFIGS:
        items.append({
            "workload_name": f"FMAPI DB {model.replace('databricks-', '')} ({rate_type})",
            "workload_type": "FMAPI_DATABRICKS",
            "display_order": (order := order + 1),
            "fmapi_provider": "databricks",
            "fmapi_model": model,
            "fmapi_endpoint_type": "foundation_model",
            "fmapi_rate_type": rate_type,
            "fmapi_quantity": 100,
            "notes": f"Databricks OSS: {model} — {rate_type}",
        })

    # =========================================================================
    # 9. LAKEBASE — Various CU/storage/HA combinations
    # =========================================================================
    for cu, storage, nodes, retention in LAKEBASE_CONFIGS:
        items.append({
            "workload_name": f"Lakebase CU{cu} {storage}GB {'HA' if nodes > 1 else 'Single'}",
            "workload_type": "LAKEBASE",
            "display_order": (order := order + 1),
            "lakebase_cu": cu,
            "lakebase_storage_gb": storage,
            "lakebase_ha_nodes": nodes,
            "lakebase_backup_retention_days": retention,
            "hours_per_month": 730,
            "notes": f"CU={cu}, {storage}GB, {nodes} node(s), {retention}d retention",
        })

    # =========================================================================
    # 10. VM PRICING VARIANTS — A few Jobs with different pricing tiers
    # =========================================================================
    for driver_inst, worker_inst in VM_INSTANCES.get(cloud, VM_INSTANCES["aws"]):
        for pricing_tier in ["on_demand", "1yr_reserved", "3yr_reserved"]:
            for payment in ["no_upfront", "partial_upfront", "all_upfront"]:
                if pricing_tier == "on_demand" and payment != "no_upfront":
                    continue  # On-demand doesn't have upfront options
                items.append({
                    "workload_name": f"Jobs VM {driver_inst} {pricing_tier} {payment}",
                    "workload_type": "JOBS",
                    "display_order": (order := order + 1),
                    "driver_node_type": driver_inst,
                    "worker_node_type": worker_inst,
                    "num_workers": 4,
                    "photon_enabled": False,
                    "hours_per_month": 200,
                    "driver_pricing_tier": pricing_tier,
                    "worker_pricing_tier": pricing_tier,
                    "driver_payment_option": payment,
                    "worker_payment_option": payment,
                    "notes": f"VM pricing: {pricing_tier}/{payment}",
                })

    return items


def create_estimate(session: requests.Session, base_url: str,
                    cloud: str, region: str, tier: str) -> str:
    """Create an estimate and return its ID."""
    resp = session.post(f"{base_url}/api/v1/estimates/", json={
        "estimate_name": f"[TEST] All Workloads — {cloud.upper()} {region} {tier.upper()}",
        "cloud": cloud.upper(),
        "region": region,
        "tier": tier.upper(),
        "status": "draft",
    })
    if resp.status_code != 201:
        print(f"  FAILED to create estimate: {resp.status_code} {resp.text[:200]}")
        sys.exit(1)
    eid = resp.json()["estimate_id"]
    print(f"  Created estimate: {eid}")
    return eid


def create_line_items(session: requests.Session, base_url: str,
                      estimate_id: str, items: list[dict]) -> int:
    """Create all line items. Returns count of successfully created items."""
    ok = 0
    for i, item in enumerate(items):
        item["estimate_id"] = estimate_id
        resp = session.post(f"{base_url}/api/v1/line-items/", json=item)
        if resp.status_code == 201:
            ok += 1
        else:
            print(f"  [{i+1}/{len(items)}] FAILED: {item['workload_name']}")
            print(f"    {resp.status_code}: {resp.text[:200]}")
        if (i + 1) % 20 == 0:
            print(f"  [{i+1}/{len(items)}] created...")
    return ok


def main():
    parser = argparse.ArgumentParser(description="Populate ALL workload combinations")
    parser.add_argument("--url", required=True, help="Base URL of the Lakemeter app")
    parser.add_argument("--cloud", default="aws", choices=["aws", "azure", "gcp"])
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--tier", default="PREMIUM")
    parser.add_argument("--token", help="OAuth token (for Databricks Apps auth)")
    args = parser.parse_args()

    base = args.url.rstrip("/")
    session = requests.Session()
    session.headers["Content-Type"] = "application/json"
    if args.token:
        session.headers["Authorization"] = f"Bearer {args.token}"

    print(f"\n{'='*60}")
    print(f"  Lakemeter — Populate ALL Workload Combinations")
    print(f"  URL:    {base}")
    print(f"  Cloud:  {args.cloud}")
    print(f"  Region: {args.region}")
    print(f"  Tier:   {args.tier}")
    print(f"{'='*60}\n")

    # Build workload list
    items = build_workloads(args.cloud)
    print(f"Total workloads to create: {len(items)}")

    # Breakdown
    types = {}
    for item in items:
        wt = item["workload_type"]
        types[wt] = types.get(wt, 0) + 1
    for wt, count in sorted(types.items()):
        print(f"  {wt:25s}: {count}")
    print()

    # Create estimate
    estimate_id = create_estimate(session, base, args.cloud, args.region, args.tier)

    # Create all line items
    ok = create_line_items(session, base, estimate_id, items)
    print(f"\nDone: {ok}/{len(items)} workloads created successfully")
    print(f"Estimate ID: {estimate_id}")
    print(f"View at: {base}/ → open the estimate '[TEST] All Workloads'")


if __name__ == "__main__":
    main()
