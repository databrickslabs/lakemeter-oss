"""T-shirt sizing and cost math for Lakehouse Federation.

Single source of truth so the calculate endpoint and the Excel export agree.

Serverless SQL warehouses bill on warehouse *uptime*, not query-seconds: auto-stop keeps the
warehouse warm between queries. Modeling a federated workload as a fixed number of "hours of
querying" therefore massively overstates cost, because a bursty workload never holds the
warehouse continuously.
"""
from __future__ import annotations

# Serverless SQL warehouse DBU/hour by size.
WAREHOUSE_DBU_PER_HOUR = {
    "2X-Small": 4.0,
    "X-Small": 6.0,
    "Small": 12.0,
    "Medium": 24.0,
    "Large": 40.0,
    "X-Large": 80.0,
    "2X-Large": 144.0,
    "3X-Large": 272.0,
    "4X-Large": 528.0,
}

# Lakehouse Federation t-shirt tiers, sized by number of users running federated queries.
FEDERATION_TIERS = {
    "S":  {"num_users": 10,  "queries_per_day": 20.0,   "warehouse_size": "2X-Small"},
    "M":  {"num_users": 50,  "queries_per_day": 100.0,  "warehouse_size": "2X-Small"},
    "L":  {"num_users": 150, "queries_per_day": 500.0,  "warehouse_size": "X-Small"},
    "XL": {"num_users": 500, "queries_per_day": 2000.0, "warehouse_size": "Small"},
}

TIER_LABELS = {"S": "Small", "M": "Medium", "L": "Large", "XL": "Extra Large"}

def _f(value, default: float = 0.0) -> float:
    """Coerce a value to float, tolerating Decimal/int/str/None.

    Postgres NUMERIC columns come back as ``decimal.Decimal``, which raises TypeError when
    mixed with floats (``Decimal('250') - 150.0``). Every numeric input is funnelled through
    here so callers can pass ORM values directly.
    """
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def warehouse_dbu_per_hour(size: str | None) -> float:
    """DBU/hour for a Serverless SQL warehouse size (defaults to 2X-Small)."""
    return WAREHOUSE_DBU_PER_HOUR.get(size or "2X-Small", 4.0)


def federation_warehouse_hours(
    queries_per_day: float,
    avg_query_seconds: float = 10.0,
    auto_stop_minutes: float = 10.0,
    active_hours_per_day: float = 8.0,
    days_per_month: int = 22,
) -> dict:
    """Warehouse uptime hours/month for a bursty query workload.

    Serverless SQL bills warehouse uptime, which is query execution time plus warm-idle time
    held open by auto-stop. Three regimes, taking the smallest (most realistic) bound:

    1. **Per-query**: each query holds the warehouse for its duration plus the auto-stop
       window — valid when queries are far apart.
    2. **Continuously warm**: if queries arrive more often than the auto-stop window the
       warehouse never idles down, capped at ``active_hours_per_day * days_per_month``.
    3. **Idle-overhead cap**: uptime cannot realistically exceed execution time plus one
       auto-stop window per contiguous busy block. Without this bound, evenly-spreading a
       light workload (e.g. 1,000 queries/month) across the day would bill a near-full
       always-on warehouse — up to ~100x the actual execution time.

    Returns hours plus the regime, so callers can explain the number to a customer.
    """
    queries_per_day = _f(queries_per_day)
    avg_query_seconds = _f(avg_query_seconds, 10.0) or 10.0
    auto_stop_minutes = _f(auto_stop_minutes, 10.0) or 10.0
    active_hours_per_day = _f(active_hours_per_day, 8.0) or 8.0
    days_per_month = int(_f(days_per_month, 22) or 22)

    if queries_per_day <= 0:
        return {"hours_per_month": 0.0, "saturated": False, "queries_per_month": 0.0,
                "execution_hours_per_month": 0.0, "regime": "none"}

    queries_per_month = queries_per_day * days_per_month
    execution_hours = queries_per_month * avg_query_seconds / 3600.0
    ceiling = active_hours_per_day * days_per_month
    minutes_between = (active_hours_per_day * 60.0) / queries_per_day

    # Regime 1: per-query hold (duration + auto-stop each)
    per_query_hours = queries_per_month * (auto_stop_minutes + avg_query_seconds / 60.0) / 60.0

    # Regime 3: execution time + one auto-stop tail per busy block. Treat the day's queries as
    # clustering into at most a handful of bursts rather than perfectly even arrivals.
    bursts_per_day = min(queries_per_day, max(1.0, active_hours_per_day))
    idle_capped_hours = execution_hours + (bursts_per_day * days_per_month * auto_stop_minutes / 60.0)

    if minutes_between < auto_stop_minutes:
        # Continuously warm, but never more than the idle-capped estimate.
        hours = min(ceiling, idle_capped_hours)
        regime = "continuously_warm" if hours >= ceiling - 1e-9 else "idle_capped"
        return {"hours_per_month": hours, "saturated": regime == "continuously_warm",
                "queries_per_month": queries_per_month,
                "execution_hours_per_month": execution_hours, "regime": regime}

    hours = min(ceiling, per_query_hours, idle_capped_hours)
    return {"hours_per_month": hours, "saturated": False,
            "queries_per_month": queries_per_month,
            "execution_hours_per_month": execution_hours, "regime": "bursty"}


def normalize_queries_per_day(queries_per_period: float, period: str, days_per_month: int = 22) -> float:
    """Convert a per-day/week/month query volume into queries per active day."""
    queries_per_period = _f(queries_per_period)
    days_per_month = int(_f(days_per_month, 22) or 22)
    p = (period or "day").lower()
    if p == "month":
        return queries_per_period / max(1, days_per_month)
    if p == "week":
        return queries_per_period / 5.0  # active weekdays
    return queries_per_period


def resolve_federation_config(
    size: str,
    num_users=None,
    queries_per_period=None,
    query_period: str = "day",
    warehouse_size=None,
    days_per_month: int = 22,
) -> dict:
    """Resolve a Federation config from a t-shirt size, explicit values taking precedence."""
    key = (size or "M").upper()
    tier = FEDERATION_TIERS.get(key)
    if tier is None:
        tier = FEDERATION_TIERS["M"]
    if queries_per_period is None:
        queries_per_day = tier["queries_per_day"]
    else:
        queries_per_day = normalize_queries_per_day(queries_per_period, query_period, days_per_month)
    return {
        "num_users": tier["num_users"] if num_users is None else int(_f(num_users)),
        "queries_per_day": _f(queries_per_day),
        "warehouse_size": warehouse_size or tier["warehouse_size"],
    }
