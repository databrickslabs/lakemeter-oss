"""Model Serving calculation endpoint (GPU-based, independent pricing)."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.model_serving_pricing import (
    calculate_model_serving_dbu_per_hour,
    get_billing_capacity_units,
    is_gpu_workload_type,
)
from app.services.validators import validate_cloud, validate_region, validate_tier, validate_sku_specific_discounts
from app.services.lakebase_queries import get_product_type_for_pricing
from app.routes.calculate.helpers import build_sku_breakdown_serverless
from app.routes.calculate.discount import (
    apply_discount_to_sku_breakdown, calculate_total_discount_summary, enhance_total_cost_with_discount,
)
from app.routes.calculate.jobs import normalize_usage_params
from app.routes.calculate.schemas import ModelServingCalculationRequest

logger = logging.getLogger(__name__)
router = APIRouter()

SCALE_OUT_PRESETS = {"small": 4, "medium": 12, "large": 40}


@router.post("/calculate/model-serving", tags=["Cost Calculation"])
def calculate_model_serving_cost(
    request: ModelServingCalculationRequest,
    db: Session = Depends(get_db),
):
    usage = normalize_usage_params(request, mode="daily_or_monthly")

    error = validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])

    # Resolve concurrency
    if request.scale_out == "custom":
        if request.custom_concurrency is None or request.custom_concurrency < 4:
            raise HTTPException(status_code=400, detail="custom_concurrency must be >= 4 for custom scale_out")
        if request.custom_concurrency % 4 != 0:
            raise HTTPException(status_code=400, detail="custom_concurrency must be a multiple of 4")
        concurrency = request.custom_concurrency
    else:
        concurrency = SCALE_OUT_PRESETS.get(request.scale_out)
        if concurrency is None:
            raise HTTPException(status_code=400, detail=f"Invalid scale_out: {request.scale_out}")

    try:
        # Look up GPU DBU rate from serverless_rates
        gpu_query = text("""
            SELECT dbu_rate
            FROM lakemeter.sync_product_serverless_rates
            WHERE product = 'model_serving'
              AND UPPER(cloud) = UPPER(:cloud)
              AND size_or_model = :gpu_type
            LIMIT 1
        """)
        gpu_row = db.execute(gpu_query, {"cloud": request.cloud, "gpu_type": request.gpu_type}).fetchone()
        if not gpu_row:
            raise HTTPException(status_code=400, detail=f"GPU type '{request.gpu_type}' not found for {request.cloud}")

        gpu_dbu_rate = float(gpu_row.dbu_rate)

        hours_per_month = usage.hours_per_month or 0

        # GPU rates are per replica and one replica provides four concurrency
        # units. CPU rates remain per concurrency unit.
        capacity_units = get_billing_capacity_units(
            request.gpu_type, concurrency
        )
        dbu_per_hour = calculate_model_serving_dbu_per_hour(
            gpu_dbu_rate, request.gpu_type, concurrency
        )
        dbu_per_month = dbu_per_hour * hours_per_month
        is_gpu = is_gpu_workload_type(request.gpu_type)
        capacity_label = "GPU replicas" if is_gpu else "CPU concurrency"

        # Look up DBU price
        sku_type = get_product_type_for_pricing(db, "MODEL_SERVING", False, False, None, None, None)
        dbu_price_query = text("""
            SELECT price_per_dbu
            FROM lakemeter.sync_pricing_dbu_rates
            WHERE UPPER(cloud) = UPPER(:cloud)
              AND UPPER(region) = UPPER(:region)
              AND UPPER(tier) = UPPER(:tier)
              AND UPPER(sku_name) = UPPER(:product_type)
            LIMIT 1
        """)
        price_row = db.execute(dbu_price_query, {
            "cloud": request.cloud, "region": request.region,
            "tier": request.tier, "product_type": sku_type,
        }).fetchone()
        dbu_price = float(price_row.price_per_dbu) if price_row else 0.0

        dbu_cost_per_month = dbu_per_month * dbu_price
        cost_per_month = dbu_cost_per_month

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
                "workload_type": "MODEL_SERVING", "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(), "region": request.region, "tier": request.tier.upper(),
                    "gpu_type": request.gpu_type, "scale_out": request.scale_out, "concurrency": concurrency,
                },
                "usage": {"hours_per_month": hours_per_month},
                "dbu_calculation": {
                    "gpu_dbu_rate": gpu_dbu_rate, "concurrency": concurrency,
                    "gpu_replicas": capacity_units if is_gpu else None,
                    "concurrency_per_gpu_replica": 4 if is_gpu else None,
                    "billing_capacity_units": capacity_units,
                    "dbu_per_hour": round(dbu_per_hour, 4), "dbu_per_month": round(dbu_per_month, 2),
                    "dbu_price": dbu_price, "dbu_cost_per_month": round(dbu_cost_per_month, 2),
                    "calculation": (
                        (
                            f"{concurrency} concurrency ÷ 4 concurrency/replica "
                            f"= {capacity_units:g} GPU replicas; "
                            if is_gpu
                            else ""
                        )
                        + f"{gpu_dbu_rate} DBU/{'replica' if is_gpu else 'concurrency'}-hr "
                        + f"× {capacity_units:g} {capacity_label} "
                        + f"× {hours_per_month} hrs"
                    ),
                },
                "total_cost": {
                    "cost_per_month": round(cost_per_month, 2),
                    "note": "Model Serving is serverless - no VM costs",
                },
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
        logger.error(f"Error calculating Model Serving cost: {e}")
        return {"success": False, "error": {"code": "CALCULATION_ERROR", "message": str(e)}}
