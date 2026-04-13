"""Line Item model for estimate workloads."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class LineItem(Base):
    """Line Item model matching lakemeter.line_items table."""

    __tablename__ = "line_items"
    __table_args__ = {"schema": "lakemeter"}

    line_item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estimate_id = Column(UUID(as_uuid=True), ForeignKey("lakemeter.estimates.estimate_id"), nullable=False)
    display_order = Column(Integer, default=0)
    workload_name = Column(String(255), nullable=False)
    workload_type = Column(String(50), ForeignKey("lakemeter.ref_workload_types.workload_type"))
    cloud = Column(String(50))

    # Serverless toggle
    serverless_enabled = Column(Boolean, default=False)
    serverless_mode = Column(String(20))  # standard, performance

    # Classic Compute Configuration
    photon_enabled = Column(Boolean, default=False)
    driver_node_type = Column(String(100))
    worker_node_type = Column(String(100))
    num_workers = Column(Integer, default=1)

    # DLT Configuration
    dlt_edition = Column(String(20))  # core, pro, advanced

    # DBSQL Configuration
    dbsql_warehouse_type = Column(String(20))  # classic, pro, serverless
    dbsql_warehouse_size = Column(String(20))  # 2x-small, x-small, small, medium, large, x-large, etc.
    dbsql_num_clusters = Column(Integer, default=1)
    dbsql_vm_pricing_tier = Column(String(20))  # on-demand, 1yr, 3yr
    dbsql_vm_payment_option = Column(String(20))  # no-upfront, partial-upfront, all-upfront

    # Vector Search Configuration
    vector_search_mode = Column(String(20))  # standard, storage_optimized
    vector_capacity_millions = Column(Integer)
    vector_search_storage_gb = Column(Integer)

    # Model Serving Configuration
    model_serving_gpu_type = Column(String(50))  # cpu, gpu_small_t4, gpu_medium_a10g_1x, etc.
    model_serving_concurrency = Column(Integer)   # Resolved concurrency value (multiples of 4)
    model_serving_scale_out = Column(String(20))  # small, medium, large, custom
    model_servings_number_endpoints = Column(Integer)

    # Foundation Model API Configuration (Proprietary)
    fmapi_provider = Column(String(50))  # anthropic, openai, google
    fmapi_model = Column(String(100))  # claude-sonnet-4-5, gpt-5, etc.
    fmapi_endpoint_type = Column(String(20))  # global, in_geo
    fmapi_context_length = Column(String(20))  # all, short, long
    fmapi_rate_type = Column(String(20))  # input_token, output_token, cache_read, cache_write
    fmapi_quantity = Column(Numeric(18, 2))  # quantity in millions (M)

    # Databricks Apps Configuration
    databricks_apps_size = Column(String(20))  # medium, large
    databricks_apps_hours_per_month = Column(Numeric(12, 2))
    databricks_apps_num_apps = Column(Integer)

    # Clean Room Configuration
    clean_room_num_collaborators = Column(Integer)  # 1-10
    clean_room_days_per_month = Column(Integer)

    # AI Parse Configuration
    ai_parse_calculation_method = Column(String(20))  # dbu, pages
    ai_parse_complexity = Column(String(20))  # low_text, low_images, medium, high
    ai_parse_dbu_quantity = Column(Numeric(12, 2))
    ai_parse_num_pages = Column(Numeric(12, 2))  # pages

    # Shutterstock ImageAI Configuration
    shutterstock_imageai_num_images = Column(Integer)  # number of images per month

    # Databricks Support Configuration
    databricks_support_tier = Column(String(50))
    databricks_support_annual_commit = Column(Numeric(18, 2))

    # Lakeflow Connect Configuration
    lakeflow_connect_connector_type = Column(String(50))
    lakeflow_connect_pipeline_driver_node_type = Column(String(100))
    lakeflow_connect_pipeline_worker_node_type = Column(String(100))
    lakeflow_connect_pipeline_num_workers = Column(Integer)
    lakeflow_connect_pipeline_serverless_mode = Column(String(20))
    lakeflow_connect_pipeline_runs_per_day = Column(Integer)
    lakeflow_connect_pipeline_avg_runtime_minutes = Column(Integer)
    lakeflow_connect_pipeline_hours_per_month = Column(Numeric(12, 2))
    lakeflow_connect_gateway_cloud = Column(String(50))
    lakeflow_connect_gateway_instance_type = Column(String(100))
    lakeflow_connect_gateway_num_workers = Column(Integer)
    lakeflow_connect_gateway_hours_per_month = Column(Numeric(12, 2))

    # Lakebase Configuration
    lakebase_cu = Column(Numeric(5, 1))
    lakebase_storage_gb = Column(Integer)
    lakebase_ha_nodes = Column(Integer)
    lakebase_backup_retention_days = Column(Integer)

    # Usage Configuration
    runs_per_day = Column(Integer)
    avg_runtime_minutes = Column(Integer)
    days_per_month = Column(Integer, default=22)
    hours_per_month = Column(Integer)

    # Pricing Configuration
    driver_pricing_tier = Column(String(20))  # on-demand, 1yr, 3yr
    worker_pricing_tier = Column(String(20))  # spot, on-demand, 1yr, 3yr
    driver_payment_option = Column(String(20))  # no-upfront, partial-upfront, all-upfront
    worker_payment_option = Column(String(20))  # no-upfront, partial-upfront, all-upfront

    # Additional Configuration
    workload_config = Column(JSON)  # Flexible JSON for additional config
    notes = Column(Text)

    # Calculated results
    cost_calculation_response = Column(JSON)
    calculation_completed_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    estimate = relationship("Estimate", back_populates="line_items")
    workload_type_ref = relationship("RefWorkloadType", back_populates="line_items")
    decision_records = relationship("DecisionRecord", back_populates="line_item", cascade="all, delete-orphan")
