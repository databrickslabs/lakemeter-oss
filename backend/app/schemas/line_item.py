"""Line Item schemas."""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
import math
from typing import Optional, Dict, Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


AI_FUNCTION_CONFIG_FIELDS = (
    "ai_extract_document_type",
    "ai_extract_num_inputs",
    "ai_extract_dbus_per_thousand",
    "ai_classify_document_type",
    "ai_classify_num_docs",
    "ai_classify_dbus_per_thousand",
)

AI_GATEWAY_CONFIG_FIELDS = (
    "ai_gateway_inference_tables_enabled",
    "ai_gateway_inference_tables_input_method",
    "ai_gateway_inference_tables_requests_millions",
    "ai_gateway_inference_tables_avg_request_payload_kb",
    "ai_gateway_inference_tables_avg_response_payload_kb",
    "ai_gateway_inference_tables_monthly_payload_gb",
    "ai_gateway_usage_tracking_enabled",
    "ai_gateway_usage_tracking_input_method",
    "ai_gateway_usage_tracking_requests_millions",
    "ai_gateway_usage_tracking_avg_request_payload_kb",
    "ai_gateway_usage_tracking_avg_response_payload_kb",
    "ai_gateway_usage_tracking_monthly_payload_gb",
)

AGENT_EVALUATION_CONFIG_FIELDS = (
    "agent_evaluation_labels_enabled",
    "agent_evaluation_input_tokens_millions",
    "agent_evaluation_output_tokens_millions",
    "agent_evaluation_synthetic_data_enabled",
    "agent_evaluation_synthetic_questions",
)

AI_SEARCH_CONFIG_FIELDS = (
    "ai_search_reranker_enabled",
    "ai_search_reranker_requests_thousands",
)

AI_RUNTIME_CONFIG_FIELDS = (
    "ai_runtime_accelerator_type",
)

JSON_BACKED_CONFIG_FIELDS = (
    *AI_FUNCTION_CONFIG_FIELDS,
    *AI_GATEWAY_CONFIG_FIELDS,
    *AGENT_EVALUATION_CONFIG_FIELDS,
    *AI_SEARCH_CONFIG_FIELDS,
    *AI_RUNTIME_CONFIG_FIELDS,
)


def map_ai_parse_api_fields(
    data: dict,
    provided_fields: set[str],
    existing_workload_config: Optional[Dict[str, Any]] = None,
) -> dict:
    """Map public API fields onto existing storage columns and workload_config."""
    if "ai_parse_mode" in provided_fields:
        mode = data.get("ai_parse_mode")
        if isinstance(mode, str):
            mode = mode.lower()
            if mode in {"dbu", "pages"}:
                mode = f"{mode}_based"
        data["ai_parse_calculation_method"] = mode
    data.pop("ai_parse_mode", None)

    if "ai_parse_pages_thousands" in provided_fields:
        pages_thousands = data.get("ai_parse_pages_thousands")
        data["ai_parse_num_pages"] = (
            pages_thousands * 1000 if pages_thousands is not None else None
        )
    data.pop("ai_parse_pages_thousands", None)

    if "shutterstock_images" in provided_fields:
        data["shutterstock_imageai_num_images"] = data.get(
            "shutterstock_images"
        )
    data.pop("shutterstock_images", None)

    ai_fields_provided = any(
        field in provided_fields for field in JSON_BACKED_CONFIG_FIELDS
    )
    if ai_fields_provided:
        config = deepcopy(existing_workload_config or {})
        if "workload_config" in provided_fields:
            config = deepcopy(data.get("workload_config") or {})
        for field in JSON_BACKED_CONFIG_FIELDS:
            if field not in provided_fields:
                continue
            value = data.get(field)
            if value is None:
                config.pop(field, None)
            else:
                config[field] = value
        data["workload_config"] = config or None

    if "workload_type" in provided_fields:
        workload_type = (data.get("workload_type") or "").upper()
        config_source = (
            data.get("workload_config")
            if "workload_config" in data
            else existing_workload_config
        )
        config = deepcopy(config_source or {})
        fields_to_remove = []
        if workload_type != "AI_EXTRACT":
            fields_to_remove.extend(AI_FUNCTION_CONFIG_FIELDS[:3])
        if workload_type != "AI_CLASSIFY":
            fields_to_remove.extend(AI_FUNCTION_CONFIG_FIELDS[3:])
        if workload_type != "AI_GATEWAY":
            fields_to_remove.extend(AI_GATEWAY_CONFIG_FIELDS)
        if workload_type != "AGENT_EVALUATION":
            fields_to_remove.extend(AGENT_EVALUATION_CONFIG_FIELDS)
        if workload_type != "VECTOR_SEARCH":
            fields_to_remove.extend(AI_SEARCH_CONFIG_FIELDS)
        if workload_type != "AI_RUNTIME":
            fields_to_remove.extend(AI_RUNTIME_CONFIG_FIELDS)
        original_config = dict(config)
        for field in fields_to_remove:
            config.pop(field, None)
        if config != original_config:
            data["workload_config"] = config or None

    for field in JSON_BACKED_CONFIG_FIELDS:
        data.pop(field, None)

    return data


def validate_ai_function_workload_config(
    workload_type: Optional[str],
    workload_config: Optional[Dict[str, Any]],
) -> None:
    """Validate the JSON-backed configuration for AI Functions workloads."""
    workload_type = (workload_type or "").upper()
    config = workload_config or {}
    if workload_type == "AI_EXTRACT":
        prefix = "ai_extract"
        allowed_types = {
            "short_text",
            "invoice",
            "complex_reasoning",
            "deep_nesting",
            "custom",
        }
        quantity_field = "ai_extract_num_inputs"
    elif workload_type == "AI_CLASSIFY":
        prefix = "ai_classify"
        allowed_types = {"short_text", "rental_contract", "custom"}
        quantity_field = "ai_classify_num_docs"
    else:
        return

    document_type_field = f"{prefix}_document_type"
    custom_rate_field = f"{prefix}_dbus_per_thousand"
    document_type = config.get(document_type_field)
    if document_type is not None and document_type not in allowed_types:
        raise ValueError(
            f"{document_type_field} must be one of: "
            f"{', '.join(sorted(allowed_types))}"
        )

    quantity = config.get(quantity_field)
    if quantity is not None:
        try:
            quantity_value = float(quantity)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{quantity_field} must be a number") from exc
        if quantity_value < 0:
            raise ValueError(f"{quantity_field} must be greater than or equal to 0")

    custom_rate = config.get(custom_rate_field)
    if custom_rate is not None:
        try:
            custom_rate_value = float(custom_rate)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{custom_rate_field} must be a number") from exc
        if custom_rate_value <= 0:
            raise ValueError(f"{custom_rate_field} must be greater than 0")
    if document_type == "custom" and custom_rate is None:
        raise ValueError(
            f"{custom_rate_field} is required when {document_type_field} is custom"
        )


def validate_ai_gateway_workload_config(
    workload_type: Optional[str],
    workload_config: Optional[Dict[str, Any]],
) -> None:
    """Validate JSON-backed AI Gateway configuration."""
    if (workload_type or "").upper() != "AI_GATEWAY":
        return

    config = workload_config or {}
    components = ("inference_tables", "usage_tracking")
    numeric_suffixes = (
        "requests_millions",
        "avg_request_payload_kb",
        "avg_response_payload_kb",
        "monthly_payload_gb",
    )
    numeric_fields = tuple(
        f"ai_gateway_{component}_{suffix}"
        for component in components
        for suffix in numeric_suffixes
    )
    for field in numeric_fields:
        value = config.get(field)
        if value is None:
            continue
        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} must be a number") from exc
        if not math.isfinite(numeric_value):
            raise ValueError(f"{field} must be finite")
        if numeric_value < 0:
            raise ValueError(f"{field} must be greater than or equal to 0")

    feature_fields = (
        "ai_gateway_inference_tables_enabled",
        "ai_gateway_usage_tracking_enabled",
    )
    for field in feature_fields:
        value = config.get(field)
        if value is not None and not isinstance(value, bool):
            raise ValueError(f"{field} must be a boolean")
    if not any(config.get(field) is True for field in feature_fields):
        raise ValueError(
            "At least one paid AI Gateway feature must be enabled: "
            "inference tables or usage tracking"
        )

    for component in components:
        enabled_field = f"ai_gateway_{component}_enabled"
        if config.get(enabled_field) is not True:
            continue
        input_method_field = f"ai_gateway_{component}_input_method"
        input_method = config.get(input_method_field)
        if input_method not in {"requests", "payload_gb"}:
            raise ValueError(
                f"{input_method_field} must be requests or payload_gb"
            )
        required_suffixes = (
            numeric_suffixes[:3]
            if input_method == "requests"
            else ("monthly_payload_gb",)
        )
        missing_fields = [
            f"ai_gateway_{component}_{suffix}"
            for suffix in required_suffixes
            if config.get(f"ai_gateway_{component}_{suffix}") is None
        ]
        if missing_fields:
            raise ValueError(
                f"{', '.join(missing_fields)} required for enabled "
                f"{component}"
            )


def validate_agent_evaluation_workload_config(
    workload_type: Optional[str],
    workload_config: Optional[Dict[str, Any]],
) -> None:
    """Validate JSON-backed Agent Evaluation configuration."""
    if (workload_type or "").upper() != "AGENT_EVALUATION":
        return

    config = workload_config or {}
    labels_enabled = config.get("agent_evaluation_labels_enabled")
    synthetic_enabled = config.get(
        "agent_evaluation_synthetic_data_enabled"
    )
    for field, value in (
        ("agent_evaluation_labels_enabled", labels_enabled),
        ("agent_evaluation_synthetic_data_enabled", synthetic_enabled),
    ):
        if not isinstance(value, bool):
            raise ValueError(f"{field} must be a boolean")
    if not (labels_enabled or synthetic_enabled):
        raise ValueError(
            "At least one Agent Evaluation feature must be enabled: "
            "labels or synthetic data"
        )

    numeric_fields = (
        "agent_evaluation_input_tokens_millions",
        "agent_evaluation_output_tokens_millions",
        "agent_evaluation_synthetic_questions",
    )
    for field in numeric_fields:
        value = config.get(field)
        if value is None:
            continue
        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} must be a number") from exc
        if not math.isfinite(numeric_value):
            raise ValueError(f"{field} must be finite")
        if numeric_value < 0:
            raise ValueError(f"{field} must be greater than or equal to 0")

    if labels_enabled:
        missing = [
            field
            for field in numeric_fields[:2]
            if config.get(field) is None
        ]
        if missing:
            raise ValueError(
                f"{', '.join(missing)} required when labels are enabled"
            )
    questions = config.get("agent_evaluation_synthetic_questions")
    if synthetic_enabled and questions is None:
        raise ValueError(
            "agent_evaluation_synthetic_questions is required when "
            "synthetic data is enabled"
        )
    if questions is not None and (
        isinstance(questions, bool)
        or not float(questions).is_integer()
    ):
        raise ValueError(
            "agent_evaluation_synthetic_questions must be an integer"
        )


def validate_ai_search_workload_config(
    workload_type: Optional[str],
    workload_config: Optional[Dict[str, Any]],
) -> None:
    """Validate JSON-backed AI Search reranker configuration."""
    if (workload_type or "").upper() != "VECTOR_SEARCH":
        return

    config = workload_config or {}
    enabled = config.get("ai_search_reranker_enabled")
    if enabled is not None and not isinstance(enabled, bool):
        raise ValueError("ai_search_reranker_enabled must be a boolean")

    requests = config.get("ai_search_reranker_requests_thousands")
    if requests is None:
        if enabled:
            raise ValueError(
                "ai_search_reranker_requests_thousands is required when "
                "AI Search Reranker is enabled"
            )
        return
    try:
        requests_value = float(requests)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "ai_search_reranker_requests_thousands must be a number"
        ) from exc
    if not math.isfinite(requests_value):
        raise ValueError(
            "ai_search_reranker_requests_thousands must be finite"
        )
    if requests_value < 0:
        raise ValueError(
            "ai_search_reranker_requests_thousands must be greater than "
            "or equal to 0"
        )


def validate_ai_runtime_workload_config(
    workload_type: Optional[str],
    workload_config: Optional[Dict[str, Any]],
) -> None:
    """Validate the JSON-backed AI Runtime accelerator."""
    if (workload_type or "").upper() != "AI_RUNTIME":
        return
    accelerator = (workload_config or {}).get(
        "ai_runtime_accelerator_type"
    )
    allowed = {
        "GPU_1xA10",
        "GPU_1xH100",
        "GPU_8xH100",
    }
    if accelerator not in allowed:
        raise ValueError(
            "ai_runtime_accelerator_type must be one of: "
            f"{', '.join(sorted(allowed))}"
        )


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

    # AI Search Configuration (internal workload type remains VECTOR_SEARCH)
    vector_search_mode: Optional[str] = None
    vector_capacity_millions: Optional[int] = None
    vector_search_storage_gb: Optional[int] = None
    ai_search_reranker_enabled: Optional[bool] = None
    ai_search_reranker_requests_thousands: Optional[float] = Field(
        default=None, ge=0, allow_inf_nan=False
    )

    # Model Serving Configuration
    model_serving_gpu_type: Optional[str] = None
    model_serving_concurrency: Optional[int] = None
    model_serving_scale_out: Optional[str] = None
    model_servings_number_endpoints: Optional[int] = None

    # AI Runtime Configuration (stored in workload_config)
    ai_runtime_accelerator_type: Optional[
        Literal["GPU_1xA10", "GPU_1xH100", "GPU_8xH100"]
    ] = None

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

    # AI Parse Configuration
    ai_parse_calculation_method: Optional[str] = None
    ai_parse_complexity: Optional[str] = None
    ai_parse_dbu_quantity: Optional[float] = None
    ai_parse_num_pages: Optional[float] = None
    ai_parse_mode: Optional[str] = None
    ai_parse_pages_thousands: Optional[float] = None

    # Shutterstock ImageAI Configuration
    shutterstock_imageai_num_images: Optional[int] = None
    shutterstock_images: Optional[int] = None

    # AI Extract Configuration
    ai_extract_document_type: Optional[
        Literal[
            "short_text",
            "invoice",
            "complex_reasoning",
            "deep_nesting",
            "custom",
        ]
    ] = None
    ai_extract_num_inputs: Optional[float] = Field(default=None, ge=0)
    ai_extract_dbus_per_thousand: Optional[float] = Field(
        default=None,
        gt=0,
    )

    # AI Classify Configuration
    ai_classify_document_type: Optional[
        Literal["short_text", "rental_contract", "custom"]
    ] = None
    ai_classify_num_docs: Optional[float] = Field(default=None, ge=0)
    ai_classify_dbus_per_thousand: Optional[float] = Field(
        default=None,
        gt=0,
    )

    # AI Gateway Configuration (stored in workload_config)
    ai_gateway_inference_tables_enabled: Optional[bool] = None
    ai_gateway_inference_tables_input_method: Optional[
        Literal["requests", "payload_gb"]
    ] = None
    ai_gateway_inference_tables_requests_millions: Optional[float] = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    ai_gateway_inference_tables_avg_request_payload_kb: Optional[
        float
    ] = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    ai_gateway_inference_tables_avg_response_payload_kb: Optional[
        float
    ] = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    ai_gateway_inference_tables_monthly_payload_gb: Optional[float] = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    ai_gateway_usage_tracking_enabled: Optional[bool] = None
    ai_gateway_usage_tracking_input_method: Optional[
        Literal["requests", "payload_gb"]
    ] = None
    ai_gateway_usage_tracking_requests_millions: Optional[float] = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    ai_gateway_usage_tracking_avg_request_payload_kb: Optional[
        float
    ] = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    ai_gateway_usage_tracking_avg_response_payload_kb: Optional[
        float
    ] = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    ai_gateway_usage_tracking_monthly_payload_gb: Optional[float] = Field(
        default=None, ge=0, allow_inf_nan=False
    )

    # Agent Evaluation Configuration (stored in workload_config)
    agent_evaluation_labels_enabled: Optional[bool] = None
    agent_evaluation_input_tokens_millions: Optional[float] = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    agent_evaluation_output_tokens_millions: Optional[float] = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    agent_evaluation_synthetic_data_enabled: Optional[bool] = None
    agent_evaluation_synthetic_questions: Optional[int] = Field(
        default=None, ge=0
    )

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

    # AI Search Configuration (internal workload type remains VECTOR_SEARCH)
    vector_search_mode: Optional[str] = None
    vector_capacity_millions: Optional[int] = None
    vector_search_storage_gb: Optional[int] = None
    ai_search_reranker_enabled: Optional[bool] = None
    ai_search_reranker_requests_thousands: Optional[float] = Field(
        default=None, ge=0, allow_inf_nan=False
    )

    # Model Serving Configuration
    model_serving_gpu_type: Optional[str] = None
    model_serving_concurrency: Optional[int] = None
    model_serving_scale_out: Optional[str] = None
    model_servings_number_endpoints: Optional[int] = None

    # AI Runtime Configuration (stored in workload_config)
    ai_runtime_accelerator_type: Optional[
        Literal["GPU_1xA10", "GPU_1xH100", "GPU_8xH100"]
    ] = None

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

    # AI Parse Configuration
    ai_parse_calculation_method: Optional[str] = None
    ai_parse_complexity: Optional[str] = None
    ai_parse_dbu_quantity: Optional[float] = None
    ai_parse_num_pages: Optional[float] = None
    ai_parse_mode: Optional[str] = None
    ai_parse_pages_thousands: Optional[float] = None

    # Shutterstock ImageAI Configuration
    shutterstock_imageai_num_images: Optional[int] = None
    shutterstock_images: Optional[int] = None

    # AI Extract Configuration (stored in workload_config)
    ai_extract_document_type: Optional[
        Literal[
            "short_text",
            "invoice",
            "complex_reasoning",
            "deep_nesting",
            "custom",
        ]
    ] = None
    ai_extract_num_inputs: Optional[float] = Field(default=None, ge=0)
    ai_extract_dbus_per_thousand: Optional[float] = Field(
        default=None,
        gt=0,
    )

    # AI Classify Configuration (stored in workload_config)
    ai_classify_document_type: Optional[
        Literal["short_text", "rental_contract", "custom"]
    ] = None
    ai_classify_num_docs: Optional[float] = Field(default=None, ge=0)
    ai_classify_dbus_per_thousand: Optional[float] = Field(
        default=None,
        gt=0,
    )

    # AI Gateway Configuration (stored in workload_config)
    ai_gateway_inference_tables_enabled: Optional[bool] = None
    ai_gateway_inference_tables_input_method: Optional[
        Literal["requests", "payload_gb"]
    ] = None
    ai_gateway_inference_tables_requests_millions: Optional[float] = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    ai_gateway_inference_tables_avg_request_payload_kb: Optional[
        float
    ] = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    ai_gateway_inference_tables_avg_response_payload_kb: Optional[
        float
    ] = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    ai_gateway_inference_tables_monthly_payload_gb: Optional[float] = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    ai_gateway_usage_tracking_enabled: Optional[bool] = None
    ai_gateway_usage_tracking_input_method: Optional[
        Literal["requests", "payload_gb"]
    ] = None
    ai_gateway_usage_tracking_requests_millions: Optional[float] = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    ai_gateway_usage_tracking_avg_request_payload_kb: Optional[
        float
    ] = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    ai_gateway_usage_tracking_avg_response_payload_kb: Optional[
        float
    ] = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    ai_gateway_usage_tracking_monthly_payload_gb: Optional[float] = Field(
        default=None, ge=0, allow_inf_nan=False
    )

    # Agent Evaluation Configuration (stored in workload_config)
    agent_evaluation_labels_enabled: Optional[bool] = None
    agent_evaluation_input_tokens_millions: Optional[float] = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    agent_evaluation_output_tokens_millions: Optional[float] = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    agent_evaluation_synthetic_data_enabled: Optional[bool] = None
    agent_evaluation_synthetic_questions: Optional[int] = Field(
        default=None, ge=0
    )

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

    @model_validator(mode="before")
    @classmethod
    def populate_frontend_api_fields(cls, value):
        """Expose frontend fields from their legacy storage columns."""
        if isinstance(value, dict):
            data = dict(value)
        else:
            data = {
                field_name: getattr(value, field_name, None)
                for field_name in cls.model_fields
            }

        if data.get("ai_parse_mode") is None:
            storage_mode = data.get("ai_parse_calculation_method")
            if isinstance(storage_mode, str):
                data["ai_parse_mode"] = storage_mode.lower().removesuffix("_based")

        if data.get("ai_parse_pages_thousands") is None:
            num_pages = data.get("ai_parse_num_pages")
            if num_pages is not None:
                data["ai_parse_pages_thousands"] = float(num_pages) / 1000

        if data.get("shutterstock_images") is None:
            data["shutterstock_images"] = data.get(
                "shutterstock_imageai_num_images"
            )

        workload_config = data.get("workload_config") or {}
        for field in JSON_BACKED_CONFIG_FIELDS:
            if data.get(field) is None:
                data[field] = workload_config.get(field)

        return data

    model_config = ConfigDict(from_attributes=True)
