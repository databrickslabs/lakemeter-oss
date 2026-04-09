"""
Sprint 2: All-Purpose Frontend vs Backend Alignment Tests

After iteration 2 fixes, all three discrepancies are now RESOLVED:
1. ALL_PURPOSE Serverless mode: BE now always forces 2x (matching FE)
2. num_workers=0: BE now uses 0 (matching FE)
3. Hours fallback: BE now returns 0 (matching FE)
"""
import pytest
from tests.export.all_purpose.test_allpurpose_calculations import (
    frontend_calc_allpurpose,
    backend_calc_allpurpose,
)


class TestClassicStandardAlignment:
    """Classic standard should match between frontend and backend."""

    def test_fe_be_match_with_workers(self):
        """With explicit workers, FE and BE should agree."""
        fe = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730, dbu_price=0.40,
        )
        be = backend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730, dbu_price=0.40,
        )
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"])
        assert fe["monthly_dbus"] == pytest.approx(be["monthly_dbus"])
        assert fe["sku"] == be["sku"]

    def test_fe_be_match_run_based(self):
        """Run-based hours should match between FE and BE."""
        fe = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=False,
            runs_per_day=5, avg_runtime_minutes=45, days_per_month=20,
        )
        be = backend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=False,
            runs_per_day=5, avg_runtime_minutes=45, days_per_month=20,
        )
        assert fe["hours_per_month"] == pytest.approx(be["hours_per_month"])
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"])


class TestClassicPhotonAlignment:
    """Classic photon should match between FE and BE."""

    def test_fe_be_photon_match(self):
        fe = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=True, serverless_enabled=False,
            hours_per_month=730, dbu_price=0.40,
        )
        be = backend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=True, serverless_enabled=False,
            hours_per_month=730, dbu_price=0.40,
        )
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"])
        assert fe["monthly_dbus"] == pytest.approx(be["monthly_dbus"])
        assert fe["sku"] == be["sku"]


class TestServerlessModeAlignment:
    """
    FIXED: ALL_PURPOSE Serverless multiplier.

    Both frontend and backend now always use performance mode (2x) for ALL_PURPOSE.
    """

    def test_performance_mode_aligned(self):
        """Performance mode: FE and BE both use 2x — should match."""
        fe = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="performance", hours_per_month=730,
        )
        be = backend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="performance", hours_per_month=730,
        )
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"])
        assert fe["dbu_per_hour"] == pytest.approx(20.0)

    def test_standard_mode_now_aligned(self):
        """
        FIXED: When serverless_mode='standard', both FE and BE use 2x for ALL_PURPOSE.
        Previously: FE=20.0, BE=10.0. Now: both=20.0.
        """
        fe = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard", hours_per_month=730,
        )
        be = backend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard", hours_per_month=730,
        )
        assert fe["dbu_per_hour"] == pytest.approx(20.0)
        assert be["dbu_per_hour"] == pytest.approx(20.0)
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"]), \
            "FE and BE should now agree for ALL_PURPOSE serverless standard mode"

    def test_both_modes_produce_same_result(self):
        """Standard and performance mode both yield 20.0 for ALL_PURPOSE serverless."""
        for mode in ("standard", "performance"):
            be = backend_calc_allpurpose(
                driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
                photon_enabled=False, serverless_enabled=True,
                serverless_mode=mode, hours_per_month=730,
            )
            assert be["dbu_per_hour"] == pytest.approx(20.0), \
                f"ALL_PURPOSE serverless {mode} mode should always be 20.0"


class TestNumWorkersAlignment:
    """
    FIXED: num_workers=0 handling now matches between FE and BE.

    Both use 0 workers (driver only) when num_workers=0.
    """

    def test_zero_workers_now_aligned(self):
        """FIXED: Both FE and BE treat 0 workers as driver-only."""
        fe = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730,
        )
        be = backend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730,
        )
        assert fe["dbu_per_hour"] == pytest.approx(1.0), "FE: 0 workers = driver only"
        assert be["dbu_per_hour"] == pytest.approx(1.0), "BE: 0 workers = driver only"
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"])

    def test_explicit_workers_still_match(self):
        """Explicit num_workers should still work correctly."""
        for n in (1, 2, 4, 8):
            fe = frontend_calc_allpurpose(
                driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=n,
                photon_enabled=False, serverless_enabled=False,
                hours_per_month=730,
            )
            be = backend_calc_allpurpose(
                driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=n,
                photon_enabled=False, serverless_enabled=False,
                hours_per_month=730,
            )
            assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"]), \
                f"FE/BE mismatch with {n} workers"


class TestHoursFallbackAlignment:
    """
    FIXED: No hours/runs set now returns 0 in both FE and BE.

    Previously: FE=0, BE=11. Now: both=0.
    """

    def test_no_hours_no_runs_now_aligned(self):
        """FIXED: Both FE and BE return 0 hours when no input."""
        fe = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=False,
        )
        be = backend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=False,
        )
        assert fe["hours_per_month"] == pytest.approx(0)
        assert be["hours_per_month"] == pytest.approx(0)
        assert fe["dbu_cost"] == 0
        assert be["dbu_cost"] == 0

    def test_explicit_hours_still_work(self):
        """Explicit hours_per_month still works correctly."""
        for h in (100, 200, 730):
            fe = frontend_calc_allpurpose(
                driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
                photon_enabled=False, serverless_enabled=False,
                hours_per_month=h,
            )
            be = backend_calc_allpurpose(
                driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
                photon_enabled=False, serverless_enabled=False,
                hours_per_month=h,
            )
            assert fe["hours_per_month"] == pytest.approx(be["hours_per_month"])


class TestSKUAlignment:
    """SKU mapping should be identical between FE and BE for all variants."""

    @pytest.mark.parametrize("photon,serverless,mode,expected_sku", [
        (False, False, "standard", "ALL_PURPOSE_COMPUTE"),
        (True, False, "standard", "ALL_PURPOSE_COMPUTE_(PHOTON)"),
        (False, True, "standard", "ALL_PURPOSE_SERVERLESS_COMPUTE"),
        (False, True, "performance", "ALL_PURPOSE_SERVERLESS_COMPUTE"),
    ])
    def test_sku_matches(self, photon, serverless, mode, expected_sku):
        fe = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=photon, serverless_enabled=serverless,
            serverless_mode=mode, hours_per_month=100,
        )
        be = backend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=photon, serverless_enabled=serverless,
            serverless_mode=mode, hours_per_month=100,
        )
        assert fe["sku"] == expected_sku
        assert be["sku"] == expected_sku
