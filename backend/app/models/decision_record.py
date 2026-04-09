"""Decision Record model for tracking AI decisions."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class DecisionRecord(Base):
    """Decision Record model matching lakemeter.decision_records table."""
    
    __tablename__ = "decision_records"
    __table_args__ = {"schema": "lakemeter"}
    
    record_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_item_id = Column(UUID(as_uuid=True), ForeignKey("lakemeter.line_items.line_item_id"), nullable=False)
    record_type = Column(String(50))
    user_input = Column(Text)
    agent_response = Column(Text)
    assumptions = Column(JSON)
    calculations = Column(JSON)
    reasoning = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    line_item = relationship("LineItem", back_populates="decision_records")


