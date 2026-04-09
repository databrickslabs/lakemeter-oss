"""Shared calculation helpers for Model Serving tests.

Replicates frontend (Calculator.tsx) and backend (calculations.py) logic
for MODEL_SERVING workloads so tests can compare FE vs BE independently.
"""
import json
import os

# Load actual model-serving-rates.json from backend
_PRICING_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', 'backend', 'static', 'pricing'
)
_RATES_PATH = os.path.join(_PRICING_DIR, 'model-serving-rates.json')
if os.path.exists(_RATES_PATH):
    with open(_RATES_PATH) as f:
        MODEL_SERVING_RATES = json.load(f)
else:
    MODEL_SERVING_RATES = {}

# Fallback $/DBU for SERVERLESS_REAL_TIME_INFERENCE
MODEL_SERVING_DBU_PRICE = 0.07

# GPU display name mapping (from helpers.py)
GPU_DISPLAY_NAMES = {
    'cpu': 'CPU',
    'gpu_small_t4': 'Small (T4)',
    'gpu_medium_a10g_1x': 'Medium (A10G 1x)',
    'gpu_medium_a10g_4x': 'Medium (A10G 4x)',
    'gpu_medium_a10g_8x': 'Medium (A10G 8x)',
    'gpu_large_a10g_4x': 'Large (A10G 4x)',
    'gpu_medium_a100_1x': 'Medium (A100 1x)',
    'gpu_large_a100_2x': 'Large (A100 2x)',
    'gpu_xlarge_a100_40gb_8x': 'XLarge (A100 40GB 8x)',
    'gpu_xlarge_a100_80gb_8x': 'XLarge (A100 80GB 8x)',
    'gpu_xlarge_a100_80gb_1x': 'XLarge (A100 80GB 1x)',
    'gpu_2xlarge_a100_80gb_2x': '2XLarge (A100 80GB 2x)',
    'gpu_4xlarge_a100_80gb_4x': '4XLarge (A100 80GB 4x)',
    'gpu_medium_g2_standard_8': 'Medium (G2 Standard 8)',
}


def get_gpu_dbu_rate(cloud: str, gpu_type: str) -> float:
    """Look up DBU/hr for a GPU type from pricing JSON."""
    key = f"{cloud}:{gpu_type}"
    info = MODEL_SERVING_RATES.get(key, {})
    return info.get('dbu_rate', 0)


def calc_hours(hours_per_month=None, runs_per_day=None,
               avg_runtime_minutes=None, days_per_month=22):
    """Calculate hours per month (same logic as all workloads)."""
    if runs_per_day and avg_runtime_minutes:
        return (runs_per_day * avg_runtime_minutes / 60) * days_per_month
    if hours_per_month:
        return float(hours_per_month)
    return 0


def frontend_calc_model_serving(
    gpu_type='cpu', cloud='aws', hours_per_month=730,
    runs_per_day=None, avg_runtime_minutes=None, days_per_month=22,
):
    """Replicate frontend Calculator.tsx MODEL_SERVING logic."""
    hours = calc_hours(hours_per_month, runs_per_day,
                       avg_runtime_minutes, days_per_month)
    dbu_per_hour = get_gpu_dbu_rate(cloud, gpu_type)
    if dbu_per_hour == 0:
        dbu_per_hour = 2  # Frontend fallback default
    monthly_dbus = dbu_per_hour * hours
    sku = 'SERVERLESS_REAL_TIME_INFERENCE'
    dbu_cost = monthly_dbus * MODEL_SERVING_DBU_PRICE
    return {
        'hours': hours,
        'dbu_per_hour': dbu_per_hour,
        'monthly_dbus': monthly_dbus,
        'sku': sku,
        'dbu_price': MODEL_SERVING_DBU_PRICE,
        'dbu_cost': dbu_cost,
        'total_cost': dbu_cost,  # No VM costs
        'is_serverless': True,
    }


def backend_calc_model_serving(
    gpu_type='cpu', cloud='aws', hours_per_month=730,
    runs_per_day=None, avg_runtime_minutes=None, days_per_month=22,
):
    """Replicate backend calculations.py MODEL_SERVING logic."""
    hours = calc_hours(hours_per_month, runs_per_day,
                       avg_runtime_minutes, days_per_month)
    dbu_per_hour = get_gpu_dbu_rate(cloud, gpu_type)
    monthly_dbus = dbu_per_hour * hours
    sku = 'SERVERLESS_REAL_TIME_INFERENCE'
    dbu_cost = monthly_dbus * MODEL_SERVING_DBU_PRICE
    return {
        'hours': hours,
        'dbu_per_hour': dbu_per_hour,
        'monthly_dbus': monthly_dbus,
        'sku': sku,
        'dbu_price': MODEL_SERVING_DBU_PRICE,
        'dbu_cost': dbu_cost,
        'total_cost': dbu_cost,
        'is_serverless': True,
    }
