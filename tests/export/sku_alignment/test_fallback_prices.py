"""Test that backend FALLBACK_DBU_PRICES match frontend DEFAULT_DBU_PRICING.

Frontend reference: frontend/src/utils/costCalculation.ts (DEFAULT_DBU_PRICING.aws)
Backend under test: backend/app/routes/export/pricing.py (FALLBACK_DBU_PRICES)
"""
import pytest
from app.routes.export.pricing import FALLBACK_DBU_PRICES


# Frontend DEFAULT_DBU_PRICING.aws from costCalculation.ts
FRONTEND_FALLBACK_RATES = {
    'JOBS_COMPUTE': 0.15,
    'JOBS_COMPUTE_(PHOTON)': 0.15,
    'JOBS_SERVERLESS_COMPUTE': 0.39,
    'ALL_PURPOSE_COMPUTE': 0.55,
    'ALL_PURPOSE_COMPUTE_(PHOTON)': 0.55,
    'ALL_PURPOSE_SERVERLESS_COMPUTE': 0.83,
    'DLT_CORE_COMPUTE': 0.20,
    'DLT_CORE_COMPUTE_(PHOTON)': 0.20,
    'DLT_PRO_COMPUTE': 0.25,
    'DLT_PRO_COMPUTE_(PHOTON)': 0.25,
    'DLT_ADVANCED_COMPUTE': 0.36,
    'DLT_ADVANCED_COMPUTE_(PHOTON)': 0.36,
    'DELTA_LIVE_TABLES_SERVERLESS': 0.30,
    'SQL_COMPUTE': 0.22,
    'SQL_PRO_COMPUTE': 0.55,
    'SERVERLESS_SQL_COMPUTE': 0.70,
    'SERVERLESS_REAL_TIME_INFERENCE': 0.07,
    'OPENAI_MODEL_SERVING': 0.07,
    'ANTHROPIC_MODEL_SERVING': 0.07,
    'GOOGLE_MODEL_SERVING': 0.07,
    'DATABASE_SERVERLESS_COMPUTE': 0.48,
}


class TestFallbackPriceAlignment:
    """Every shared SKU must have the same $/DBU in backend and frontend."""

    @pytest.mark.parametrize("sku,expected_price", list(FRONTEND_FALLBACK_RATES.items()))
    def test_backend_matches_frontend(self, sku, expected_price):
        backend_price = FALLBACK_DBU_PRICES.get(sku)
        assert backend_price is not None, (
            f"Backend FALLBACK_DBU_PRICES missing SKU '{sku}' (frontend has it at ${expected_price})"
        )
        assert backend_price == pytest.approx(expected_price, abs=0.001), (
            f"Price mismatch for '{sku}': backend=${backend_price}, frontend=${expected_price}"
        )


class TestRemovedEntries:
    """SKUs that should NOT be in the backend fallback."""

    def test_vector_search_endpoint_removed(self):
        """VECTOR_SEARCH_ENDPOINT was unused by frontend and should be removed."""
        assert 'VECTOR_SEARCH_ENDPOINT' not in FALLBACK_DBU_PRICES


class TestDLTServerlessFallbackRate:
    """Bug 1 + Bug 6: DLT Serverless now resolves to JOBS_SERVERLESS_COMPUTE,
    but the DELTA_LIVE_TABLES_SERVERLESS entry should still be $0.30 (not $0.50)
    in case any other code path references it."""

    def test_delta_live_tables_serverless_rate(self):
        assert FALLBACK_DBU_PRICES['DELTA_LIVE_TABLES_SERVERLESS'] == pytest.approx(0.30)

    def test_jobs_serverless_compute_rate(self):
        assert FALLBACK_DBU_PRICES['JOBS_SERVERLESS_COMPUTE'] == pytest.approx(0.39)


class TestLakebaseFallbackRate:
    """Bug 6: DATABASE_SERVERLESS_COMPUTE was $0.40, frontend has $0.48."""

    def test_database_serverless_compute_rate(self):
        assert FALLBACK_DBU_PRICES['DATABASE_SERVERLESS_COMPUTE'] == pytest.approx(0.48)
