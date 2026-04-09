"""Sharing schemas."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ShareCreate(BaseModel):
    """Schema for creating a share."""
    estimate_id: UUID
    share_type: str = "user"  # user or link
    shared_with_user_id: Optional[UUID] = None
    permission: str = "view"  # view or edit
    expires_at: Optional[datetime] = None


class ShareResponse(BaseModel):
    """Schema for share response."""
    share_id: UUID
    estimate_id: UUID
    share_type: str
    shared_with_user_id: Optional[UUID] = None
    share_link: Optional[str] = None
    permission: str
    expires_at: Optional[datetime] = None
    access_count: int
    last_accessed_at: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


