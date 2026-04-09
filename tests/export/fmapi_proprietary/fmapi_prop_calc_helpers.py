"""Shared calculation helpers for FMAPI Proprietary tests.

Replicates backend pricing.py / excel_builder.py logic for FMAPI_PROPRIETARY
so tests can verify correctness independently.
"""
import json
import os

_PRICING_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', 'backend', 'static', 'pricing'
)
_RATES_PATH = os.path.join(_PRICING_DIR, 'fmapi-proprietary-rates.json')
if os.path.exists(_RATES_PATH):
    with open(_RATES_PATH) as f:
        FMAPI_PROP_RATES = json.load(f)
else:
    FMAPI_PROP_RATES = {}

FMAPI_DBU_PRICE = 0.07

TOKEN_RATE_TYPES = (
    'input_token', 'output_token', 'input', 'output',
    'cache_read', 'cache_write',
)
PROVISIONED_RATE_TYPES = ('provisioned_scaling', 'provisioned_entry', 'batch_inference')

PROVIDER_SKU_MAP = {
    'anthropic': 'ANTHROPIC_MODEL_SERVING',
    'openai': 'OPENAI_MODEL_SERVING',
    'google': 'GEMINI_MODEL_SERVING',
}


def get_rate_info(cloud, provider, model, endpoint, context, rate_type):
    """Look up rate info from pricing JSON."""
    key = f"{cloud}:{provider}:{model}:{endpoint}:{context}:{rate_type}"
    return FMAPI_PROP_RATES.get(key, {})


def get_dbu_rate(cloud, provider, model, endpoint, context, rate_type):
    """Look up dbu_rate for a model + rate_type."""
    info = get_rate_info(cloud, provider, model, endpoint, context, rate_type)
    return info.get('dbu_rate', 0)


def is_token_based(rate_type):
    return rate_type in TOKEN_RATE_TYPES


def is_provisioned(rate_type):
    return rate_type in PROVISIONED_RATE_TYPES


def calc_monthly_dbus(quantity, dbu_rate, rate_type):
    """Calculate monthly DBUs from quantity and rate."""
    return quantity * dbu_rate


def get_all_providers(cloud='aws'):
    """Get unique providers from pricing JSON."""
    providers = set()
    prefix = f"{cloud}:"
    for key in FMAPI_PROP_RATES:
        if key.startswith(prefix):
            parts = key.split(':')
            if len(parts) == 6:
                providers.add(parts[1])
    return sorted(providers)


def get_provider_models(cloud, provider):
    """Get all models for a provider."""
    models = set()
    for key in FMAPI_PROP_RATES:
        parts = key.split(':')
        if len(parts) == 6 and parts[0] == cloud and parts[1] == provider:
            models.add(parts[2])
    return sorted(models)


def get_model_rate_types(cloud, provider, model):
    """Get all rate types for a model."""
    rate_types = set()
    for key in FMAPI_PROP_RATES:
        parts = key.split(':')
        if (len(parts) == 6 and parts[0] == cloud
                and parts[1] == provider and parts[2] == model):
            rate_types.add(parts[5])
    return sorted(rate_types)
