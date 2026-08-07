"""Lakehouse Federation calculation endpoint.

Lakehouse Federation (querying external sources — Postgres, MySQL, Snowflake, Redshift,
BigQuery, etc. — through Unity Catalog) has **no separate Databricks SKU**. Federated queries
bill entirely through the Serverless SQL warehouse that executes them, so adding a distinct
"federation DBU" line would double-count.

Usage is driven by **query volume**, not a raw hours figure. Serverless SQL bills on warehouse
uptime: auto-stop (default 10 min) keeps the warehouse warm between queries, so once queries
arrive more often than the auto-stop window the warehouse stays up continuously and uptime
saturates at ``active_hours_per_day * days_per_month``. Below that threshold, cost scales with
query count. Modeling raw "hours of querying" as continuous warehouse uptime massively
overstates cost for bursty federated workloads.

Two costs that are NOT on the Databricks bill are surfaced as warnings: the remote source
system's own compute, and cloud network egress.
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
from app.services.lakehouse_federation_sizing import (
    TIER_LABELS, resolve_federation_config, federation_warehouse_hours, warehouse_dbu_per_hour,
)
from app.routes.calculate.helpers import build_sku_breakdown_serverless
from app.routes.calculate.discount import (
    apply_discount_to_sku_breakdown, calculate_total_discount_summary, enhance_total_cost_with_discount,
)
from app.routes.calculate.schemas import LakehouseFederationCalculationRequest

logger = logging.getLogger(__name__)
router = APIRouter()

WAREHOUSE_SKU = "SERVERLESS_SQL_COMPUTE"

_PRICING_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'static', 'pricing')


def _load_json(filename: str) -> dict:
    path = os.path.join(_PRICING_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}


DBU_RATES_BY_REGION = _load_json('dbu-rates.json')
FALLBACK_WAREHOUSE_PRICE = 0.70  # US East Serverless SQL list price ($/DBU)


def _get_warehouse_dbu_price(cloud: str, region: str, tier: str) -> float:
    cloud_lc = cloud.lower()
    key = f"{cloud_lc}:{region}:{tier.upper()}"
    region_rates = DBU_RATES_BY_REGION.get(key, {})
    if WAREHOUSE_SKU in region_rates:
        return region_rates[WAREHOUSE_SKU]
    for k, v in DBU_RATES_BY_REGION.items():
        parts = k.split(':')
        if len(parts) == 3 and parts[0] == cloud_lc and parts[2] == tier.upper() and WAREHOUSE_SKU in v:
            return v[WAREHOUSE_SKU]
    return FALLBACK_WAREHOUSE_PRICE


@router.post("/calculate/lakehouse-federation", tags=["Cost Calculation"])
def calculate_lakehouse_federation_cost(
    request: LakehouseFederationCalculationRequest,
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

        cfg = resolve_federation_config(
            request.size,
            num_users=request.num_users,
            queries_per_period=request.queries_per_period,
            query_period=request.query_period,
            warehouse_size=request.warehouse_size,
            days_per_month=request.days_per_month,
        )

        uptime = federation_warehouse_hours(
            queries_per_day=cfg["queries_per_day"],
            avg_query_seconds=request.avg_query_seconds,
            auto_stop_minutes=request.auto_stop_minutes,
            active_hours_per_day=request.active_hours_per_day,
            days_per_month=request.days_per_month,
        )

        dbu_per_hour = warehouse_dbu_per_hour(cfg["warehouse_size"])
        hours = uptime["hours_per_month"]
        dbus = dbu_per_hour * hours
        dbu_price = _get_warehouse_dbu_price(cloud_upper, request.region, tier_upper)
        cost = dbus * dbu_price

        sku_breakdown = build_sku_breakdown_serverless(
            sku_type=WAREHOUSE_SKU, dbu_cost=cost, dbu_quantity=dbus, dbu_price=dbu_price,
        )

        if request.discount_config:
            if request.discount_config.sku_specific:
                error = validate_sku_specific_discounts(request.discount_config.sku_specific, db)
                if error:
                    raise HTTPException(status_code=400, detail=error["error"])
            sku_breakdown = apply_discount_to_sku_breakdown(sku_breakdown, request.discount_config, db)

        warnings = [
            "Lakehouse Federation has no separate SKU — this is the Serverless SQL warehouse "
            "compute that executes the federated queries.",
            "NOT included: the remote source system's own compute (e.g., Snowflake/BigQuery charges).",
            "NOT included: cloud network egress between Databricks and the external source.",
        ]
        if uptime["saturated"]:
            warnings.append(
                f"At {cfg['queries_per_day']:.0f} queries/day the warehouse stays warm continuously "
                f"(queries arrive within the {request.auto_stop_minutes:.0f}-min auto-stop window), so uptime is "
                f"capped at {request.active_hours_per_day:.0f}h x {request.days_per_month}d = {hours:.0f}h/month.")
        else:
            warnings.append(
                f"Bursty workload: {cfg['queries_per_day']:.0f} queries/day keeps the warehouse up ~{hours:.1f}h/month "
                f"(each query holds it for its duration plus the {request.auto_stop_minutes:.0f}-min auto-stop window).")

        response_data = {
            "success": True,
            "data": {
                "workload_type": "LAKEHOUSE_FEDERATION",
                "sku_type": WAREHOUSE_SKU,
                "configuration": {
                    "cloud": cloud_upper, "region": request.region, "tier": tier_upper,
                    "size": (request.size or "M").upper(),
                    "size_label": TIER_LABELS.get((request.size or "M").upper(), "Custom"),
                    "num_users": cfg["num_users"],
                    "queries_per_day": cfg["queries_per_day"],
                    "queries_per_month": round(uptime["queries_per_month"], 1),
                    "avg_query_seconds": request.avg_query_seconds,
                    "warehouse_size": cfg["warehouse_size"],
                    "auto_stop_minutes": request.auto_stop_minutes,
                    "active_hours_per_day": request.active_hours_per_day,
                    "days_per_month": request.days_per_month,
                },
                "usage": {
                    "hours_per_month": round(hours, 2),
                    "warehouse_saturated": uptime["saturated"],
                    "queries_per_month": round(uptime["queries_per_month"], 1),
                },
                "dbu_calculation": {
                    "dbu_per_hour": round(dbu_per_hour, 4),
                    "dbu_per_month": round(dbus, 4),
                    "dbu_price": dbu_price,
                    "dbu_cost_per_month": round(cost, 2),
                },
                "total_cost": {"cost_per_month": round(cost, 2)},
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
        logger.error(f"Error calculating Lakehouse Federation cost: {e}")
        return {"success": False, "error": {"code": "CALCULATION_ERROR", "message": str(e)}}
