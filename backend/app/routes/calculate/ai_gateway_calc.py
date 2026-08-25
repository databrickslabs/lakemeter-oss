"""Unity AI Gateway additive feature cost calculation."""
import logging
import math
from typing import Optional

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
from app.routes.calculate.schemas import AIGatewayCalculationRequest
from app.services.validators import (
    validate_cloud,
    validate_region,
    validate_sku_specific_discounts,
    validate_tier,
)


logger = logging.getLogger(__name__)
router = APIRouter()

AI_GATEWAY_SKU = "SERVERLESS_REAL_TIME_INFERENCE"
AI_GATEWAY_COMPONENT_RATES = {
    "inference_tables": 1.429,
    "usage_tracking": 1.429,
}
AI_GATEWAY_EXCLUSION_NOTE = (
    "AI Gateway charges are additive. Underlying Model Serving or Foundation "
    "Model API inference and guardrail evaluator costs are excluded."
)
AI_GATEWAY_DIRECT_GB_NOTE = (
    "Direct monthly payload GB is preferred when metered billable payload is "
    "known."
)


def _calculate_component_usage(
    component: str,
    enabled: bool,
    input_method: Optional[str],
    requests_millions: Optional[float],
    avg_request_payload_kb: Optional[float],
    avg_response_payload_kb: Optional[float],
    monthly_payload_gb: Optional[float],
) -> Optional[dict]:
    """Calculate one enabled AI Gateway component independently."""
    if not enabled:
        return None

    normalized_input_method = (input_method or "").lower()
    if normalized_input_method not in {"requests", "payload_gb"}:
        raise ValueError(
            f"{component}_input_method must be requests or payload_gb"
        )

    numeric_values = {
        f"{component}_requests_millions": requests_millions,
        f"{component}_avg_request_payload_kb": avg_request_payload_kb,
        f"{component}_avg_response_payload_kb": avg_response_payload_kb,
        f"{component}_monthly_payload_gb": monthly_payload_gb,
    }
    for field, value in numeric_values.items():
        if value is None:
            continue
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise ValueError(f"{field} must be finite")
        if numeric_value < 0:
            raise ValueError(f"{field} must be greater than or equal to 0")

    if normalized_input_method == "requests":
        request_fields = {
            f"{component}_requests_millions": requests_millions,
            f"{component}_avg_request_payload_kb": avg_request_payload_kb,
            f"{component}_avg_response_payload_kb": avg_response_payload_kb,
        }
        missing = [
            field for field, value in request_fields.items() if value is None
        ]
        if missing:
            raise ValueError(
                f"{', '.join(missing)} required for requests input method"
            )
        payload_gb = float(requests_millions) * (
            float(avg_request_payload_kb)
            + float(avg_response_payload_kb)
        )
    else:
        if monthly_payload_gb is None:
            raise ValueError(
                f"{component}_monthly_payload_gb required for "
                "payload_gb input method"
            )
        payload_gb = float(monthly_payload_gb)

    dbu_per_gb = AI_GATEWAY_COMPONENT_RATES[component]
    return {
        "component": component,
        "display_name": component.replace("_", " ").title(),
        "enabled": True,
        "input_method": normalized_input_method,
        "dbu_per_gb": dbu_per_gb,
        "monthly_payload_gb": payload_gb,
        "monthly_dbus": payload_gb * dbu_per_gb,
    }


def calculate_ai_gateway_usage(
    inference_tables_enabled: bool,
    inference_tables_input_method: Optional[str],
    inference_tables_requests_millions: Optional[float],
    inference_tables_avg_request_payload_kb: Optional[float],
    inference_tables_avg_response_payload_kb: Optional[float],
    inference_tables_monthly_payload_gb: Optional[float],
    usage_tracking_enabled: bool,
    usage_tracking_input_method: Optional[str],
    usage_tracking_requests_millions: Optional[float],
    usage_tracking_avg_request_payload_kb: Optional[float],
    usage_tracking_avg_response_payload_kb: Optional[float],
    usage_tracking_monthly_payload_gb: Optional[float],
) -> dict:
    """Calculate each enabled AI Gateway component independently."""
    if not (inference_tables_enabled or usage_tracking_enabled):
        raise ValueError("At least one paid AI Gateway feature must be enabled")

    components = []
    component_inputs = (
        (
            "inference_tables",
            inference_tables_enabled,
            inference_tables_input_method,
            inference_tables_requests_millions,
            inference_tables_avg_request_payload_kb,
            inference_tables_avg_response_payload_kb,
            inference_tables_monthly_payload_gb,
        ),
        (
            "usage_tracking",
            usage_tracking_enabled,
            usage_tracking_input_method,
            usage_tracking_requests_millions,
            usage_tracking_avg_request_payload_kb,
            usage_tracking_avg_response_payload_kb,
            usage_tracking_monthly_payload_gb,
        ),
    )
    for component_input in component_inputs:
        component_usage = _calculate_component_usage(*component_input)
        if component_usage:
            components.append(component_usage)

    return {
        "components": components,
        "monthly_dbus": sum(
            component["monthly_dbus"] for component in components
        ),
    }


@router.post("/calculate/ai-gateway", tags=["Cost Calculation"])
def calculate_ai_gateway_cost(
    request: AIGatewayCalculationRequest,
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
    if request.tier.upper() == "STANDARD":
        raise HTTPException(
            status_code=400,
            detail="Unity AI Gateway requires Premium or Enterprise tier",
        )

    try:
        usage = calculate_ai_gateway_usage(
            inference_tables_enabled=request.inference_tables_enabled,
            inference_tables_input_method=(
                request.inference_tables_input_method
            ),
            inference_tables_requests_millions=(
                request.inference_tables_requests_millions
            ),
            inference_tables_avg_request_payload_kb=(
                request.inference_tables_avg_request_payload_kb
            ),
            inference_tables_avg_response_payload_kb=(
                request.inference_tables_avg_response_payload_kb
            ),
            inference_tables_monthly_payload_gb=(
                request.inference_tables_monthly_payload_gb
            ),
            usage_tracking_enabled=request.usage_tracking_enabled,
            usage_tracking_input_method=request.usage_tracking_input_method,
            usage_tracking_requests_millions=(
                request.usage_tracking_requests_millions
            ),
            usage_tracking_avg_request_payload_kb=(
                request.usage_tracking_avg_request_payload_kb
            ),
            usage_tracking_avg_response_payload_kb=(
                request.usage_tracking_avg_response_payload_kb
            ),
            usage_tracking_monthly_payload_gb=(
                request.usage_tracking_monthly_payload_gb
            ),
        )
        dbu_price = get_required_regional_dbu_price(
            db,
            request.cloud,
            request.region,
            request.tier,
            AI_GATEWAY_SKU,
        )
        monthly_dbu_cost = usage["monthly_dbus"] * dbu_price
        component_breakdown = [
            {
                **component,
                "dbu_price": dbu_price,
                "monthly_dbu_cost": component["monthly_dbus"] * dbu_price,
            }
            for component in usage["components"]
        ]

        sku_breakdown = build_sku_breakdown_serverless(
            sku_type=AI_GATEWAY_SKU,
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
                "workload_type": "AI_GATEWAY",
                "sku_type": AI_GATEWAY_SKU,
                "configuration": {
                    "cloud": request.cloud.upper(),
                    "region": request.region,
                    "tier": request.tier.upper(),
                    "inference_tables_enabled": (
                        request.inference_tables_enabled
                    ),
                    "inference_tables_input_method": (
                        request.inference_tables_input_method
                    ),
                    "inference_tables_requests_millions": (
                        request.inference_tables_requests_millions
                    ),
                    "inference_tables_avg_request_payload_kb": (
                        request.inference_tables_avg_request_payload_kb
                    ),
                    "inference_tables_avg_response_payload_kb": (
                        request.inference_tables_avg_response_payload_kb
                    ),
                    "inference_tables_monthly_payload_gb": (
                        request.inference_tables_monthly_payload_gb
                    ),
                    "usage_tracking_enabled": request.usage_tracking_enabled,
                    "usage_tracking_input_method": (
                        request.usage_tracking_input_method
                    ),
                    "usage_tracking_requests_millions": (
                        request.usage_tracking_requests_millions
                    ),
                    "usage_tracking_avg_request_payload_kb": (
                        request.usage_tracking_avg_request_payload_kb
                    ),
                    "usage_tracking_avg_response_payload_kb": (
                        request.usage_tracking_avg_response_payload_kb
                    ),
                    "usage_tracking_monthly_payload_gb": (
                        request.usage_tracking_monthly_payload_gb
                    ),
                },
                "usage_calculation": {
                    component["component"]: {
                        "input_method": component["input_method"],
                        "monthly_payload_gb": (
                            component["monthly_payload_gb"]
                        ),
                        "monthly_dbus": component["monthly_dbus"],
                    }
                    for component in usage["components"]
                },
                "component_breakdown": component_breakdown,
                "dbu_calculation": {
                    "monthly_dbus": usage["monthly_dbus"],
                    "dbu_per_month": usage["monthly_dbus"],
                    "dbu_price": dbu_price,
                    "monthly_dbu_cost": monthly_dbu_cost,
                    "dbu_cost_per_month": monthly_dbu_cost,
                },
                "total_cost": {
                    "cost_per_month": monthly_dbu_cost,
                },
                "sku_breakdown": sku_breakdown,
                "notes": [
                    AI_GATEWAY_DIRECT_GB_NOTE,
                    AI_GATEWAY_EXCLUSION_NOTE,
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
    except Exception as exc:
        logger.error("Error calculating AI Gateway cost: %s", exc)
        return {
            "success": False,
            "error": {
                "code": "CALCULATION_ERROR",
                "message": str(exc),
            },
        }
