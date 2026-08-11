"""AI Classify calculation endpoint.

AI Classify uses SERVERLESS_REAL_TIME_INFERENCE SKU.
Inputs must first be parsed with ai_parse_document; AI Classify consumes the
parsed documents, not raw files.

Document presets (DBU per 1,000 documents, midpoints of the published planning
ranges, same convention as the AI Parse complexity rates):
  short_text: 4.5 (news brief or similar short text; range 3-6)
  contract: 50    (rental contract, 7-10 pages; range 40-60)
  custom: caller-supplied dbus_per_thousand
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.validators import validate_cloud, validate_region, validate_tier, validate_sku_specific_discounts
from app.routes.calculate.helpers import build_sku_breakdown_serverless
from app.routes.calculate.discount import (
    apply_discount_to_sku_breakdown, calculate_total_discount_summary, enhance_total_cost_with_discount,
)
from app.routes.calculate.schemas import AIClassifyCalculationRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# DBU per 1,000 documents by preset
CLASSIFY_DOCUMENT_RATES = {
    "short_text": 4.5,
    "contract": 50.0,
}

AI_PARSE_DEPENDENCY_NOTE = (
    "AI Classify consumes documents produced by ai_parse_document; it does not "
    "accept files directly. Include an AI Parse workload for the same documents "
    "unless they are already parsed."
)


@router.post("/calculate/ai-classify", tags=["Cost Calculation"])
def calculate_ai_classify_cost(
    request: AIClassifyCalculationRequest,
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

    document_type = (request.document_type or "short_text").lower()
    if document_type not in CLASSIFY_DOCUMENT_RATES and document_type != "custom":
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document_type: {document_type}. Valid: {list(CLASSIFY_DOCUMENT_RATES.keys()) + ['custom']}")
    if document_type == "custom" and not request.dbus_per_thousand:
        raise HTTPException(
            status_code=400,
            detail="document_type 'custom' requires dbus_per_thousand")

    try:
        sku_type = "SERVERLESS_REAL_TIME_INFERENCE"

        # Look up DBU price
        price_row = db.execute(text("""
            SELECT price_per_dbu FROM lakemeter.sync_pricing_dbu_rates
            WHERE UPPER(cloud) = UPPER(:cloud) AND UPPER(region) = UPPER(:region)
              AND UPPER(tier) = UPPER(:tier)
              AND (UPPER(product_type) = UPPER(:pt) OR UPPER(sku_name) = UPPER(:pt))
            LIMIT 1
        """), {"cloud": request.cloud, "region": request.region, "tier": request.tier, "pt": sku_type}).fetchone()
        dbu_price = float(price_row.price_per_dbu) if price_row else 0.0

        if document_type == "custom":
            rate = float(request.dbus_per_thousand)
        else:
            rate = CLASSIFY_DOCUMENT_RATES[document_type]
        num_docs = request.num_docs or 0
        dbu_per_month = (num_docs / 1000.0) * rate

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
                "workload_type": "AI_CLASSIFY", "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(), "region": request.region,
                    "tier": request.tier.upper(), "document_type": document_type,
                    "num_docs": num_docs,
                },
                "dbu_calculation": {
                    "dbu_per_1000_docs": rate,
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
        logger.error(f"Error calculating AI Classify cost: {e}")
        return {"success": False, "error": {"code": "CALCULATION_ERROR", "message": str(e)}}
