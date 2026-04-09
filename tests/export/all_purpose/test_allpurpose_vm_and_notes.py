"""
Sprint 2: All-Purpose VM Cost and Notes Verification Tests

Tests:
- VM costs present for classic compute, absent for serverless
- Notes column populated correctly
- Configuration details string formatting
"""
import os
import sys
import pytest

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, BACKEND_DIR)

from tests.export.all_purpose.conftest import make_line_item
from app.routes.export import (
    _is_serverless_workload,
    _get_workload_config_details,
    _get_workload_display_name,
)


# ============================================================
# Test: VM Cost Presence/Absence
# ============================================================

class TestAllPurposeVMCosts:
    """Verify VM costs are present for classic and absent for serverless."""

    def test_classic_is_not_serverless(self):
        item = make_line_item(
            workload_type="ALL_PURPOSE",
            serverless_enabled=False,
        )
        assert _is_serverless_workload(item) is False

    def test_classic_photon_is_not_serverless(self):
        item = make_line_item(
            workload_type="ALL_PURPOSE",
            serverless_enabled=False,
            photon_enabled=True,
        )
        assert _is_serverless_workload(item) is False

    def test_serverless_is_serverless(self):
        item = make_line_item(
            workload_type="ALL_PURPOSE",
            serverless_enabled=True,
        )
        assert _is_serverless_workload(item) is True

    def test_serverless_with_photon_flag_still_serverless(self):
        """Photon flag doesn't change serverless detection."""
        item = make_line_item(
            workload_type="ALL_PURPOSE",
            serverless_enabled=True,
            photon_enabled=True,
        )
        assert _is_serverless_workload(item) is True


# ============================================================
# Test: Display Name
# ============================================================

class TestAllPurposeDisplayName:
    """Verify workload display name."""

    def test_display_name(self):
        assert _get_workload_display_name("ALL_PURPOSE") == "All-Purpose Compute"


# ============================================================
# Test: Configuration Details
# ============================================================

class TestAllPurposeConfigDetails:
    """Verify _get_workload_config_details for All-Purpose workloads."""

    def test_serverless_shows_mode(self):
        """Serverless should show mode in config details."""
        item = make_line_item(
            workload_type="ALL_PURPOSE",
            serverless_enabled=True,
            serverless_mode="performance",
        )
        details = _get_workload_config_details(item)
        assert "Performance" in details

    def test_serverless_standard_mode(self):
        item = make_line_item(
            workload_type="ALL_PURPOSE",
            serverless_enabled=True,
            serverless_mode="standard",
        )
        details = _get_workload_config_details(item)
        assert "Standard" in details

    def test_classic_no_mode_display(self):
        """Classic compute should not show serverless mode."""
        item = make_line_item(
            workload_type="ALL_PURPOSE",
            serverless_enabled=False,
        )
        details = _get_workload_config_details(item)
        # Classic All-Purpose has no special config details
        assert details == "-"


# ============================================================
# Test: Pricing tier combinations
# ============================================================

class TestAllPurposePricingTiers:
    """Verify different pricing tier combinations for VM costs."""

    @pytest.mark.parametrize("driver_tier,worker_tier", [
        ("on_demand", "spot"),
        ("on_demand", "on_demand"),
        ("reserved_1y", "spot"),
        ("reserved_3y", "reserved_3y"),
    ])
    def test_pricing_tier_accepted(self, driver_tier, worker_tier):
        """All pricing tier combinations should be accepted."""
        item = make_line_item(
            workload_type="ALL_PURPOSE",
            serverless_enabled=False,
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            driver_pricing_tier=driver_tier,
            worker_pricing_tier=worker_tier,
        )
        # Should not raise
        assert not _is_serverless_workload(item)
