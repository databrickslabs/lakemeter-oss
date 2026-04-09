"""SKU Discount Mapping model for sku_discount_mapping table."""
from sqlalchemy import Column, String, Boolean
from app.database import Base


class SKUDiscountMapping(Base):
    __tablename__ = "sku_discount_mapping"
    __table_args__ = {"schema": "lakemeter"}

    sku = Column(String, primary_key=True)
    discount_category = Column(String)
    workload_group = Column(String)
    description = Column(String)
    cross_service_eligible = Column(Boolean, default=True)
