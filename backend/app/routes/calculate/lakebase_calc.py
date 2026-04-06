"""Lakebase calculation endpoint (CU-based, independent pricing)."""
import logging
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

# Hardcoded DBU/CU-hour rates by cloud/tier
LAKEBASE_DBU_RATES = {
    "AWS": {"PREMIUM": 0.230, "ENTERPRISE": 0.213},
    "AZURE": {"PREMIUM": 1.0, "ENTERPRISE": 1.0},
    "GCP": {"PREMIUM": 1.0, "ENTERPRISE": 1.0},
}

VALID_CU_SIZES = [0.5, 1, 2, 4, 8, 16, 32, 48, 64, 80, 96, 112]


@router.post("/calculate/lakebase", tags=["Cost Calculation"])
def calculate_lakebase_cost(
    request: LakebaseCalculationRequest,
    db: Session = Depends(get_db),
):
    error = validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])

    if request.cu_size not in VALID_CU_SIZES:
        raise HTTPException(status_code=400, detail=f"Invalid CU size: {request.cu_size}. Valid: {VALID_CU_SIZES}")

    num_nodes = 1 + request.read_replicas
    if num_nodes > 3:
        raise HTTPException(status_code=400, detail="Total nodes (1 primary + read_replicas) cannot exceed 3")

    try:
        # Resolve hours
        if request.hours_per_month is not None:
            hours_per_month = request.hours_per_month
        elif getattr(request, 'hours_per_day', None) is not None:
            days = request.days_per_month or 30
            hours_per_month = request.hours_per_day * days
        else:
            hours_per_month = 730  # default always-on

        # Look up DBU/CU-hour rate
        cloud_upper = request.cloud.upper()
        tier_upper = request.tier.upper()
        cloud_rates = LAKEBASE_DBU_RATES.get(cloud_upper, {})
        dbu_per_cu_hour = cloud_rates.get(tier_upper, 1.0)

        # Calculate DBUs
        total_dbu_per_hour = request.cu_size * dbu_per_cu_hour * num_nodes
        dbu_per_month = total_dbu_per_hour * hours_per_month

        # Look up DBU price
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

        dbu_cost_per_month = dbu_per_month * dbu_price

        # CU metadata
        cu_type = "autoscale" if request.cu_size <= 32 else "fixed"
        ram_gb = request.cu_size * 2

        sku_breakdown = build_sku_breakdown_serverless(
            sku_type=sku_type, dbu_cost=dbu_cost_per_month,
            dbu_quantity=dbu_per_month, dbu_price=dbu_price,
        )

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
                    "read_replicas": request.read_replicas, "total_nodes": num_nodes,
                },
                "usage": {"hours_per_month": hours_per_month},
                "dbu_calculation": {
                    "dbu_per_cu_hour": dbu_per_cu_hour,
                    "dbu_per_hour_per_compute": round(request.cu_size * dbu_per_cu_hour, 4),
                    "dbu_per_hour": round(total_dbu_per_hour, 4),
                    "total_dbu_per_hour": round(total_dbu_per_hour, 4),
                    "dbu_per_month": round(dbu_per_month, 2),
                    "dbu_price": dbu_price,
                    "dbu_cost_per_month": round(dbu_cost_per_month, 2),
                },
                "total_cost": {"cost_per_month": round(dbu_cost_per_month, 2)},
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
