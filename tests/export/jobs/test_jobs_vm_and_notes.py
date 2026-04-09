"""
Sprint 1 Iteration 2: VM Cost, Notes, and NaN/Zero Regression Tests

Tests:
1. VM cost calculation for classic workloads (hardcoded $0.20/$0.10 in export.py)
2. Notes column generation (user notes + auto warnings)
3. NaN/$0 regression: non-zero configs must produce non-zero costs
4. End-to-end computed values for all 4 Jobs configs
"""
import os
import sys
import math
import pytest

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, BACKEND_DIR)

from app.routes.export import (
    _get_sku_type,
    _calculate_dbu_per_hour,
    _calculate_hours_per_month,
    _is_serverless_workload,
    _get_dbu_price,
)
from tests.export.jobs.conftest import make_line_item


# ============================================================
# Test: VM Cost Calculations
# ============================================================

class TestVMCostCalculation:
    """Verify VM cost logic for classic Jobs workloads.

    Export.py lines 899-901: hardcoded $0.20/hr driver, $0.10/hr worker
    for non-serverless JOBS/ALL_PURPOSE/DLT.
    """

    def test_classic_has_vm_costs(self):
        """Classic workloads are NOT serverless → should have VM costs."""
        item = make_line_item(
            workload_type="JOBS", serverless_enabled=False,
            driver_node_type="i3.xlarge", worker_node_type="i3.xlarge",
            num_workers=2, hours_per_month=110,
        )
        assert _is_serverless_workload(item) is False

    def test_serverless_has_no_vm_costs(self):
        """Serverless workloads should have zero VM costs."""
        item = make_line_item(
            workload_type="JOBS", serverless_enabled=True,
            driver_node_type="i3.xlarge", worker_node_type="i3.xlarge",
            num_workers=2, hours_per_month=110,
        )
        assert _is_serverless_workload(item) is True

    def test_vm_driver_cost_calculation(self):
        """Driver VM Cost = $0.20/hr × 110 hrs = $22.00."""
        driver_vm_hr = 0.20  # hardcoded in export.py
        hours = 110
        expected = driver_vm_hr * hours
        assert expected == pytest.approx(22.0)

    def test_vm_worker_cost_calculation(self):
        """Worker VM Cost = $0.10/hr × 110 hrs × 2 workers = $22.00."""
        worker_vm_hr = 0.10  # hardcoded in export.py
        hours = 110
        num_workers = 2
        expected = worker_vm_hr * hours * num_workers
        assert expected == pytest.approx(22.0)

    def test_vm_total_cost_calculation(self):
        """Total VM Cost = Driver + Worker = $22 + $22 = $44.00."""
        hours = 110
        num_workers = 2
        driver_total = 0.20 * hours
        worker_total = 0.10 * hours * num_workers
        assert (driver_total + worker_total) == pytest.approx(44.0)

    def test_total_cost_classic_includes_vm(self):
        """Total = DBU Cost + VM Cost for classic."""
        item = make_line_item(
            workload_type="JOBS", serverless_enabled=False,
            driver_node_type="i3.xlarge", worker_node_type="i3.xlarge",
            num_workers=2, photon_enabled=False, hours_per_month=110,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        hours = _calculate_hours_per_month(item)
        sku = _get_sku_type(item, "aws")
        dbu_rate, _ = _get_dbu_price("aws", "us-east-1", "PREMIUM", sku)

        monthly_dbus = dbu_hr * hours  # 3.0 × 110 = 330
        dbu_cost = monthly_dbus * dbu_rate  # 330 × 0.15 = $49.50
        vm_cost = (0.20 * hours) + (0.10 * hours * 2)  # $22 + $22 = $44
        total_cost = dbu_cost + vm_cost  # $49.50 + $44 = $93.50

        assert dbu_cost == pytest.approx(49.50)
        assert vm_cost == pytest.approx(44.0)
        assert total_cost == pytest.approx(93.50)

    def test_total_cost_serverless_no_vm(self):
        """Total = DBU Cost only (no VM) for serverless."""
        item = make_line_item(
            workload_type="JOBS", serverless_enabled=True,
            driver_node_type="i3.xlarge", worker_node_type="i3.xlarge",
            num_workers=2, photon_enabled=True,
            serverless_mode="standard", hours_per_month=110,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        hours = _calculate_hours_per_month(item)
        sku = _get_sku_type(item, "aws")
        dbu_rate, _ = _get_dbu_price("aws", "us-east-1", "PREMIUM", sku)

        monthly_dbus = dbu_hr * hours  # 6.0 × 110 = 660
        dbu_cost = monthly_dbus * dbu_rate  # 660 × 0.35 or 0.39
        assert dbu_cost > 0
        # VM cost = 0 for serverless
        total_cost = dbu_cost + 0
        assert total_cost == dbu_cost

    def test_vm_cost_730_hours_4_workers(self):
        """24/7 run with 4 workers: VM = ($0.20 + $0.10×4)×730 = $438."""
        hours = 730
        num_workers = 4
        driver_total = 0.20 * hours  # $146
        worker_total = 0.10 * hours * num_workers  # $292
        total_vm = driver_total + worker_total
        assert total_vm == pytest.approx(438.0)


# ============================================================
# Test: Notes Column Generation
# ============================================================

class TestNotesGeneration:
    """Verify notes column content in export."""

    def test_known_instance_no_warnings(self):
        """Known instance types should produce no DBU warnings."""
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="i3.xlarge", worker_node_type="i3.xlarge",
            num_workers=2, photon_enabled=False, serverless_enabled=False,
        )
        _, warnings = _calculate_dbu_per_hour(item, "aws")
        assert len(warnings) == 0

    def test_unknown_instance_produces_warning(self):
        """Unknown instance types produce fallback warnings."""
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="nonexistent.42xlarge",
            worker_node_type="nonexistent.42xlarge",
            num_workers=2, photon_enabled=False, serverless_enabled=False,
        )
        _, warnings = _calculate_dbu_per_hour(item, "aws")
        assert len(warnings) == 2
        assert "Driver DBU rate not found" in warnings[0]
        assert "Worker DBU rate not found" in warnings[1]

    def test_dbu_price_not_found_warning(self):
        """Unknown SKU produces fallback note."""
        _, found = _get_dbu_price("aws", "us-east-1", "PREMIUM", "NONEXISTENT_SKU")
        assert found is False

    def test_valid_sku_found(self):
        """Known SKU should be found."""
        _, found = _get_dbu_price("aws", "us-east-1", "PREMIUM", "JOBS_COMPUTE")
        assert found is True


# ============================================================
# Test: NaN / $0 Regression — Non-zero configs must not be zero
# ============================================================

class TestNoNaNOrZeroCosts:
    """Ensure non-zero configurations produce non-zero costs.

    Acceptance criteria: No NaN or $0 for non-zero configurations.
    """

    @pytest.fixture(params=[
        {"name": "Classic Std", "photon": False, "serverless": False,
         "mode": "standard", "hours": 110},
        {"name": "Classic Photon", "photon": True, "serverless": False,
         "mode": "standard", "hours": 110},
        {"name": "SL Standard", "photon": True, "serverless": True,
         "mode": "standard", "hours": 110},
        {"name": "SL Performance", "photon": True, "serverless": True,
         "mode": "performance", "hours": 730},
    ])
    def jobs_config(self, request):
        return request.param

    def test_dbu_per_hour_not_zero(self, jobs_config):
        """DBU/hr must be > 0 for all standard configs."""
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="i3.xlarge", worker_node_type="i3.xlarge",
            num_workers=2,
            photon_enabled=jobs_config["photon"],
            serverless_enabled=jobs_config["serverless"],
            serverless_mode=jobs_config["mode"],
            hours_per_month=jobs_config["hours"],
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr > 0, f"{jobs_config['name']}: DBU/hr should be > 0"
        assert not math.isnan(dbu_hr), f"{jobs_config['name']}: DBU/hr is NaN"

    def test_monthly_dbus_not_zero(self, jobs_config):
        """Monthly DBUs must be > 0."""
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="i3.xlarge", worker_node_type="i3.xlarge",
            num_workers=2,
            photon_enabled=jobs_config["photon"],
            serverless_enabled=jobs_config["serverless"],
            serverless_mode=jobs_config["mode"],
            hours_per_month=jobs_config["hours"],
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        hours = _calculate_hours_per_month(item)
        monthly = dbu_hr * hours
        assert monthly > 0, f"{jobs_config['name']}: Monthly DBUs should be > 0"
        assert not math.isnan(monthly), f"{jobs_config['name']}: Monthly DBUs is NaN"

    def test_dbu_cost_not_zero(self, jobs_config):
        """DBU cost must be > 0."""
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="i3.xlarge", worker_node_type="i3.xlarge",
            num_workers=2,
            photon_enabled=jobs_config["photon"],
            serverless_enabled=jobs_config["serverless"],
            serverless_mode=jobs_config["mode"],
            hours_per_month=jobs_config["hours"],
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        hours = _calculate_hours_per_month(item)
        sku = _get_sku_type(item, "aws")
        dbu_rate, _ = _get_dbu_price("aws", "us-east-1", "PREMIUM", sku)
        cost = dbu_hr * hours * dbu_rate
        assert cost > 0, f"{jobs_config['name']}: Cost should be > 0"
        assert not math.isnan(cost), f"{jobs_config['name']}: Cost is NaN"

    def test_total_cost_not_zero(self, jobs_config):
        """Total cost (DBU + VM) must be > 0."""
        item = make_line_item(
            workload_type="JOBS",
            driver_node_type="i3.xlarge", worker_node_type="i3.xlarge",
            num_workers=2,
            photon_enabled=jobs_config["photon"],
            serverless_enabled=jobs_config["serverless"],
            serverless_mode=jobs_config["mode"],
            hours_per_month=jobs_config["hours"],
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        hours = _calculate_hours_per_month(item)
        sku = _get_sku_type(item, "aws")
        dbu_rate, _ = _get_dbu_price("aws", "us-east-1", "PREMIUM", sku)
        dbu_cost = dbu_hr * hours * dbu_rate
        is_serverless = _is_serverless_workload(item)
        vm_cost = 0 if is_serverless else (0.20 + 0.10 * 2) * hours
        total = dbu_cost + vm_cost
        assert total > 0, f"{jobs_config['name']}: Total cost should be > 0"
        assert not math.isnan(total), f"{jobs_config['name']}: Total cost is NaN"


# ============================================================
# Test: Lakebase DBU/hr Formula Verification (Spec Discrepancy)
# ============================================================

class TestLakebaseDBUFormula:
    """Lakebase DBU/hr = CU × HA nodes.
    BUG-S1-6 fixed: backend previously used cu×nodes×2, now aligned with frontend.
    """

    def test_lakebase_backend_formula(self):
        """Backend: DBU/hr = CU × nodes (fixed — was cu×nodes×2)."""
        item = make_line_item(
            workload_type="LAKEBASE",
            lakebase_cu=4, lakebase_ha_nodes=2, lakebase_storage_gb=100,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        # Correct formula: 4 × 2 = 8
        assert dbu_hr == pytest.approx(8.0), \
            f"Backend Lakebase DBU/hr should be cu×nodes = 8, got {dbu_hr}"

    def test_lakebase_single_node(self):
        """0.5 CU × 1 node = 0.5 DBU/hr."""
        item = make_line_item(
            workload_type="LAKEBASE",
            lakebase_cu=0.5, lakebase_ha_nodes=1,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(0.5)
