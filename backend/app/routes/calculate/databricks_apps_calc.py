"""Databricks Apps calculation endpoint.

Databricks Apps uses ALL_PURPOSE_SERVERLESS_COMPUTE SKU.
Sizes: medium (0.5 DBU/hr), large (1.0 DBU/hr). Always-on (730 hrs/month default).
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.validators import validate_cloud, validate_region, validate_tier, validate_sku_specific_discounts
from app.services.lakebase_queries import get_product_type_for_pricing
from app.routes.calculate.helpers import build_sku_breakdown_serverless
from app.routes.calculate.discount import (
    apply_discount_to_sku_breakdown, calculate_total_discount_summary, enhance_total_cost_with_discount,
)
from app.routes.calculate.schemas import DatabricksAppsCalculationRequest

logger = logging.getLogger(__name__)
router = APIRouter()

APPS_DBU_RATES = {
    "medium": 0.5,
    "large": 1.0,
}


@router.post("/calculate/databricks-apps", tags=["Cost Calculation"])
def calculate_databricks_apps_cost(
    request: DatabricksAppsCalculationRequest,
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

    size = (request.size or "medium").lower()
    if size not in APPS_DBU_RATES:
        raise HTTPException(status_code=400, detail=f"Invalid size: {size}. Valid: medium, large")

    try:
        hours_per_month = request.hours_per_month if request.hours_per_month is not None else 730
        dbu_per_hour = APPS_DBU_RATES[size]
        dbu_per_month = dbu_per_hour * hours_per_month

        sku_type = get_product_type_for_pricing(db, "DATABRICKS_APPS", True, False, None, None, None)
        # Look up DBU price
        from sqlalchemy import text
        price_row = db.execute(text("""
            SELECT price_per_dbu FROM lakemeter.sync_pricing_dbu_rates
            WHERE UPPER(cloud) = UPPER(:cloud) AND UPPER(region) = UPPER(:region)
              AND UPPER(tier) = UPPER(:tier)
              AND (UPPER(product_type) = UPPER(:pt) OR UPPER(sku_name) = UPPER(:pt))
            LIMIT 1
        """), {"cloud": request.cloud, "region": request.region, "tier": request.tier, "pt": sku_type}).fetchone()
        dbu_price = float(price_row.price_per_dbu) if price_row else 0.0

        dbu_cost = dbu_per_month * dbu_price

        sku_breakdown = build_sku_breakdown_serverless(
            sku_type=sku_type, dbu_cost=dbu_cost,
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
                "workload_type": "DATABRICKS_APPS", "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(), "region": request.region,
                    "tier": request.tier.upper(), "size": size,
                },
                "usage": {"hours_per_month": hours_per_month},
                "dbu_calculation": {
                    "dbu_per_hour": dbu_per_hour,
                    "dbu_per_month": round(dbu_per_month, 2),
                    "dbu_price": dbu_price,
                    "dbu_cost_per_month": round(dbu_cost, 2),
                },
                "total_cost": {"cost_per_month": round(dbu_cost, 2)},
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
        logger.error(f"Error calculating Databricks Apps cost: {e}")
        return {"success": False, "error": {"code": "CALCULATION_ERROR", "message": str(e)}}
