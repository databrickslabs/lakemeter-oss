"""Pydantic schemas for VM pricing."""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class VMPricingResponse(BaseModel):
    """Response schema for VM pricing data."""
    cloud: str
    region: str
    instance_type: str
    pricing_tier: str
    payment_option: str
    cost_per_hour: float
    currency: str = "USD"
    source: Optional[str] = None
    fetched_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class VMInstanceTypesResponse(BaseModel):
    """Response schema for unique instance types for a cloud/region."""
    instance_type: str


class VMPricingTierResponse(BaseModel):
    """Response schema for pricing tier options."""
    id: str
    name: str
    description: str


class VMPaymentOptionResponse(BaseModel):
    """Response schema for payment options (AWS only)."""
    id: str
    name: str
    description: str

