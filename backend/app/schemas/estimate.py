"""Estimate schemas."""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class EstimateBase(BaseModel):
    """Base estimate schema."""
    estimate_name: str
    cloud: Optional[str] = None
    region: Optional[str] = None
    tier: Optional[str] = None
    status: Optional[str] = "draft"


class EstimateCreate(EstimateBase):
    """Schema for creating an estimate."""
    template_id: Optional[UUID] = None
    original_prompt: Optional[str] = None


class EstimateUpdate(BaseModel):
    """Schema for updating an estimate."""
    estimate_name: Optional[str] = None
    cloud: Optional[str] = None
    region: Optional[str] = None
    tier: Optional[str] = None
    status: Optional[str] = None


class LineItemSummary(BaseModel):
    """Summary of line item for estimate response."""
    line_item_id: UUID
    workload_name: str
    workload_type: Optional[str] = None
    display_order: int

    model_config = ConfigDict(from_attributes=True)


class EstimateResponse(EstimateBase):
    """Schema for estimate response."""
    estimate_id: UUID
    owner_user_id: Optional[UUID] = None
    version: int
    template_id: Optional[UUID] = None
    original_prompt: Optional[str] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    updated_by: Optional[UUID] = None
    line_items: List[LineItemSummary] = []

    model_config = ConfigDict(from_attributes=True)


class EstimateListResponse(BaseModel):
    """Schema for listing estimates."""
    estimate_id: UUID
    estimate_name: str
    customer_name: Optional[str] = None
    cloud: Optional[str] = None
    region: Optional[str] = None
    tier: Optional[str] = None
    status: Optional[str] = None
    version: int
    line_item_count: int = 0
    display_order: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EstimateWithLineItemsResponse(EstimateBase):
    """Schema for estimate with full line items - optimized single-query response."""
    estimate_id: UUID
    owner_user_id: Optional[UUID] = None
    version: int
    template_id: Optional[UUID] = None
    original_prompt: Optional[str] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    updated_by: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)
