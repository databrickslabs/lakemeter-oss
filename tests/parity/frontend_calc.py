"""Python reimplementation of frontend costCalculation.ts formulas.

Each function mirrors the exact logic from the TypeScript frontend so we can
compare backend calculations against frontend expectations.
"""
import math


def fe_hours_per_month(*, runs_per_day=None, avg_runtime_minutes=None,
                       days_per_month=None, hours_per_month=None):
    """Frontend hours-per-month calculation (matches costCalculation.ts)."""
    if runs_per_day and avg_runtime_minutes:
        days = days_per_month or 22
        return (float(runs_per_day) * float(avg_runtime_minutes) / 60) * float(days)
    if hours_per_month:
        return float(hours_per_month)
    return 0


def fe_compute_dbu_per_hour(*, driver_dbu_rate, worker_dbu_rate, num_workers,
                            photon_enabled=False, serverless_enabled=False,
                            serverless_mode='standard', workload_type='JOBS',
                            photon_multiplier=2.0):
    """Frontend DBU/hr for JOBS, ALL_PURPOSE, DLT (matches costCalculation.ts)."""
    base_dbu = driver_dbu_rate + (worker_dbu_rate * num_workers)

    if serverless_enabled:
        base_dbu *= photon_multiplier  # photon always on in serverless
        if workload_type == 'ALL_PURPOSE':
            mode_mult = 2  # always performance
        else:
            mode_mult = 2 if serverless_mode == 'performance' else 1
        return base_dbu * mode_mult

    if photon_enabled:
        base_dbu *= photon_multiplier
    return base_dbu


def fe_dbsql_dbu_per_hour(*, warehouse_size='Small', num_clusters=1):
    """Frontend DBSQL DBU/hr (matches costCalculation.ts DBSQL_DBU_RATES)."""
    size_map = {
        '2X-Small': 4, 'X-Small': 6, 'Small': 12, 'Medium': 24,
        'Large': 40, 'X-Large': 80, '2X-Large': 144,
        '3X-Large': 272, '4X-Large': 528,
    }
    dbu = size_map.get(warehouse_size, 12)
    return float(dbu * max(1, num_clusters))


def fe_vector_search_dbu_per_hour(*, capacity_millions=1, mode='standard',
                                  dbu_rate=None, input_divisor=None):
    """Frontend AI Search DBU/hr (matches costCalculation.ts ceiling calc)."""
    if dbu_rate is None:
        dbu_rate = 4.0 if mode == 'standard' else 18.29
    if input_divisor is None:
        input_divisor = 2_000_000 if mode == 'standard' else 64_000_000
    vectors_total = capacity_millions * 1_000_000
    units = math.ceil(vectors_total / input_divisor) if input_divisor else 0
    return units * dbu_rate


def fe_vector_search_storage_cost(
    *,
    storage_gb,
    units_used,
    mode="standard",
    price_per_dsu=0.023,
):
    """Frontend AI Search storage cost (matches costCalculation.ts).

    The first 30 GB is free when an endpoint unit is provisioned.
    Billable = max(0, total - free)
    Cost = billable × mode-specific DSU/GB × regional $/DSU
    """
    free_gb = 30 if units_used > 0 else 0
    billable_gb = max(0, storage_gb - free_gb)
    dsu_per_gb = 2 if mode == "storage_optimized" else 10
    return billable_gb * dsu_per_gb * price_per_dsu


def fe_model_serving_dbu_per_hour(
    *,
    gpu_dbu_rate,
    workload_type="gpu",
    concurrency=4,
):
    """Frontend Model Serving DBU/hr from CPU concurrency or GPU replicas."""
    capacity = (
        concurrency
        if workload_type.lower().startswith("cpu")
        else concurrency / 4
    )
    return gpu_dbu_rate * capacity


def fe_fmapi_token_cost(*, quantity_millions, dbu_per_million, dbu_price):
    """Frontend FMAPI token-based cost (matches costCalculation.ts)."""
    total_dbus = quantity_millions * dbu_per_million
    return total_dbus * dbu_price


def fe_fmapi_provisioned_cost(*, hours, dbu_per_hour, dbu_price):
    """Frontend FMAPI provisioned cost (matches costCalculation.ts)."""
    total_dbus = dbu_per_hour * hours
    return total_dbus * dbu_price


def fe_lakebase_dbu_per_hour(*, cu, ha_nodes=1):
    """Frontend Lakebase equivalent DBU/hr (discounted always-on floor)."""
    return float(cu) * float(ha_nodes) * 0.230 * 0.75


def fe_lakebase_storage_cost(*, storage_gb, price_per_dsu=0.023):
    """Frontend Lakebase storage: GB * 15 DSU/GB * regional $/DSU."""
    dsu_per_gb = 15
    return float(storage_gb) * dsu_per_gb * price_per_dsu


def fe_general_storage_cost(
    *,
    quantity,
    unit,
    cloud="aws",
    tier1_operations_thousands=0,
    tier2_operations_thousands=0,
    price_per_dsu,
):
    """Frontend Default Storage DSUs × exact regional rate."""
    billable_gb = float(quantity) * 1024 if unit.lower() == "tb" else float(quantity)
    operation_rates = {
        "aws": (0.2174, 0.0174),
        "azure": (0.3535, 0.0226),
        "gcp": (0.2174, 0.0174),
    }
    tier1_rate, tier2_rate = operation_rates[cloud.lower()]
    total_dsu = (
        billable_gb
        + float(tier1_operations_thousands) * tier1_rate
        + float(tier2_operations_thousands) * tier2_rate
    )
    return total_dsu * float(price_per_dsu)


def fe_zerobus_cost(*, monthly_ingested_gb, mode, dbu_price):
    """Frontend Zerobus monthly DBUs times the regional serverless rate."""
    dbu_per_gb = 0.222 if mode == "otel" else 0.143
    return float(monthly_ingested_gb) * dbu_per_gb * float(dbu_price)


def fe_monthly_dbu_cost(*, dbu_per_hour, hours_per_month, dbu_price):
    """Frontend standard monthly DBU cost."""
    monthly_dbus = dbu_per_hour * hours_per_month
    return monthly_dbus * dbu_price


def fe_total_monthly_cost(*, dbu_cost, storage_cost=0, vm_cost=0):
    """Frontend total monthly cost."""
    return dbu_cost + storage_cost + vm_cost
