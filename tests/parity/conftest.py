"""Shared fixtures for parity tests — loads real pricing data."""
import json
import os
import sys
import pytest
from types import SimpleNamespace

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, BACKEND_DIR)
PRICING_DIR = os.path.join(BACKEND_DIR, 'static', 'pricing')


def _load(name):
    with open(os.path.join(PRICING_DIR, name)) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def pricing():
    """All pricing data in one bundle."""
    return {
        'dbu_rates': _load('dbu-rates.json'),
        'instance_dbu_rates': _load('instance-dbu-rates.json'),
        'dbu_multipliers': _load('dbu-multipliers.json'),
        'dbsql_rates': _load('dbsql-rates.json'),
        'vector_search_rates': _load('vector-search-rates.json'),
        'model_serving_rates': _load('model-serving-rates.json'),
        'fmapi_db_rates': _load('fmapi-databricks-rates.json'),
        'fmapi_prop_rates': _load('fmapi-proprietary-rates.json'),
    }


def make_item(**kwargs):
    """Create a SimpleNamespace item with all fields defaulted to None."""
    defaults = dict(
        workload_type=None, workload_name=None,
        driver_node_type=None, worker_node_type=None, num_workers=0,
        photon_enabled=False, serverless_enabled=False, serverless_mode=None,
        runs_per_day=None, avg_runtime_minutes=None, days_per_month=None,
        hours_per_month=None,
        dlt_edition=None,
        dbsql_warehouse_type=None, dbsql_warehouse_size=None,
        dbsql_num_clusters=1,
        vector_search_mode=None, vector_capacity_millions=None,
        model_serving_gpu_type=None,
        fmapi_model=None, fmapi_rate_type=None, fmapi_quantity=None,
        fmapi_provider=None, fmapi_endpoint_type=None,
        fmapi_context_length=None,
        lakebase_cu=None, lakebase_ha_nodes=None, lakebase_storage_gb=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)
