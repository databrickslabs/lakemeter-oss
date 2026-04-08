"""FMAPI calculation endpoints (Databricks + Proprietary token-based pricing).

Uses static JSON pricing data instead of stored functions to avoid
OSS Lakebase schema compatibility issues with calculate_fmapi_databricks_dbu.
"""
import json
import logging
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.validators import (
    validate_cloud, validate_region, validate_tier, validate_sku_specific_discounts,
)
from app.services.lakebase_queries import get_product_type_for_pricing
from app.routes.calculate.helpers import build_sku_breakdown_serverless
from app.routes.calculate.discount import (
    apply_discount_to_sku_breakdown, calculate_total_discount_summary, enhance_total_cost_with_discount,
)
from app.routes.calculate.schemas import FMAPIDatabricksCalculationRequest, FMAPIProprietaryCalculationRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# Load FMAPI pricing from static JSON
_PRICING_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'static', 'pricing')


def _load_json(filename: str) -> dict:
    path = os.path.join(_PRICING_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}


FMAPI_DB_RATES = _load_json('fmapi-databricks-rates.json')
FMAPI_PROP_RATES = _load_json('fmapi-proprietary-rates.json')

# DBU price ($/DBU) for FMAPI SKUs — looked up from dbu-rates.json or fallback
DBU_RATES_BY_REGION = _load_json('dbu-rates.json')
FALLBACK_DBU_PRICES = {
    'SERVERLESS_REAL_TIME_INFERENCE': 0.07,
    'OPENAI_MODEL_SERVING': 0.07,
    'ANTHROPIC_MODEL_SERVING': 0.07,
    'GEMINI_MODEL_SERVING': 0.07,
    'GOOGLE_MODEL_SERVING': 0.07,
}


def _get_dbu_price_for_sku(cloud: str, region: str, tier: str, sku: str) -> float:
    """Look up $/DBU price for a SKU from static pricing data."""
    key = f"{cloud}:{region}:{tier.upper()}"
    region_rates = DBU_RATES_BY_REGION.get(key, {})
    if sku in region_rates:
        return region_rates[sku]
    # Try without region specificity
    for k, v in DBU_RATES_BY_REGION.items():
        parts = k.split(':')
        if len(parts) == 3 and parts[0] == cloud and parts[2] == tier.upper() and sku in v:
            return v[sku]
    return FALLBACK_DBU_PRICES.get(sku, 0.07)


def _build_fmapi_line_items_direct(request, workload_type, cloud, region, tier,
                                    provider=None, endpoint_type="global", context_length="all"):
    """Build FMAPI line items using static pricing JSON (no stored function)."""
    line_items = []

    token_types = []

    # Frontend sends quantity + rate_type (single rate per request)
    if getattr(request, 'quantity', None) and request.quantity > 0 and getattr(request, 'rate_type', None):
        token_types.append((request.rate_type, request.quantity))
    else:
        # Legacy: input_tokens_per_month / output_tokens_per_month / provisioned_hours_per_month
        if request.input_tokens_per_month and request.input_tokens_per_month > 0:
            token_types.append(("input_token", request.input_tokens_per_month))
        if request.output_tokens_per_month and request.output_tokens_per_month > 0:
            token_types.append(("output_token", request.output_tokens_per_month))
        if getattr(request, 'provisioned_hours_per_month', None) and request.provisioned_hours_per_month > 0:
            token_types.append(("provisioned_scaling", request.provisioned_hours_per_month))

    if not token_types:
        raise HTTPException(status_code=400, detail="Must provide at least one token quantity (input, output, or provisioned)")

    cloud_lc = cloud.lower()

    for rate_type, quantity in token_types:
        # Look up rate from static JSON
        if workload_type == "FMAPI_DATABRICKS":
            key = f"{cloud_lc}:{request.model}:{rate_type}"
            info = FMAPI_DB_RATES.get(key, {})
        else:
            key = f"{cloud_lc}:{provider}:{request.model}:{endpoint_type}:{context_length}:{rate_type}"
            info = FMAPI_PROP_RATES.get(key, {})

        if not info:
            logger.warning(f"FMAPI rate not found for key={key}")
            line_items.append({
                "rate_type": rate_type, "quantity": quantity,
                "dbu_quantity": 0, "dbu_price": 0, "dbu_per_hour": 0, "cost": 0,
                "unit": "million_tokens" if rate_type in ("input_token", "output_token") else "hours",
            })
            continue

        dbu_rate = info.get('dbu_rate', 0)
        input_divisor = info.get('input_divisor', 1_000_000)
        is_hourly = info.get('is_hourly', False)
        sku_product_type = info.get('sku_product_type', 'SERVERLESS_REAL_TIME_INFERENCE')

        # Calculate DBU quantity
        # For token-based: quantity is in millions, dbu_rate is DBU per million tokens
        # For hourly (provisioned): quantity is hours, dbu_rate is DBU per hour
        if is_hourly:
            dbu_quantity = dbu_rate * quantity
        else:
            # quantity is already in millions (e.g., 10 = 10M tokens)
            # dbu_rate is DBU per million tokens
            dbu_quantity = dbu_rate * quantity

        # Get $/DBU price
        dbu_price = _get_dbu_price_for_sku(cloud_lc, region, tier, sku_product_type)
        cost = dbu_quantity * dbu_price

        is_token = rate_type in ("input_token", "output_token", "cache_read", "cache_write")

        line_items.append({
            "rate_type": rate_type,
            "quantity": quantity,
            "dbu_quantity": round(dbu_quantity, 6),
            "dbu_price": dbu_price,
            "dbu_per_hour": dbu_rate if is_hourly else 0,
            "cost": round(cost, 2),
            "unit": "million_tokens" if is_token else "hours",
        })

    return line_items


@router.post("/calculate/fmapi-databricks", tags=["Cost Calculation"])
def calculate_fmapi_databricks_cost(
    request: FMAPIDatabricksCalculationRequest,
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

    try:
        cloud_upper = request.cloud.upper()
        tier_upper = request.tier.upper()

        line_items = _build_fmapi_line_items_direct(
            request, "FMAPI_DATABRICKS", cloud_upper, request.region, tier_upper,
        )

        sku_type = get_product_type_for_pricing(db, "FMAPI_DATABRICKS", True, False, None, None, None)
        total_cost = sum(item["cost"] for item in line_items)

        sku_breakdown = []
        for item in line_items:
            if item["cost"] > 0:
                sku_breakdown.append({
                    "type": "dbu",
                    "sku": sku_type or "SERVERLESS_REAL_TIME_INFERENCE",
                    "cost": round(item["cost"], 2),
                    "qty": round(item["dbu_quantity"], 6),
                    "usage_unit": item["unit"],
                    "unit_price_before_discount": round(item["dbu_price"], 6),
                    "rate_type": item["rate_type"],
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
                "workload_type": "FMAPI_DATABRICKS", "sku_type": sku_type,
                "configuration": {
                    "cloud": cloud_upper, "region": request.region, "tier": tier_upper,
                    "model": request.model,
                },
                "line_items": line_items,
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
        logger.error(f"Error calculating FMAPI Databricks cost: {e}")
        return {"success": False, "error": {"code": "CALCULATION_ERROR", "message": str(e)}}


@router.post("/calculate/fmapi-proprietary", tags=["Cost Calculation"])
def calculate_fmapi_proprietary_cost(
    request: FMAPIProprietaryCalculationRequest,
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

    try:
        cloud_upper = request.cloud.upper()
        tier_upper = request.tier.upper()

        line_items = _build_fmapi_line_items_direct(
            request, "FMAPI_PROPRIETARY", cloud_upper, request.region, tier_upper,
            provider=request.provider,
            endpoint_type=request.endpoint_type,
            context_length=request.context_length or "all",
        )

        sku_type = get_product_type_for_pricing(
            db, "FMAPI_PROPRIETARY", True, False, None, None, request.provider
        )
        total_cost = sum(item["cost"] for item in line_items)

        sku_breakdown = []
        for item in line_items:
            if item["cost"] > 0:
                sku_breakdown.append({
                    "type": "dbu",
                    "sku": sku_type or f"{request.provider.upper()}_MODEL_SERVING",
                    "cost": round(item["cost"], 2),
                    "qty": round(item["dbu_quantity"], 6),
                    "usage_unit": item["unit"],
                    "unit_price_before_discount": round(item["dbu_price"], 6),
                    "rate_type": item["rate_type"],
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
                "workload_type": "FMAPI_PROPRIETARY", "sku_type": sku_type,
                "configuration": {
                    "cloud": cloud_upper, "region": request.region, "tier": tier_upper,
                    "provider": request.provider, "model": request.model,
                    "endpoint_type": request.endpoint_type,
                    "context_length": request.context_length,
                },
                "line_items": line_items,
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
        logger.error(f"Error calculating FMAPI Proprietary cost: {e}")
        return {"success": False, "error": {"code": "CALCULATION_ERROR", "message": str(e)}}
