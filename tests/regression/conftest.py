"""Shared fixtures for Sprint 5 regression tests — multi-config items."""
from types import SimpleNamespace


def make_item(**kwargs):
    """Create a mock line item with all fields defaulting to None."""
    defaults = {
        "workload_type": "JOBS", "workload_name": "Test",
        "serverless_enabled": False, "serverless_mode": None,
        "photon_enabled": False,
        "driver_node_type": None, "worker_node_type": None,
        "num_workers": None, "dlt_edition": None,
        "dbsql_warehouse_type": None, "dbsql_warehouse_size": None,
        "dbsql_num_clusters": None,
        "vector_search_mode": None, "vector_capacity_millions": None,
        "vector_search_storage_gb": None, "model_serving_gpu_type": None,
        "fmapi_provider": None, "fmapi_model": None,
        "fmapi_endpoint_type": None, "fmapi_context_length": None,
        "fmapi_rate_type": None, "fmapi_quantity": None,
        "lakebase_cu": None, "lakebase_ha_nodes": None,
        "lakebase_storage_gb": None, "lakebase_backup_retention_days": None,
        "runs_per_day": None, "avg_runtime_minutes": None,
        "days_per_month": None, "hours_per_month": None,
        "driver_pricing_tier": None, "worker_pricing_tier": None,
        "driver_payment_option": None, "worker_payment_option": None,
        "notes": None, "display_order": 0,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---- JOBS configs ----
def make_jobs_classic():
    return make_item(workload_type="JOBS", workload_name="Jobs Classic",
                     hours_per_month=160)


def make_jobs_photon():
    return make_item(workload_type="JOBS", workload_name="Jobs Photon",
                     photon_enabled=True, num_workers=2, hours_per_month=160)


def make_jobs_serverless_std():
    return make_item(workload_type="JOBS", workload_name="Jobs SL Std",
                     serverless_enabled=True, serverless_mode="standard",
                     hours_per_month=200)


def make_jobs_serverless_perf():
    return make_item(workload_type="JOBS", workload_name="Jobs SL Perf",
                     serverless_enabled=True, serverless_mode="performance",
                     hours_per_month=200)


# ---- ALL_PURPOSE configs ----
def make_ap_classic():
    return make_item(workload_type="ALL_PURPOSE", workload_name="AP Classic",
                     num_workers=1, hours_per_month=730)


def make_ap_photon():
    return make_item(workload_type="ALL_PURPOSE", workload_name="AP Photon",
                     photon_enabled=True, num_workers=2, hours_per_month=730)


def make_ap_serverless():
    return make_item(workload_type="ALL_PURPOSE", workload_name="AP Serverless",
                     serverless_enabled=True, hours_per_month=500)


# ---- DLT configs ----
def make_dlt_core_classic():
    return make_item(workload_type="DLT", workload_name="DLT Core Classic",
                     dlt_edition="CORE", hours_per_month=100)


def make_dlt_pro_serverless():
    return make_item(workload_type="DLT", workload_name="DLT Pro SL",
                     dlt_edition="PRO", serverless_enabled=True,
                     serverless_mode="standard", hours_per_month=100)


def make_dlt_advanced_photon():
    return make_item(workload_type="DLT", workload_name="DLT Adv Photon",
                     dlt_edition="ADVANCED", photon_enabled=True,
                     num_workers=4, hours_per_month=100)


# ---- DBSQL configs ----
def make_dbsql_classic_small():
    return make_item(workload_type="DBSQL", workload_name="DBSQL Classic Sm",
                     dbsql_warehouse_type="CLASSIC",
                     dbsql_warehouse_size="Small", hours_per_month=500)


def make_dbsql_pro_medium():
    return make_item(workload_type="DBSQL", workload_name="DBSQL Pro Med",
                     dbsql_warehouse_type="PRO",
                     dbsql_warehouse_size="Medium", hours_per_month=500)


def make_dbsql_serverless_large():
    return make_item(workload_type="DBSQL", workload_name="DBSQL SL Large",
                     dbsql_warehouse_type="SERVERLESS",
                     dbsql_warehouse_size="Large", hours_per_month=500)


# ---- MODEL_SERVING configs ----
def make_ms_cpu():
    return make_item(workload_type="MODEL_SERVING", workload_name="MS CPU",
                     model_serving_gpu_type="cpu", hours_per_month=730)


def make_ms_gpu_a10g():
    return make_item(workload_type="MODEL_SERVING", workload_name="MS A10G",
                     model_serving_gpu_type="gpu_medium_a10g_1x",
                     hours_per_month=200)


# ---- FMAPI_DATABRICKS configs ----
def make_fmapi_db_input():
    return make_item(workload_type="FMAPI_DATABRICKS",
                     workload_name="FMAPI DB Input",
                     fmapi_model="llama-3-3-70b",
                     fmapi_rate_type="input_token", fmapi_quantity=100)


def make_fmapi_db_output():
    return make_item(workload_type="FMAPI_DATABRICKS",
                     workload_name="FMAPI DB Output",
                     fmapi_model="llama-3-3-70b",
                     fmapi_rate_type="output_token", fmapi_quantity=50)


def make_fmapi_db_batch():
    return make_item(workload_type="FMAPI_DATABRICKS",
                     workload_name="FMAPI DB Batch",
                     fmapi_model="llama-3-3-70b",
                     fmapi_rate_type="batch_inference", fmapi_quantity=200)


def make_fmapi_db_provisioned():
    return make_item(workload_type="FMAPI_DATABRICKS",
                     workload_name="FMAPI DB Prov",
                     fmapi_model="llama-3-3-70b",
                     fmapi_rate_type="provisioned_scaling",
                     fmapi_quantity=100)


# ---- FMAPI_PROPRIETARY configs ----
def make_fmapi_prop_openai_input():
    return make_item(workload_type="FMAPI_PROPRIETARY",
                     workload_name="FMAPI OAI Input",
                     fmapi_provider="openai", fmapi_model="gpt-4o",
                     fmapi_endpoint_type="global", fmapi_context_length="all",
                     fmapi_rate_type="input_token", fmapi_quantity=80)


def make_fmapi_prop_anthropic_output():
    return make_item(workload_type="FMAPI_PROPRIETARY",
                     workload_name="FMAPI Anth Output",
                     fmapi_provider="anthropic",
                     fmapi_model="claude-haiku-4-5",
                     fmapi_endpoint_type="global", fmapi_context_length="all",
                     fmapi_rate_type="output_token", fmapi_quantity=50)


def make_fmapi_prop_google_input():
    return make_item(workload_type="FMAPI_PROPRIETARY",
                     workload_name="FMAPI Google Input",
                     fmapi_provider="google",
                     fmapi_model="gemini-2.0-flash",
                     fmapi_endpoint_type="global", fmapi_context_length="all",
                     fmapi_rate_type="input_token", fmapi_quantity=120)


# ---- VECTOR_SEARCH configs ----
def make_vs_standard():
    return make_item(workload_type="VECTOR_SEARCH",
                     workload_name="VS Standard 5M",
                     vector_search_mode="standard",
                     vector_capacity_millions=5,
                     vector_search_storage_gb=50, hours_per_month=730)


def make_vs_storage_opt():
    return make_item(workload_type="VECTOR_SEARCH",
                     workload_name="VS StorageOpt 10M",
                     vector_search_mode="storage_optimized",
                     vector_capacity_millions=10,
                     vector_search_storage_gb=0, hours_per_month=730)


# ---- LAKEBASE configs ----
def make_lakebase_small():
    return make_item(workload_type="LAKEBASE", workload_name="LB 2CU 1HA",
                     lakebase_cu=2, lakebase_ha_nodes=1,
                     lakebase_storage_gb=50, hours_per_month=730)


def make_lakebase_large():
    return make_item(workload_type="LAKEBASE", workload_name="LB 8CU 3HA",
                     lakebase_cu=8, lakebase_ha_nodes=3,
                     lakebase_storage_gb=500, hours_per_month=730)


def make_all_regression_items():
    """Full list of 24 items covering all 9 workload types with multiple configs."""
    return [
        make_jobs_classic(), make_jobs_photon(),
        make_jobs_serverless_std(), make_jobs_serverless_perf(),
        make_ap_classic(), make_ap_photon(), make_ap_serverless(),
        make_dlt_core_classic(), make_dlt_pro_serverless(),
        make_dlt_advanced_photon(),
        make_dbsql_classic_small(), make_dbsql_pro_medium(),
        make_dbsql_serverless_large(),
        make_ms_cpu(), make_ms_gpu_a10g(),
        make_fmapi_db_input(), make_fmapi_db_output(),
        make_fmapi_db_batch(), make_fmapi_db_provisioned(),
        make_fmapi_prop_openai_input(), make_fmapi_prop_anthropic_output(),
        make_fmapi_prop_google_input(),
        make_vs_standard(), make_vs_storage_opt(),
        make_lakebase_small(), make_lakebase_large(),
    ]
