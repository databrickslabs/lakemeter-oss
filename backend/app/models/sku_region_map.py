"""SKU Region Map model for sync_ref_sku_region_map table."""
from sqlalchemy import Column, String
from app.database import Base


class SKURegionMap(Base):
    """Model for SKU region mapping data from Lakebase sync_ref_sku_region_map table."""
    __tablename__ = "sync_ref_sku_region_map"
    __table_args__ = {'schema': 'lakemeter'}
    
    # Columns based on actual table structure:
    # cloud, sku_region, region_code
    cloud = Column(String, primary_key=True)
    sku_region = Column(String, primary_key=True)  # e.g., "US_EAST_N_VIRGINIA"
    region_code = Column(String)  # e.g., "us-east-1"

