"""Conversation Message model for AI chat history."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class ConversationMessage(Base):
    """Conversation Message model matching lakemeter.conversation_messages table."""
    
    __tablename__ = "conversation_messages"
    __table_args__ = {"schema": "lakemeter"}
    
    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estimate_id = Column(UUID(as_uuid=True), ForeignKey("lakemeter.estimates.estimate_id"), nullable=False)
    message_role = Column(String(20))  # user, assistant, system
    message_content = Column(Text)
    message_sequence = Column(Integer)
    message_type = Column(String(50))
    tokens_used = Column(Integer)
    model_used = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    estimate = relationship("Estimate", back_populates="conversations")


