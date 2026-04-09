"""Shared fixtures for Sprint 10 (Full Combined Estimate) tests."""
from types import SimpleNamespace


def make_line_item(**kwargs):
    """Create a mock line item with all fields defaulting to None."""
    defaults = {
        "workload_type": "JOBS",
        "workload_name": "Test Workload",
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
        "vector_search_storage_gb": None,
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
        "lakebase_backup_retention_days": None,
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


def make_jobs_serverless():
    """Jobs Serverless Performance — 200 hrs/month."""
    return make_line_item(
        workload_type="JOBS",
        workload_name="Jobs Serverless Perf",
        serverless_enabled=True,
        serverless_mode="performance",
        hours_per_month=200,
        display_order=0,
    )


def make_all_purpose_classic_photon():
    """All-Purpose Classic Photon — 2 workers, 730 hrs/month."""
    return make_line_item(
        workload_type="ALL_PURPOSE",
        workload_name="All-Purpose Classic Photon",
        photon_enabled=True,
        num_workers=2,
        hours_per_month=730,
        display_order=1,
    )


def make_dlt_pro_serverless():
    """DLT Pro Serverless Standard — 100 hrs/month."""
    return make_line_item(
        workload_type="DLT",
        workload_name="DLT Pro Serverless",
        dlt_edition="PRO",
        serverless_enabled=True,
        serverless_mode="standard",
        hours_per_month=100,
        display_order=2,
    )


def make_dbsql_serverless_medium():
    """DBSQL Serverless Medium — 1 cluster, 500 hrs/month."""
    return make_line_item(
        workload_type="DBSQL",
        workload_name="DBSQL Serverless Medium",
        dbsql_warehouse_type="SERVERLESS",
        dbsql_warehouse_size="Medium",
        dbsql_num_clusters=1,
        hours_per_month=500,
        display_order=3,
    )


def make_model_serving_gpu():
    """Model Serving Medium GPU (A10G x1) — 200 hrs/month."""
    return make_line_item(
        workload_type="MODEL_SERVING",
        workload_name="Model Serving GPU",
        model_serving_gpu_type="gpu_medium_a10g_1x",
        hours_per_month=200,
        display_order=4,
    )


def make_fmapi_databricks():
    """FMAPI Databricks — llama input tokens, 100M/month."""
    return make_line_item(
        workload_type="FMAPI_DATABRICKS",
        workload_name="FMAPI DB Llama Input",
        fmapi_model="llama-3-3-70b",
        fmapi_rate_type="input_token",
        fmapi_quantity=100,
        display_order=5,
    )


def make_fmapi_proprietary():
    """FMAPI Proprietary — Anthropic Claude output tokens, 50M/month."""
    return make_line_item(
        workload_type="FMAPI_PROPRIETARY",
        workload_name="FMAPI Anthropic Output",
        fmapi_provider="anthropic",
        fmapi_model="claude-haiku-4-5",
        fmapi_endpoint_type="global",
        fmapi_context_length="all",
        fmapi_rate_type="output_token",
        fmapi_quantity=50,
        display_order=6,
    )


def make_vector_search_standard():
    """Vector Search Standard — 5M vectors, 50GB storage, 730 hrs/month."""
    return make_line_item(
        workload_type="VECTOR_SEARCH",
        workload_name="Vector Search Standard 5M",
        vector_search_mode="standard",
        vector_capacity_millions=5,
        vector_search_storage_gb=50,
        hours_per_month=730,
        display_order=7,
    )


def make_lakebase():
    """Lakebase — 4 CU, 2 HA nodes, 100GB, 730 hrs/month."""
    return make_line_item(
        workload_type="LAKEBASE",
        workload_name="Lakebase 4CU 2HA",
        lakebase_cu=4,
        lakebase_ha_nodes=2,
        lakebase_storage_gb=100,
        hours_per_month=730,
        display_order=8,
    )


def make_all_nine_items():
    """Create the canonical list of all 9 workload types."""
    return [
        make_jobs_serverless(),
        make_all_purpose_classic_photon(),
        make_dlt_pro_serverless(),
        make_dbsql_serverless_medium(),
        make_model_serving_gpu(),
        make_fmapi_databricks(),
        make_fmapi_proprietary(),
        make_vector_search_standard(),
        make_lakebase(),
    ]
