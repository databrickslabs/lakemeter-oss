"""Template model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Template(Base):
    """Template model matching lakemeter.templates table."""
    
    __tablename__ = "templates"
    __table_args__ = {"schema": "lakemeter"}
    
    template_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_name = Column(String(255), nullable=False)
    workload_type = Column(String(100))
    file_path = Column(String(500))
    file_format = Column(String(10))
    mandatory_fields = Column(JSON)
    optional_fields = Column(JSON)
    description = Column(Text)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    estimates = relationship("Estimate", back_populates="template")


