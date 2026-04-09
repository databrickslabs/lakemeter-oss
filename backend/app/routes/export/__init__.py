"""Export package — modularized from the original 1209-line export.py.

Re-exports all public symbols so existing imports continue to work:
  from app.routes.export import router
  from app.routes.export import _calculate_dbu_per_hour
  etc.
"""
# Router (used by app.routes.__init__)
from .routes import router

# Pricing functions (used by tests)
from .pricing import (
    _get_dbu_price,
    _get_sku_type,
    _get_fmapi_sku,
    _get_fmapi_dbu_per_million,
    _is_fmapi_hourly,
    FALLBACK_DBU_PRICES,
    DBU_RATES_BY_REGION,
    INSTANCE_DBU_RATES,
    MODEL_SERVING_RATES,
    FMAPI_DB_RATES,
    FMAPI_PROP_RATES,
    VECTOR_SEARCH_RATES,
    DBSQL_RATES,
)

# Helper functions (access control, display names)
from .helpers import (
    _check_estimate_access,
    _get_workload_display_name,
    _get_workload_config_details,
    _get_pricing_tier_display,
)

# Calculation functions (used by tests)
from .calculations import (
    _calculate_hours_per_month,
    _calculate_dbu_per_hour,
    _is_serverless_workload,
)

# Excel builder (used internally)
from .excel_builder import build_estimate_excel

__all__ = [
    'router',
    '_get_dbu_price', '_get_sku_type', '_get_fmapi_sku',
    '_get_fmapi_dbu_per_million', '_is_fmapi_hourly',
    '_check_estimate_access', '_get_workload_display_name',
    '_get_workload_config_details', '_calculate_hours_per_month',
    '_calculate_dbu_per_hour', '_is_serverless_workload',
    '_get_pricing_tier_display', 'build_estimate_excel',
    'FALLBACK_DBU_PRICES', 'DBU_RATES_BY_REGION', 'INSTANCE_DBU_RATES',
    'MODEL_SERVING_RATES', 'FMAPI_DB_RATES', 'FMAPI_PROP_RATES',
    'VECTOR_SEARCH_RATES', 'DBSQL_RATES',
]
