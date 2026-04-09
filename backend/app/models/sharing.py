"""Sharing model for estimate sharing."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Sharing(Base):
    """Sharing model matching lakemeter.sharing table."""
    
    __tablename__ = "sharing"
    __table_args__ = {"schema": "lakemeter"}
    
    share_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estimate_id = Column(UUID(as_uuid=True), ForeignKey("lakemeter.estimates.estimate_id"), nullable=False)
    share_type = Column(String(20))  # user, link
    shared_with_user_id = Column(UUID(as_uuid=True), ForeignKey("lakemeter.users.user_id"))
    share_link = Column(String(255), unique=True)
    permission = Column(String(20), default="view")  # view, edit
    expires_at = Column(DateTime)
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    estimate = relationship("Estimate", back_populates="sharing")
    shared_with_user = relationship("User", back_populates="shared_estimates", foreign_keys=[shared_with_user_id])


