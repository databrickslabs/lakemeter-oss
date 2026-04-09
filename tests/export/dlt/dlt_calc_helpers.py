"""
Shared DLT calculation helper functions for Sprint 3 tests.

Replicate frontend (costCalculation.ts) and backend (calculations.py)
logic so tests can verify both independently and compare them.
"""

# Frontend hardcoded $/DBU rates (fallback)
FRONTEND_DLT_PRICES = {
    'DLT_CORE_COMPUTE': 0.20,
    'DLT_CORE_COMPUTE_(PHOTON)': 0.20,
    'DLT_PRO_COMPUTE': 0.25,
    'DLT_PRO_COMPUTE_(PHOTON)': 0.25,
    'DLT_ADVANCED_COMPUTE': 0.36,
    'DLT_ADVANCED_COMPUTE_(PHOTON)': 0.36,
    'JOBS_SERVERLESS_COMPUTE': 0.39,
    'DELTA_LIVE_TABLES_SERVERLESS': 0.30,
}


def frontend_calc_dlt(
    driver_dbu_rate: float,
    worker_dbu_rate: float,
    num_workers: int,
    dlt_edition: str = "CORE",
    photon_enabled: bool = False,
    serverless_enabled: bool = False,
    serverless_mode: str = "standard",
    hours_per_month: float = 0,
    runs_per_day: int = 0,
    avg_runtime_minutes: int = 0,
    days_per_month: int = 22,
    dbu_price: float = None,
) -> dict:
    """Replicate frontend costCalculation.ts logic for DLT."""
    if runs_per_day and avg_runtime_minutes:
        hours = (runs_per_day * (avg_runtime_minutes / 60)) * days_per_month
    elif hours_per_month:
        hours = hours_per_month
    else:
        hours = 0

    edition = (dlt_edition or 'CORE').upper()
    if serverless_enabled:
        sku = "JOBS_SERVERLESS_COMPUTE"
    else:
        sku = f"DLT_{edition}_COMPUTE"
        if photon_enabled:
            sku += "_(PHOTON)"

    if not serverless_enabled and not photon_enabled:
        photon_mult = 1.0
    else:
        photon_mult = 2.0

    if not serverless_enabled:
        serverless_mult = 1
    elif serverless_mode == "performance":
        serverless_mult = 2
    else:
        serverless_mult = 1

    if serverless_enabled:
        dbu_per_hour = (driver_dbu_rate + (worker_dbu_rate * num_workers)) * photon_mult * serverless_mult
        vm_cost = 0
    else:
        dbu_per_hour = (driver_dbu_rate + (worker_dbu_rate * num_workers)) * photon_mult
        vm_cost = 0

    monthly_dbus = dbu_per_hour * hours
    if dbu_price is None:
        dbu_price = FRONTEND_DLT_PRICES.get(sku, 0.20)
    dbu_cost = monthly_dbus * dbu_price

    return {
        "hours_per_month": hours,
        "dbu_per_hour": dbu_per_hour,
        "monthly_dbus": monthly_dbus,
        "dbu_cost": dbu_cost,
        "vm_cost": vm_cost,
        "total_cost": dbu_cost + vm_cost,
        "sku": sku,
        "photon_multiplier": photon_mult,
        "serverless_multiplier": serverless_mult,
    }


def backend_calc_dlt(
    driver_dbu_rate: float,
    worker_dbu_rate: float,
    num_workers: int,
    dlt_edition: str = "CORE",
    photon_enabled: bool = False,
    serverless_enabled: bool = False,
    serverless_mode: str = "standard",
    hours_per_month: float = 0,
    runs_per_day: int = 0,
    avg_runtime_minutes: int = 0,
    days_per_month: int = 22,
    dbu_price: float = None,
) -> dict:
    """Replicate backend export calculations.py logic for DLT."""
    if runs_per_day and avg_runtime_minutes:
        hours = (runs_per_day * avg_runtime_minutes / 60) * days_per_month
    elif hours_per_month:
        hours = hours_per_month
    else:
        hours = 0

    nw = num_workers if num_workers else 0
    base_dbu = driver_dbu_rate + (worker_dbu_rate * nw)

    if serverless_enabled:
        base_dbu *= 2
        mode_mult = 2 if serverless_mode == 'performance' else 1
        dbu_per_hour = base_dbu * mode_mult
    else:
        if photon_enabled:
            base_dbu *= 2
        dbu_per_hour = base_dbu

    monthly_dbus = dbu_per_hour * hours

    if serverless_enabled:
        sku = "DELTA_LIVE_TABLES_SERVERLESS"
    else:
        edition = (dlt_edition or 'CORE').upper()
        sku = f"DLT_{edition}_COMPUTE"

    from app.routes.export.pricing import FALLBACK_DBU_PRICES
    if dbu_price is None:
        dbu_price = FALLBACK_DBU_PRICES.get(sku, 0.20)
    dbu_cost = monthly_dbus * dbu_price

    return {
        "hours_per_month": hours,
        "dbu_per_hour": dbu_per_hour,
        "monthly_dbus": monthly_dbus,
        "dbu_cost": dbu_cost,
        "sku": sku,
    }
