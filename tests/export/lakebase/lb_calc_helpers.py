"""Helper functions for Lakebase calculation verification."""


def calc_dbu_per_hour(cu: float, ha_nodes: int = 1) -> float:
    """Calculate Lakebase DBU/hr: CU × HA_nodes."""
    return cu * ha_nodes


def calc_monthly_dbus(cu: float, ha_nodes: int, hours: float) -> float:
    """Calculate monthly DBUs: DBU/hr × hours."""
    return calc_dbu_per_hour(cu, ha_nodes) * hours


def calc_storage_cost(storage_gb: float, rate_per_gb: float = 0.023) -> float:
    """Calculate monthly storage cost: GB × $/GB/month."""
    return storage_gb * rate_per_gb


def calc_total_monthly_cost(
    cu: float, ha_nodes: int, hours: float,
    dbu_rate: float, storage_gb: float,
    storage_rate: float = 0.023, discount_pct: float = 0.0,
) -> float:
    """Total = compute DBU cost + storage cost."""
    monthly_dbus = calc_monthly_dbus(cu, ha_nodes, hours)
    dbu_cost = monthly_dbus * dbu_rate * (1 - discount_pct)
    storage_cost = calc_storage_cost(storage_gb, storage_rate)
    return dbu_cost + storage_cost
