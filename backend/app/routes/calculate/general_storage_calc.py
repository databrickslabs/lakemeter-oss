"""Databricks Default Storage monthly cost calculation."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.routes.calculate.discount import (
    apply_discount_to_sku_breakdown,
    calculate_total_discount_summary,
    enhance_total_cost_with_discount,
)
from app.routes.calculate.helpers import get_required_regional_dbu_price
from app.routes.calculate.schemas import GeneralStorageCalculationRequest
from app.services.general_storage_pricing import (
    GENERAL_STORAGE_SKU,
    calculate_general_storage_usage,
)
from app.services.validators import (
    validate_cloud,
    validate_region,
    validate_sku_specific_discounts,
    validate_tier,
)


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/calculate/general-storage", tags=["Cost Calculation"])
def calculate_general_storage_cost(
    request: GeneralStorageCalculationRequest,
    db: Session = Depends(get_db),
):
    """Calculate Default Storage DSUs using the exact regional rate."""
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
        usage = calculate_general_storage_usage(
            request.quantity,
            request.unit,
            request.cloud,
            request.tier_1_operations_thousands,
            request.tier_2_operations_thousands,
        )
        dsu_price = get_required_regional_dbu_price(
            db,
            request.cloud,
            request.region,
            request.tier,
            GENERAL_STORAGE_SKU,
        )
        components = [
            {
                "rate_type": "stored_data",
                "display_name": "Stored Data",
                "input_quantity": usage["billable_gb_months"],
                "input_unit": "GB_MONTH",
                "dsu_multiplier": (
                    usage["dsu_rates"]["stored_data_per_gb_month"]
                ),
                "dsu": usage["stored_data_dsu"],
            },
            {
                "rate_type": "tier_1_operations",
                "display_name": "Tier 1 Operations",
                "input_quantity": usage["tier_1_operations_thousands"],
                "input_unit": "THOUSAND_OPERATIONS",
                "dsu_multiplier": (
                    usage["dsu_rates"]["tier_1_per_thousand"]
                ),
                "dsu": usage["tier_1_operations_dsu"],
            },
            {
                "rate_type": "tier_2_operations",
                "display_name": "Tier 2 Operations",
                "input_quantity": usage["tier_2_operations_thousands"],
                "input_unit": "THOUSAND_OPERATIONS",
                "dsu_multiplier": (
                    usage["dsu_rates"]["tier_2_per_thousand"]
                ),
                "dsu": usage["tier_2_operations_dsu"],
            },
        ]
        for component in components:
            component["cost_per_month"] = component["dsu"] * dsu_price

        monthly_cost = usage["total_dsu"] * dsu_price
        sku_breakdown = [
            {
                "type": "dsu",
                "sku": GENERAL_STORAGE_SKU,
                "cost": round(component["cost_per_month"], 6),
                "qty": round(component["dsu"], 6),
                "usage_unit": "DSU",
                "unit_price_before_discount": round(dsu_price, 6),
                "rate_type": component["rate_type"],
            }
            for component in components
        ]

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
                "workload_type": "GENERAL_STORAGE",
                "sku_type": GENERAL_STORAGE_SKU,
                "configuration": {
                    "cloud": request.cloud.upper(),
                    "region": request.region,
                    "tier": request.tier.upper(),
                    "quantity": usage["quantity"],
                    "unit": usage["unit"],
                    "tier_1_operations_thousands": (
                        usage["tier_1_operations_thousands"]
                    ),
                    "tier_2_operations_thousands": (
                        usage["tier_2_operations_thousands"]
                    ),
                },
                "usage_calculation": usage,
                "dsu_calculation": {
                    "components": components,
                    "total_dsu": usage["total_dsu"],
                    "price_per_dsu": dsu_price,
                    "monthly_dsu_cost": monthly_cost,
                },
                "storage_calculation": {
                    "billable_gb_months": usage["billable_gb_months"],
                    "unit_price": dsu_price,
                    "price_per_dsu": dsu_price,
                    "monthly_storage_cost": monthly_cost,
                },
                "total_cost": {
                    "cost_per_month": monthly_cost,
                    "breakdown": {"dsu_cost": monthly_cost},
                },
                "sku_breakdown": sku_breakdown,
                "notes": [
                    "Default Storage is billed in binary GB-months; 1 TB "
                    "is converted to 1,024 GB.",
                    "Tier 1 includes PUT, COPY, POST, and LIST operations. "
                    "Tier 2 includes other API operations.",
                    "Customer-managed object storage, backups, and data "
                    "transfer are excluded.",
                    "Pricing reference: "
                    "https://www.databricks.com/product/pricing/storage",
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
        logger.error("Error calculating General Storage cost: %s", exc)
        return {
            "success": False,
            "error": {
                "code": "CALCULATION_ERROR",
                "message": str(exc),
            },
        }
