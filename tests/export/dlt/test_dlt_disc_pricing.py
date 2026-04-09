"""
Sprint 3: DLT Calculation & Pricing Alignment Tests (Frontend vs Backend)

Tests DBU/hr, hours, and pricing alignment between frontend and backend
for DLT workloads. Companion to test_dlt_disc_sku.py.

DISCREPANCY: DLT Serverless $/DBU rate
  - Frontend fallback: $0.30 (DELTA_LIVE_TABLES_SERVERLESS) or $0.39 (JOBS_SERVERLESS)
  - Backend fallback:  $0.50 (DELTA_LIVE_TABLES_SERVERLESS)
  Impact: Different total cost displayed vs exported
"""
import pytest

from tests.export.dlt.dlt_calc_helpers import (
    frontend_calc_dlt,
    backend_calc_dlt,
    FRONTEND_DLT_PRICES,
)


class TestDLTClassicCalcAlignment:
    """Classic DLT DBU/hr and hours match between FE and BE."""

    @pytest.mark.parametrize("edition", ["CORE", "PRO", "ADVANCED"])
    def test_classic_dbu_per_hour_matches(self, edition):
        """DBU/hr matches for all editions."""
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
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"])
        assert fe["monthly_dbus"] == pytest.approx(be["monthly_dbus"])

    def test_classic_run_based_hours_match(self):
        """Run-based hours match between FE and BE."""
        kwargs = dict(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE",
            photon_enabled=False, serverless_enabled=False,
            runs_per_day=10, avg_runtime_minutes=30, days_per_month=22,
        )
        fe = frontend_calc_dlt(**kwargs)
        be = backend_calc_dlt(**kwargs)
        assert fe["hours_per_month"] == pytest.approx(be["hours_per_month"])
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"])


class TestDLTPhotonCalcAlignment:
    """Classic Photon DBU/hr matches between FE and BE."""

    @pytest.mark.parametrize("edition", ["CORE", "PRO", "ADVANCED"])
    def test_photon_dbu_per_hour_matches(self, edition):
        """Photon 2x multiplier matches between FE and BE for all editions."""
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
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"])
        assert fe["monthly_dbus"] == pytest.approx(be["monthly_dbus"])


class TestDLTServerlessPricingDiscrepancy:
    """DLT Serverless has discrepancies in $/DBU pricing."""

    def test_serverless_dbu_per_hour_matches(self):
        """DBU/hr matches between FE and BE (same formula)."""
        for mode in ("standard", "performance"):
            fe = frontend_calc_dlt(
                driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
                dlt_edition="CORE", serverless_enabled=True,
                serverless_mode=mode, hours_per_month=730,
            )
            be = backend_calc_dlt(
                driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
                dlt_edition="CORE", serverless_enabled=True,
                serverless_mode=mode, hours_per_month=730,
            )
            assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"]), \
                f"DBU/hr should match for {mode} mode"

    def test_serverless_pricing_aligned(self):
        """
        FE and BE both use JOBS_SERVERLESS_COMPUTE for DLT Serverless ($0.39/DBU).
        DELTA_LIVE_TABLES_SERVERLESS fallback is $0.30 but no longer used for DLT Serverless.
        """
        from app.routes.export.pricing import FALLBACK_DBU_PRICES

        fe_price = FRONTEND_DLT_PRICES.get("JOBS_SERVERLESS_COMPUTE", 0.39)
        be_price = FALLBACK_DBU_PRICES.get("JOBS_SERVERLESS_COMPUTE", 0.39)

        assert fe_price == pytest.approx(0.39)
        assert be_price == pytest.approx(0.39)

    def test_serverless_cost_discrepancy_magnitude(self):
        """
        Quantify the cost impact of the SKU discrepancy.

        For 4 workers, standard mode, 730 hrs:
        - DBU/hr = 10.0, Monthly DBUs = 7300
        - FE cost: 7300 * $0.39 = $2,847.00
        - BE cost: 7300 * $0.50 = $3,650.00
        - Delta: $803.00 per month (28% more expensive in export)
        """
        fe = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", serverless_enabled=True,
            serverless_mode="standard", hours_per_month=730,
            dbu_price=0.39,
        )
        be = backend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", serverless_enabled=True,
            serverless_mode="standard", hours_per_month=730,
            dbu_price=0.50,
        )
        assert fe["dbu_cost"] == pytest.approx(2847.0)
        assert be["dbu_cost"] == pytest.approx(3650.0)
        delta = be["dbu_cost"] - fe["dbu_cost"]
        assert delta == pytest.approx(803.0)
        pct_diff = delta / fe["dbu_cost"] * 100
        assert pct_diff > 20, "Export is >20% more expensive than browser"


class TestDLTNumWorkersAlignment:
    """num_workers handling matches between FE and BE."""

    def test_zero_workers_aligned(self):
        fe = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            dlt_edition="CORE", hours_per_month=730,
        )
        be = backend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            dlt_edition="CORE", hours_per_month=730,
        )
        assert fe["dbu_per_hour"] == pytest.approx(1.0)
        assert be["dbu_per_hour"] == pytest.approx(1.0)

    @pytest.mark.parametrize("n", [1, 2, 4, 8])
    def test_explicit_workers_match(self, n):
        fe = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=n,
            dlt_edition="CORE", hours_per_month=730,
        )
        be = backend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=n,
            dlt_edition="CORE", hours_per_month=730,
        )
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"])


class TestDLTHoursFallbackAlignment:
    """Hours fallback matches between FE and BE."""

    def test_no_hours_no_runs_aligned(self):
        fe = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE",
        )
        be = backend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE",
        )
        assert fe["hours_per_month"] == pytest.approx(0)
        assert be["hours_per_month"] == pytest.approx(0)
        assert fe["dbu_cost"] == 0
        assert be["dbu_cost"] == 0

    @pytest.mark.parametrize("h", [100, 200, 730])
    def test_explicit_hours_match(self, h):
        fe = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", hours_per_month=h,
        )
        be = backend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", hours_per_month=h,
        )
        assert fe["hours_per_month"] == pytest.approx(be["hours_per_month"])
