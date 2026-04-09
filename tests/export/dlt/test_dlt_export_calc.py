"""
Sprint 3: DLT Export — Calculation & Classification Tests

Split from test_dlt_export.py (BUG-S3-E3-1).
Tests _calculate_dbu_per_hour, _calculate_hours_per_month, _is_serverless_workload.
"""
import os
import sys
import pytest

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, BACKEND_DIR)

from tests.export.dlt.conftest import make_line_item

from app.routes.export import (
    _calculate_dbu_per_hour,
    _calculate_hours_per_month,
    _is_serverless_workload,
)


# ============================================================
# Test: DBU Per Hour Calculation
# ============================================================

class TestDLTCalculateDBUPerHour:
    """Verify _calculate_dbu_per_hour for DLT workloads."""

    def test_core_classic_4workers(self):
        """i3.xlarge driver(1.0) + 4x i3.xlarge workers(1.0) = 5.0 DBU/hr."""
        item = make_line_item(
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            dlt_edition="CORE",
            photon_enabled=False,
            serverless_enabled=False,
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(5.0)
        assert len(warnings) == 0

    def test_classic_photon_doubles(self):
        """Photon: (1.0 + 1.0*4) * 2.9 = 14.5 DBU/hr."""
        item = make_line_item(
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            dlt_edition="ADVANCED",
            photon_enabled=True,
            serverless_enabled=False,
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(14.5)

    def test_serverless_standard(self):
        """DLT Serverless standard: (1.0 + 1.0*4) * 2.9 * 1 = 14.5."""
        item = make_line_item(
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            dlt_edition="CORE",
            serverless_enabled=True,
            serverless_mode="standard",
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(14.5)

    def test_serverless_performance(self):
        """DLT Serverless performance: (1.0 + 1.0*4) * 2.9 * 2 = 29.0."""
        item = make_line_item(
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            dlt_edition="CORE",
            serverless_enabled=True,
            serverless_mode="performance",
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(29.0)

    def test_mixed_instance_types(self):
        """m5.xlarge driver(0.69) + 4x r5.xlarge workers(0.9) = 4.29."""
        item = make_line_item(
            driver_node_type="m5.xlarge",
            worker_node_type="r5.xlarge",
            num_workers=4,
            dlt_edition="PRO",
            photon_enabled=False,
            serverless_enabled=False,
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(4.29)

    def test_num_workers_defaults_to_0(self):
        """Backend defaults num_workers=None to 0."""
        item = make_line_item(
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=None,
            dlt_edition="CORE",
            photon_enabled=False,
            serverless_enabled=False,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(1.0)

    def test_unknown_instance_warning(self):
        """Unknown instance type warns and uses fallback."""
        item = make_line_item(
            driver_node_type="nonexistent.type",
            worker_node_type="nonexistent.type",
            num_workers=4,
            dlt_edition="CORE",
        )
        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert len(warnings) == 2
        assert dbu_hr == pytest.approx(2.5)  # 0.5 + 0.5*4 (matching frontend)

    @pytest.mark.parametrize("edition", ["CORE", "PRO", "ADVANCED"])
    def test_dbu_per_hour_same_for_all_editions(self, edition):
        """DBU/hr calculation is the same regardless of edition."""
        item = make_line_item(
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            dlt_edition=edition,
            photon_enabled=False,
            serverless_enabled=False,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(5.0)


# ============================================================
# Test: Hours Calculation
# ============================================================

class TestDLTCalculateHoursPerMonth:
    """Verify _calculate_hours_per_month for DLT workloads."""

    def test_direct_hours(self):
        item = make_line_item(hours_per_month=730)
        assert _calculate_hours_per_month(item) == pytest.approx(730.0)

    def test_run_based(self):
        """24 runs/day * 60 min * 30 days = 720 hours."""
        item = make_line_item(
            runs_per_day=24, avg_runtime_minutes=60, days_per_month=30,
        )
        assert _calculate_hours_per_month(item) == pytest.approx(720.0)

    def test_run_based_priority(self):
        """Run-based takes priority over hours_per_month."""
        item = make_line_item(
            runs_per_day=10, avg_runtime_minutes=30, days_per_month=22,
            hours_per_month=730,
        )
        assert _calculate_hours_per_month(item) == pytest.approx(110.0)

    def test_fallback_zero_hours(self):
        """No data -> 0 hours."""
        item = make_line_item()
        assert _calculate_hours_per_month(item) == pytest.approx(0.0)


# ============================================================
# Test: Serverless Detection
# ============================================================

class TestDLTIsServerless:
    """Verify _is_serverless_workload for DLT variants."""

    def test_classic_not_serverless(self):
        item = make_line_item(serverless_enabled=False)
        assert _is_serverless_workload(item) is False

    def test_serverless_is_serverless(self):
        item = make_line_item(serverless_enabled=True)
        assert _is_serverless_workload(item) is True

    def test_classic_photon_not_serverless(self):
        item = make_line_item(photon_enabled=True, serverless_enabled=False)
        assert _is_serverless_workload(item) is False
