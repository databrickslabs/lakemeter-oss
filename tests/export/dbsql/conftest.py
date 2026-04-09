"""Shared fixtures for Sprint 4 (DBSQL) tests."""
from types import SimpleNamespace


def make_line_item(**kwargs):
    """Create a mock line item with default values for DBSQL workloads."""
    defaults = {
        "workload_type": "DBSQL",
        "workload_name": "Test DBSQL Warehouse",
        "serverless_enabled": False,
        "serverless_mode": None,
        "photon_enabled": False,
        "driver_node_type": None,
        "worker_node_type": None,
        "num_workers": None,
        "dlt_edition": None,
        "dbsql_warehouse_type": "SERVERLESS",
        "dbsql_warehouse_size": "Small",
        "dbsql_num_clusters": 1,
        "dbsql_vm_pricing_tier": None,
        "dbsql_vm_payment_option": None,
        "dbsql_driver_pricing_tier": None,
        "dbsql_driver_payment_option": None,
        "dbsql_worker_pricing_tier": None,
        "dbsql_worker_payment_option": None,
        "vector_search_mode": None,
        "vector_capacity_millions": None,
        "model_serving_gpu_type": None,
        "fmapi_provider": None,
        "fmapi_model": None,
        "fmapi_endpoint_type": None,
        "fmapi_context_length": None,
        "fmapi_rate_type": None,
        "fmapi_quantity": None,
        "lakebase_cu": None,
        "lakebase_ha_nodes": None,
        "lakebase_storage_gb": None,
        "runs_per_day": None,
        "avg_runtime_minutes": None,
        "days_per_month": None,
        "hours_per_month": 100,
        "driver_pricing_tier": None,
        "worker_pricing_tier": None,
        "driver_payment_option": None,
        "worker_payment_option": None,
        "notes": None,
        "display_order": 0,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)
