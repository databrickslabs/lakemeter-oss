"""Shared fixtures for Sprint 6 (FMAPI Databricks) tests."""
from types import SimpleNamespace


def make_line_item(**kwargs):
    """Create a mock line item with defaults for FMAPI_DATABRICKS workloads."""
    defaults = {
        "workload_type": "FMAPI_DATABRICKS",
        "workload_name": "Test FMAPI Databricks",
        "serverless_enabled": False,
        "serverless_mode": None,
        "photon_enabled": False,
        "driver_node_type": None,
        "worker_node_type": None,
        "num_workers": None,
        "dlt_edition": None,
        "dbsql_warehouse_type": None,
        "dbsql_warehouse_size": None,
        "dbsql_num_clusters": None,
        "vector_search_mode": None,
        "vector_capacity_millions": None,
        "model_serving_gpu_type": None,
        "fmapi_provider": None,
        "fmapi_model": "llama-3-3-70b",
        "fmapi_endpoint_type": None,
        "fmapi_context_length": None,
        "fmapi_rate_type": "input_token",
        "fmapi_quantity": 100,
        "lakebase_cu": None,
        "lakebase_ha_nodes": None,
        "lakebase_storage_gb": None,
        "runs_per_day": None,
        "avg_runtime_minutes": None,
        "days_per_month": None,
        "hours_per_month": None,
        "driver_pricing_tier": None,
        "worker_pricing_tier": None,
        "driver_payment_option": None,
        "worker_payment_option": None,
        "notes": None,
        "display_order": 0,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)
