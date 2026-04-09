"""Line Item schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class LineItemBase(BaseModel):
    """Base line item schema."""
    workload_name: str
    workload_type: Optional[str] = None
    display_order: Optional[int] = 0
    cloud: Optional[str] = None
    
    # Serverless toggle
    serverless_enabled: Optional[bool] = False
    serverless_mode: Optional[str] = None
    
    # Classic Compute Configuration
    photon_enabled: Optional[bool] = False
    driver_node_type: Optional[str] = None
    worker_node_type: Optional[str] = None
    num_workers: Optional[int] = 1
    
    # DLT Configuration
    dlt_edition: Optional[str] = None
    
    # DBSQL Configuration
    dbsql_warehouse_type: Optional[str] = None
    dbsql_warehouse_size: Optional[str] = None
    dbsql_num_clusters: Optional[int] = None
    dbsql_vm_pricing_tier: Optional[str] = None
    dbsql_vm_payment_option: Optional[str] = None
    
    # Vector Search Configuration
    vector_search_mode: Optional[str] = None
    vector_capacity_millions: Optional[int] = None
    vector_search_storage_gb: Optional[int] = None

    # Model Serving Configuration
    model_serving_gpu_type: Optional[str] = None

    # Foundation Model API Configuration (Proprietary)
    fmapi_provider: Optional[str] = None
    fmapi_model: Optional[str] = None
    fmapi_endpoint_type: Optional[str] = None
    fmapi_context_length: Optional[str] = None
    fmapi_rate_type: Optional[str] = None  # input_token, output_token, cache_read, cache_write
    fmapi_quantity: Optional[Decimal] = None  # quantity in millions (M)

    # Lakebase Configuration
    lakebase_cu: Optional[float] = None
    lakebase_storage_gb: Optional[int] = None
    lakebase_ha_nodes: Optional[int] = None
    lakebase_backup_retention_days: Optional[int] = None

    # Usage Configuration
    runs_per_day: Optional[int] = None
    avg_runtime_minutes: Optional[int] = None
    days_per_month: Optional[int] = 22
    hours_per_month: Optional[int] = None

    # Pricing Configuration
    driver_pricing_tier: Optional[str] = None
    worker_pricing_tier: Optional[str] = None
    driver_payment_option: Optional[str] = None
    worker_payment_option: Optional[str] = None

    # Additional Configuration
    workload_config: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class LineItemCreate(LineItemBase):
    """Schema for creating a line item."""
    estimate_id: UUID


class LineItemUpdate(BaseModel):
    """Schema for updating a line item."""
    workload_name: Optional[str] = None
    workload_type: Optional[str] = None
    display_order: Optional[int] = None
    cloud: Optional[str] = None

    # Serverless toggle
    serverless_enabled: Optional[bool] = None
    serverless_mode: Optional[str] = None

    # Classic Compute Configuration
    photon_enabled: Optional[bool] = None
    driver_node_type: Optional[str] = None
    worker_node_type: Optional[str] = None
    num_workers: Optional[int] = None

    # DLT Configuration
    dlt_edition: Optional[str] = None

    # DBSQL Configuration
    dbsql_warehouse_type: Optional[str] = None
    dbsql_warehouse_size: Optional[str] = None
    dbsql_num_clusters: Optional[int] = None
    dbsql_vm_pricing_tier: Optional[str] = None
    dbsql_vm_payment_option: Optional[str] = None

    # Vector Search Configuration
    vector_search_mode: Optional[str] = None
    vector_capacity_millions: Optional[int] = None
    vector_search_storage_gb: Optional[int] = None
    
    # Model Serving Configuration
    model_serving_gpu_type: Optional[str] = None
    
    # Foundation Model API Configuration (Proprietary)
    fmapi_provider: Optional[str] = None
    fmapi_model: Optional[str] = None
    fmapi_endpoint_type: Optional[str] = None
    fmapi_context_length: Optional[str] = None
    fmapi_rate_type: Optional[str] = None
    fmapi_quantity: Optional[Decimal] = None
    
    # Lakebase Configuration
    lakebase_cu: Optional[float] = None
    lakebase_storage_gb: Optional[int] = None
    lakebase_ha_nodes: Optional[int] = None
    lakebase_backup_retention_days: Optional[int] = None
    
    # Usage Configuration
    runs_per_day: Optional[int] = None
    avg_runtime_minutes: Optional[int] = None
    days_per_month: Optional[int] = None
    hours_per_month: Optional[int] = None
    
    # Pricing Configuration
    driver_pricing_tier: Optional[str] = None
    worker_pricing_tier: Optional[str] = None
    driver_payment_option: Optional[str] = None
    worker_payment_option: Optional[str] = None
    
    # Additional Configuration
    workload_config: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class LineItemResponse(LineItemBase):
    """Schema for line item response."""
    line_item_id: UUID
    estimate_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
