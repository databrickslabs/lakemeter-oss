"""Test that backend _get_sku_type() returns the same SKU as frontend for all 9 workload types.

Frontend reference: frontend/src/utils/costCalculation.ts (switch on workload_type)
Backend under test: backend/app/routes/export/pricing.py (_get_sku_type)
"""
import pytest
from app.routes.export.pricing import _get_sku_type
from .conftest import make_line_item


# ── JOBS ──────────────────────────────────────────────────────────────

class TestJobsSKU:
    def test_classic(self):
        item = make_line_item(workload_type='JOBS')
        assert _get_sku_type(item, 'aws') == 'JOBS_COMPUTE'

    def test_photon(self):
        item = make_line_item(workload_type='JOBS', photon_enabled=True)
        assert _get_sku_type(item, 'aws') == 'JOBS_COMPUTE_(PHOTON)'

    def test_serverless(self):
        item = make_line_item(workload_type='JOBS', serverless_enabled=True)
        assert _get_sku_type(item, 'aws') == 'JOBS_SERVERLESS_COMPUTE'


# ── ALL_PURPOSE ───────────────────────────────────────────────────────

class TestAllPurposeSKU:
    def test_classic(self):
        item = make_line_item(workload_type='ALL_PURPOSE')
        assert _get_sku_type(item, 'aws') == 'ALL_PURPOSE_COMPUTE'

    def test_photon(self):
        item = make_line_item(workload_type='ALL_PURPOSE', photon_enabled=True)
        assert _get_sku_type(item, 'aws') == 'ALL_PURPOSE_COMPUTE_(PHOTON)'

    def test_serverless(self):
        item = make_line_item(workload_type='ALL_PURPOSE', serverless_enabled=True)
        assert _get_sku_type(item, 'aws') == 'ALL_PURPOSE_SERVERLESS_COMPUTE'


# ── DLT ───────────────────────────────────────────────────────────────

class TestDLTSKU:
    """DLT Serverless MUST return JOBS_SERVERLESS_COMPUTE (Bug 1 fix)."""

    def test_classic_core(self):
        item = make_line_item(workload_type='DLT', dlt_edition='CORE')
        assert _get_sku_type(item, 'aws') == 'DLT_CORE_COMPUTE'

    def test_classic_pro(self):
        item = make_line_item(workload_type='DLT', dlt_edition='PRO')
        assert _get_sku_type(item, 'aws') == 'DLT_PRO_COMPUTE'

    def test_classic_advanced(self):
        item = make_line_item(workload_type='DLT', dlt_edition='ADVANCED')
        assert _get_sku_type(item, 'aws') == 'DLT_ADVANCED_COMPUTE'

    def test_classic_core_photon(self):
        item = make_line_item(workload_type='DLT', dlt_edition='CORE', photon_enabled=True)
        assert _get_sku_type(item, 'aws') == 'DLT_CORE_COMPUTE_(PHOTON)'

    def test_classic_advanced_photon(self):
        item = make_line_item(workload_type='DLT', dlt_edition='ADVANCED', photon_enabled=True)
        assert _get_sku_type(item, 'aws') == 'DLT_ADVANCED_COMPUTE_(PHOTON)'

    def test_serverless_returns_jobs_serverless(self):
        """Bug 1: DLT Serverless must use JOBS_SERVERLESS_COMPUTE, not DELTA_LIVE_TABLES_SERVERLESS."""
        item = make_line_item(workload_type='DLT', serverless_enabled=True)
        assert _get_sku_type(item, 'aws') == 'JOBS_SERVERLESS_COMPUTE'

    def test_serverless_ignores_edition(self):
        """Edition doesn't matter for serverless DLT — always JOBS_SERVERLESS_COMPUTE."""
        for edition in ('CORE', 'PRO', 'ADVANCED'):
            item = make_line_item(workload_type='DLT', serverless_enabled=True, dlt_edition=edition)
            assert _get_sku_type(item, 'aws') == 'JOBS_SERVERLESS_COMPUTE'


# ── DBSQL ─────────────────────────────────────────────────────────────

class TestDBSQLSKU:
    def test_serverless(self):
        item = make_line_item(workload_type='DBSQL', dbsql_warehouse_type='SERVERLESS')
        assert _get_sku_type(item, 'aws') == 'SERVERLESS_SQL_COMPUTE'

    def test_pro(self):
        item = make_line_item(workload_type='DBSQL', dbsql_warehouse_type='PRO')
        assert _get_sku_type(item, 'aws') == 'SQL_PRO_COMPUTE'

    def test_classic(self):
        item = make_line_item(workload_type='DBSQL', dbsql_warehouse_type='CLASSIC')
        assert _get_sku_type(item, 'aws') == 'SQL_COMPUTE'

    def test_default_is_serverless(self):
        item = make_line_item(workload_type='DBSQL')
        assert _get_sku_type(item, 'aws') == 'SERVERLESS_SQL_COMPUTE'


# ── VECTOR_SEARCH ─────────────────────────────────────────────────────

class TestVectorSearchSKU:
    def test_sku(self):
        item = make_line_item(workload_type='VECTOR_SEARCH')
        assert _get_sku_type(item, 'aws') == 'SERVERLESS_REAL_TIME_INFERENCE'


# ── MODEL_SERVING ─────────────────────────────────────────────────────

class TestModelServingSKU:
    def test_sku(self):
        item = make_line_item(workload_type='MODEL_SERVING')
        assert _get_sku_type(item, 'aws') == 'SERVERLESS_REAL_TIME_INFERENCE'


# ── FMAPI_DATABRICKS ─────────────────────────────────────────────────

class TestFMAPIDatabricksSKU:
    def test_default_sku(self):
        """Without matching pricing data, defaults to SERVERLESS_REAL_TIME_INFERENCE."""
        item = make_line_item(
            workload_type='FMAPI_DATABRICKS',
            fmapi_model='databricks-meta-llama-3-1-70b-instruct',
            fmapi_rate_type='input_token',
        )
        sku = _get_sku_type(item, 'aws')
        assert sku == 'SERVERLESS_REAL_TIME_INFERENCE'


# ── FMAPI_PROPRIETARY ────────────────────────────────────────────────

class TestFMAPIProprietarySKU:
    def test_openai(self):
        item = make_line_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='openai',
            fmapi_model='gpt-4o', fmapi_rate_type='input_token',
        )
        assert _get_sku_type(item, 'aws') == 'OPENAI_MODEL_SERVING'

    def test_anthropic(self):
        item = make_line_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='anthropic',
            fmapi_model='claude-sonnet-4', fmapi_rate_type='input_token',
        )
        assert _get_sku_type(item, 'aws') == 'ANTHROPIC_MODEL_SERVING'

    def test_google(self):
        item = make_line_item(
            workload_type='FMAPI_PROPRIETARY', fmapi_provider='google',
            fmapi_model='gemini-1.5-pro', fmapi_rate_type='input_token',
        )
        assert _get_sku_type(item, 'aws') == 'GEMINI_MODEL_SERVING'

    def test_default_provider(self):
        item = make_line_item(
            workload_type='FMAPI_PROPRIETARY',
            fmapi_rate_type='input_token',
        )
        assert _get_sku_type(item, 'aws') == 'OPENAI_MODEL_SERVING'


# ── LAKEBASE ──────────────────────────────────────────────────────────

class TestLakebaseSKU:
    def test_sku(self):
        item = make_line_item(workload_type='LAKEBASE', lakebase_cu=2)
        assert _get_sku_type(item, 'aws') == 'DATABASE_SERVERLESS_COMPUTE'


# ── DATABRICKS_APPS ───────────────────────────────────────────────────

class TestDatabricksAppsSKU:
    def test_sku(self):
        item = make_line_item(workload_type='DATABRICKS_APPS')
        assert _get_sku_type(item, 'aws') == 'ALL_PURPOSE_SERVERLESS_COMPUTE'


# ── DEFAULT / UNKNOWN ─────────────────────────────────────────────────

class TestDefaultSKU:
    def test_empty_workload_type(self):
        item = make_line_item(workload_type='')
        assert _get_sku_type(item, 'aws') == 'JOBS_COMPUTE'

    def test_none_workload_type(self):
        item = make_line_item(workload_type=None)
        assert _get_sku_type(item, 'aws') == 'JOBS_COMPUTE'
