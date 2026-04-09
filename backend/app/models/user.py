"""User model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    """User model matching lakemeter.users table."""
    
    __tablename__ = "users"
    __table_args__ = {"schema": "lakemeter"}
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    role = Column(String(50))
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    estimates = relationship("Estimate", back_populates="owner", foreign_keys="Estimate.owner_user_id")
    shared_estimates = relationship("Sharing", back_populates="shared_with_user", foreign_keys="Sharing.shared_with_user_id")


