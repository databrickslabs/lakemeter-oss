"""Shared fixtures for Lakehouse Federation export tests."""
from types import SimpleNamespace


def make_federation_item(**kwargs):
    """Create a mock line item with defaults for LAKEHOUSE_FEDERATION workloads."""
    defaults = {
        "workload_type": "LAKEHOUSE_FEDERATION",
        "workload_name": "Test Federation",
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
        "vector_search_storage_gb": 0,
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
        # Federation fields (tier drives these unless explicitly overridden)
        "federation_size": "M",
        "federation_num_users": None,
        "federation_queries_per_period": None,
        "federation_query_period": "day",
        "federation_avg_query_seconds": 10,
        "federation_warehouse_size": None,
        "runs_per_day": None,
        "avg_runtime_minutes": None,
        "days_per_month": None,
        "hours_per_month": None,
        "workload_config": None,
        "driver_pricing_tier": None,
        "worker_pricing_tier": None,
        "driver_payment_option": None,
        "worker_payment_option": None,
        "notes": None,
        "display_order": 0,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)
