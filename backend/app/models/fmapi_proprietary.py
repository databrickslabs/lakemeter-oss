"""FMAPI Proprietary model for sync_product_fmapi_proprietary table."""
from sqlalchemy import Column, String, Float
from app.database import Base


class FMAPIProprietary(Base):
    __tablename__ = "sync_product_fmapi_proprietary"
    __table_args__ = {"schema": "lakemeter"}

    provider = Column(String, primary_key=True)
    model = Column(String, primary_key=True)
    endpoint_type = Column(String, primary_key=True)
    context_length = Column(String, primary_key=True)
    rate_type = Column(String, primary_key=True)
    price_per_million = Column(Float)
    dbu_per_million = Column(Float)
