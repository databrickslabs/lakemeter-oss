#!/usr/bin/env python3
"""Convert JSON pricing files to pre-flattened CSV for Lakebase loading.

Reads each JSON file from backend/static/pricing/, applies the same
transformation logic as the installer's _load_*() functions, and writes
one CSV per target table. Also exports vm-costs.csv and sku-region-map.csv
from Unity Catalog via Databricks SDK.

Usage:
    # Convert JSON files only (no UC export)
    python scripts/convert_pricing_to_csv.py

    # Convert JSON files + export from UC
    python scripts/convert_pricing_to_csv.py --profile lakemeter

    # Export UC tables only (skip JSON conversion)
    python scripts/convert_pricing_to_csv.py --profile lakemeter --uc-only
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
PRICING_DIR = PROJECT_ROOT / "backend" / "static" / "pricing"


def convert_dbu_rates():
    """dbu-rates.json -> dbu-rates.csv"""
    src = PRICING_DIR / "dbu-rates.json"
    dst = PRICING_DIR / "dbu-rates.csv"
    with open(src) as f:
        data = json.load(f)

    now = datetime.utcnow().isoformat()
    rows = []
    for key, rate in data.items():
        parts = key.split(":")
        if len(parts) < 3:
            continue
        cloud, region, tier = parts[0], parts[1], parts[2]
        if isinstance(rate, dict):
            for sku_name, val in rate.items():
                if isinstance(val, dict):
                    rows.append({
                        "sku_name": sku_name,
                        "cloud": cloud.upper(),
                        "tier": tier,
                        "product_type": val.get("product_type", ""),
                        "sku_region": val.get("sku_region", ""),
                        "region": region,
                        "usage_unit": val.get("usage_unit", "DBU"),
                        "price_per_dbu": val.get("price_per_dbu", 0),
                        "currency_code": val.get("currency_code", "USD"),
                        "pricing_type": val.get("pricing_type", ""),
                        "fetched_at": now,
                    })
                else:
                    rows.append({
                        "sku_name": sku_name,
                        "cloud": cloud.upper(),
                        "tier": tier,
                        "product_type": "",
                        "sku_region": "",
                        "region": region,
                        "usage_unit": "DBU",
                        "price_per_dbu": float(val) if val else 0,
                        "currency_code": "USD",
                        "pricing_type": "",
                        "fetched_at": now,
                    })

    cols = ["sku_name", "cloud", "tier", "product_type", "sku_region", "region",
            "usage_unit", "price_per_dbu", "currency_code", "pricing_type", "fetched_at"]
    _write_csv(dst, cols, rows)
    return len(rows)


def convert_instance_dbu_rates():
    """instance-dbu-rates.json -> instance-dbu-rates.csv"""
    src = PRICING_DIR / "instance-dbu-rates.json"
    dst = PRICING_DIR / "instance-dbu-rates.csv"
    with open(src) as f:
        data = json.load(f)

    rows = []
    for key, val in data.items():
        if isinstance(val, dict) and "dbu_rate" not in val:
            cloud = key
            for instance_type, info in val.items():
                if isinstance(info, dict):
                    rows.append({
                        "cloud": cloud.upper(),
                        "instance_type": instance_type,
                        "vcpus": info.get("vcpus", 0),
                        "memory_gb": info.get("memory_gb", 0),
                        "dbu_rate": info.get("dbu_rate", 0),
                        "instance_family": info.get("family", info.get("instance_family", "")),
                        "is_active": True,
                        "source": "pricing_bundle",
                    })
        else:
            parts = key.split(":")
            if len(parts) < 2:
                continue
            cloud, instance_type = parts[0], parts[1]
            info = val if isinstance(val, dict) else {}
            rows.append({
                "cloud": cloud.upper(),
                "instance_type": instance_type,
                "vcpus": info.get("vcpus", 0),
                "memory_gb": info.get("memory_gb", 0),
                "dbu_rate": info.get("dbu_rate", 0),
                "instance_family": info.get("family", info.get("instance_family", "")),
                "is_active": True,
                "source": "pricing_bundle",
            })

    cols = ["cloud", "instance_type", "vcpus", "memory_gb", "dbu_rate",
            "instance_family", "is_active", "source"]
    _write_csv(dst, cols, rows)
    return len(rows)


def convert_dbu_multipliers():
    """dbu-multipliers.json -> dbu-multipliers.csv"""
    src = PRICING_DIR / "dbu-multipliers.json"
    dst = PRICING_DIR / "dbu-multipliers.csv"
    with open(src) as f:
        data = json.load(f)

    rows = []
    for key, info in data.items():
        parts = key.split(":")
        if len(parts) < 3:
            continue
        cloud, sku_type, feature = parts[0], parts[1], parts[2]
        rows.append({
            "cloud": cloud.upper(),
            "sku_type": sku_type,
            "feature": feature,
            "multiplier": info.get("multiplier", 1.0),
            "category": info.get("category", ""),
        })

    cols = ["cloud", "sku_type", "feature", "multiplier", "category"]
    _write_csv(dst, cols, rows)
    return len(rows)


def convert_dbsql_rates():
    """dbsql-rates.json -> dbsql-rates.csv"""
    src = PRICING_DIR / "dbsql-rates.json"
    dst = PRICING_DIR / "dbsql-rates.csv"
    with open(src) as f:
        data = json.load(f)

    rows = []
    for key, info in data.items():
        parts = key.split(":")
        if len(parts) < 3:
            continue
        cloud, wh_type, wh_size = parts[0], parts[1], parts[2]
        rows.append({
            "cloud": cloud.upper(),
            "warehouse_type": wh_type,
            "warehouse_size": wh_size,
            "sku_product_type": info.get("sku_product_type", ""),
            "dbu_per_hour": info.get("dbu_per_hour", 0),
            "includes_compute": info.get("includes_compute", False),
        })

    cols = ["cloud", "warehouse_type", "warehouse_size", "sku_product_type",
            "dbu_per_hour", "includes_compute"]
    _write_csv(dst, cols, rows)
    return len(rows)


def convert_dbsql_warehouse_config():
    """dbsql-warehouse-config.json -> dbsql-warehouse-config.csv"""
    src = PRICING_DIR / "dbsql-warehouse-config.json"
    dst = PRICING_DIR / "dbsql-warehouse-config.csv"
    with open(src) as f:
        data = json.load(f)

    rows = []
    for key, info in data.items():
        parts = key.split(":")
        if len(parts) < 3:
            continue
        cloud, wh_size, wh_type = parts[0], parts[1], parts[2] if len(parts) > 2 else ""
        rows.append({
            "cloud": cloud.upper(),
            "warehouse_size": wh_size,
            "worker_count": str(info.get("worker_count", "")),
            "driver_instance_type": info.get("driver_instance_type", ""),
            "worker_instance_type": info.get("worker_instance_type", ""),
            "warehouse_type": wh_type,
        })

    cols = ["cloud", "warehouse_size", "worker_count", "driver_instance_type",
            "worker_instance_type", "warehouse_type"]
    _write_csv(dst, cols, rows)
    return len(rows)


def convert_serverless_rates():
    """model-serving-rates.json + vector-search-rates.json -> serverless-rates.csv"""
    dst = PRICING_DIR / "serverless-rates.csv"
    rows = []

    # Model serving
    src = PRICING_DIR / "model-serving-rates.json"
    with open(src) as f:
        data = json.load(f)
    for key, info in data.items():
        parts = key.split(":")
        if len(parts) < 2:
            continue
        cloud, model_or_type = parts[0].upper(), parts[1]
        if isinstance(info, dict):
            rows.append({
                "cloud": cloud,
                "product": "model_serving",
                "size_or_model": model_or_type,
                "rate_type": info.get("rate_type", ""),
                "dbu_rate": info.get("dbu_rate", 0),
                "input_divisor": info.get("input_divisor", ""),
                "is_hourly": info.get("is_hourly", False),
                "sku_product_type": info.get("sku_product_type", ""),
                "description": info.get("description", ""),
            })

    # Vector search
    src = PRICING_DIR / "vector-search-rates.json"
    with open(src) as f:
        data = json.load(f)
    for key, info in data.items():
        parts = key.split(":")
        if len(parts) < 2:
            continue
        cloud, ep_type = parts[0].upper(), parts[1]
        if isinstance(info, dict):
            rows.append({
                "cloud": cloud,
                "product": "vector_search",
                "size_or_model": ep_type,
                "rate_type": info.get("rate_type", ""),
                "dbu_rate": info.get("dbu_rate", 0),
                "input_divisor": info.get("input_divisor", ""),
                "is_hourly": info.get("is_hourly", True),
                "sku_product_type": info.get("sku_product_type", ""),
                "description": info.get("description", ""),
            })

    cols = ["cloud", "product", "size_or_model", "rate_type", "dbu_rate",
            "input_divisor", "is_hourly", "sku_product_type", "description"]
    _write_csv(dst, cols, rows)
    return len(rows)


def convert_fmapi_databricks():
    """fmapi-databricks-rates.json -> fmapi-databricks-rates.csv"""
    src = PRICING_DIR / "fmapi-databricks-rates.json"
    dst = PRICING_DIR / "fmapi-databricks-rates.csv"
    with open(src) as f:
        data = json.load(f)

    rows = []
    for key, rate in data.items():
        parts = key.split(":")
        if len(parts) < 3:
            continue
        cloud, model, rate_type = parts[0].upper(), parts[1], parts[2]
        if isinstance(rate, (int, float)):
            rows.append({
                "cloud": cloud, "model": model, "rate_type": rate_type,
                "dbu_rate": rate, "input_divisor": "", "is_hourly": False,
                "sku_product_type": "",
            })
        elif isinstance(rate, dict):
            rows.append({
                "cloud": cloud, "model": model, "rate_type": rate_type,
                "dbu_rate": rate.get("dbu_rate", 0),
                "input_divisor": rate.get("input_divisor", ""),
                "is_hourly": rate.get("is_hourly", False),
                "sku_product_type": rate.get("sku_product_type", ""),
            })

    cols = ["cloud", "model", "rate_type", "dbu_rate", "input_divisor",
            "is_hourly", "sku_product_type"]
    _write_csv(dst, cols, rows)
    return len(rows)


def convert_fmapi_proprietary():
    """fmapi-proprietary-rates.json -> fmapi-proprietary-rates.csv"""
    src = PRICING_DIR / "fmapi-proprietary-rates.json"
    dst = PRICING_DIR / "fmapi-proprietary-rates.csv"
    with open(src) as f:
        data = json.load(f)

    rows = []
    for key, rate in data.items():
        parts = key.split(":")
        if len(parts) < 3:
            continue
        cloud_or_provider = parts[0]
        model = parts[1]
        rate_type = parts[2]

        if isinstance(rate, dict):
            rows.append({
                "provider": rate.get("provider", cloud_or_provider),
                "model": model,
                "endpoint_type": rate.get("endpoint_type", ""),
                "context_length": rate.get("context_length", ""),
                "rate_type": rate_type,
                "dbu_rate": rate.get("dbu_rate", 0),
                "input_divisor": rate.get("input_divisor", ""),
                "is_hourly": rate.get("is_hourly", False),
                "sku_product_type": rate.get("sku_product_type", ""),
                "cloud": rate.get("cloud", cloud_or_provider.upper()),
            })
        elif isinstance(rate, (int, float)):
            rows.append({
                "provider": cloud_or_provider,
                "model": model,
                "endpoint_type": "",
                "context_length": "",
                "rate_type": rate_type,
                "dbu_rate": rate,
                "input_divisor": "",
                "is_hourly": False,
                "sku_product_type": "",
                "cloud": cloud_or_provider.upper(),
            })

    cols = ["provider", "model", "endpoint_type", "context_length", "rate_type",
            "dbu_rate", "input_divisor", "is_hourly", "sku_product_type", "cloud"]
    _write_csv(dst, cols, rows)
    return len(rows)


def export_uc_vm_costs(profile: str):
    """Export lakemeter_catalog.lakemeter.pricing_vm_costs -> vm-costs.csv"""
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient(profile=profile)
    warehouse_id = _get_warehouse_id(w)

    dst = PRICING_DIR / "vm-costs.csv"
    cols = ["cloud", "region", "instance_type", "pricing_tier", "payment_option",
            "cost_per_hour", "currency", "source", "fetched_at"]

    print(f"  Fetching vm-costs from UC (this may take a minute)...")
    rows = _fetch_uc_table(
        w, warehouse_id,
        "SELECT cloud, region, instance_type, pricing_tier, payment_option, "
        "cost_per_hour, currency, source, fetched_at "
        "FROM lakemeter_catalog.lakemeter.pricing_vm_costs"
    )
    _write_csv(dst, cols, [dict(zip(cols, r)) for r in rows])
    return len(rows)


def export_uc_sku_region_map(profile: str):
    """Export lakemeter_catalog.lakemeter.sync_ref_sku_region_map -> sku-region-map.csv"""
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient(profile=profile)
    warehouse_id = _get_warehouse_id(w)

    dst = PRICING_DIR / "sku-region-map.csv"
    cols = ["cloud", "sku_region", "region_code"]

    print(f"  Fetching sku-region-map from UC...")
    rows = _fetch_uc_table(
        w, warehouse_id,
        "SELECT cloud, sku_region, region_code "
        "FROM lakemeter_catalog.lakemeter.sync_ref_sku_region_map"
    )
    _write_csv(dst, cols, [dict(zip(cols, r)) for r in rows])
    return len(rows)


def _get_warehouse_id(w):
    """Find the first available SQL warehouse."""
    warehouses = list(w.warehouses.list())
    for wh in warehouses:
        state = wh.state.value if hasattr(wh.state, 'value') else str(wh.state)
        if state in ("RUNNING", "STOPPED", "STARTING"):
            return wh.id
    # Fall back to first warehouse if none are in expected state
    if warehouses:
        return warehouses[0].id
    raise RuntimeError("No SQL warehouse found")


def _fetch_uc_table(w, warehouse_id: str, sql: str) -> list:
    """Execute SQL and return all rows, handling pagination."""
    from databricks.sdk.service.sql import Disposition, Format

    resp = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=sql,
        disposition=Disposition.INLINE,
        format=Format.JSON_ARRAY,
        wait_timeout="50s",
    )

    if resp.status.state.value == "FAILED":
        raise RuntimeError(f"SQL failed: {resp.status.error}")

    rows = []
    if resp.result and resp.result.data_array:
        rows.extend(resp.result.data_array)

    # Handle chunked results
    if resp.result and resp.result.next_chunk_index is not None:
        chunk_idx = resp.result.next_chunk_index
        while chunk_idx is not None:
            chunk = w.statement_execution.get_statement_result_chunk_n(
                resp.statement_id, chunk_idx
            )
            if chunk.data_array:
                rows.extend(chunk.data_array)
            chunk_idx = chunk.next_chunk_index

    print(f"    Got {len(rows)} rows")
    return rows


def _write_csv(path: Path, columns: list, rows: list):
    """Write rows (list of dicts) to CSV."""
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Wrote {path.name}: {len(rows)} rows")


def update_manifest(has_uc: bool):
    """Update manifest.json to list CSV files."""
    csv_files = sorted(p.name for p in PRICING_DIR.glob("*.csv"))
    manifest = {
        "generated_at": datetime.utcnow().isoformat(),
        "format": "csv",
        "total_files": len(csv_files),
        "files": csv_files,
    }
    dst = PRICING_DIR / "manifest.json"
    with open(dst, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nUpdated manifest.json: {len(csv_files)} CSV files")


def main():
    parser = argparse.ArgumentParser(description="Convert pricing JSON to CSV")
    parser.add_argument("--profile", help="Databricks CLI profile for UC export")
    parser.add_argument("--uc-only", action="store_true", help="Only export UC tables")
    args = parser.parse_args()

    if not PRICING_DIR.exists():
        print(f"ERROR: Pricing directory not found: {PRICING_DIR}", file=sys.stderr)
        sys.exit(1)

    total = 0

    if not args.uc_only:
        print("Converting JSON files to CSV...")
        converters = [
            ("dbu-rates", convert_dbu_rates),
            ("instance-dbu-rates", convert_instance_dbu_rates),
            ("dbu-multipliers", convert_dbu_multipliers),
            ("dbsql-rates", convert_dbsql_rates),
            ("dbsql-warehouse-config", convert_dbsql_warehouse_config),
            ("serverless-rates", convert_serverless_rates),
            ("fmapi-databricks", convert_fmapi_databricks),
            ("fmapi-proprietary", convert_fmapi_proprietary),
        ]
        for name, fn in converters:
            count = fn()
            total += count
        print(f"\nConverted {total} rows from 9 JSON files into 8 CSV files")

    if args.profile:
        print("\nExporting UC tables...")
        total += export_uc_vm_costs(args.profile)
        total += export_uc_sku_region_map(args.profile)

    update_manifest(has_uc=bool(args.profile))
    print(f"\nDone. Total: {total} rows across all CSV files")


if __name__ == "__main__":
    main()
