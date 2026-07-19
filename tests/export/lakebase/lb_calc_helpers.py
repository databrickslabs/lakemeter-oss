"""Helper functions for Lakebase calculation verification."""


def calc_dbu_per_hour(cu: float, ha_nodes: int = 1, dbu_per_cu_hour: float = 0.230, discount_pct: float = 25.0) -> float:
    """Calculate discounted equivalent Lakebase DBU/hr for an always-on minimum CU floor."""
    return cu * ha_nodes * dbu_per_cu_hour * (1 - discount_pct / 100)


def calc_monthly_dbus(cu: float, ha_nodes: int, hours: float) -> float:
    """Calculate billable monthly DBUs."""
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
