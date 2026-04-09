"""
Sprint 1: Jobs Excel Export Verification Tests

Tests the backend export helper functions directly:
- _get_sku_type
- _calculate_dbu_per_hour
- _calculate_hours_per_month
- _is_serverless_workload
- Excel formula structure verification
"""
import os
import sys
import pytest

# Import backend export functions
BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, BACKEND_DIR)

from tests.export.jobs.conftest import make_line_item

# Import export functions after path setup
from app.routes.export import (
    _get_sku_type,
    _calculate_dbu_per_hour,
    _calculate_hours_per_month,
    _is_serverless_workload,
    _get_dbu_price,
)


# ============================================================
# Test: SKU Type Determination
# ============================================================

class TestGetSkuType:
    """Verify _get_sku_type returns correct SKU for Jobs variants."""

    def test_jobs_classic_standard(self):
        item = make_line_item(workload_type="JOBS", serverless_enabled=False, photon_enabled=False)
        assert _get_sku_type(item, "aws") == "JOBS_COMPUTE"

    def test_jobs_classic_photon(self):
        item = make_line_item(workload_type="JOBS", serverless_enabled=False, photon_enabled=True)
        assert _get_sku_type(item, "aws") == "JOBS_COMPUTE_(PHOTON)"

    def test_jobs_serverless(self):
        item = make_line_item(workload_type="JOBS", serverless_enabled=True)
        assert _get_sku_type(item, "aws") == "JOBS_SERVERLESS_COMPUTE"

    def test_jobs_serverless_ignores_photon_flag(self):
        """Serverless SKU doesn't change based on photon flag."""
        item = make_line_item(workload_type="JOBS", serverless_enabled=True, photon_enabled=True)
        assert _get_sku_type(item, "aws") == "JOBS_SERVERLESS_COMPUTE"


# ============================================================
# Test: DBU Per Hour Calculation
# ============================================================

class TestCalculateDBUPerHour:
    """Verify _calculate_dbu_per_hour for Jobs workloads."""

    def test_classic_standard_with_instance_types(self):
        """i3.xlarge driver(1.0) + 2× i3.xlarge workers(1.0) = 3.0 DBU/hr."""
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=2,
            photon_enabled=False,
            serverless_enabled=False,
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(3.0)
        assert len(warnings) == 0

    def test_classic_photon_doubles(self):
        """Photon: (1.0 + 1.0×2) × 2.9 = 8.7 DBU/hr."""
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=2,
            photon_enabled=True,
            serverless_enabled=False,
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(8.7)

    def test_serverless_standard_no_photon_flag(self):
        """
        Serverless always has photon built-in (BUG-S1-5 fix).
        Backend: base(3.0) × 2.9 (photon always, from dbu-multipliers.json) × 1 (standard) = 8.7
        """
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=2,
            photon_enabled=False,
            serverless_enabled=True,
            serverless_mode="standard",
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(8.7)

    def test_serverless_standard_with_photon_flag(self):
        """
        Backend: serverless with photon_enabled=True.
        base(3.0) × 2.9 (photon, from dbu-multipliers.json) × 1 (standard) = 8.7
        """
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=2,
            photon_enabled=True,
            serverless_enabled=True,
            serverless_mode="standard",
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(8.7)

    def test_serverless_performance(self):
        """Serverless performance: base(3.0) × 2.9 (photon always) × 2 (performance) = 17.4."""
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=2,
            photon_enabled=False,
            serverless_enabled=True,
            serverless_mode="performance",
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(17.4)

    def test_serverless_performance_with_photon(self):
        """Serverless performance + photon: base(3.0) × 2.9 × 2 = 17.4."""
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=2,
            photon_enabled=True,
            serverless_enabled=True,
            serverless_mode="performance",
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(17.4)

    def test_fallback_dbu_rates_when_no_instance(self):
        """Unknown instance types fall back to driver=0.5, worker=0.5 (matching frontend)."""
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="unknown.type",
            worker_node_type="unknown.type",
            num_workers=2,
            photon_enabled=False,
            serverless_enabled=False,
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        expected = 0.5 + (0.5 * 2)  # 1.5
        assert dbu_hr == pytest.approx(expected)
        assert len(warnings) == 2  # Both driver and worker warnings

    def test_default_num_workers_is_0(self):
        """Backend defaults num_workers to 0 when not set (FIXED: was 1)."""
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=None,  # Not set
            photon_enabled=False,
            serverless_enabled=False,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        # FIXED: int(None or 0) = 0, so driver_dbu only. i3.xlarge rate = 1.0
        assert dbu_hr == pytest.approx(1.0)

    def test_mixed_instance_types(self):
        """m5.xlarge driver(0.69) + 4× i3.2xlarge workers(2.0) = 8.69 DBU/hr."""
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="m5.xlarge",
            worker_node_type="i3.2xlarge",
            num_workers=4,
            photon_enabled=False,
            serverless_enabled=False,
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(8.69)


# ============================================================
# Test: Hours Per Month Calculation
# ============================================================

class TestCalculateHoursPerMonth:
    """Verify _calculate_hours_per_month for Jobs workloads."""

    def test_run_based(self):
        item = make_line_item(runs_per_day=10, avg_runtime_minutes=30, days_per_month=22)
        assert _calculate_hours_per_month(item) == pytest.approx(110.0)

    def test_direct_hours(self):
        item = make_line_item(hours_per_month=730)
        assert _calculate_hours_per_month(item) == pytest.approx(730.0)

    def test_run_based_priority(self):
        """Run-based takes priority over hours_per_month."""
        item = make_line_item(
            runs_per_day=10, avg_runtime_minutes=30, days_per_month=22,
            hours_per_month=730,
        )
        assert _calculate_hours_per_month(item) == pytest.approx(110.0)

    def test_default_days(self):
        """Default days_per_month = 22."""
        item = make_line_item(runs_per_day=1, avg_runtime_minutes=60, days_per_month=None)
        assert _calculate_hours_per_month(item) == pytest.approx(22.0)

    def test_fallback_when_nothing_set(self):
        """Backend returns 0 when nothing set (FIXED: was 11 hours)."""
        item = make_line_item()
        assert _calculate_hours_per_month(item) == pytest.approx(0.0)


# ============================================================
# Test: Serverless Detection
# ============================================================

class TestIsServerlessWorkload:
    """Verify _is_serverless_workload for Jobs workloads."""

    def test_jobs_classic_is_not_serverless(self):
        item = make_line_item(workload_type="JOBS", serverless_enabled=False)
        assert _is_serverless_workload(item) is False

    def test_jobs_serverless_is_serverless(self):
        item = make_line_item(workload_type="JOBS", serverless_enabled=True)
        assert _is_serverless_workload(item) is True


# ============================================================
# Test: DBU Price Lookup
# ============================================================

class TestDBUPriceLookup:
    """Verify _get_dbu_price returns correct $/DBU rates."""

    def test_jobs_compute_us_east_1(self):
        price, found = _get_dbu_price("aws", "us-east-1", "PREMIUM", "JOBS_COMPUTE")
        assert found is True
        assert price == pytest.approx(0.15)

    def test_jobs_compute_photon_us_east_1(self):
        price, found = _get_dbu_price("aws", "us-east-1", "PREMIUM", "JOBS_COMPUTE_(PHOTON)")
        assert found is True
        assert price == pytest.approx(0.15)

    def test_jobs_serverless_compute_us_east_1(self):
        price, found = _get_dbu_price("aws", "us-east-1", "PREMIUM", "JOBS_SERVERLESS_COMPUTE")
        assert found is True
        assert price == pytest.approx(0.35)

    def test_fallback_for_unknown_sku(self):
        price, found = _get_dbu_price("aws", "us-east-1", "PREMIUM", "NONEXISTENT_SKU")
        assert found is False
        assert price == 0  # No fallback for unknown SKU


# ============================================================
# Test: End-to-End Export Row Calculation
# ============================================================

class TestExportRowCalculation:
    """End-to-end: create a mock line item and verify all computed values."""

    def test_jobs_classic_standard_full_calc(self):
        """Full calculation chain for Jobs Classic Standard."""
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=2,
            photon_enabled=False,
            serverless_enabled=False,
            runs_per_day=10,
            avg_runtime_minutes=30,
            days_per_month=22,
        )

        # Step 1: Hours
        hours = _calculate_hours_per_month(item)
        assert hours == pytest.approx(110.0)

        # Step 2: DBU/hr
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(3.0)

        # Step 3: Monthly DBUs
        monthly_dbus = dbu_hr * hours
        assert monthly_dbus == pytest.approx(330.0)

        # Step 4: DBU price
        sku = _get_sku_type(item, "aws")
        assert sku == "JOBS_COMPUTE"
        dbu_price, found = _get_dbu_price("aws", "us-east-1", "PREMIUM", sku)
        assert dbu_price == pytest.approx(0.15)

        # Step 5: DBU cost
        dbu_cost = monthly_dbus * dbu_price
        assert dbu_cost == pytest.approx(49.50)

        # Step 6: No VM for this test (would need VM price lookup)
        assert _is_serverless_workload(item) is False

    def test_jobs_serverless_performance_full_calc(self):
        """Full calculation chain for Jobs Serverless Performance."""
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=2,
            photon_enabled=True,  # Set photon for backend to match frontend
            serverless_enabled=True,
            serverless_mode="performance",
            hours_per_month=730,
        )

        hours = _calculate_hours_per_month(item)
        assert hours == pytest.approx(730.0)

        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        # base(3.0) × photon(2.9) × performance(2) = 17.4
        assert dbu_hr == pytest.approx(17.4)

        monthly_dbus = dbu_hr * hours
        assert monthly_dbus == pytest.approx(12702.0)

        sku = _get_sku_type(item, "aws")
        assert sku == "JOBS_SERVERLESS_COMPUTE"

        dbu_price, _ = _get_dbu_price("aws", "us-east-1", "PREMIUM", sku)
        assert dbu_price == pytest.approx(0.35)

        dbu_cost = monthly_dbus * dbu_price
        assert dbu_cost == pytest.approx(4445.7)

        assert _is_serverless_workload(item) is True

    def test_jobs_classic_photon_full_calc(self):
        """Full calculation chain for Jobs Classic Photon."""
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=2,
            photon_enabled=True,
            serverless_enabled=False,
            hours_per_month=110,
        )

        hours = _calculate_hours_per_month(item)
        assert hours == pytest.approx(110.0)

        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(8.7)  # 3.0 × 2.9

        monthly_dbus = dbu_hr * hours
        assert monthly_dbus == pytest.approx(957.0)

        sku = _get_sku_type(item, "aws")
        assert sku == "JOBS_COMPUTE_(PHOTON)"

        dbu_price, _ = _get_dbu_price("aws", "us-east-1", "PREMIUM", sku)
        dbu_cost = monthly_dbus * dbu_price
        assert dbu_cost == pytest.approx(143.55)  # 957 × $0.15
