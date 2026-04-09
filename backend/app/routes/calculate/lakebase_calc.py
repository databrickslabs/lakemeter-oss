"""Lakebase calculation endpoint (CU-based, independent pricing).

Compute: billed against Database Serverless SKU at DBU multiplier per CU-hour.
Storage/PITR/Snapshots: billed against Databricks Storage SKU at DSU multipliers per GB-month.
"""
import json
import logging
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.validators import validate_cloud, validate_region, validate_tier, validate_sku_specific_discounts
from app.services.lakebase_queries import get_product_type_for_pricing
from app.routes.calculate.helpers import build_sku_breakdown_serverless
from app.routes.calculate.discount import (
    apply_discount_to_sku_breakdown, calculate_total_discount_summary, enhance_total_cost_with_discount,
)
from app.routes.calculate.schemas import LakebaseCalculationRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# DBU multiplier per CU-hour (Database Serverless Compute SKU)
# Ref: https://www.databricks.com/product/pricing/lakebase
# Azure Premium = AWS/GCP Enterprise tier per pricing page footnote
LAKEBASE_DBU_RATES = {
    "AWS": {"PREMIUM": 0.230, "ENTERPRISE": 0.213},
    "AZURE": {"PREMIUM": 0.213, "ENTERPRISE": 0.213},
    # GCP: Lakebase not available yet
}

VALID_CU_SIZES = [0.5, 1, 2, 4, 8, 16, 32, 48, 64, 80, 96, 112]

# DSU multipliers for Databricks Storage SKU (per GB-month)
# Ref: Database Serverless Compute SKU page
STORAGE_DSU_MULTIPLIER = 15.0
PITR_DSU_MULTIPLIER = 8.7
SNAPSHOT_DSU_MULTIPLIER = 3.91

# Load static DSU/storage pricing
_PRICING_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'static', 'pricing')


def _load_dbu_rates() -> dict:
    path = os.path.join(_PRICING_DIR, 'dbu-rates.json')
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}


DBU_RATES_BY_REGION = _load_dbu_rates()


def _get_dsu_price(cloud: str, region: str, tier: str) -> float:
    """Look up DATABRICKS_STORAGE $/DSU price from static pricing data."""
    key = f"{cloud.lower()}:{region}:{tier.upper()}"
    region_rates = DBU_RATES_BY_REGION.get(key, {})
    if 'DATABRICKS_STORAGE' in region_rates:
        return region_rates['DATABRICKS_STORAGE']
    # Fallback: try without exact region match
    for k, v in DBU_RATES_BY_REGION.items():
        parts = k.split(':')
        if len(parts) == 3 and parts[0] == cloud.lower() and parts[2] == tier.upper():
            if 'DATABRICKS_STORAGE' in v:
                return v['DATABRICKS_STORAGE']
    return 0.023  # default fallback


@router.post("/calculate/lakebase", tags=["Cost Calculation"])
def calculate_lakebase_cost(
    request: LakebaseCalculationRequest,
    db: Session = Depends(get_db),
):
    error = validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])

    cloud_upper = request.cloud.upper()
    tier_upper = request.tier.upper()

    # Lakebase is not available on GCP
    if cloud_upper == "GCP":
        raise HTTPException(status_code=400, detail="Lakebase is not available on GCP yet")

    error = validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])

    if request.cu_size not in VALID_CU_SIZES:
        raise HTTPException(status_code=400, detail=f"Invalid CU size: {request.cu_size}. Valid: {VALID_CU_SIZES}")

    # Resolve num_nodes: prefer num_nodes (frontend sends this), fall back to read_replicas
    if request.num_nodes is not None:
        num_nodes = request.num_nodes
    else:
        num_nodes = 1 + request.read_replicas
    if num_nodes > 3:
        raise HTTPException(status_code=400, detail="Total nodes cannot exceed 3")
    read_replicas = num_nodes - 1

    try:
        # Resolve hours
        if request.hours_per_month is not None:
            hours_per_month = request.hours_per_month
        elif getattr(request, 'hours_per_day', None) is not None:
            days = request.days_per_month or 30
            hours_per_month = request.hours_per_day * days
        else:
            hours_per_month = 730  # default always-on

        # ── Compute cost ──────────────────────────────────────────────
        cloud_rates = LAKEBASE_DBU_RATES.get(cloud_upper, {})
        dbu_per_cu_hour = cloud_rates.get(tier_upper, 0.213)

        total_dbu_per_hour = request.cu_size * dbu_per_cu_hour * num_nodes
        dbu_per_month = total_dbu_per_hour * hours_per_month

        # Look up DBU price from database
        sku_type = get_product_type_for_pricing(db, "LAKEBASE", True, False, None, None, None)
        dbu_price_query = text("""
            SELECT price_per_dbu
            FROM lakemeter.sync_pricing_dbu_rates
            WHERE UPPER(cloud) = UPPER(:cloud)
              AND UPPER(region) = UPPER(:region)
              AND UPPER(tier) = UPPER(:tier)
              AND (UPPER(product_type) = UPPER(:product_type) OR UPPER(sku_name) = UPPER(:product_type))
            LIMIT 1
        """)
        price_row = db.execute(dbu_price_query, {
            "cloud": request.cloud, "region": request.region,
            "tier": request.tier, "product_type": sku_type,
        }).fetchone()
        dbu_price = float(price_row.price_per_dbu) if price_row else 0.0

        compute_cost = dbu_per_month * dbu_price

        # CU metadata
        cu_type = "autoscale" if request.cu_size <= 32 else "fixed"
        ram_gb = request.cu_size * 2

        sku_breakdown = build_sku_breakdown_serverless(
            sku_type=sku_type, dbu_cost=compute_cost,
            dbu_quantity=dbu_per_month, dbu_price=dbu_price,
        )

        # ── Storage / PITR / Snapshot costs ───────────────────────────
        dsu_price = _get_dsu_price(cloud_upper, request.region, tier_upper)
        storage_gb = request.storage_gb or 0
        pitr_gb = request.pitr_gb or 0
        snapshot_gb = request.snapshot_gb or 0

        storage_cost = storage_gb * STORAGE_DSU_MULTIPLIER * dsu_price
        pitr_cost = pitr_gb * PITR_DSU_MULTIPLIER * dsu_price
        snapshot_cost = snapshot_gb * SNAPSHOT_DSU_MULTIPLIER * dsu_price

        if storage_cost > 0:
            sku_breakdown.append({
                "type": "storage",
                "sku": "DATABRICKS_STORAGE",
                "cost": round(storage_cost, 2),
                "qty": round(storage_gb, 2),
                "usage_unit": "GB-month",
                "unit_price_before_discount": round(dsu_price * STORAGE_DSU_MULTIPLIER, 6),
                "rate_type": "database_storage",
            })
        if pitr_cost > 0:
            sku_breakdown.append({
                "type": "storage",
                "sku": "DATABRICKS_STORAGE",
                "cost": round(pitr_cost, 2),
                "qty": round(pitr_gb, 2),
                "usage_unit": "GB-month",
                "unit_price_before_discount": round(dsu_price * PITR_DSU_MULTIPLIER, 6),
                "rate_type": "pitr",
            })
        if snapshot_cost > 0:
            sku_breakdown.append({
                "type": "storage",
                "sku": "DATABRICKS_STORAGE",
                "cost": round(snapshot_cost, 2),
                "qty": round(snapshot_gb, 2),
                "usage_unit": "GB-month",
                "unit_price_before_discount": round(dsu_price * SNAPSHOT_DSU_MULTIPLIER, 6),
                "rate_type": "snapshots",
            })

        total_cost = compute_cost + storage_cost + pitr_cost + snapshot_cost

        # ── Discount ──────────────────────────────────────────────────
        if request.discount_config:
            if request.discount_config.sku_specific:
                error = validate_sku_specific_discounts(request.discount_config.sku_specific, db)
                if error:
                    raise HTTPException(status_code=400, detail=error["error"])
            sku_breakdown = apply_discount_to_sku_breakdown(sku_breakdown, request.discount_config, db)

        response_data = {
            "success": True,
            "data": {
                "workload_type": "LAKEBASE", "sku_type": sku_type,
                "configuration": {
                    "cloud": cloud_upper, "region": request.region, "tier": tier_upper,
                    "cu_size": request.cu_size, "cu_type": cu_type, "ram_gb": ram_gb,
                    "read_replicas": read_replicas, "total_nodes": num_nodes,
                },
                "usage": {"hours_per_month": hours_per_month},
                "dbu_calculation": {
                    "dbu_per_cu_hour": dbu_per_cu_hour,
                    "dbu_per_hour_per_compute": round(request.cu_size * dbu_per_cu_hour, 4),
                    "dbu_per_hour": round(total_dbu_per_hour, 4),
                    "total_dbu_per_hour": round(total_dbu_per_hour, 4),
                    "dbu_per_month": round(dbu_per_month, 2),
                    "dbu_price": dbu_price,
                    "dbu_cost_per_month": round(compute_cost, 2),
                },
                "storage_calculation": {
                    "dsu_price": dsu_price,
                    "storage_gb": storage_gb,
                    "storage_dsu_multiplier": STORAGE_DSU_MULTIPLIER,
                    "storage_cost": round(storage_cost, 2),
                    "pitr_gb": pitr_gb,
                    "pitr_dsu_multiplier": PITR_DSU_MULTIPLIER,
                    "pitr_cost": round(pitr_cost, 2),
                    "snapshot_gb": snapshot_gb,
                    "snapshot_dsu_multiplier": SNAPSHOT_DSU_MULTIPLIER,
                    "snapshot_cost": round(snapshot_cost, 2),
                },
                "total_cost": {"cost_per_month": round(total_cost, 2)},
                "sku_breakdown": sku_breakdown,
            },
        }

        if request.discount_config:
            response_data["data"]["total_cost"] = enhance_total_cost_with_discount(
                response_data["data"]["total_cost"], sku_breakdown)
            response_data["data"]["discount_summary"] = calculate_total_discount_summary(sku_breakdown)

        return response_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating Lakebase cost: {e}")
        return {"success": False, "error": {"code": "CALCULATION_ERROR", "message": str(e)}}
