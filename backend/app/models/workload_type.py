"""Reference Workload Type model - matches the CSV schema."""
from sqlalchemy import Column, String, Integer, Boolean, Text
from sqlalchemy.orm import relationship
from app.database import Base


class RefWorkloadType(Base):
    """Reference Workload Type model matching lakemeter.ref_workload_types table."""
    
    __tablename__ = "ref_workload_types"
    __table_args__ = {"schema": "lakemeter"}
    
    workload_type = Column(String(50), primary_key=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Configuration visibility flags
    show_compute_config = Column(Boolean, default=False)
    show_serverless_toggle = Column(Boolean, default=False)
    show_serverless_performance_mode = Column(Boolean, default=False)
    show_photon_toggle = Column(Boolean, default=False)
    show_dlt_config = Column(Boolean, default=False)
    show_dbsql_config = Column(Boolean, default=False)
    show_serverless_product = Column(Boolean, default=False)
    show_fmapi_config = Column(Boolean, default=False)
    show_lakebase_config = Column(Boolean, default=False)
    show_vector_search_mode = Column(Boolean, default=False)
    show_vm_pricing = Column(Boolean, default=False)
    show_usage_hours = Column(Boolean, default=False)
    show_usage_runs = Column(Boolean, default=False)
    show_usage_tokens = Column(Boolean, default=False)
    
    # SKU product types
    sku_product_type_standard = Column(String(100))
    sku_product_type_photon = Column(String(100))
    sku_product_type_serverless = Column(String(100))
    
    display_order = Column(Integer, default=0)
    
    # Relationships
    line_items = relationship("LineItem", back_populates="workload_type_ref")


