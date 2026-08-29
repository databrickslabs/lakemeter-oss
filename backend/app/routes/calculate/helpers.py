"""Shared helper functions for calculation endpoints."""
from fastapi import HTTPException
from sqlalchemy import text


def get_sku_type(
    workload_type: str,
    serverless_enabled: bool = False,
    photon_enabled: bool = False,
    dlt_edition: str = None,
    dbsql_warehouse_type: str = None,
    fmapi_provider: str = None,
) -> str:
    """Determine the SKU product type based on workload configuration."""
    workload_upper = workload_type.upper()

    if workload_upper == "JOBS":
        if serverless_enabled:
            return "JOBS_SERVERLESS_COMPUTE"
        elif photon_enabled:
            return "JOBS_COMPUTE_(PHOTON)"
        else:
            return "JOBS_COMPUTE"

    elif workload_upper == "ALL_PURPOSE":
        if serverless_enabled:
            return "ALL_PURPOSE_SERVERLESS_COMPUTE"
        elif photon_enabled:
            return "ALL_PURPOSE_COMPUTE_(PHOTON)"
        else:
            return "ALL_PURPOSE_COMPUTE"

    elif workload_upper == "DLT":
        if serverless_enabled:
            return "DELTA_LIVE_TABLES_SERVERLESS"
        else:
            edition = (dlt_edition or "CORE").upper()
            base = f"DLT_{edition}_COMPUTE"
            return f"{base}_(PHOTON)" if photon_enabled else base

    elif workload_upper == "DBSQL":
        warehouse_type_upper = (dbsql_warehouse_type or "CLASSIC").upper()
        if warehouse_type_upper == "SERVERLESS":
            return "SERVERLESS_SQL_COMPUTE"
        elif warehouse_type_upper == "PRO":
            return "SQL_PRO_COMPUTE"
        else:
            return "SQL_COMPUTE"

    elif workload_upper == "VECTOR_SEARCH":
        return "SERVERLESS_REAL_TIME_INFERENCE"

    elif workload_upper == "MODEL_SERVING":
        return "SERVERLESS_REAL_TIME_INFERENCE"

    elif workload_upper == "AI_RUNTIME":
        return "MODEL_TRAINING"

    elif workload_upper == "GENERAL_STORAGE":
        return "DATABRICKS_STORAGE"

    elif workload_upper == "ZEROBUS":
        return "JOBS_SERVERLESS_COMPUTE"

    elif workload_upper == "FMAPI_DATABRICKS":
        return "SERVERLESS_REAL_TIME_INFERENCE"

    elif workload_upper == "FMAPI_PROPRIETARY":
        if fmapi_provider:
            return f"{fmapi_provider.upper()}_MODEL_SERVING"
        return "MODEL_SERVING"

    elif workload_upper == "LAKEBASE":
        return "DATABASE_SERVERLESS_COMPUTE"

    elif workload_upper == "DATABRICKS_APPS":
        return "ALL_PURPOSE_SERVERLESS_COMPUTE"

    elif workload_upper in (
        "AI_PARSE",
        "AI_EXTRACT",
        "AI_CLASSIFY",
        "AI_GATEWAY",
        "AGENT_EVALUATION",
        "SHUTTERSTOCK_IMAGEAI",
    ):
        return "SERVERLESS_REAL_TIME_INFERENCE"

    elif workload_upper == "LAKEFLOW_CONNECT":
        return "JOBS_SERVERLESS_COMPUTE"

    raise ValueError(f"Unsupported workload type: {workload_type!r}")


def get_required_regional_dbu_price(
    db,
    cloud: str,
    region: str,
    tier: str,
    sku_type: str,
) -> float:
    """Return an exact regional DBU price or reject the calculation."""
    price_row = db.execute(text("""
        SELECT price_per_dbu FROM lakemeter.sync_pricing_dbu_rates
        WHERE UPPER(cloud) = UPPER(:cloud) AND UPPER(region) = UPPER(:region)
          AND UPPER(tier) = UPPER(:tier)
          AND (UPPER(product_type) = UPPER(:pt) OR UPPER(sku_name) = UPPER(:pt))
        LIMIT 1
    """), {
        "cloud": cloud,
        "region": region,
        "tier": tier,
        "pt": sku_type,
    }).fetchone()
    if price_row is None or price_row.price_per_dbu is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"{sku_type} pricing is not available for "
                f"{cloud.upper()} {region} {tier.upper()}"
            ),
        )
    price = float(price_row.price_per_dbu)
    if price <= 0:
        raise HTTPException(
            status_code=400,
            detail=(
                f"{sku_type} pricing is invalid for "
                f"{cloud.upper()} {region} {tier.upper()}"
            ),
        )
    return price


def build_sku_breakdown_classic(
    sku_type: str,
    dbu_cost: float,
    dbu_quantity: float,
    dbu_price: float,
    driver_vm_cost: float,
    worker_vm_cost: float,
    hours_per_month: float,
    driver_vm_price_per_hour: float,
    worker_vm_price_per_hour: float,
    driver_pricing_tier: str,
    worker_pricing_tier: str,
    num_workers: int,
):
    """Build flat-list SKU breakdown for classic compute workloads."""
    breakdown = []

    if dbu_cost > 0:
        breakdown.append({
            "type": "dbu",
            "sku": sku_type,
            "cost": round(dbu_cost, 2),
            "qty": round(dbu_quantity, 2),
            "usage_unit": "DBU",
            "unit_price_before_discount": round(dbu_price, 6),
        })

    if driver_vm_cost > 0:
        breakdown.append({
            "type": "vm",
            "sku": f"VM_{driver_pricing_tier.upper()}",
            "cost": round(driver_vm_cost, 2),
            "qty": round(hours_per_month, 2),
            "usage_unit": "DBU",
            "unit_price_before_discount": round(driver_vm_price_per_hour, 6),
        })

    if worker_vm_cost > 0 and num_workers > 0:
        breakdown.append({
            "type": "vm",
            "sku": f"VM_{worker_pricing_tier.upper()}",
            "cost": round(worker_vm_cost, 2),
            "qty": round(hours_per_month * num_workers, 2),
            "usage_unit": "DBU",
            "unit_price_before_discount": round(worker_vm_price_per_hour, 6),
        })

    return breakdown


def build_sku_breakdown_serverless(
    sku_type: str,
    dbu_cost: float,
    dbu_quantity: float,
    dbu_price: float,
):
    """Build flat-list SKU breakdown for serverless workloads (DBU only)."""
    breakdown = []
    if dbu_cost > 0:
        breakdown.append({
            "type": "dbu",
            "sku": sku_type,
            "cost": round(dbu_cost, 2),
            "qty": round(dbu_quantity, 2),
            "usage_unit": "DBU",
            "unit_price_before_discount": round(dbu_price, 6),
        })
    return breakdown
