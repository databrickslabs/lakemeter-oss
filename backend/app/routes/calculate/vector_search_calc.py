"""AI Search calculation endpoint (legacy route name retained for compatibility)."""
import logging
import math
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.validators import (
    validate_cloud, validate_region, validate_tier, validate_sku_specific_discounts,
)
from app.services.lakebase_queries import call_calculate_line_item_costs, get_product_type_for_pricing
from app.routes.calculate.helpers import (
    build_sku_breakdown_serverless,
    get_required_regional_dbu_price,
)
from app.routes.calculate.discount import (
    apply_discount_to_sku_breakdown, calculate_total_discount_summary, enhance_total_cost_with_discount,
)
from app.routes.calculate.jobs import normalize_usage_params
from app.routes.calculate.schemas import VectorSearchCalculationRequest

logger = logging.getLogger(__name__)
router = APIRouter()

AI_SEARCH_INCLUDED_STORAGE_GB = 30
AI_SEARCH_STANDARD_STORAGE_DSU_PER_GB = 10
AI_SEARCH_STORAGE_OPTIMIZED_DSU_PER_GB = 2
AI_SEARCH_RERANKER_DBU_PER_THOUSAND_REQUESTS = 28.571


def calculate_ai_search_addons(
    *,
    units_used: int,
    mode: str,
    storage_gb: float,
    storage_price_per_dsu: float,
    reranker_enabled: bool,
    reranker_requests_thousands: float,
) -> dict:
    """Calculate AI Search storage and optional reranker usage."""
    free_storage_gb = AI_SEARCH_INCLUDED_STORAGE_GB if units_used > 0 else 0
    billable_storage_gb = max(0.0, storage_gb - free_storage_gb)
    storage_dsu_per_gb = (
        AI_SEARCH_STORAGE_OPTIMIZED_DSU_PER_GB
        if mode == "storage_optimized"
        else AI_SEARCH_STANDARD_STORAGE_DSU_PER_GB
    )
    storage_dsu = billable_storage_gb * storage_dsu_per_gb
    storage_cost = storage_dsu * storage_price_per_dsu
    reranker_dbus = (
        reranker_requests_thousands
        * AI_SEARCH_RERANKER_DBU_PER_THOUSAND_REQUESTS
        if reranker_enabled
        else 0.0
    )
    return {
        "storage": {
            "total_gb": storage_gb,
            "free_gb": free_storage_gb,
            "billable_gb": billable_storage_gb,
            "dsu_per_gb": storage_dsu_per_gb,
            "dsu_per_month": storage_dsu,
            "price_per_dsu": storage_price_per_dsu,
            "cost_per_month": storage_cost,
        },
        "reranker": {
            "enabled": reranker_enabled,
            "requests_thousands": reranker_requests_thousands,
            "dbu_per_thousand_requests": (
                AI_SEARCH_RERANKER_DBU_PER_THOUSAND_REQUESTS
            ),
            "dbu_per_month": reranker_dbus,
        },
    }


@router.post("/calculate/vector-search", tags=["Cost Calculation"])
def calculate_vector_search_cost(
    request: VectorSearchCalculationRequest,
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

    try:
        params = {
            "p1": "VECTOR_SEARCH", "p2": request.cloud.upper(), "p3": request.region, "p4": request.tier.upper(),
            "p5": True, "p6": False, "p7": None,
            "p8": None, "p9": None, "p10": 0,
            "p11": "on_demand", "p12": "on_demand",
            "p13": 0, "p14": 0,
            "p15": usage.days_per_month,
            "p16": usage.hours_per_month,
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

        sku_type = get_product_type_for_pricing(
            db,
            "VECTOR_SEARCH",
            True,
            False,
            None,
            None,
            None,
        )

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
        billable_storage_gb = max(
            0.0,
            request.storage_gb
            - (AI_SEARCH_INCLUDED_STORAGE_GB if units_used > 0 else 0),
        )
        storage_price_per_dsu = (
            get_required_regional_dbu_price(
                db,
                request.cloud,
                request.region,
                request.tier,
                "DATABRICKS_STORAGE",
            )
            if billable_storage_gb > 0
            else 0
        )
        addons = calculate_ai_search_addons(
            units_used=units_used,
            mode=request.mode,
            storage_gb=request.storage_gb,
            storage_price_per_dsu=storage_price_per_dsu,
            reranker_enabled=request.reranker_enabled,
            reranker_requests_thousands=request.reranker_requests_thousands,
        )
        reranker_dbus = addons["reranker"]["dbu_per_month"]
        reranker_cost = reranker_dbus * dbu_price
        total_dbu_quantity = dbu_quantity + reranker_dbus
        total_dbu_cost = dbu_cost + reranker_cost
        storage_cost = addons["storage"]["cost_per_month"]

        sku_breakdown = build_sku_breakdown_serverless(
            sku_type=sku_type, dbu_cost=total_dbu_cost,
            dbu_quantity=total_dbu_quantity, dbu_price=dbu_price,
        )
        if addons["storage"]["dsu_per_month"] > 0:
            sku_breakdown.append({
                "type": "dsu",
                "sku": "DATABRICKS_STORAGE",
                "cost": round(storage_cost, 6),
                "qty": round(addons["storage"]["dsu_per_month"], 6),
                "usage_unit": "DSU",
                "unit_price_before_discount": storage_price_per_dsu,
                "rate_type": "ai_search_storage",
            })

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
                "display_name": "AI Search",
                "configuration": {
                    "cloud": request.cloud.upper(), "region": request.region, "tier": request.tier.upper(),
                    "mode": request.mode, "num_vectors_millions": request.num_vectors_millions,
                },
                "usage": {
                    "hours_per_month": float(row.hours_per_month or 0),
                    "units_used": units_used,
                },
                "dbu_calculation": {
                    "dbu_per_hour": round(dbu_per_hour, 4),
                    "serving_dbu_per_month": round(dbu_quantity, 3),
                    "reranker_dbu_per_month": round(reranker_dbus, 3),
                    "dbu_per_month": round(total_dbu_quantity, 3),
                    "dbu_price": dbu_price,
                    "dbu_cost_per_month": round(total_dbu_cost, 2),
                },
                "components": addons,
                "total_cost": {
                    "cost_per_month": round(
                        total_dbu_cost + storage_cost,
                        2,
                    ),
                    "breakdown": {
                        "dbu_cost": round(total_dbu_cost, 2),
                        "dsu_cost": round(storage_cost, 2),
                    },
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
        logger.error(f"Error calculating AI Search cost: {e}")
        return {"success": False, "error": {"code": "CALCULATION_ERROR", "message": str(e)}}
