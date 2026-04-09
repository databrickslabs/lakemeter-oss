"""Shared calculation helpers for DBSQL tests.

Replicates both frontend (costCalculation.ts) and backend (calculations.py)
logic for DBSQL workloads so tests can compare FE vs BE independently.
"""

# Warehouse size → DBU/hr mapping (shared by frontend and backend)
DBSQL_SIZE_DBU = {
    '2X-Small': 4,
    'X-Small': 6,
    'Small': 12,
    'Medium': 24,
    'Large': 40,
    'X-Large': 80,
    '2X-Large': 144,
    '3X-Large': 272,
    '4X-Large': 528,
}

# Fallback $/DBU rates from both frontend and backend
FRONTEND_DBSQL_PRICES = {
    'SQL_COMPUTE': 0.22,
    'SQL_PRO_COMPUTE': 0.55,
    'SERVERLESS_SQL_COMPUTE': 0.70,
}

BACKEND_DBSQL_PRICES = {
    'SQL_COMPUTE': 0.22,
    'SQL_PRO_COMPUTE': 0.55,
    'SERVERLESS_SQL_COMPUTE': 0.70,
}


def frontend_calc_dbsql(
    warehouse_type='SERVERLESS',
    warehouse_size='Small',
    num_clusters=1,
    hours_per_month=100,
    runs_per_day=None,
    avg_runtime_minutes=None,
    days_per_month=22,
):
    """Replicate frontend costCalculation.ts DBSQL logic."""
    # Hours calculation (same as all workloads)
    if runs_per_day and avg_runtime_minutes:
        hours = (runs_per_day * avg_runtime_minutes / 60) * days_per_month
    elif hours_per_month:
        hours = hours_per_month
    else:
        hours = 0

    # DBU/hr from size map
    size_dbu = DBSQL_SIZE_DBU.get(warehouse_size, 12)
    dbu_per_hour = size_dbu * num_clusters

    # Monthly DBUs
    monthly_dbus = dbu_per_hour * hours

    # SKU determination
    wh_type = (warehouse_type or 'SERVERLESS').upper()
    if wh_type == 'SERVERLESS':
        sku = 'SERVERLESS_SQL_COMPUTE'
    elif wh_type == 'PRO':
        sku = 'SQL_PRO_COMPUTE'
    else:
        sku = 'SQL_COMPUTE'

    # Is serverless?
    is_serverless = wh_type == 'SERVERLESS'

    # $/DBU
    dbu_price = FRONTEND_DBSQL_PRICES.get(sku, 0.22)

    # DBU cost
    dbu_cost = monthly_dbus * dbu_price

    return {
        'hours_per_month': hours,
        'dbu_per_hour': dbu_per_hour,
        'monthly_dbus': monthly_dbus,
        'sku': sku,
        'dbu_price': dbu_price,
        'dbu_cost': dbu_cost,
        'is_serverless': is_serverless,
    }


def backend_calc_dbsql(
    warehouse_type='SERVERLESS',
    warehouse_size='Small',
    num_clusters=1,
    hours_per_month=100,
    runs_per_day=None,
    avg_runtime_minutes=None,
    days_per_month=22,
):
    """Replicate backend calculations.py DBSQL logic."""
    # Hours calculation
    if runs_per_day and avg_runtime_minutes:
        hours = (runs_per_day * avg_runtime_minutes / 60) * days_per_month
    elif hours_per_month:
        hours = hours_per_month
    else:
        hours = 0

    # _calc_dbsql_dbu logic
    size_dbu = DBSQL_SIZE_DBU.copy()
    wh_size = warehouse_size or 'Small'
    if wh_size not in size_dbu:
        wh_size = 'Small'
    dbu_per_hour = float(size_dbu[wh_size] * int(num_clusters or 1))

    # Monthly DBUs
    monthly_dbus = dbu_per_hour * hours

    # _get_sku_type logic
    wh_type = (warehouse_type or 'SERVERLESS').upper()
    if wh_type == 'SERVERLESS':
        sku = 'SERVERLESS_SQL_COMPUTE'
    elif wh_type == 'PRO':
        sku = 'SQL_PRO_COMPUTE'
    else:
        sku = 'SQL_COMPUTE'

    # _is_serverless_workload logic
    is_serverless = wh_type == 'SERVERLESS'

    dbu_price = BACKEND_DBSQL_PRICES.get(sku, 0.22)
    dbu_cost = monthly_dbus * dbu_price

    return {
        'hours_per_month': hours,
        'dbu_per_hour': dbu_per_hour,
        'monthly_dbus': monthly_dbus,
        'sku': sku,
        'dbu_price': dbu_price,
        'dbu_cost': dbu_cost,
        'is_serverless': is_serverless,
    }
