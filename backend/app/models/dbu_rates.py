"""DBU Rates model for sync_pricing_dbu_rates table."""
from sqlalchemy import Column, String, Float
from app.database import Base


class DBURates(Base):
    __tablename__ = "sync_pricing_dbu_rates"
    __table_args__ = {"schema": "lakemeter"}

    cloud = Column(String, primary_key=True)
    region = Column(String, primary_key=True)
    tier = Column(String, primary_key=True)
    product_type = Column(String, primary_key=True)
    dbu_price = Column(Float)
    dbu_per_hour = Column(Float)
