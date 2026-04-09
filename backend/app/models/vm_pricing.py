"""VM Pricing model for sync_pricing_vm_costs table."""
from sqlalchemy import Column, String, Float, DateTime
from app.database import Base


class VMPricing(Base):
    """Model for VM pricing data from Lakebase sync_pricing_vm_costs table."""
    __tablename__ = "sync_pricing_vm_costs"
    __table_args__ = {'schema': 'lakemeter'}
    
    # Composite primary key: cloud + region + instance_type + pricing_tier + payment_option
    cloud = Column(String, primary_key=True)
    region = Column(String, primary_key=True)
    instance_type = Column(String, primary_key=True)
    pricing_tier = Column(String, primary_key=True)
    payment_option = Column(String, primary_key=True, default="NA")
    
    cost_per_hour = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    source = Column(String)
    fetched_at = Column(DateTime)
    updated_at = Column(DateTime)

