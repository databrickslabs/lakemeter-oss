"""Shared fixtures for Genie / Genie Code and Lakehouse Federation export tests."""
from types import SimpleNamespace


def make_genie_item(**kwargs):
    """Create a mock line item with defaults for GENIE / GENIE_CODE workloads."""
    defaults = {
        "workload_type": "GENIE",
        "workload_name": "Test Genie",
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
        # Genie fields (t-shirt sizing; explicit values override the tier)
        "genie_product": "genie",
        "genie_size": "custom",
        "genie_num_users": 10,
        "genie_dbus_per_user_per_month": 200,
        "genie_num_service_principals": 0,
        "genie_dbus_per_sp_per_month": 0,
        "genie_warehouse_size": "2X-Small",
        "genie_active_hours_per_month": 176,
        "genie_reuse_existing_warehouse": False,
        "genie_apply_promo": True,
        "genie_promo_pct": 25,
        # Federation fields
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


def make_federation_item(**kwargs):
    """Create a mock line item with defaults for LAKEHOUSE_FEDERATION workloads."""
    item = make_genie_item()
    item.workload_type = "LAKEHOUSE_FEDERATION"
    item.workload_name = "Test Federation"
    item.genie_product = None
    item.genie_size = None
    item.genie_num_users = None
    item.genie_dbus_per_user_per_month = None
    item.genie_apply_promo = None
    item.genie_promo_pct = None
    item.federation_size = "M"
    item.federation_warehouse_size = None  # let the tier drive it
    item.hours_per_month = None
    for k, v in kwargs.items():
        setattr(item, k, v)
    return item
