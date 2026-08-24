"""AI Extract calculation endpoint.

AI Extract uses SERVERLESS_REAL_TIME_INFERENCE SKU. Raw STRING inputs can be
passed directly. Document files must first be parsed with ai_parse_document.

Document presets (DBU per 1,000 inputs, midpoints of the published planning
ranges, same convention as the AI Parse complexity rates):
  short_text: 45        (receipt with a few fields; range 30-60)
  invoice: 45           (typical invoice or purchase order, ~1 page; range 30-60)
  complex_reasoning: 562.5 (reasoning-heavy fields; precision mode; range 400-725)
  deep_nesting: 537.5   (deeply nested schemas; precision mode; range 375-700)
  custom: caller-supplied dbus_per_thousand
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.validators import validate_cloud, validate_region, validate_tier, validate_sku_specific_discounts
from app.routes.calculate.helpers import (
    build_sku_breakdown_serverless,
    get_required_regional_dbu_price,
)
from app.routes.calculate.discount import (
    apply_discount_to_sku_breakdown, calculate_total_discount_summary, enhance_total_cost_with_discount,
)
from app.routes.calculate.schemas import AIExtractCalculationRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# DBU per 1,000 document inputs by preset
EXTRACT_DOCUMENT_RATES = {
    "short_text": 45.0,
    "invoice": 45.0,
    "complex_reasoning": 562.5,
    "deep_nesting": 537.5,
}

AI_PARSE_DEPENDENCY_NOTE = (
    "AI Extract accepts raw STRING inputs directly. For document files, call "
    "ai_parse_document first and include an AI Parse workload for that volume."
)


@router.post("/calculate/ai-extract", tags=["Cost Calculation"])
def calculate_ai_extract_cost(
    request: AIExtractCalculationRequest,
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

    document_type = (request.document_type or "invoice").lower()
    if document_type not in EXTRACT_DOCUMENT_RATES and document_type != "custom":
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document_type: {document_type}. Valid: {list(EXTRACT_DOCUMENT_RATES.keys()) + ['custom']}")
    if document_type == "custom" and request.dbus_per_thousand is None:
        raise HTTPException(
            status_code=400,
            detail="document_type 'custom' requires dbus_per_thousand")

    try:
        sku_type = "SERVERLESS_REAL_TIME_INFERENCE"

        dbu_price = get_required_regional_dbu_price(
            db,
            request.cloud,
            request.region,
            request.tier,
            sku_type,
        )

        if document_type == "custom":
            rate = float(request.dbus_per_thousand)
        else:
            rate = EXTRACT_DOCUMENT_RATES[document_type]
        num_inputs = request.num_inputs or 0
        dbu_per_month = (num_inputs / 1000.0) * rate

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
                "workload_type": "AI_EXTRACT", "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(), "region": request.region,
                    "tier": request.tier.upper(), "document_type": document_type,
                    "num_inputs": num_inputs,
                },
                "dbu_calculation": {
                    "dbu_per_1000_inputs": rate,
                    "dbu_per_month": round(dbu_per_month, 2),
                    "dbu_price": dbu_price,
                    "dbu_cost_per_month": round(dbu_cost, 2),
                },
                "total_cost": {"cost_per_month": round(dbu_cost, 2)},
                "sku_breakdown": sku_breakdown,
                "notes": [AI_PARSE_DEPENDENCY_NOTE],
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
        logger.error(f"Error calculating AI Extract cost: {e}")
        return {"success": False, "error": {"code": "CALCULATION_ERROR", "message": str(e)}}
