"""Zerobus Ingest cost calculation."""
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
from app.routes.calculate.schemas import ZerobusCalculationRequest
from app.services.validators import (
    validate_cloud,
    validate_region,
    validate_sku_specific_discounts,
    validate_tier,
)
from app.services.zerobus_pricing import (
    ZEROBUS_SKU,
    calculate_zerobus_usage,
    validate_zerobus_availability,
)


logger = logging.getLogger(__name__)
router = APIRouter()

ZEROBUS_EXCLUSION_NOTE = (
    "Producer compute, target Delta storage, downstream processing, and data "
    "transfer are excluded."
)


@router.post("/calculate/zerobus", tags=["Cost Calculation"])
def calculate_zerobus_cost(
    request: ZerobusCalculationRequest,
    db: Session = Depends(get_db),
):
    """Calculate standard or OpenTelemetry Zerobus ingestion cost."""
    error = validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    error = validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])

    try:
        validate_zerobus_availability(request.cloud, request.tier)
        usage = calculate_zerobus_usage(
            request.monthly_ingested_gb,
            request.mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        dbu_price = get_required_regional_dbu_price(
            db,
            request.cloud,
            request.region,
            request.tier,
            ZEROBUS_SKU,
        )
        monthly_dbu_cost = usage["monthly_dbus"] * dbu_price
        sku_breakdown = build_sku_breakdown_serverless(
            sku_type=ZEROBUS_SKU,
            dbu_cost=monthly_dbu_cost,
            dbu_quantity=usage["monthly_dbus"],
            dbu_price=dbu_price,
        )
        if sku_breakdown:
            sku_breakdown[0]["qty"] = round(usage["monthly_dbus"], 6)
            sku_breakdown[0]["cost"] = round(monthly_dbu_cost, 6)

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
                "workload_type": "ZEROBUS",
                "sku_type": ZEROBUS_SKU,
                "configuration": {
                    "cloud": request.cloud.upper(),
                    "region": request.region,
                    "tier": request.tier.upper(),
                    "mode": usage["mode"],
                    "monthly_ingested_gb": usage["monthly_ingested_gb"],
                },
                "usage_calculation": usage,
                "dbu_calculation": {
                    "monthly_dbus": usage["monthly_dbus"],
                    "dbu_per_month": usage["monthly_dbus"],
                    "dbu_per_gb": usage["dbu_per_gb"],
                    "dbu_price": dbu_price,
                    "list_price_per_gb": usage["dbu_per_gb"] * dbu_price,
                    "monthly_dbu_cost": monthly_dbu_cost,
                    "dbu_cost_per_month": monthly_dbu_cost,
                },
                "total_cost": {
                    "cost_per_month": monthly_dbu_cost,
                },
                "sku_breakdown": sku_breakdown,
                "notes": [ZEROBUS_EXCLUSION_NOTE],
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
    except Exception as exc:
        logger.error("Error calculating Zerobus cost: %s", exc)
        return {
            "success": False,
            "error": {
                "code": "CALCULATION_ERROR",
                "message": str(exc),
            },
        }
