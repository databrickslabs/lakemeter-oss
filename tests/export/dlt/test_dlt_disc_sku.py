"""
Sprint 3: DLT SKU Alignment Tests (Frontend vs Backend)

Tests SKU name alignment/discrepancy between frontend and backend
for all DLT variants. Companion to test_dlt_disc_pricing.py.

DISCREPANCY 1: DLT Classic Photon SKU suffix
  - Frontend: DLT_{EDITION}_COMPUTE_(PHOTON)
  - Backend:  DLT_{EDITION}_COMPUTE (no _(PHOTON) suffix)

DISCREPANCY 2: DLT Serverless SKU
  - Frontend: JOBS_SERVERLESS_COMPUTE
  - Backend:  DELTA_LIVE_TABLES_SERVERLESS
"""
import pytest

from tests.export.dlt.dlt_calc_helpers import frontend_calc_dlt, backend_calc_dlt


class TestDLTClassicSKUAlignment:
    """Classic non-photon SKU matches between FE and BE."""

    @pytest.mark.parametrize("edition", ["CORE", "PRO", "ADVANCED"])
    def test_classic_sku_matches(self, edition):
        """Classic non-photon SKU matches between FE and BE."""
        fe = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=edition,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730,
        )
        be = backend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=edition,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730,
        )
        assert fe["sku"] == be["sku"]


class TestDLTPhotonSKUDiscrepancy:
    """Classic Photon: FE adds _(PHOTON) suffix, BE does not."""

    @pytest.mark.parametrize("edition", ["CORE", "PRO", "ADVANCED"])
    def test_photon_sku_discrepancy(self, edition):
        """
        DISCREPANCY: FE adds _(PHOTON) suffix, BE does not.

        FE: DLT_{EDITION}_COMPUTE_(PHOTON)
        BE: DLT_{EDITION}_COMPUTE
        """
        fe = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=edition,
            photon_enabled=True, serverless_enabled=False,
            hours_per_month=730,
        )
        be = backend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=edition,
            photon_enabled=True, serverless_enabled=False,
            hours_per_month=730,
        )
        assert fe["sku"] != be["sku"], \
            "Expected SKU discrepancy between FE and BE for DLT photon"
        assert fe["sku"] == f"DLT_{edition}_COMPUTE_(PHOTON)"
        assert be["sku"] == f"DLT_{edition}_COMPUTE"


class TestDLTServerlessSKUDiscrepancy:
    """DLT Serverless SKU differs between FE and BE."""

    def test_serverless_sku_discrepancy(self):
        """
        DISCREPANCY: DLT Serverless SKU differs between FE and BE.

        FE: JOBS_SERVERLESS_COMPUTE
        BE: DELTA_LIVE_TABLES_SERVERLESS
        """
        fe = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", serverless_enabled=True,
            hours_per_month=730,
        )
        be = backend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", serverless_enabled=True,
            hours_per_month=730,
        )
        assert fe["sku"] == "JOBS_SERVERLESS_COMPUTE"
        assert be["sku"] == "DELTA_LIVE_TABLES_SERVERLESS"
        assert fe["sku"] != be["sku"], \
            "Expected SKU discrepancy between FE and BE for DLT serverless"


class TestDLTSKUAlignmentMatrix:
    """Full matrix of DLT variant SKU alignment."""

    @pytest.mark.parametrize("edition,photon,serverless,fe_sku,be_sku,aligned", [
        # Classic standard: ALIGNED
        ("CORE", False, False, "DLT_CORE_COMPUTE", "DLT_CORE_COMPUTE", True),
        ("PRO", False, False, "DLT_PRO_COMPUTE", "DLT_PRO_COMPUTE", True),
        ("ADVANCED", False, False, "DLT_ADVANCED_COMPUTE", "DLT_ADVANCED_COMPUTE", True),
        # Classic photon: DISCREPANCY (FE adds _(PHOTON) suffix)
        ("CORE", True, False, "DLT_CORE_COMPUTE_(PHOTON)", "DLT_CORE_COMPUTE", False),
        ("PRO", True, False, "DLT_PRO_COMPUTE_(PHOTON)", "DLT_PRO_COMPUTE", False),
        ("ADVANCED", True, False, "DLT_ADVANCED_COMPUTE_(PHOTON)", "DLT_ADVANCED_COMPUTE", False),
        # Serverless: DISCREPANCY (different SKU entirely)
        ("CORE", False, True, "JOBS_SERVERLESS_COMPUTE", "DELTA_LIVE_TABLES_SERVERLESS", False),
        ("PRO", False, True, "JOBS_SERVERLESS_COMPUTE", "DELTA_LIVE_TABLES_SERVERLESS", False),
        ("ADVANCED", False, True, "JOBS_SERVERLESS_COMPUTE", "DELTA_LIVE_TABLES_SERVERLESS", False),
    ])
    def test_sku_alignment(self, edition, photon, serverless, fe_sku, be_sku, aligned):
        """Comprehensive SKU alignment check for all DLT variants."""
        fe = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=edition,
            photon_enabled=photon, serverless_enabled=serverless,
            hours_per_month=100,
        )
        be = backend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=edition,
            photon_enabled=photon, serverless_enabled=serverless,
            hours_per_month=100,
        )
        assert fe["sku"] == fe_sku
        assert be["sku"] == be_sku
        if aligned:
            assert fe["sku"] == be["sku"]
        else:
            assert fe["sku"] != be["sku"]
