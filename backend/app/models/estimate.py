"""Estimate model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Estimate(Base):
    """Estimate model matching lakemeter.estimates table."""
    
    __tablename__ = "estimates"
    __table_args__ = {"schema": "lakemeter"}
    
    estimate_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estimate_name = Column(String(500), nullable=False)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("lakemeter.users.user_id"))
    customer_name = Column(String(255))
    cloud = Column(String(50))
    region = Column(String(50))
    tier = Column(String(20))
    status = Column(String(20), default="draft")
    version = Column(Integer, default=1)
    template_id = Column(UUID(as_uuid=True), ForeignKey("lakemeter.templates.template_id"))
    original_prompt = Column(Text)
    display_order = Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("lakemeter.users.user_id"))
    
    # Relationships
    owner = relationship("User", back_populates="estimates", foreign_keys=[owner_user_id])
    line_items = relationship("LineItem", back_populates="estimate", cascade="all, delete-orphan")
    template = relationship("Template", back_populates="estimates")
    sharing = relationship("Sharing", back_populates="estimate", cascade="all, delete-orphan")
    conversations = relationship("ConversationMessage", back_populates="estimate", cascade="all, delete-orphan")
