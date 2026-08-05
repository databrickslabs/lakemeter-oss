"""Genie / Genie Code calculation endpoint (LLM + Serverless SQL warehouse).

Genie cost has two additive components (per go/geniepricing):

1. **LLM usage** — DBUs on the regionalized Serverless Realtime Inference (SRTI) SKU
   (``SERVERLESS_REAL_TIME_INFERENCE``). Each identified user receives 150 free DBUs per
   account per month; service principals receive none. A 25% intro promo applies to paid
   DBUs through Jan 31 2027 (applied by reducing the billed DBU quantity).

2. **Serverless SQL warehouse** — Genie queries execute on a SQL warehouse. Serverless SQL
   bills on warehouse *uptime* (auto-stop keeps it warm between queries), so cost is driven
   by active hours and warehouse size rather than raw query count. The warehouse is shared
   across all users, so per-user cost falls as adoption grows. Set
   ``reuse_existing_warehouse`` when the customer already runs a warm warehouse, to avoid
   double-counting against an existing DBSQL line item.

Sizing uses t-shirt sizes (S/M/L/XL) that drive users, DBUs/user, active hours and warehouse
size; any field may be overridden explicitly (``size="custom"`` for a fully manual config).

Pricing is looked up from static JSON (same approach as FMAPI) to avoid coupling to the
OSS Lakebase stored-function schema.
"""
import json
import logging
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.validators import (
    validate_cloud, validate_region, validate_tier, validate_sku_specific_discounts,
)
from app.services.genie_federation_sizing import (
    FREE_DBUS_PER_USER, TIER_LABELS,
    resolve_genie_config, calculate_genie_llm_dbus, warehouse_dbu_per_hour,
)
from app.routes.calculate.discount import (
    apply_discount_to_sku_breakdown, calculate_total_discount_summary, enhance_total_cost_with_discount,
)
from app.routes.calculate.schemas import GenieCalculationRequest

logger = logging.getLogger(__name__)
router = APIRouter()

GENIE_LLM_SKU = "SERVERLESS_REAL_TIME_INFERENCE"
WAREHOUSE_SKU = "SERVERLESS_SQL_COMPUTE"

_PRICING_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'static', 'pricing')


def _load_json(filename: str) -> dict:
    path = os.path.join(_PRICING_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}


DBU_RATES_BY_REGION = _load_json('dbu-rates.json')
FALLBACK_DBU_PRICES = {
    GENIE_LLM_SKU: 0.07,     # US East SRTI list price ($/DBU)
    WAREHOUSE_SKU: 0.70,     # US East Serverless SQL list price ($/DBU)
}


def _get_dbu_price(cloud: str, region: str, tier: str, sku: str) -> float:
    """Look up $/DBU for a SKU from static pricing data, falling back to list price."""
    cloud_lc = cloud.lower()
    key = f"{cloud_lc}:{region}:{tier.upper()}"
    region_rates = DBU_RATES_BY_REGION.get(key, {})
    if sku in region_rates:
        return region_rates[sku]
    for k, v in DBU_RATES_BY_REGION.items():
        parts = k.split(':')
        if len(parts) == 3 and parts[0] == cloud_lc and parts[2] == tier.upper() and sku in v:
            return v[sku]
    return FALLBACK_DBU_PRICES.get(sku, 0.07)


@router.post("/calculate/genie", tags=["Cost Calculation"])
def calculate_genie_cost(
    request: GenieCalculationRequest,
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
        product = (request.product or "genie").lower()
        is_code = product == "genie_code"

        cfg = resolve_genie_config(
            request.size,
            num_users=request.num_users,
            dbus_per_user_per_month=request.dbus_per_user_per_month,
            warehouse_size=request.warehouse_size,
            active_hours_per_month=request.active_hours_per_month,
        )

        # ── 1. LLM usage on the SRTI SKU ──────────────────────────────────────
        llm = calculate_genie_llm_dbus(
            num_users=cfg["num_users"],
            dbus_per_user=cfg["dbus_per_user"],
            num_service_principals=request.num_service_principals,
            dbus_per_sp=request.dbus_per_sp_per_month,
            apply_promo=request.apply_promo,
            promo_pct=request.promo_pct,
        )
        llm_price = _get_dbu_price(cloud_upper, request.region, tier_upper, GENIE_LLM_SKU)
        llm_cost = llm["billable_dbus"] * llm_price

        # ── 2. Serverless SQL warehouse underneath ────────────────────────────
        wh_dbu_per_hour = warehouse_dbu_per_hour(cfg["warehouse_size"])
        wh_hours = 0.0 if request.reuse_existing_warehouse else cfg["active_hours"]
        wh_dbus = wh_dbu_per_hour * wh_hours
        wh_price = _get_dbu_price(cloud_upper, request.region, tier_upper, WAREHOUSE_SKU)
        wh_cost = wh_dbus * wh_price

        total_cost = llm_cost + wh_cost

        sku_breakdown = []
        if llm_cost > 0:
            sku_breakdown.append({
                "type": "dbu", "sku": GENIE_LLM_SKU,
                "cost": round(llm_cost, 2), "qty": round(llm["billable_dbus"], 4),
                "usage_unit": "DBU", "unit_price_before_discount": round(llm_price, 6),
                "rate_type": "genie_code_llm" if is_code else "genie_llm",
            })
        if wh_cost > 0:
            sku_breakdown.append({
                "type": "dbu", "sku": WAREHOUSE_SKU,
                "cost": round(wh_cost, 2), "qty": round(wh_dbus, 4),
                "usage_unit": "DBU", "unit_price_before_discount": round(wh_price, 6),
                "rate_type": "genie_warehouse",
            })

        if request.discount_config:
            if request.discount_config.sku_specific:
                error = validate_sku_specific_discounts(request.discount_config.sku_specific, db)
                if error:
                    raise HTTPException(status_code=400, detail=error["error"])
            sku_breakdown = apply_discount_to_sku_breakdown(sku_breakdown, request.discount_config, db)

        per_user_total = (total_cost / cfg["num_users"]) if cfg["num_users"] else 0.0
        unit_label = "developers" if is_code else "users"

        warnings = [
            f"Includes both LLM usage (SRTI SKU) and the Serverless SQL warehouse underneath. "
            f"The warehouse is shared across all {unit_label}, so per-{unit_label[:-1]} cost falls as adoption grows.",
            f"Each identified {unit_label[:-1]} receives {FREE_DBUS_PER_USER:.0f} free LLM DBUs/month "
            f"(service principals receive none).",
        ]
        if request.apply_promo:
            warnings.append(f"{request.promo_pct:.0f}% intro promo applied to paid LLM DBUs (through Jan 31, 2027).")
        if request.reuse_existing_warehouse:
            warnings.append("Warehouse cost excluded — reusing an existing warm SQL warehouse.")
        else:
            warnings.append(
                "Serverless SQL bills on warehouse uptime (auto-stop keeps it warm between queries), "
                "so cost tracks active hours and warehouse size rather than raw query count.")
        if not is_code:
            warnings.append(
                "Genie One and Genie Agents LLM usage is fully free through Jan 31, 2027 for identified "
                "users; this estimate reflects the standard Paygo model.")

        response_data = {
            "success": True,
            "data": {
                "workload_type": "GENIE_CODE" if is_code else "GENIE",
                "sku_type": GENIE_LLM_SKU,
                "configuration": {
                    "cloud": cloud_upper, "region": request.region, "tier": tier_upper,
                    "product": product,
                    "size": (request.size or "M").upper(),
                    "size_label": TIER_LABELS.get((request.size or "M").upper(), "Custom"),
                    "num_users": cfg["num_users"],
                    "unit_label": unit_label,
                    "dbus_per_user_per_month": cfg["dbus_per_user"],
                    "free_dbus_per_user": FREE_DBUS_PER_USER,
                    "num_service_principals": request.num_service_principals,
                    "warehouse_size": cfg["warehouse_size"],
                    "active_hours_per_month": cfg["active_hours"],
                    "reuse_existing_warehouse": request.reuse_existing_warehouse,
                    "apply_promo": request.apply_promo,
                },
                "usage": {
                    "free_dbus_per_month": round(llm["free_dbus"], 4),
                    "gross_paid_dbus_per_month": round(llm["gross_paid_dbus"], 4),
                    "billable_llm_dbus_per_month": round(llm["billable_dbus"], 4),
                    "warehouse_hours_per_month": round(wh_hours, 2),
                    "warehouse_dbus_per_month": round(wh_dbus, 4),
                },
                "dbu_calculation": {
                    "dbu_per_hour": round(wh_dbu_per_hour, 4),
                    "dbu_per_month": round(llm["billable_dbus"] + wh_dbus, 4),
                    "dbu_price": llm_price,
                    "dbu_cost_per_month": round(total_cost, 2),
                },
                "total_cost": {
                    "cost_per_month": round(total_cost, 2),
                    "breakdown": {
                        "llm_cost": round(llm_cost, 2),
                        "warehouse_cost": round(wh_cost, 2),
                    },
                    "cost_per_user_per_month": round(per_user_total, 2),
                },
                "sku_breakdown": sku_breakdown,
                "warnings": warnings,
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
        logger.error(f"Error calculating Genie cost: {e}")
        return {"success": False, "error": {"code": "CALCULATION_ERROR", "message": str(e)}}
