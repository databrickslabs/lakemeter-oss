"""Lakeflow Connect calculation endpoint.

Lakeflow Connect has two components:
  1. Pipeline: DLT Serverless (ADVANCED edition default)
  2. Gateway: DLT Classic ADVANCED (database connectors only) — optional

Pipeline uses DELTA_LIVE_TABLES_SERVERLESS SKU.
Gateway uses DLT_ADVANCED_COMPUTE SKU with VM costs.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.validators import validate_cloud, validate_region, validate_tier, validate_sku_specific_discounts
from app.services.lakebase_queries import call_calculate_line_item_costs, get_product_type_for_pricing
from app.routes.calculate.helpers import build_sku_breakdown_serverless, build_sku_breakdown_classic
from app.routes.calculate.discount import (
    apply_discount_to_sku_breakdown, calculate_total_discount_summary, enhance_total_cost_with_discount,
)
from app.routes.calculate.jobs import _validate_usage_params
from app.routes.calculate.schemas import LakeflowConnectCalculationRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# Default gateway instances per cloud (single driver, no workers)
DEFAULT_GATEWAY_INSTANCES = {
    "AWS": "i3.xlarge",
    "AZURE": "Standard_DS3_v2",
    "GCP": "n1-standard-4",
}


@router.post("/calculate/lakeflow-connect", tags=["Cost Calculation"])
def calculate_lakeflow_connect_cost(
    request: LakeflowConnectCalculationRequest,
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

        # ── Pipeline (DLT Serverless) ─────────────────────────────────
        has_run_params, has_hours = _validate_usage_params(request, require_runs=False)
        if has_run_params and request.days_per_month is None:
            request.days_per_month = 30

        params = {
            "p1": "DLT", "p2": cloud_upper, "p3": request.region, "p4": tier_upper,
            "p5": True, "p6": False, "p7": None,
            "p8": None, "p9": None, "p10": 0,
            "p11": "on_demand", "p12": "on_demand",
            "p13": request.runs_per_day or 0,
            "p14": request.avg_runtime_minutes or 0,
            "p15": request.days_per_month or 30,
            "p16": int(request.hours_per_month) if has_hours and request.hours_per_month is not None else None,
            "p17": "standard", "p18": (request.dlt_edition or "ADVANCED").upper(),
            "p19": None, "p20": 1,
            "p21": "on_demand", "p22": None,
            "p23": 0, "p24": None, "p25": None, "p26": None,
            "p27": "global", "p28": "all", "p29": "input_token", "p30": 0, "p31": 0, "p32": 1,
            "p33": "NA", "p34": "NA", "p35": "NA",
        }
        pipeline_row = call_calculate_line_item_costs(db, params)
        if not pipeline_row:
            raise HTTPException(status_code=500, detail="Pipeline calculation returned no result")

        pipeline_sku = get_product_type_for_pricing(db, "DLT", True, False, None, None, (request.dlt_edition or "ADVANCED").upper())
        pipeline_dbu_cost = float(pipeline_row.dbu_cost_per_month or 0)
        pipeline_dbu_qty = float(pipeline_row.dbu_per_month or 0)
        pipeline_dbu_price = float(pipeline_row.dbu_price or 0)
        pipeline_hours = float(pipeline_row.hours_per_month or 0)

        sku_breakdown = build_sku_breakdown_serverless(
            sku_type=pipeline_sku, dbu_cost=pipeline_dbu_cost,
            dbu_quantity=pipeline_dbu_qty, dbu_price=pipeline_dbu_price,
        )

        total_cost = pipeline_dbu_cost
        gateway_data = None

        # ── Gateway (DLT Classic Advanced) ────────────────────────────
        if request.gateway_enabled:
            gateway_instance = request.gateway_instance_type or DEFAULT_GATEWAY_INSTANCES.get(cloud_upper, "i3.xlarge")
            gateway_hours = request.gateway_hours_per_month or 730  # always-on

            gateway_params = {
                "p1": "DLT", "p2": cloud_upper, "p3": request.region, "p4": tier_upper,
                "p5": False, "p6": False, "p7": None,
                "p8": gateway_instance, "p9": gateway_instance, "p10": 0,
                "p11": request.gateway_pricing_tier or "on_demand",
                "p12": request.gateway_pricing_tier or "on_demand",
                "p13": 0, "p14": 0, "p15": 30,
                "p16": int(gateway_hours),
                "p17": "standard", "p18": "ADVANCED",
                "p19": None, "p20": 1,
                "p21": "on_demand", "p22": None,
                "p23": 0, "p24": None, "p25": None, "p26": None,
                "p27": "global", "p28": "all", "p29": "input_token", "p30": 0, "p31": 0, "p32": 1,
                "p33": request.gateway_payment_option or "NA",
                "p34": request.gateway_payment_option or "NA",
                "p35": "NA",
            }
            gateway_row = call_calculate_line_item_costs(db, gateway_params)

            if gateway_row:
                gw_dbu_cost = float(gateway_row.dbu_cost_per_month or 0)
                gw_vm_cost = float(gateway_row.vm_cost_per_month or 0)
                gw_total = gw_dbu_cost + gw_vm_cost

                gateway_sku = get_product_type_for_pricing(db, "DLT", False, False, None, None, "ADVANCED")
                gateway_breakdown = build_sku_breakdown_classic(
                    sku_type=gateway_sku,
                    dbu_cost=gw_dbu_cost,
                    dbu_quantity=float(gateway_row.dbu_per_month or 0),
                    dbu_price=float(gateway_row.dbu_price or 0),
                    driver_vm_cost=float(gateway_row.driver_vm_cost_per_month or 0),
                    worker_vm_cost=float(gateway_row.total_worker_vm_cost_per_month or 0),
                    hours_per_month=gateway_hours,
                    driver_vm_price_per_hour=float(gateway_row.driver_vm_cost_per_hour or 0),
                    worker_vm_price_per_hour=float(gateway_row.worker_vm_cost_per_hour or 0),
                    driver_pricing_tier=request.gateway_pricing_tier or "on_demand",
                    worker_pricing_tier=request.gateway_pricing_tier or "on_demand",
                    num_workers=0,
                )
                sku_breakdown.extend(gateway_breakdown)
                total_cost += gw_total

                gateway_data = {
                    "instance_type": gateway_instance,
                    "hours_per_month": gateway_hours,
                    "dbu_cost": round(gw_dbu_cost, 2),
                    "vm_cost": round(gw_vm_cost, 2),
                    "total_cost": round(gw_total, 2),
                }

        # ── Discount ──────────────────────────────────────────────────
        if request.discount_config:
            if request.discount_config.sku_specific:
                error = validate_sku_specific_discounts(request.discount_config.sku_specific, db)
                if error:
                    raise HTTPException(status_code=400, detail=error["error"])
            sku_breakdown = apply_discount_to_sku_breakdown(sku_breakdown, request.discount_config, db)

        response_data = {
            "success": True,
            "data": {
                "workload_type": "LAKEFLOW_CONNECT",
                "sku_type": pipeline_sku,
                "configuration": {
                    "cloud": cloud_upper, "region": request.region, "tier": tier_upper,
                    "dlt_edition": (request.dlt_edition or "ADVANCED").upper(),
                    "gateway_enabled": request.gateway_enabled,
                },
                "pipeline": {
                    "hours_per_month": pipeline_hours,
                    "dbu_per_month": round(pipeline_dbu_qty, 2),
                    "dbu_price": pipeline_dbu_price,
                    "dbu_cost": round(pipeline_dbu_cost, 2),
                },
                "total_cost": {"cost_per_month": round(total_cost, 2)},
                "sku_breakdown": sku_breakdown,
            },
        }

        if gateway_data:
            response_data["data"]["gateway"] = gateway_data

        if request.discount_config:
            response_data["data"]["total_cost"] = enhance_total_cost_with_discount(
                response_data["data"]["total_cost"], sku_breakdown)
            response_data["data"]["discount_summary"] = calculate_total_discount_summary(sku_breakdown)

        return response_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating Lakeflow Connect cost: {e}")
        return {"success": False, "error": {"code": "CALCULATION_ERROR", "message": str(e)}}
