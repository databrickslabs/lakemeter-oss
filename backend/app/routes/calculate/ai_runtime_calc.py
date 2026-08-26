"""AI Runtime serverless GPU model-training cost calculation."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.routes.calculate.discount import (
    apply_discount_to_sku_breakdown,
    calculate_total_discount_summary,
    enhance_total_cost_with_discount,
)
from app.routes.calculate.helpers import (
    build_sku_breakdown_serverless,
    get_required_regional_dbu_price,
)
from app.routes.calculate.schemas import AIRuntimeCalculationRequest
from app.services.ai_runtime_pricing import (
    AI_RUNTIME_SKU,
    calculate_ai_runtime_usage,
)
from app.services.validators import (
    validate_cloud,
    validate_region,
    validate_sku_specific_discounts,
    validate_tier,
)


logger = logging.getLogger(__name__)
router = APIRouter()


def calculate_runtime_hours(request: AIRuntimeCalculationRequest) -> float:
    """Resolve direct or run-based monthly runtime hours."""
    if request.hours_per_month is not None:
        return float(request.hours_per_month)
    return (
        float(request.runs_per_day or 0)
        * (float(request.avg_runtime_minutes or 0) / 60)
        * float(request.days_per_month or 22)
    )


@router.post("/calculate/ai-runtime", tags=["Cost Calculation"])
def calculate_ai_runtime_cost(
    request: AIRuntimeCalculationRequest,
    db: Session = Depends(get_db),
):
    """Calculate AI Runtime usage on the MODEL_TRAINING SKU."""
    error = validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    if request.tier.upper() == "STANDARD":
        raise HTTPException(
            status_code=400,
            detail="AI Runtime requires Premium or Enterprise tier",
        )

    try:
        runtime_hours = calculate_runtime_hours(request)
        usage = calculate_ai_runtime_usage(
            request.cloud,
            request.accelerator_type,
            runtime_hours,
        )
        dbu_price = get_required_regional_dbu_price(
            db,
            request.cloud,
            request.region,
            request.tier,
            AI_RUNTIME_SKU,
        )
        monthly_cost = usage["monthly_dbus"] * dbu_price
        sku_breakdown = build_sku_breakdown_serverless(
            sku_type=AI_RUNTIME_SKU,
            dbu_cost=monthly_cost,
            dbu_quantity=usage["monthly_dbus"],
            dbu_price=dbu_price,
        )
        if sku_breakdown:
            sku_breakdown[0]["qty"] = round(usage["monthly_dbus"], 6)
            sku_breakdown[0]["cost"] = round(monthly_cost, 6)

        if request.discount_config:
            if request.discount_config.sku_specific:
                error = validate_sku_specific_discounts(
                    request.discount_config.sku_specific,
                    db,
                )
                if error:
                    raise HTTPException(
                        status_code=400,
                        detail=error["error"],
                    )
            sku_breakdown = apply_discount_to_sku_breakdown(
                sku_breakdown,
                request.discount_config,
                db,
            )

        response_data = {
            "success": True,
            "data": {
                "workload_type": "AI_RUNTIME",
                "sku_type": AI_RUNTIME_SKU,
                "billing_origin_product": "AI_RUNTIME",
                "configuration": {
                    "cloud": request.cloud.upper(),
                    "region": request.region,
                    "tier": request.tier.upper(),
                    "accelerator_type": usage["accelerator_type"],
                    "runtime_hours": runtime_hours,
                    "gpu_count": usage["gpu_count"],
                },
                "usage_calculation": {
                    "runtime_hours": runtime_hours,
                    "gpu_count": usage["gpu_count"],
                    "monthly_gpu_hours": usage["monthly_gpu_hours"],
                    "dbu_per_gpu_hour": usage["dbu_per_gpu_hour"],
                    "dbu_per_node_hour": usage["dbu_per_node_hour"],
                    "monthly_dbus": usage["monthly_dbus"],
                },
                "dbu_calculation": {
                    "dbu_per_hour": usage["dbu_per_node_hour"],
                    "monthly_dbus": usage["monthly_dbus"],
                    "dbu_per_month": usage["monthly_dbus"],
                    "dbu_price": dbu_price,
                    "monthly_dbu_cost": monthly_cost,
                    "dbu_cost_per_month": monthly_cost,
                },
                "total_cost": {
                    "cost_per_month": monthly_cost,
                },
                "sku_breakdown": sku_breakdown,
                "notes": [
                    "AI Runtime usage is identified by billing origin "
                    "AI_RUNTIME and charged on the MODEL_TRAINING SKU.",
                    "Runtime hours are node hours; 8xH100 consumes eight "
                    "GPU-hours per node hour.",
                ],
            },
        }
        if request.discount_config:
            response_data["data"]["total_cost"] = (
                enhance_total_cost_with_discount(
                    response_data["data"]["total_cost"],
                    sku_breakdown,
                )
            )
            response_data["data"]["discount_summary"] = (
                calculate_total_discount_summary(sku_breakdown)
            )
        return response_data
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Error calculating AI Runtime cost: %s", exc)
        return {
            "success": False,
            "error": {
                "code": "CALCULATION_ERROR",
                "message": str(exc),
            },
        }
