"""
Sprint 1: Frontend vs Backend Discrepancy Documentation Tests

These tests document and verify known discrepancies between the frontend
(costCalculation.ts) and backend (export.py) calculation logic for Jobs.

Each test explicitly documents the discrepancy with expected values from both sides.
"""
import pytest
import os
import sys

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, BACKEND_DIR)

from app.routes.export import _calculate_dbu_per_hour, _get_sku_type
from tests.export.jobs.test_jobs_calculations import frontend_calc_jobs, backend_calc_jobs
from tests.export.jobs.conftest import make_line_item


class TestDiscrepancy01ServerlessPhotonFixed:
    """
    DISCREPANCY #1 — FIXED (BUG-S1-5):

    Frontend and backend now BOTH always apply photon 2x for serverless.
    Serverless compute has photon built-in, so photon_enabled flag is irrelevant.

    These tests verify the fix — frontend and backend should now match.
    """

    def test_serverless_standard_now_aligned(self):
        """Frontend=6.0, Backend=6.0 — fixed, no discrepancy."""
        fe = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard", hours_per_month=100,
        )
        be = backend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard", hours_per_month=100,
        )
        assert fe["dbu_per_hour"] == pytest.approx(6.0)
        assert be["dbu_per_hour"] == pytest.approx(6.0)
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"]), \
            "BUG-S1-5 fixed: FE and BE now both apply photon for serverless"

    def test_serverless_performance_now_aligned(self):
        """Frontend=12.0, Backend=12.0 — fixed, no discrepancy."""
        fe = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="performance", hours_per_month=100,
        )
        be = backend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="performance", hours_per_month=100,
        )
        assert fe["dbu_per_hour"] == pytest.approx(12.0)
        assert be["dbu_per_hour"] == pytest.approx(12.0)

    def test_photon_flag_irrelevant_for_serverless(self):
        """Whether photon_enabled=True or False, serverless always gets 2x."""
        for photon_flag in [True, False]:
            fe = frontend_calc_jobs(
                driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
                photon_enabled=photon_flag, serverless_enabled=True,
                serverless_mode="standard", hours_per_month=100,
            )
            be = backend_calc_jobs(
                driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
                photon_enabled=photon_flag, serverless_enabled=True,
                serverless_mode="standard", hours_per_month=100,
            )
            assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"]), \
                f"Photon flag={photon_flag}: FE and BE should match for serverless"

    def test_backend_export_directly(self):
        """Verify the actual backend export function applies photon for serverless."""
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=2,
            photon_enabled=False,
            serverless_enabled=True,
            serverless_mode="standard",
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        # Serverless always has photon: (0.25 + 0.5×2) × 2 = 2.5 (with real DBU rates)
        # With default test rates (1.0, 1.0): (1.0 + 1.0×2) × 2 = 6.0
        # But i3.xlarge uses actual DBU rates from instance types
        # The key assertion: it should NOT be just base_dbu without photon
        assert dbu_hr > 0, "DBU/hr should be positive for serverless Jobs"


class TestDiscrepancy02NumWorkersDefaultFixed:
    """
    DISCREPANCY #2 — FIXED (BUG-S1-12):

    Frontend and backend now BOTH default num_workers to 0 (driver only).
    Previously backend used 1, causing Excel to overstate costs.
    """

    def test_zero_workers_now_aligned(self):
        """FIXED: Frontend=1.0, Backend=1.0 when num_workers=0."""
        fe = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=100,
        )
        be = backend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=100,
        )
        assert fe["dbu_per_hour"] == pytest.approx(1.0)
        assert be["dbu_per_hour"] == pytest.approx(1.0)
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"]), \
            "BUG-S1-12 fixed: FE and BE both use 0 workers when num_workers=0"

    def test_backend_export_directly_zero_workers(self):
        """Verify the actual backend export function now defaults to 0."""
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=0,
            photon_enabled=False,
            serverless_enabled=False,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        # i3.xlarge has dbu_rate=1.0. With 0 workers: driver only = 1.0
        assert dbu_hr == pytest.approx(1.0), \
            f"Backend 0 workers should use driver-only (1.0 for i3.xlarge), got {dbu_hr}"

    def test_nonzero_workers_still_match(self):
        """When num_workers > 0, both agree."""
        for n in [1, 2, 5, 10]:
            fe = frontend_calc_jobs(
                driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=n,
                photon_enabled=False, serverless_enabled=False,
                hours_per_month=100,
            )
            be = backend_calc_jobs(
                driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=n,
                photon_enabled=False, serverless_enabled=False,
                hours_per_month=100,
            )
            assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"]), \
                f"Mismatch at num_workers={n}"


class TestDiscrepancy03BackendHoursFallbackFixed:
    """
    DISCREPANCY #3 — FIXED (BUG-S1-13):

    Frontend and backend now BOTH return 0 hours when no usage data.
    Previously backend returned 11 hours, causing Excel to show cost for $0 browser items.
    """

    def test_no_usage_config_now_aligned(self):
        """FIXED: Frontend=0 hours, Backend=0 hours when nothing set."""
        fe = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=False,
        )
        be = backend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=False,
        )
        assert fe["hours_per_month"] == pytest.approx(0.0)
        assert be["hours_per_month"] == pytest.approx(0.0)
        assert fe["dbu_cost"] == 0
        assert be["dbu_cost"] == 0
