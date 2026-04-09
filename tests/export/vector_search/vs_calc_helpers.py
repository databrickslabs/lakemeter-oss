"""Vector Search calculation helpers for FE/BE alignment tests."""
import json
import os
import math

PRICING_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', 'backend', 'static', 'pricing'
)

_VS_RATES = None


def _load_vs_rates():
    global _VS_RATES
    if _VS_RATES is None:
        path = os.path.join(PRICING_DIR, 'vector-search-rates.json')
        with open(path) as f:
            _VS_RATES = json.load(f)
    return _VS_RATES


def get_vs_rate_info(cloud: str, mode: str) -> dict:
    """Get Vector Search rate info for a cloud:mode key."""
    rates = _load_vs_rates()
    key = f"{cloud}:{mode}"
    return rates.get(key, {})


def get_dbu_rate(cloud: str, mode: str) -> float:
    """Get DBU/hr per unit for a cloud:mode combination."""
    info = get_vs_rate_info(cloud, mode)
    if mode == 'storage_optimized':
        return info.get('dbu_rate', 18.29)
    return info.get('dbu_rate', 4.0)


def get_input_divisor(cloud: str, mode: str) -> int:
    """Get the input_divisor (vectors per unit) for a cloud:mode."""
    info = get_vs_rate_info(cloud, mode)
    if mode == 'storage_optimized':
        return info.get('input_divisor', 64000000)
    return info.get('input_divisor', 2000000)


def calc_units(capacity_millions: float, mode: str, cloud: str = 'aws') -> int:
    """Calculate number of units from capacity in millions (ceiling)."""
    divisor = get_input_divisor(cloud, mode)
    if divisor == 0:
        return 0
    vectors_total = capacity_millions * 1_000_000
    return math.ceil(vectors_total / divisor)


def calc_dbu_per_hour(capacity_millions: float, mode: str,
                      cloud: str = 'aws') -> float:
    """Calculate DBU/hr for Vector Search — mirrors backend logic."""
    units = calc_units(capacity_millions, mode, cloud)
    dbu_rate = get_dbu_rate(cloud, mode)
    return units * dbu_rate


def calc_monthly_dbus(capacity_millions: float, mode: str,
                      hours_per_month: float = 730,
                      cloud: str = 'aws') -> float:
    """Calculate total monthly DBUs."""
    dbu_hr = calc_dbu_per_hour(capacity_millions, mode, cloud)
    return dbu_hr * hours_per_month


def calc_storage_gb(capacity_millions: float) -> float:
    """Approximate storage GB from capacity — 1M vectors ~ 1 GB."""
    return capacity_millions


def get_all_cloud_mode_combos():
    """Return all (cloud, mode) tuples from the rates file."""
    rates = _load_vs_rates()
    combos = []
    for key in rates:
        parts = key.split(':')
        if len(parts) == 2:
            combos.append((parts[0], parts[1]))
    return combos
