"""Workload Type schemas - matches the CSV schema."""
from typing import Optional
from pydantic import BaseModel, ConfigDict


class WorkloadTypeResponse(BaseModel):
    """Schema for workload type response."""
    workload_type: str
    display_name: str
    description: Optional[str] = None
    
    # Configuration visibility flags
    show_compute_config: bool = False
    show_serverless_toggle: bool = False
    show_serverless_performance_mode: bool = False
    show_photon_toggle: bool = False
    show_dlt_config: bool = False
    show_dbsql_config: bool = False
    show_serverless_product: bool = False
    show_fmapi_config: bool = False
    show_lakebase_config: bool = False
    show_vector_search_mode: bool = False
    show_vm_pricing: bool = False
    show_usage_hours: bool = False
    show_usage_runs: bool = False
    show_usage_tokens: bool = False
    
    # SKU product types
    sku_product_type_standard: Optional[str] = None
    sku_product_type_photon: Optional[str] = None
    sku_product_type_serverless: Optional[str] = None
    
    display_order: int = 0
    
    model_config = ConfigDict(from_attributes=True)
