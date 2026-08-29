"""Estimate-level Databricks Platform add-on calculation endpoint."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.platform_addons import calculate_platform_addon_cost


router = APIRouter()


class PlatformAddonCalculationRequest(BaseModel):
    cloud: str = Field(..., description="Cloud provider: AWS, AZURE, GCP")
    tier: str = Field(..., description="Databricks pricing tier")
    addon_type: Literal[
        "ENHANCED_SECURITY_COMPLIANCE",
        "MISSION_CRITICAL",
    ]
    product_spend_at_list: float = Field(
        ...,
        ge=0,
        description="Databricks product spend before discounts, credits, or add-ons",
    )
    pricing_date: date | None = Field(
        default=None,
        description="Optional date used to resolve time-bound promotions",
    )
    discount_pct: float = Field(
        default=0,
        ge=0,
        le=100,
        description="Negotiated discount applied to the calculated add-on charge",
    )


@router.post("/calculate/platform-addon", tags=["Cost Calculation"])
def calculate_platform_addon(
    request: PlatformAddonCalculationRequest,
):
    """Apply the published add-on uplift to product spend at list."""
    try:
        result = calculate_platform_addon_cost(
            request.product_spend_at_list,
            request.addon_type,
            request.cloud,
            request.tier,
            pricing_date=request.pricing_date,
            discount_pct=request.discount_pct,
        )
        return {
            "success": True,
            "data": {
                **result,
                "notes": [
                    "Product Spend is calculated before discounts, usage credits, "
                    "add-on uplifts, or support fees.",
                    "Cloud-provider VM infrastructure is excluded.",
                    f"Pricing reference: {result['source_url']}",
                ],
            },
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
