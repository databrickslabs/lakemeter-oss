"""DBU Multipliers model for sync_ref_dbu_multipliers table."""
from sqlalchemy import Column, String, Float
from app.database import Base


class DBUMultipliers(Base):
    __tablename__ = "sync_ref_dbu_multipliers"
    __table_args__ = {"schema": "lakemeter"}

    feature = Column(String, primary_key=True)
    cloud = Column(String, primary_key=True)
    sku_type = Column(String, primary_key=True)
    multiplier = Column(Float)
