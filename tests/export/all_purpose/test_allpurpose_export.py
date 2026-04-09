"""
Sprint 2: All-Purpose Excel Export Verification Tests

Tests the backend export helper functions directly for All-Purpose workloads:
- _get_sku_type
- _calculate_dbu_per_hour
- _calculate_hours_per_month
- _is_serverless_workload
"""
import os
import sys
import pytest

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, BACKEND_DIR)

from tests.export.all_purpose.conftest import make_line_item

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

class TestAllPurposeGetSkuType:
    """Verify _get_sku_type returns correct SKU for All-Purpose variants."""

    def test_classic_standard(self):
        item = make_line_item(
            workload_type="ALL_PURPOSE",
            serverless_enabled=False, photon_enabled=False,
        )
        assert _get_sku_type(item, "aws") == "ALL_PURPOSE_COMPUTE"

    def test_classic_photon(self):
        item = make_line_item(
            workload_type="ALL_PURPOSE",
            serverless_enabled=False, photon_enabled=True,
        )
        assert _get_sku_type(item, "aws") == "ALL_PURPOSE_COMPUTE_(PHOTON)"

    def test_serverless(self):
        item = make_line_item(
            workload_type="ALL_PURPOSE",
            serverless_enabled=True,
        )
        assert _get_sku_type(item, "aws") == "ALL_PURPOSE_SERVERLESS_COMPUTE"

    def test_serverless_ignores_photon_flag(self):
        """Serverless SKU doesn't change based on photon flag."""
        item = make_line_item(
            workload_type="ALL_PURPOSE",
            serverless_enabled=True, photon_enabled=True,
        )
        assert _get_sku_type(item, "aws") == "ALL_PURPOSE_SERVERLESS_COMPUTE"


# ============================================================
# Test: DBU Per Hour Calculation
# ============================================================

class TestAllPurposeCalculateDBUPerHour:
    """Verify _calculate_dbu_per_hour for All-Purpose workloads."""

    def test_classic_standard_4workers(self):
        """i3.xlarge driver(1.0) + 4x i3.xlarge workers(1.0) = 5.0 DBU/hr."""
        item = make_line_item(
            workload_type="ALL_PURPOSE",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            photon_enabled=False,
            serverless_enabled=False,
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(5.0)
        assert len(warnings) == 0

    def test_classic_photon_doubles(self):
        """Photon: (1.0 + 1.0*4) * 2 = 10.0 DBU/hr."""
        item = make_line_item(
            workload_type="ALL_PURPOSE",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            photon_enabled=True,
            serverless_enabled=False,
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(10.0)

    def test_serverless_standard_mode(self):
        """
        Serverless standard: ALL_PURPOSE always forces performance (2x).
        FIXED: (1.0 + 1.0*4) * 2 (photon) * 2 (always perf) = 20.0.
        """
        item = make_line_item(
            workload_type="ALL_PURPOSE",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            serverless_enabled=True,
            serverless_mode="standard",
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        # FIXED: ALL_PURPOSE always performance: base(5) * photon(2) * perf(2) = 20
        assert dbu_hr == pytest.approx(20.0)

    def test_serverless_performance_mode(self):
        """Serverless perf: (1.0 + 1.0*4) * 2 (photon) * 2 (perf) = 20.0."""
        item = make_line_item(
            workload_type="ALL_PURPOSE",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            serverless_enabled=True,
            serverless_mode="performance",
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(20.0)

    def test_mixed_instance_types(self):
        """m5.xlarge driver(0.69) + 4x r5.xlarge workers(0.9) = 4.29."""
        item = make_line_item(
            workload_type="ALL_PURPOSE",
            driver_node_type="m5.xlarge",
            worker_node_type="r5.xlarge",
            num_workers=4,
            photon_enabled=False,
            serverless_enabled=False,
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(4.29)

    def test_unknown_instance_type_warning(self):
        """Unknown instance type falls back to defaults and warns."""
        item = make_line_item(
            workload_type="ALL_PURPOSE",
            driver_node_type="nonexistent.type",
            worker_node_type="nonexistent.type",
            num_workers=4,
            photon_enabled=False,
            serverless_enabled=False,
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert len(warnings) == 2  # Both driver and worker not found
        # Fallback: driver=0.5 + worker=0.5*4 = 2.5 (matching frontend)
        assert dbu_hr == pytest.approx(2.5)

    def test_num_workers_defaults_to_0(self):
        """Backend defaults num_workers=None to 0 (FIXED: was 1)."""
        item = make_line_item(
            workload_type="ALL_PURPOSE",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=None,
            photon_enabled=False,
            serverless_enabled=False,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        # FIXED: int(None or 0) = 0, so driver_dbu only. i3.xlarge rate = 1.0
        assert dbu_hr == pytest.approx(1.0)


# ============================================================
# Test: Hours Calculation
# ============================================================

class TestAllPurposeCalculateHoursPerMonth:
    """Verify _calculate_hours_per_month for All-Purpose workloads."""

    def test_direct_hours(self):
        item = make_line_item(hours_per_month=730)
        assert _calculate_hours_per_month(item) == pytest.approx(730.0)

    def test_run_based(self):
        """5 runs/day * 45 min * 20 days = 75 hours."""
        item = make_line_item(
            runs_per_day=5, avg_runtime_minutes=45, days_per_month=20,
        )
        assert _calculate_hours_per_month(item) == pytest.approx(75.0)

    def test_run_based_priority(self):
        """Run-based takes priority over hours_per_month."""
        item = make_line_item(
            runs_per_day=5, avg_runtime_minutes=45, days_per_month=20,
            hours_per_month=730,
        )
        assert _calculate_hours_per_month(item) == pytest.approx(75.0)

    def test_fallback_zero_hours(self):
        """No data -> 0 hours (FIXED: was 11)."""
        item = make_line_item()
        assert _calculate_hours_per_month(item) == pytest.approx(0.0)


# ============================================================
# Test: Serverless Detection
# ============================================================

class TestAllPurposeIsServerless:
    """Verify _is_serverless_workload for All-Purpose variants."""

    def test_classic_not_serverless(self):
        item = make_line_item(
            workload_type="ALL_PURPOSE",
            serverless_enabled=False,
        )
        assert _is_serverless_workload(item) is False

    def test_serverless_is_serverless(self):
        item = make_line_item(
            workload_type="ALL_PURPOSE",
            serverless_enabled=True,
        )
        assert _is_serverless_workload(item) is True


# ============================================================
# Test: DBU Price Lookup
# ============================================================

class TestAllPurposeDBUPrice:
    """Verify DBU $/DBU rate lookup for All-Purpose SKUs."""

    def test_classic_has_price(self):
        price, _ = _get_dbu_price("aws", "us-east-1", "PREMIUM", "ALL_PURPOSE_COMPUTE")
        assert price > 0

    def test_photon_has_price(self):
        price, _ = _get_dbu_price("aws", "us-east-1", "PREMIUM", "ALL_PURPOSE_COMPUTE_(PHOTON)")
        assert price > 0

    def test_serverless_has_price(self):
        price, _ = _get_dbu_price("aws", "us-east-1", "PREMIUM", "ALL_PURPOSE_SERVERLESS_COMPUTE")
        assert price > 0

    def test_serverless_more_expensive_than_classic(self):
        """ALL_PURPOSE_SERVERLESS_COMPUTE should cost more per DBU than classic."""
        classic_price, _ = _get_dbu_price("aws", "us-east-1", "PREMIUM", "ALL_PURPOSE_COMPUTE")
        sl_price, _ = _get_dbu_price("aws", "us-east-1", "PREMIUM", "ALL_PURPOSE_SERVERLESS_COMPUTE")
        assert sl_price > classic_price
