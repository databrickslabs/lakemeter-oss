"""Shared calculation helpers for FMAPI Databricks tests.

Replicates frontend (costCalculation.ts) and backend (pricing.py / excel_builder.py)
logic for FMAPI_DATABRICKS so tests can compare FE vs BE independently.
"""
import json
import os

_PRICING_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', 'backend', 'static', 'pricing'
)
_RATES_PATH = os.path.join(_PRICING_DIR, 'fmapi-databricks-rates.json')
if os.path.exists(_RATES_PATH):
    with open(_RATES_PATH) as f:
        FMAPI_DB_RATES = json.load(f)
else:
    FMAPI_DB_RATES = {}

# Fallback $/DBU for SERVERLESS_REAL_TIME_INFERENCE
FMAPI_DBU_PRICE = 0.07

# Token vs provisioned detection
TOKEN_RATE_TYPES = ('input_token', 'output_token', 'input', 'output')
PROVISIONED_RATE_TYPES = ('provisioned_scaling', 'provisioned_entry')


def get_fmapi_db_rate(cloud: str, model: str, rate_type: str) -> dict:
    """Look up rate info from pricing JSON. Returns dict or empty."""
    key = f"{cloud}:{model}:{rate_type}"
    return FMAPI_DB_RATES.get(key, {})


def get_dbu_rate(cloud: str, model: str, rate_type: str) -> float:
    """Look up dbu_rate for a model + rate_type."""
    info = get_fmapi_db_rate(cloud, model, rate_type)
    return info.get('dbu_rate', 0)


def is_token_based(rate_type: str) -> bool:
    return rate_type in TOKEN_RATE_TYPES


def is_provisioned(rate_type: str) -> bool:
    return rate_type in PROVISIONED_RATE_TYPES


def frontend_calc_fmapi_db(
    model='llama-3-3-70b', rate_type='input_token', quantity=100,
    cloud='aws',
):
    """Replicate frontend Calculator.tsx FMAPI_DATABRICKS logic.

    quantity: millions (for tokens) or hours (for provisioned).
    """
    info = get_fmapi_db_rate(cloud, model, rate_type)
    if is_provisioned(rate_type):
        dbu_per_hour = info.get('dbu_rate', 0)
        if dbu_per_hour == 0:
            dbu_per_hour = 200 if rate_type == 'provisioned_scaling' else 50
        monthly_dbus = quantity * dbu_per_hour
    else:
        dbu_per_1m = info.get('dbu_rate', 0)
        if dbu_per_1m == 0:
            dbu_per_1m = 3.0 if rate_type == 'output_token' else 1.0
        monthly_dbus = quantity * dbu_per_1m

    sku = 'SERVERLESS_REAL_TIME_INFERENCE'
    dbu_cost = monthly_dbus * FMAPI_DBU_PRICE
    return {
        'quantity': quantity,
        'rate_type': rate_type,
        'monthly_dbus': monthly_dbus,
        'sku': sku,
        'dbu_price': FMAPI_DBU_PRICE,
        'dbu_cost': dbu_cost,
        'total_cost': dbu_cost,
        'is_serverless': True,
    }


def backend_calc_fmapi_db(
    model='llama-3-3-70b', rate_type='input_token', quantity=100,
    cloud='aws',
):
    """Replicate backend excel_builder.py FMAPI_DATABRICKS logic."""
    info = get_fmapi_db_rate(cloud, model, rate_type)
    dbu_rate = info.get('dbu_rate', 0)

    if is_provisioned(rate_type):
        monthly_dbus = quantity * dbu_rate
    else:
        monthly_dbus = quantity * dbu_rate

    sku = info.get('sku_product_type', 'SERVERLESS_REAL_TIME_INFERENCE')
    dbu_cost = monthly_dbus * FMAPI_DBU_PRICE
    return {
        'quantity': quantity,
        'rate_type': rate_type,
        'monthly_dbus': monthly_dbus,
        'sku': sku,
        'dbu_price': FMAPI_DBU_PRICE,
        'dbu_cost': dbu_cost,
        'total_cost': dbu_cost,
        'is_serverless': True,
    }


def get_all_models(cloud: str = 'aws') -> list:
    """Get all unique model names for a cloud from pricing JSON."""
    models = set()
    prefix = f"{cloud}:"
    for key in FMAPI_DB_RATES:
        if key.startswith(prefix):
            parts = key.split(':')
            if len(parts) == 3:
                models.add(parts[1])
    return sorted(models)


def get_model_rate_types(cloud: str, model: str) -> list:
    """Get all rate types available for a model on a cloud."""
    rate_types = []
    for key in FMAPI_DB_RATES:
        parts = key.split(':')
        if len(parts) == 3 and parts[0] == cloud and parts[1] == model:
            rate_types.append(parts[2])
    return sorted(rate_types)
