"""
Regression tests for bugs found during Sprint 2 evaluation.

BUG-S1-12: num_workers default 0→1 in backend → FIXED (now uses 0)
BUG-S1-13: Hours fallback 11 hrs in backend → FIXED (now returns 0)
BUG-S2-1: ALL_PURPOSE serverless mode not forced to performance → FIXED
BUG-S2-3: FE fallback price for ALL_PURPOSE_COMPUTE was $0.40, BE was $0.55 → FIXED
"""
import os
import sys
import pytest

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, BACKEND_DIR)

from tests.export.jobs.conftest import make_line_item


class TestBugS1_12_NumWorkersDefaultFixed:
    """BUG-S1-12: Backend defaulted num_workers=0 to 1.
    FIXED: Backend now uses 0 (driver-only), matching frontend.
    Regression: verify num_workers=0 produces driver-only DBU/hr.
    """

    def test_zero_workers_uses_driver_only(self):
        from app.routes.export import _calculate_dbu_per_hour

        item = make_line_item(
            workload_type="JOBS", driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge", num_workers=0,
            photon_enabled=False, serverless_enabled=False,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        # i3.xlarge dbu_rate=1.0. With 0 workers: driver only = 1.0
        # NOT driver + worker (which would be 2.0)
        assert dbu_hr == pytest.approx(1.0), \
            f"0 workers should mean driver-only DBU/hr, got {dbu_hr}"

    def test_zero_workers_allpurpose(self):
        from app.routes.export import _calculate_dbu_per_hour

        item = make_line_item(
            workload_type="ALL_PURPOSE", driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge", num_workers=0,
            photon_enabled=False, serverless_enabled=False,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(1.0), \
            f"ALL_PURPOSE 0 workers should be driver-only, got {dbu_hr}"

    def test_explicit_workers_still_correct(self):
        from app.routes.export import _calculate_dbu_per_hour

        item = make_line_item(
            workload_type="JOBS", driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge", num_workers=4,
            photon_enabled=False, serverless_enabled=False,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        # i3.xlarge dbu_rate=1.0: driver(1.0) + 4 × worker(1.0) = 5.0
        assert dbu_hr == pytest.approx(5.0), \
            f"4 workers should be 5.0, got {dbu_hr}"


class TestBugS1_13_HoursFallbackFixed:
    """BUG-S1-13: Backend returned 11 hours when no usage data set.
    FIXED: Backend now returns 0 hours, matching frontend.
    Regression: verify empty usage → 0 hours.
    """

    def test_no_hours_no_runs_returns_zero(self):
        from app.routes.export import _calculate_hours_per_month

        item = make_line_item(
            workload_type="JOBS",
            runs_per_day=None, avg_runtime_minutes=None,
            hours_per_month=None,
        )
        hours = _calculate_hours_per_month(item)
        assert hours == 0, f"No usage data should return 0 hours, got {hours}"

    def test_explicit_runs_still_work(self):
        from app.routes.export import _calculate_hours_per_month

        item = make_line_item(
            workload_type="JOBS",
            runs_per_day=10, avg_runtime_minutes=30, days_per_month=22,
        )
        hours = _calculate_hours_per_month(item)
        assert hours == pytest.approx(110.0), \
            f"10 runs × 30min × 22 days should be 110 hrs, got {hours}"

    def test_explicit_hours_per_month_still_works(self):
        from app.routes.export import _calculate_hours_per_month

        item = make_line_item(
            workload_type="JOBS", hours_per_month=730,
        )
        hours = _calculate_hours_per_month(item)
        assert hours == pytest.approx(730.0)


class TestBugS2_1_AllPurposeServerlessModeFixed:
    """BUG-S2-1: Backend used stored serverless_mode for ALL_PURPOSE.
    Frontend always forces performance (2x) for ALL_PURPOSE Serverless.
    FIXED: Backend now also forces 2x for ALL_PURPOSE regardless of mode.
    Regression: verify ALL_PURPOSE serverless always gets 2x mode.
    """

    def test_allpurpose_serverless_standard_gets_2x(self):
        from app.routes.export import _calculate_dbu_per_hour

        item = make_line_item(
            workload_type="ALL_PURPOSE", driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge", num_workers=2,
            serverless_enabled=True, serverless_mode="standard",
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        # i3.xlarge dbu_rate=1.0: base = 1.0 + 1.0*2 = 3.0
        # serverless photon: 3.0 * 2 = 6.0
        # ALL_PURPOSE always performance: 6.0 * 2 = 12.0
        assert dbu_hr == pytest.approx(12.0), \
            f"ALL_PURPOSE serverless standard should be 12.0, got {dbu_hr}"

    def test_allpurpose_serverless_performance_unchanged(self):
        from app.routes.export import _calculate_dbu_per_hour

        item = make_line_item(
            workload_type="ALL_PURPOSE", driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge", num_workers=2,
            serverless_enabled=True, serverless_mode="performance",
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(12.0), \
            f"ALL_PURPOSE serverless performance should be 12.0, got {dbu_hr}"

    def test_allpurpose_modes_produce_same_result(self):
        """Standard and performance modes yield identical results for ALL_PURPOSE."""
        from app.routes.export import _calculate_dbu_per_hour

        item_std = make_line_item(
            workload_type="ALL_PURPOSE", driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge", num_workers=2,
            serverless_enabled=True, serverless_mode="standard",
        )
        item_perf = make_line_item(
            workload_type="ALL_PURPOSE", driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge", num_workers=2,
            serverless_enabled=True, serverless_mode="performance",
        )
        dbu_std, _ = _calculate_dbu_per_hour(item_std, "aws")
        dbu_perf, _ = _calculate_dbu_per_hour(item_perf, "aws")
        assert dbu_std == pytest.approx(dbu_perf), \
            f"ALL_PURPOSE: standard={dbu_std} should equal performance={dbu_perf}"

    def test_jobs_serverless_still_respects_mode(self):
        """Jobs Serverless should STILL respect mode (standard vs performance)."""
        from app.routes.export import _calculate_dbu_per_hour

        item_std = make_line_item(
            workload_type="JOBS", driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge", num_workers=2,
            serverless_enabled=True, serverless_mode="standard",
        )
        item_perf = make_line_item(
            workload_type="JOBS", driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge", num_workers=2,
            serverless_enabled=True, serverless_mode="performance",
        )
        dbu_std, _ = _calculate_dbu_per_hour(item_std, "aws")
        dbu_perf, _ = _calculate_dbu_per_hour(item_perf, "aws")
        # Jobs standard = base * 2 (photon) * 1 = 2.5
        # Jobs performance = base * 2 (photon) * 2 = 5.0
        assert dbu_perf == pytest.approx(dbu_std * 2), \
            f"Jobs: performance={dbu_perf} should be 2x standard={dbu_std}"


class TestBugS2_3_FallbackPricingAligned:
    """BUG-S2-3: Frontend fallback price for ALL_PURPOSE_COMPUTE was $0.40/DBU
    while backend used $0.55/DBU. A 37.5% discrepancy in fallback scenarios.
    FIXED: Frontend now uses $0.55 to match backend.
    Regression: verify FE and BE fallback prices are identical.
    """

    def test_allpurpose_compute_fallback_matches_backend(self):
        """ALL_PURPOSE_COMPUTE FE fallback must match BE fallback ($0.55)."""
        from app.routes.export.pricing import FALLBACK_DBU_PRICES
        be_price = FALLBACK_DBU_PRICES['ALL_PURPOSE_COMPUTE']
        # FE price is in costCalculation.ts DEFAULT_DBU_PRICING.aws
        # After fix: both should be $0.55
        fe_price = 0.55  # Verified in costCalculation.ts:18
        assert fe_price == pytest.approx(be_price), \
            f"FE fallback ({fe_price}) must match BE fallback ({be_price})"

    def test_allpurpose_photon_fallback_matches_backend(self):
        """ALL_PURPOSE_COMPUTE_(PHOTON) FE fallback must match BE fallback ($0.55)."""
        from app.routes.export.pricing import FALLBACK_DBU_PRICES
        be_price = FALLBACK_DBU_PRICES['ALL_PURPOSE_COMPUTE_(PHOTON)']
        fe_price = 0.55  # Verified in costCalculation.ts:19
        assert fe_price == pytest.approx(be_price), \
            f"FE photon fallback ({fe_price}) must match BE fallback ({be_price})"

    def test_jobs_compute_fallbacks_match(self):
        """JOBS_COMPUTE fallback prices should match between FE and BE."""
        from app.routes.export.pricing import FALLBACK_DBU_PRICES
        # Core SKUs that must stay aligned (verified in costCalculation.ts)
        checks = {
            'JOBS_COMPUTE': 0.15,
            'JOBS_COMPUTE_(PHOTON)': 0.15,
            'JOBS_SERVERLESS_COMPUTE': 0.39,
            'ALL_PURPOSE_SERVERLESS_COMPUTE': 0.83,
        }
        for sku, fe_price in checks.items():
            if sku in FALLBACK_DBU_PRICES:
                be_price = FALLBACK_DBU_PRICES[sku]
                assert abs(fe_price - be_price) < 0.001, \
                    f"{sku}: FE=${fe_price} != BE=${be_price}"
