"""Pricing data loading and lookup functions for export."""
import json, logging, os

logger = logging.getLogger(__name__)

# ========== LOAD PRICING DATA FROM STATIC JSON ==========
_PRICING_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'static', 'pricing')


def _load_json(filename: str) -> dict:
    path = os.path.join(_PRICING_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}


# Load once at import time
DBU_RATES_BY_REGION = _load_json('dbu-rates.json')
INSTANCE_DBU_RATES = _load_json('instance-dbu-rates.json')
MODEL_SERVING_RATES = _load_json('model-serving-rates.json')
FMAPI_DB_RATES = _load_json('fmapi-databricks-rates.json')
FMAPI_PROP_RATES = _load_json('fmapi-proprietary-rates.json')
VECTOR_SEARCH_RATES = _load_json('vector-search-rates.json')
DBSQL_RATES = _load_json('dbsql-rates.json')
DBU_MULTIPLIERS = _load_json('dbu-multipliers.json')
DBSQL_WAREHOUSE_CONFIG = _load_json('dbsql-warehouse-config.json')

# Fallback DBU $/DBU rates — aligned with frontend DEFAULT_DBU_PRICING (costCalculation.ts)
FALLBACK_DBU_PRICES = {
    'JOBS_COMPUTE': 0.15, 'JOBS_COMPUTE_(PHOTON)': 0.15, 'JOBS_SERVERLESS_COMPUTE': 0.39,
    'ALL_PURPOSE_COMPUTE': 0.55, 'ALL_PURPOSE_COMPUTE_(PHOTON)': 0.55,
    'INTERACTIVE_SERVERLESS_COMPUTE': 0.83, 'ALL_PURPOSE_SERVERLESS_COMPUTE': 0.83,
    'DLT_CORE_COMPUTE': 0.20, 'DLT_CORE_COMPUTE_(PHOTON)': 0.20,
    'DLT_PRO_COMPUTE': 0.25, 'DLT_PRO_COMPUTE_(PHOTON)': 0.25,
    'DLT_ADVANCED_COMPUTE': 0.36, 'DLT_ADVANCED_COMPUTE_(PHOTON)': 0.36,
    'DELTA_LIVE_TABLES_SERVERLESS': 0.30, 'SQL_COMPUTE': 0.22,
    'SQL_PRO_COMPUTE': 0.55, 'SERVERLESS_SQL_COMPUTE': 0.70,
    'SERVERLESS_REAL_TIME_INFERENCE': 0.07, 'SERVERLESS_REAL_TIME_INFERENCE_LAUNCH': 0.07,
    'OPENAI_MODEL_SERVING': 0.07, 'ANTHROPIC_MODEL_SERVING': 0.07,
    'GEMINI_MODEL_SERVING': 0.07, 'GOOGLE_MODEL_SERVING': 0.07,
    'FOUNDATION_MODEL_TRAINING': 0.20, 'DATABASE_SERVERLESS_COMPUTE': 0.48,
    'DATABRICKS_APPS_COMPUTE': 0.07,
}


def _get_dbu_price(cloud: str, region: str, tier: str, sku: str) -> tuple:
    """Look up $/DBU from pricing JSON. Returns (price, found) tuple."""
    key = f"{cloud}:{region}:{tier.upper()}"
    region_rates = DBU_RATES_BY_REGION.get(key, {})
    if sku in region_rates:
        return region_rates[sku], True
    # Try without region specificity - find any matching cloud:*:tier
    for k, v in DBU_RATES_BY_REGION.items():
        parts = k.split(':')
        if len(parts) == 3 and parts[0] == cloud and parts[2] == tier.upper() and sku in v:
            return v[sku], True
    # Fallback — mark as not found so notes can warn
    fallback = FALLBACK_DBU_PRICES.get(sku, 0)
    return fallback, False


def _get_photon_multiplier(cloud: str, sku_base: str) -> float:
    """Get photon multiplier from dbu-multipliers.json.

    Returns the multiplier (e.g. 2.9 for DLT_ADVANCED on AWS) or 2.0 as default.
    """
    key = f"{cloud}:{sku_base}:photon"
    info = DBU_MULTIPLIERS.get(key, {})
    if isinstance(info, dict) and 'multiplier' in info:
        return info['multiplier']
    logger.warning("Photon multiplier not found for %s, using fallback 2.0", key)
    return 2.0


def _get_sku_type(item, cloud: str = 'aws') -> str:
    """Determine the SKU/product type for a line item."""
    wt = (item.workload_type or '').upper()

    if wt == 'JOBS':
        if item.serverless_enabled:
            return 'JOBS_SERVERLESS_COMPUTE'
        elif item.photon_enabled:
            return 'JOBS_COMPUTE_(PHOTON)'
        return 'JOBS_COMPUTE'
    elif wt == 'ALL_PURPOSE':
        if item.serverless_enabled:
            return 'ALL_PURPOSE_SERVERLESS_COMPUTE'
        elif item.photon_enabled:
            return 'ALL_PURPOSE_COMPUTE_(PHOTON)'
        return 'ALL_PURPOSE_COMPUTE'
    elif wt == 'DLT':
        if item.serverless_enabled:
            return 'JOBS_SERVERLESS_COMPUTE'
        edition = (item.dlt_edition or 'CORE').upper()
        if item.photon_enabled:
            return f'DLT_{edition}_COMPUTE_(PHOTON)'
        return f'DLT_{edition}_COMPUTE'
    elif wt == 'DBSQL':
        warehouse_type = (item.dbsql_warehouse_type or 'SERVERLESS').upper()
        if warehouse_type == 'SERVERLESS':
            return 'SERVERLESS_SQL_COMPUTE'
        elif warehouse_type == 'PRO':
            return 'SQL_PRO_COMPUTE'
        return 'SQL_COMPUTE'
    elif wt == 'VECTOR_SEARCH':
        return 'SERVERLESS_REAL_TIME_INFERENCE'
    elif wt == 'MODEL_SERVING':
        return 'SERVERLESS_REAL_TIME_INFERENCE'
    elif wt == 'FMAPI_DATABRICKS':
        return _get_fmapi_sku(item, cloud)
    elif wt == 'FMAPI_PROPRIETARY':
        # Use provider-specific SKU for pricing lookup (matches frontend)
        provider = (item.fmapi_provider or 'openai').lower()
        provider_mapping = {
            'google': 'GEMINI', 'anthropic': 'ANTHROPIC', 'openai': 'OPENAI'
        }
        return f'{provider_mapping.get(provider, provider.upper())}_MODEL_SERVING'
    elif wt == 'LAKEBASE':
        return 'DATABASE_SERVERLESS_COMPUTE'
    elif wt == 'DATABRICKS_APPS':
        return 'ALL_PURPOSE_SERVERLESS_COMPUTE'
    elif wt == 'AI_PARSE':
        return 'SERVERLESS_REAL_TIME_INFERENCE'
    elif wt == 'SHUTTERSTOCK_IMAGEAI':
        return 'SERVERLESS_REAL_TIME_INFERENCE'
    return 'JOBS_COMPUTE'


def _get_fmapi_sku(item, cloud: str) -> str:
    """Get the actual SKU product type for FMAPI from pricing JSON."""
    rate_type = item.fmapi_rate_type or 'input_token'
    model = item.fmapi_model or ''
    wt = item.workload_type or ''

    if wt == 'FMAPI_DATABRICKS':
        key = f"{cloud}:{model}:{rate_type}"
        info = FMAPI_DB_RATES.get(key, {})
        return info.get('sku_product_type', 'SERVERLESS_REAL_TIME_INFERENCE')
    elif wt == 'FMAPI_PROPRIETARY':
        provider = item.fmapi_provider or ''
        endpoint = getattr(item, 'fmapi_endpoint_type', 'global') or 'global'
        context = getattr(item, 'fmapi_context_length', 'all') or 'all'
        key = f"{cloud}:{provider}:{model}:{endpoint}:{context}:{rate_type}"
        info = FMAPI_PROP_RATES.get(key, {})
        return info.get('sku_product_type', 'OPENAI_MODEL_SERVING')
    return 'SERVERLESS_REAL_TIME_INFERENCE'


def _get_fmapi_dbu_per_million(item, cloud: str) -> tuple:
    """Get DBU per 1M tokens (or DBU/hr for provisioned) from pricing JSON.

    Returns (dbu_rate, found) tuple. found=False means no match in pricing data.
    """
    rate_type = item.fmapi_rate_type or 'input_token'
    model = item.fmapi_model or ''
    wt = item.workload_type or ''

    if wt == 'FMAPI_DATABRICKS':
        key = f"{cloud}:{model}:{rate_type}"
        info = FMAPI_DB_RATES.get(key, {})
        if 'dbu_rate' in info:
            return info['dbu_rate'], True
        key_lower = key.lower().strip()
        for k, v in FMAPI_DB_RATES.items():
            if k.lower().strip() == key_lower:
                return v.get('dbu_rate', 0), True
        return 0, False
    elif wt == 'FMAPI_PROPRIETARY':
        provider = item.fmapi_provider or ''
        endpoint = getattr(item, 'fmapi_endpoint_type', 'global') or 'global'
        # Default to 'all' context matching the API's default (fmapi_calc.py)
        context = getattr(item, 'fmapi_context_length', 'all') or 'all'
        key = f"{cloud}:{provider}:{model}:{endpoint}:{context}:{rate_type}"
        info = FMAPI_PROP_RATES.get(key, {})
        if 'dbu_rate' in info:
            return info['dbu_rate'], True
        # Try case-insensitive match
        key_lower = key.lower().strip()
        for k, v in FMAPI_PROP_RATES.items():
            if k.lower().strip() == key_lower:
                return v.get('dbu_rate', 0), True
        # Try alternate context as fallback (OpenAI uses 'all', Google uses 'long'/'short')
        alt_contexts = []
        if context != 'all':
            alt_contexts.append('all')
        if context != 'long':
            alt_contexts.append('long')
        for alt_ctx in alt_contexts:
            alt_key = f"{cloud}:{provider}:{model}:{endpoint}:{alt_ctx}:{rate_type}"
            info = FMAPI_PROP_RATES.get(alt_key, {})
            if 'dbu_rate' in info:
                return info['dbu_rate'], True
        return 0, False
    return 0, False

# Fallback DBU/1M token rates matching frontend costCalculation.ts
FMAPI_PROP_FALLBACK_RATES = {
    'input_token': 21.43, 'input': 21.43,
    'output_token': 321.43, 'output': 321.43,
    'cache_read': 8.57, 'cache_write': 85.71,
}


def _is_fmapi_hourly(item, cloud: str) -> bool:
    """Check if FMAPI rate is hourly (provisioned) vs token-based.
    Only provisioned_scaling/provisioned_entry are hourly — matches frontend.
    """
    rate_type = item.fmapi_rate_type or 'input_token'
    return rate_type in ('provisioned_scaling', 'provisioned_entry')