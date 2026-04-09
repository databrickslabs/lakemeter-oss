"""Instance DBU Rates model for sync_ref_instance_dbu_rates table."""
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime
from app.database import Base


class InstanceDBURates(Base):
    """Model for instance DBU rates from Lakebase sync_ref_instance_dbu_rates table."""
    __tablename__ = "sync_ref_instance_dbu_rates"
    __table_args__ = {'schema': 'lakemeter'}
    
    # Composite primary key: cloud + instance_type
    cloud = Column(String, primary_key=True)
    instance_type = Column(String, primary_key=True)
    
    instance_family = Column(String)
    vcpus = Column(Integer)
    memory_gb = Column(Integer)
    dbu_rate = Column(Float)
    is_active = Column(Boolean, default=True)
    source = Column(String)
    updated_at = Column(DateTime)

