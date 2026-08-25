"""Agent Evaluation additive service cost calculation."""
import logging
import math

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
from app.routes.calculate.schemas import AgentEvaluationCalculationRequest
from app.services.validators import (
    validate_cloud,
    validate_region,
    validate_sku_specific_discounts,
    validate_tier,
)


logger = logging.getLogger(__name__)
router = APIRouter()

AGENT_EVALUATION_SKU = "SERVERLESS_REAL_TIME_INFERENCE"
AGENT_EVALUATION_COMPONENT_RATES = {
    "input_tokens": 2.143,
    "output_tokens": 8.571,
    "synthetic_questions": 5.0,
}
AGENT_EVALUATION_EXCLUSION_NOTE = (
    "Agent Evaluation service charges are additive and exclude the evaluated "
    "app or model inference; add Model Serving or Foundation Model API "
    "workloads separately."
)


def _validate_nonnegative_finite(field: str, value: float) -> float:
    """Return a finite non-negative numeric value."""
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a number") from exc
    if not math.isfinite(numeric_value):
        raise ValueError(f"{field} must be finite")
    if numeric_value < 0:
        raise ValueError(f"{field} must be greater than or equal to 0")
    return numeric_value


def calculate_agent_evaluation_usage(
    labels_enabled: bool,
    input_tokens_millions: float,
    output_tokens_millions: float,
    synthetic_data_enabled: bool,
    synthetic_questions: int,
) -> dict:
    """Calculate enabled Agent Evaluation dimensions independently."""
    if not (labels_enabled or synthetic_data_enabled):
        raise ValueError(
            "At least one Agent Evaluation feature must be enabled: "
            "labels or synthetic data"
        )

    input_tokens = _validate_nonnegative_finite(
        "input_tokens_millions",
        input_tokens_millions,
    )
    output_tokens = _validate_nonnegative_finite(
        "output_tokens_millions",
        output_tokens_millions,
    )
    questions = _validate_nonnegative_finite(
        "synthetic_questions",
        synthetic_questions,
    )
    if isinstance(synthetic_questions, bool) or not questions.is_integer():
        raise ValueError("synthetic_questions must be an integer")

    components = []
    if labels_enabled:
        for component, display_name, quantity in (
            ("input_tokens", "Evaluation Input Tokens", input_tokens),
            ("output_tokens", "Evaluation Output Tokens", output_tokens),
        ):
            rate = AGENT_EVALUATION_COMPONENT_RATES[component]
            components.append({
                "component": component,
                "display_name": display_name,
                "enabled": True,
                "quantity": quantity,
                "quantity_unit": "million_tokens",
                "dbu_per_unit": rate,
                "monthly_dbus": quantity * rate,
            })
    if synthetic_data_enabled:
        rate = AGENT_EVALUATION_COMPONENT_RATES["synthetic_questions"]
        components.append({
            "component": "synthetic_questions",
            "display_name": "Synthetic Data Questions",
            "enabled": True,
            "quantity": int(questions),
            "quantity_unit": "questions",
            "dbu_per_unit": rate,
            "monthly_dbus": questions * rate,
        })

    return {
        "components": components,
        "monthly_dbus": sum(
            component["monthly_dbus"] for component in components
        ),
    }


@router.post("/calculate/agent-evaluation", tags=["Cost Calculation"])
def calculate_agent_evaluation_cost(
    request: AgentEvaluationCalculationRequest,
    db: Session = Depends(get_db),
):
    """Calculate regional Agent Evaluation service charges."""
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
            detail="Agent Evaluation requires Premium or Enterprise tier",
        )

    try:
        usage = calculate_agent_evaluation_usage(
            labels_enabled=request.labels_enabled,
            input_tokens_millions=request.input_tokens_millions,
            output_tokens_millions=request.output_tokens_millions,
            synthetic_data_enabled=request.synthetic_data_enabled,
            synthetic_questions=request.synthetic_questions,
        )
        dbu_price = get_required_regional_dbu_price(
            db,
            request.cloud,
            request.region,
            request.tier,
            AGENT_EVALUATION_SKU,
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
            sku_type=AGENT_EVALUATION_SKU,
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
                "workload_type": "AGENT_EVALUATION",
                "sku_type": AGENT_EVALUATION_SKU,
                "configuration": {
                    "cloud": request.cloud.upper(),
                    "region": request.region,
                    "tier": request.tier.upper(),
                    "labels_enabled": request.labels_enabled,
                    "input_tokens_millions": (
                        request.input_tokens_millions
                    ),
                    "output_tokens_millions": (
                        request.output_tokens_millions
                    ),
                    "synthetic_data_enabled": (
                        request.synthetic_data_enabled
                    ),
                    "synthetic_questions": request.synthetic_questions,
                },
                "usage_calculation": {
                    component["component"]: {
                        "quantity": component["quantity"],
                        "quantity_unit": component["quantity_unit"],
                        "dbu_per_unit": component["dbu_per_unit"],
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
                "notes": [AGENT_EVALUATION_EXCLUSION_NOTE],
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
        logger.error("Error calculating Agent Evaluation cost: %s", exc)
        return {
            "success": False,
            "error": {
                "code": "CALCULATION_ERROR",
                "message": str(exc),
            },
        }
