"""
Sprint 3: DLT Export — SKU Type & DBU Price Tests

Split from test_dlt_export.py (BUG-S3-E3-1).
Tests _get_sku_type and _get_dbu_price for DLT workloads.
"""
import os
import sys
import pytest

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, BACKEND_DIR)

from tests.export.dlt.conftest import make_line_item

from app.routes.export import (
    _get_sku_type,
    _get_dbu_price,
    FALLBACK_DBU_PRICES,
)


# ============================================================
# Test: SKU Type Determination
# ============================================================

class TestDLTGetSkuType:
    """Verify _get_sku_type returns correct SKU for DLT variants."""

    def test_core_classic(self):
        item = make_line_item(dlt_edition="CORE", serverless_enabled=False)
        assert _get_sku_type(item, "aws") == "DLT_CORE_COMPUTE"

    def test_pro_classic(self):
        item = make_line_item(dlt_edition="PRO", serverless_enabled=False)
        assert _get_sku_type(item, "aws") == "DLT_PRO_COMPUTE"

    def test_advanced_classic(self):
        item = make_line_item(dlt_edition="ADVANCED", serverless_enabled=False)
        assert _get_sku_type(item, "aws") == "DLT_ADVANCED_COMPUTE"

    def test_core_classic_lowercase(self):
        """Edition stored as lowercase 'core' should still resolve."""
        item = make_line_item(dlt_edition="core", serverless_enabled=False)
        assert _get_sku_type(item, "aws") == "DLT_CORE_COMPUTE"

    def test_serverless(self):
        """DLT Serverless -> JOBS_SERVERLESS_COMPUTE (matches frontend)."""
        item = make_line_item(
            dlt_edition="CORE", serverless_enabled=True,
        )
        assert _get_sku_type(item, "aws") == "JOBS_SERVERLESS_COMPUTE"

    def test_serverless_ignores_edition(self):
        """Serverless SKU is the same regardless of DLT edition."""
        for edition in ["CORE", "PRO", "ADVANCED"]:
            item = make_line_item(
                dlt_edition=edition, serverless_enabled=True,
            )
            assert _get_sku_type(item, "aws") == "JOBS_SERVERLESS_COMPUTE"

    def test_classic_photon_has_suffix(self):
        """DLT Classic Photon appends _(PHOTON) to match frontend."""
        item = make_line_item(
            dlt_edition="CORE", photon_enabled=True,
            serverless_enabled=False,
        )
        sku = _get_sku_type(item, "aws")
        assert sku == "DLT_CORE_COMPUTE_(PHOTON)"

    def test_advanced_photon_has_suffix(self):
        """DLT Advanced Photon: DLT_ADVANCED_COMPUTE_(PHOTON)."""
        item = make_line_item(
            dlt_edition="ADVANCED", photon_enabled=True,
            serverless_enabled=False,
        )
        assert _get_sku_type(item, "aws") == "DLT_ADVANCED_COMPUTE_(PHOTON)"

    def test_none_edition_defaults_to_core(self):
        """When dlt_edition is None, backend defaults to CORE."""
        item = make_line_item(dlt_edition=None, serverless_enabled=False)
        assert _get_sku_type(item, "aws") == "DLT_CORE_COMPUTE"


# ============================================================
# Test: DBU Price Lookup
# ============================================================

class TestDLTDBUPrice:
    """Verify DBU $/DBU rate lookup for DLT SKUs."""

    def test_core_has_price(self):
        price, found = _get_dbu_price("aws", "us-east-1", "PREMIUM", "DLT_CORE_COMPUTE")
        assert price > 0

    def test_pro_has_price(self):
        price, found = _get_dbu_price("aws", "us-east-1", "PREMIUM", "DLT_PRO_COMPUTE")
        assert price > 0

    def test_advanced_has_price(self):
        price, found = _get_dbu_price("aws", "us-east-1", "PREMIUM", "DLT_ADVANCED_COMPUTE")
        assert price > 0

    def test_serverless_has_price(self):
        """DELTA_LIVE_TABLES_SERVERLESS should have a price (even if fallback)."""
        price, found = _get_dbu_price("aws", "us-east-1", "PREMIUM", "DELTA_LIVE_TABLES_SERVERLESS")
        assert price > 0

    def test_core_cheapest_advanced_most_expensive(self):
        """Core < Pro < Advanced pricing."""
        core_price, _ = _get_dbu_price("aws", "us-east-1", "PREMIUM", "DLT_CORE_COMPUTE")
        pro_price, _ = _get_dbu_price("aws", "us-east-1", "PREMIUM", "DLT_PRO_COMPUTE")
        advanced_price, _ = _get_dbu_price("aws", "us-east-1", "PREMIUM", "DLT_ADVANCED_COMPUTE")
        assert core_price < pro_price < advanced_price

    def test_fallback_prices_exist(self):
        """All DLT SKUs have fallback prices."""
        assert "DLT_CORE_COMPUTE" in FALLBACK_DBU_PRICES
        assert "DLT_PRO_COMPUTE" in FALLBACK_DBU_PRICES
        assert "DLT_ADVANCED_COMPUTE" in FALLBACK_DBU_PRICES
        assert "DELTA_LIVE_TABLES_SERVERLESS" in FALLBACK_DBU_PRICES

    def test_photon_sku_pricing(self):
        """Check if DLT_CORE_COMPUTE_(PHOTON) has pricing data."""
        price, found = _get_dbu_price(
            "aws", "us-east-1", "PREMIUM", "DLT_CORE_COMPUTE_(PHOTON)"
        )
        assert price >= 0
