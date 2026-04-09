"""Calculation functions for export (hours, DBU/hr, serverless detection)."""
from .pricing import (
    INSTANCE_DBU_RATES, VECTOR_SEARCH_RATES, MODEL_SERVING_RATES,
    _get_photon_multiplier,
)


def _calculate_hours_per_month(item) -> float:
    """Calculate hours per month from usage config.

    Priority: If run-based fields (runs_per_day, avg_runtime_minutes) are set,
    calculate from those. Only fall back to hours_per_month if no run-based data.
    This prevents hours_per_month=730 default from overriding user's run config.

    Always-on workloads (Vector Search, Model Serving, Lakebase, Databricks Apps)
    default to 730 hours/month when no usage data is provided.
    """
    if item.runs_per_day and item.avg_runtime_minutes:
        runs = float(item.runs_per_day)
        runtime = float(item.avg_runtime_minutes)
        days = float(item.days_per_month or 22)
        return (runs * runtime / 60) * days
    if item.hours_per_month:
        return float(item.hours_per_month)
    # Always-on workloads default to 730 hours/month (24/7)
    wt = (getattr(item, 'workload_type', '') or '').upper()
    if wt in ('VECTOR_SEARCH', 'MODEL_SERVING', 'LAKEBASE', 'DATABRICKS_APPS', 'LAKEFLOW_CONNECT'):
        return 730
    return 0


def _calculate_dbu_per_hour(item, cloud: str = 'aws', tier: str = 'PREMIUM') -> tuple:
    """Calculate DBU per hour for a workload. Returns (dbu_per_hour, warnings)."""
    wt = (item.workload_type or '').upper()
    warnings = []

    if wt in ('JOBS', 'ALL_PURPOSE', 'DLT'):
        return _calc_compute_dbu(item, cloud, wt, warnings)
    elif wt == 'DBSQL':
        return _calc_dbsql_dbu(item, warnings)
    elif wt == 'VECTOR_SEARCH':
        return _calc_vector_search_dbu(item, cloud, warnings)
    elif wt == 'MODEL_SERVING':
        return _calc_model_serving_dbu(item, cloud, warnings)
    elif wt in ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY'):
        return 0, warnings  # FMAPI uses token-based, not hour-based
    elif wt == 'LAKEBASE':
        cu = float(item.lakebase_cu or 0)
        nodes = float(item.lakebase_ha_nodes or 1)
        if cu < 0:
            warnings.append(f"Lakebase CU is negative ({cu})")
        elif cu == 0:
            warnings.append("Lakebase CU not specified")
        # Multiply CU by DBU-per-CU-hour rate (matches API's LAKEBASE_DBU_RATES)
        lakebase_dbu_rates = {
            'aws': {'PREMIUM': 0.230, 'ENTERPRISE': 0.213},
            'azure': {'PREMIUM': 0.213, 'ENTERPRISE': 0.213},
            # GCP: Lakebase not available yet
        }
        cloud_lc = cloud.strip().lower() if cloud else 'aws'
        tier_upper = tier.strip().upper() if tier else 'PREMIUM'
        dbu_per_cu_hour = lakebase_dbu_rates.get(cloud_lc, {}).get(tier_upper, 1.0)
        return cu * dbu_per_cu_hour * nodes, warnings
    elif wt == 'DATABRICKS_APPS':
        size = (getattr(item, 'databricks_apps_size', None) or 'medium').lower()
        rates = {'medium': 0.5, 'large': 1.0}
        return rates.get(size, 0.5), warnings
    elif wt == 'CLEAN_ROOM':
        collaborators = int(getattr(item, 'clean_room_collaborators', None) or 1)
        # 1 DBU per collaborator per day; convert to hourly (day=24h)
        return collaborators / 24.0, warnings
    elif wt == 'AI_PARSE':
        # AI Parse is quantity-based, not hour-based; return 0, handled separately
        return 0, warnings
    elif wt == 'SHUTTERSTOCK_IMAGEAI':
        # Shutterstock is per-image, not hour-based; return 0, handled separately
        return 0, warnings
    elif wt == 'LAKEFLOW_CONNECT':
        # Pipeline: DLT Serverless (handled like DLT)
        return 0, warnings  # simplified; actual calc done at endpoint level
    return 0, warnings


def _calc_compute_dbu(item, cloud, wt, warnings):
    """Calculate DBU/hr for Jobs, All-Purpose, or DLT workloads."""
    driver_dbu = 0.5  # Match frontend fallback (costCalculation.ts:250)
    worker_dbu = 0.5
    driver_found = False
    worker_found = False
    if INSTANCE_DBU_RATES:
        cloud_instances = INSTANCE_DBU_RATES.get(cloud, {})
        if item.driver_node_type and item.driver_node_type in cloud_instances:
            driver_dbu = cloud_instances[item.driver_node_type].get('dbu_rate', 0.25)
            driver_found = True
        if item.worker_node_type and item.worker_node_type in cloud_instances:
            worker_dbu = cloud_instances[item.worker_node_type].get('dbu_rate', 0.5)
            worker_found = True
    if not driver_found and item.driver_node_type:
        warnings.append(f"Driver DBU rate not found for {item.driver_node_type}, using 0.5")
    if not worker_found and item.worker_node_type:
        warnings.append(f"Worker DBU rate not found for {item.worker_node_type}, using 0.5")

    num_workers = int(item.num_workers or 0)
    base_dbu = float(driver_dbu) + (float(worker_dbu) * num_workers)

    # Determine the base SKU for photon multiplier lookup
    edition = (item.dlt_edition or 'CORE').upper() if wt == 'DLT' else ''
    if wt == 'DLT':
        sku_base = f'DLT_{edition}_COMPUTE'
    elif wt == 'ALL_PURPOSE':
        sku_base = 'ALL_PURPOSE_COMPUTE'
    else:
        sku_base = 'JOBS_COMPUTE'

    if item.serverless_enabled:
        photon_mult = _get_photon_multiplier(cloud, sku_base)
        base_dbu *= photon_mult
        mode_multiplier = 2 if (item.serverless_mode or '').lower() == 'performance' else 1
        return base_dbu * mode_multiplier, warnings

    if item.photon_enabled:
        photon_mult = _get_photon_multiplier(cloud, sku_base)
        base_dbu *= photon_mult
    return base_dbu, warnings


def _calc_dbsql_dbu(item, warnings):
    """Calculate DBU/hr for DBSQL workloads."""
    size_dbu = {
        '2X-Small': 4, 'X-Small': 6, 'Small': 12, 'Medium': 24,
        'Large': 40, 'X-Large': 80, '2X-Large': 144, '3X-Large': 272, '4X-Large': 528
    }
    wh_size = item.dbsql_warehouse_size
    if not wh_size or wh_size.strip() == '':
        wh_size = 'Small'
        warnings.append("Empty warehouse size, defaulting to Small")
    if wh_size not in size_dbu:
        warnings.append(f"Unknown DBSQL warehouse size '{wh_size}', using Small (12 DBU)")
        wh_size = 'Small'
    num_clusters = max(1, int(item.dbsql_num_clusters or 1))
    return float(size_dbu[wh_size] * num_clusters), warnings


def _calc_vector_search_dbu(item, cloud, warnings):
    """Calculate DBU/hr for Vector Search workloads.

    Uses CEILING(capacity / divisor) to determine endpoint units, matching
    the frontend's costCalculation.ts.  Defaults capacity to 1M vectors
    when not specified (same as frontend default).
    """
    import math
    capacity = float(item.vector_capacity_millions or 1)  # Default 1, matching frontend
    if capacity <= 0:
        capacity = 1
    mode = (item.vector_search_mode or 'standard').strip().lower()
    cloud_lc = cloud.strip().lower() if cloud else 'aws'
    key = f"{cloud_lc}:{mode}"
    info = VECTOR_SEARCH_RATES.get(key, {})
    if not info:
        warnings.append(f"Vector Search rates not found for {key}, using defaults")
    dbu_rate = info.get('dbu_rate', 4.0 if mode == 'standard' else 18.29)
    divisor = info.get('input_divisor', 2000000)
    vectors_total = capacity * 1_000_000
    units = math.ceil(vectors_total / divisor) if divisor else 0
    return units * dbu_rate, warnings


def _calc_model_serving_dbu(item, cloud, warnings):
    """Calculate DBU/hr for Model Serving workloads.

    DBU/hr = gpu_dbu_rate × concurrency.
    Concurrency source priority: dedicated column > workload_config JSON > default 4.
    """
    gpu_type = (item.model_serving_gpu_type or 'cpu').lower()
    key = f"{cloud}:{gpu_type}"
    info = MODEL_SERVING_RATES.get(key, {})
    if not info:
        warnings.append(f"Model Serving rate not found for {key}")
        return 0, warnings
    base_rate = info.get('dbu_rate', 0)
    # Prefer dedicated column, fall back to workload_config JSON, then default 4
    concurrency = getattr(item, 'model_serving_concurrency', None)
    if not concurrency:
        config = getattr(item, 'workload_config', None) or {}
        concurrency = int(config.get('model_serving_concurrency', 4))
    else:
        concurrency = int(concurrency)
    return base_rate * concurrency, warnings


def _is_serverless_workload(item) -> bool:
    """Check if workload is serverless (no VM costs)."""
    wt = (item.workload_type or '').upper()
    if wt in ('VECTOR_SEARCH', 'MODEL_SERVING', 'FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY',
              'LAKEBASE', 'DATABRICKS_APPS', 'CLEAN_ROOM', 'AI_PARSE', 'SHUTTERSTOCK_IMAGEAI',
              'LAKEFLOW_CONNECT'):
        return True
    if wt in ('JOBS', 'ALL_PURPOSE', 'DLT') and item.serverless_enabled:
        return True
    if wt == 'DBSQL' and (item.dbsql_warehouse_type or '').upper() == 'SERVERLESS':
        return True
    return False


