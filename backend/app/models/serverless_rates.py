"""Serverless Rates model for sync_product_serverless_rates table."""
from sqlalchemy import Column, String, Float
from app.database import Base


class ServerlessRates(Base):
    __tablename__ = "sync_product_serverless_rates"
    __table_args__ = {"schema": "lakemeter"}

    product = Column(String, primary_key=True)
    cloud = Column(String, primary_key=True)
    size_or_model = Column(String, primary_key=True)
    dbu_per_hour = Column(Float)
