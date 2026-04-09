"""FMAPI Databricks model for sync_product_fmapi_databricks table."""
from sqlalchemy import Column, String, Float
from app.database import Base


class FMAPIDatabricks(Base):
    __tablename__ = "sync_product_fmapi_databricks"
    __table_args__ = {"schema": "lakemeter"}

    model = Column(String, primary_key=True)
    cloud = Column(String, primary_key=True)
    rate_type = Column(String, primary_key=True)
    price_per_million = Column(Float)
    dbu_per_million = Column(Float)
