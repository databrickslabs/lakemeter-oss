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
    model_serving_concurrency: Optional[int] = None
    model_serving_scale_out: Optional[str] = None
    model_servings_number_endpoints: Optional[int] = None

    # Foundation Model API Configuration (Proprietary)
    fmapi_provider: Optional[str] = None
    fmapi_model: Optional[str] = None
    fmapi_endpoint_type: Optional[str] = None
    fmapi_context_length: Optional[str] = None
    fmapi_rate_type: Optional[str] = None  # input_token, output_token, cache_read, cache_write
    fmapi_quantity: Optional[Decimal] = None  # quantity in millions (M)

    # Databricks Apps Configuration
    databricks_apps_size: Optional[str] = None
    databricks_apps_hours_per_month: Optional[float] = None
    databricks_apps_num_apps: Optional[int] = None

    # Clean Room Configuration
    clean_room_num_collaborators: Optional[int] = None
    clean_room_days_per_month: Optional[int] = None

    # AI Parse Configuration
    ai_parse_calculation_method: Optional[str] = None
    ai_parse_complexity: Optional[str] = None
    ai_parse_dbu_quantity: Optional[float] = None
    ai_parse_num_pages: Optional[float] = None

    # Shutterstock ImageAI Configuration
    shutterstock_imageai_num_images: Optional[int] = None

    # Databricks Support Configuration
    databricks_support_tier: Optional[str] = None
    databricks_support_annual_commit: Optional[float] = None

    # Lakeflow Connect Configuration
    lakeflow_connect_connector_type: Optional[str] = None
    lakeflow_connect_pipeline_driver_node_type: Optional[str] = None
    lakeflow_connect_pipeline_worker_node_type: Optional[str] = None
    lakeflow_connect_pipeline_num_workers: Optional[int] = None
    lakeflow_connect_pipeline_serverless_mode: Optional[str] = None
    lakeflow_connect_pipeline_runs_per_day: Optional[int] = None
    lakeflow_connect_pipeline_avg_runtime_minutes: Optional[int] = None
    lakeflow_connect_pipeline_hours_per_month: Optional[float] = None
    lakeflow_connect_gateway_cloud: Optional[str] = None
    lakeflow_connect_gateway_instance_type: Optional[str] = None
    lakeflow_connect_gateway_num_workers: Optional[int] = None
    lakeflow_connect_gateway_hours_per_month: Optional[float] = None

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

    # Calculated results
    cost_calculation_response: Optional[Dict[str, Any]] = None
    calculation_completed_at: Optional[datetime] = None


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
    model_serving_concurrency: Optional[int] = None
    model_serving_scale_out: Optional[str] = None
    model_servings_number_endpoints: Optional[int] = None

    # Foundation Model API Configuration (Proprietary)
    fmapi_provider: Optional[str] = None
    fmapi_model: Optional[str] = None
    fmapi_endpoint_type: Optional[str] = None
    fmapi_context_length: Optional[str] = None
    fmapi_rate_type: Optional[str] = None
    fmapi_quantity: Optional[Decimal] = None

    # Databricks Apps Configuration
    databricks_apps_size: Optional[str] = None
    databricks_apps_hours_per_month: Optional[float] = None
    databricks_apps_num_apps: Optional[int] = None

    # Clean Room Configuration
    clean_room_num_collaborators: Optional[int] = None
    clean_room_days_per_month: Optional[int] = None

    # AI Parse Configuration
    ai_parse_calculation_method: Optional[str] = None
    ai_parse_complexity: Optional[str] = None
    ai_parse_dbu_quantity: Optional[float] = None
    ai_parse_num_pages: Optional[float] = None

    # Shutterstock ImageAI Configuration
    shutterstock_imageai_num_images: Optional[int] = None

    # Databricks Support Configuration
    databricks_support_tier: Optional[str] = None
    databricks_support_annual_commit: Optional[float] = None

    # Lakeflow Connect Configuration
    lakeflow_connect_connector_type: Optional[str] = None
    lakeflow_connect_pipeline_driver_node_type: Optional[str] = None
    lakeflow_connect_pipeline_worker_node_type: Optional[str] = None
    lakeflow_connect_pipeline_num_workers: Optional[int] = None
    lakeflow_connect_pipeline_serverless_mode: Optional[str] = None
    lakeflow_connect_pipeline_runs_per_day: Optional[int] = None
    lakeflow_connect_pipeline_avg_runtime_minutes: Optional[int] = None
    lakeflow_connect_pipeline_hours_per_month: Optional[float] = None
    lakeflow_connect_gateway_cloud: Optional[str] = None
    lakeflow_connect_gateway_instance_type: Optional[str] = None
    lakeflow_connect_gateway_num_workers: Optional[int] = None
    lakeflow_connect_gateway_hours_per_month: Optional[float] = None

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

    # Calculated results
    cost_calculation_response: Optional[Dict[str, Any]] = None
    calculation_completed_at: Optional[datetime] = None


class LineItemResponse(LineItemBase):
    """Schema for line item response."""
    line_item_id: UUID
    estimate_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
