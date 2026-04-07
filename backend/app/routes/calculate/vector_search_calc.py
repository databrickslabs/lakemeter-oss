"""Vector Search calculation endpoint."""
import logging
import math
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.validators import (
    validate_cloud, validate_region, validate_tier, validate_sku_specific_discounts,
)
from app.services.lakebase_queries import call_calculate_line_item_costs, get_product_type_for_pricing
from app.routes.calculate.helpers import build_sku_breakdown_serverless
from app.routes.calculate.discount import (
    apply_discount_to_sku_breakdown, calculate_total_discount_summary, enhance_total_cost_with_discount,
)
from app.routes.calculate.jobs import _validate_usage_params
from app.routes.calculate.schemas import VectorSearchCalculationRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/calculate/vector-search", tags=["Cost Calculation"])
def calculate_vector_search_cost(
    request: VectorSearchCalculationRequest,
    db: Session = Depends(get_db),
):
    has_run_params, has_hours = _validate_usage_params(request, require_runs=False)
    if has_run_params and request.days_per_month is None:
        request.days_per_month = 30

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
        params = {
            "p1": "VECTOR_SEARCH", "p2": request.cloud.upper(), "p3": request.region, "p4": request.tier.upper(),
            "p5": True, "p6": False, "p7": None,
            "p8": None, "p9": None, "p10": 0,
            "p11": "on_demand", "p12": "on_demand",
            "p13": 0, "p14": 0,
            "p15": request.days_per_month or 30,
            "p16": int(request.hours_per_month) if has_hours and request.hours_per_month is not None else None,
            "p17": "standard", "p18": None, "p19": None, "p20": 1,
            "p21": "on_demand", "p22": request.mode,
            "p23": request.num_vectors_millions,
            "p24": None, "p25": None, "p26": None,
            "p27": "global", "p28": "all", "p29": "input_token", "p30": 0, "p31": 0, "p32": 1,
            "p33": "NA", "p34": "NA", "p35": "NA",
        }
        row = call_calculate_line_item_costs(db, params)
        if not row:
            raise HTTPException(status_code=500, detail="No calculation result returned")

        sku_type = get_product_type_for_pricing(db, "VECTOR_SEARCH", True, False, None, None, None)

        # Calculate units used for response
        if request.mode == "storage_optimized":
            units_used = math.ceil(request.num_vectors_millions / 64) if request.num_vectors_millions > 0 else 0
        else:
            units_used = math.ceil(request.num_vectors_millions / 2) if request.num_vectors_millions > 0 else 0

        dbu_cost = float(row.dbu_cost_per_month or 0)
        dbu_quantity = float(row.dbu_per_month or 0)
        dbu_price = float(row.dbu_price or 0)
        hours = float(row.hours_per_month or 0)
        # Stored function returns per-unit DBU rate; derive total from monthly quantity
        dbu_per_hour = (dbu_quantity / hours) if hours > 0 else float(row.dbu_per_hour or 0)

        sku_breakdown = build_sku_breakdown_serverless(
            sku_type=sku_type, dbu_cost=dbu_cost,
            dbu_quantity=dbu_quantity, dbu_price=dbu_price,
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
                "workload_type": "VECTOR_SEARCH", "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(), "region": request.region, "tier": request.tier.upper(),
                    "mode": request.mode, "num_vectors_millions": request.num_vectors_millions,
                },
                "usage": {
                    "hours_per_month": float(row.hours_per_month or 0),
                    "units_used": units_used,
                },
                "dbu_calculation": {
                    "dbu_per_hour": round(dbu_per_hour, 4), "dbu_per_month": round(dbu_quantity, 2),
                    "dbu_price": dbu_price, "dbu_cost_per_month": round(dbu_cost, 2),
                },
                "total_cost": {"cost_per_month": float(row.cost_per_month or 0)},
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
        logger.error(f"Error calculating Vector Search cost: {e}")
        return {"success": False, "error": {"code": "CALCULATION_ERROR", "message": str(e)}}
