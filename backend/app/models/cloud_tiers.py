"""Cloud Tiers model for ref_cloud_tiers table."""
from sqlalchemy import Column, String
from app.database import Base


class CloudTiers(Base):
    __tablename__ = "ref_cloud_tiers"
    __table_args__ = {"schema": "lakemeter"}

    cloud = Column(String, primary_key=True)
    tier = Column(String, primary_key=True)
