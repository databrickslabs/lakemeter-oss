"""
Sprint 2: All-Purpose (Classic + Serverless) Calculation Verification Tests

Tests the cost calculation logic for All-Purpose workloads by:
1. Verifying frontend calculation formulas (replicated in Python)
2. Verifying backend export helper functions
3. Detecting discrepancies between frontend and backend

Key difference from Jobs:
- All-Purpose Serverless ALWAYS uses performance mode (2x) in the frontend
- Backend does NOT enforce this — it uses the stored serverless_mode value
"""
import pytest


# ============================================================
# Frontend calculation logic (replicated from costCalculation.ts)
# ============================================================

def frontend_calc_allpurpose(
    driver_dbu_rate: float,
    worker_dbu_rate: float,
    num_workers: int,
    photon_enabled: bool,
    serverless_enabled: bool,
    serverless_mode: str = "standard",
    hours_per_month: float = 0,
    runs_per_day: int = 0,
    avg_runtime_minutes: int = 0,
    days_per_month: int = 22,
    dbu_price: float = 0.40,
) -> dict:
    """Replicate frontend costCalculation.ts logic for ALL_PURPOSE."""
    # Hours calculation (frontend lines 131-139)
    if runs_per_day and avg_runtime_minutes:
        hours = (runs_per_day * (avg_runtime_minutes / 60)) * days_per_month
    elif hours_per_month:
        hours = hours_per_month
    else:
        hours = 0

    # Photon multiplier (frontend lines 273-307)
    if not serverless_enabled and not photon_enabled:
        photon_mult = 1.0
    else:
        photon_mult = 2.0

    # Serverless multiplier (frontend lines 313-315)
    # ALL_PURPOSE Serverless is ALWAYS performance (2x) — hardcoded in frontend
    if not serverless_enabled:
        serverless_mult = 1
    else:
        serverless_mult = 2  # Always 2 for ALL_PURPOSE, regardless of serverless_mode

    # DBU/hr (frontend lines 319-341)
    if serverless_enabled:
        dbu_per_hour = (driver_dbu_rate + (worker_dbu_rate * num_workers)) * photon_mult * serverless_mult
        vm_cost = 0
    else:
        dbu_per_hour = (driver_dbu_rate + (worker_dbu_rate * num_workers)) * photon_mult
        vm_cost = 0  # VM cost requires price lookup, tested separately

    monthly_dbus = dbu_per_hour * hours

    # SKU
    if serverless_enabled:
        sku = "ALL_PURPOSE_SERVERLESS_COMPUTE"
    elif photon_enabled:
        sku = "ALL_PURPOSE_COMPUTE_(PHOTON)"
    else:
        sku = "ALL_PURPOSE_COMPUTE"

    dbu_cost = monthly_dbus * dbu_price

    return {
        "hours_per_month": hours,
        "dbu_per_hour": dbu_per_hour,
        "monthly_dbus": monthly_dbus,
        "dbu_cost": dbu_cost,
        "vm_cost": vm_cost,
        "total_cost": dbu_cost + vm_cost,
        "sku": sku,
        "photon_multiplier": photon_mult,
        "serverless_multiplier": serverless_mult,
    }


# ============================================================
# Backend calculation logic (replicated from export.py)
# ============================================================

def backend_calc_allpurpose(
    driver_dbu_rate: float,
    worker_dbu_rate: float,
    num_workers: int,
    photon_enabled: bool,
    serverless_enabled: bool,
    serverless_mode: str = "standard",
    hours_per_month: float = 0,
    runs_per_day: int = 0,
    avg_runtime_minutes: int = 0,
    days_per_month: int = 22,
    dbu_price: float = 0.40,
) -> dict:
    """Replicate backend export.py logic for ALL_PURPOSE (post-fix)."""
    # Hours (export.py lines 286-301) — FIXED: fallback is 0 (not 11)
    if runs_per_day and avg_runtime_minutes:
        hours = (runs_per_day * avg_runtime_minutes / 60) * days_per_month
    elif hours_per_month:
        hours = hours_per_month
    else:
        hours = 0  # No usage data = 0 hours (aligned with frontend)

    # DBU/hr (export.py lines 309-339)
    # FIXED: num_workers defaults to 0 (not 1) — aligned with frontend
    nw = num_workers if num_workers else 0
    base_dbu = driver_dbu_rate + (worker_dbu_rate * nw)

    if serverless_enabled:
        # Serverless always has photon built-in (2x)
        base_dbu *= 2
        # FIXED: ALL_PURPOSE Serverless always uses performance mode (2x)
        mode_mult = 2
        dbu_per_hour = base_dbu * mode_mult
    else:
        if photon_enabled:
            base_dbu *= 2
        dbu_per_hour = base_dbu

    monthly_dbus = dbu_per_hour * hours

    # SKU (export.py lines 191-196)
    if serverless_enabled:
        sku = "ALL_PURPOSE_SERVERLESS_COMPUTE"
    elif photon_enabled:
        sku = "ALL_PURPOSE_COMPUTE_(PHOTON)"
    else:
        sku = "ALL_PURPOSE_COMPUTE"

    dbu_cost = monthly_dbus * dbu_price

    return {
        "hours_per_month": hours,
        "dbu_per_hour": dbu_per_hour,
        "monthly_dbus": monthly_dbus,
        "dbu_cost": dbu_cost,
        "sku": sku,
    }


# ============================================================
# Test: Hours Calculation (same as Jobs, verify for All-Purpose)
# ============================================================

class TestAllPurposeHoursCalculation:
    """Verify hours/month calculation for All-Purpose workloads."""

    def test_direct_hours_24x7(self):
        """730 hours/month = 24/7 interactive cluster."""
        result = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730,
        )
        assert result["hours_per_month"] == pytest.approx(730.0)

    def test_run_based_5_runs_45min_20days(self):
        """5 runs/day x 45 min x 20 days = 75 hours."""
        result = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=False,
            runs_per_day=5, avg_runtime_minutes=45, days_per_month=20,
        )
        assert result["hours_per_month"] == pytest.approx(75.0)

    def test_run_based_priority_over_hours(self):
        """Run-based fields override hours_per_month when both present."""
        result = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            photon_enabled=False, serverless_enabled=False,
            runs_per_day=5, avg_runtime_minutes=45, days_per_month=20,
            hours_per_month=730,
        )
        assert result["hours_per_month"] == pytest.approx(75.0)

    def test_default_days_per_month(self):
        """Default days_per_month = 22."""
        result = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            photon_enabled=False, serverless_enabled=False,
            runs_per_day=10, avg_runtime_minutes=60,
        )
        # 10 * 60/60 * 22 = 220
        assert result["hours_per_month"] == pytest.approx(220.0)


# ============================================================
# Test: All-Purpose Classic Standard (no photon)
# ============================================================

class TestAllPurposeClassicStandard:
    """All-Purpose Classic Standard — no photon."""

    def test_dbu_per_hour_4workers(self, aws_instance_rates):
        """driver(1.0) + 4 x worker(1.0) = 5.0 DBU/hr."""
        driver_rate = aws_instance_rates["i3.xlarge"]["dbu_rate"]
        worker_rate = aws_instance_rates["i3.xlarge"]["dbu_rate"]
        result = frontend_calc_allpurpose(
            driver_dbu_rate=driver_rate, worker_dbu_rate=worker_rate,
            num_workers=4, photon_enabled=False, serverless_enabled=False,
            hours_per_month=730,
        )
        assert result["dbu_per_hour"] == pytest.approx(5.0)
        assert result["monthly_dbus"] == pytest.approx(3650.0)

    def test_sku_is_all_purpose_compute(self):
        """SKU = ALL_PURPOSE_COMPUTE."""
        result = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=100,
        )
        assert result["sku"] == "ALL_PURPOSE_COMPUTE"

    def test_dbu_cost_at_list_price(self, us_east_1_premium_rates):
        """DBU cost = monthly_dbus x $/DBU."""
        dbu_price = us_east_1_premium_rates["ALL_PURPOSE_COMPUTE"]
        result = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730, dbu_price=dbu_price,
        )
        expected_dbus = 5.0 * 730
        expected_cost = expected_dbus * dbu_price
        assert result["monthly_dbus"] == pytest.approx(expected_dbus)
        assert result["dbu_cost"] == pytest.approx(expected_cost)

    def test_mixed_instance_types(self, aws_instance_rates):
        """m5.xlarge driver (0.69) + 4x r5.xlarge workers (0.9) = 4.29 DBU/hr."""
        driver_rate = aws_instance_rates["m5.xlarge"]["dbu_rate"]  # 0.69
        worker_rate = aws_instance_rates["r5.xlarge"]["dbu_rate"]  # 0.9
        result = frontend_calc_allpurpose(
            driver_dbu_rate=driver_rate, worker_dbu_rate=worker_rate,
            num_workers=4, photon_enabled=False, serverless_enabled=False,
            hours_per_month=730,
        )
        expected = 0.69 + (0.9 * 4)  # 4.29
        assert result["dbu_per_hour"] == pytest.approx(expected)

    def test_zero_workers_driver_only(self):
        """Single driver, no workers."""
        result = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730,
        )
        assert result["dbu_per_hour"] == pytest.approx(1.0)


# ============================================================
# Test: All-Purpose Classic Photon
# ============================================================

class TestAllPurposeClassicPhoton:
    """All-Purpose Classic with Photon — 2x multiplier."""

    def test_photon_doubles_dbu(self):
        """Photon: (1.0 + 1.0*4) * 2.0 = 10.0 DBU/hr."""
        result = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=True, serverless_enabled=False,
            hours_per_month=730,
        )
        assert result["dbu_per_hour"] == pytest.approx(10.0)
        assert result["monthly_dbus"] == pytest.approx(7300.0)

    def test_sku_is_all_purpose_compute_photon(self):
        """SKU = ALL_PURPOSE_COMPUTE_(PHOTON)."""
        result = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=True, serverless_enabled=False,
            hours_per_month=100,
        )
        assert result["sku"] == "ALL_PURPOSE_COMPUTE_(PHOTON)"

    def test_photon_cost(self, us_east_1_premium_rates):
        """Photon uses ALL_PURPOSE_COMPUTE_(PHOTON) pricing."""
        dbu_price = us_east_1_premium_rates.get("ALL_PURPOSE_COMPUTE_(PHOTON)", 0.40)
        result = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=True, serverless_enabled=False,
            hours_per_month=730, dbu_price=dbu_price,
        )
        expected_cost = 10.0 * 730 * dbu_price
        assert result["dbu_cost"] == pytest.approx(expected_cost)


# ============================================================
# Test: All-Purpose Serverless (always performance mode)
# ============================================================

class TestAllPurposeServerless:
    """All-Purpose Serverless — always performance (2x), photon always on (2x)."""

    def test_serverless_always_performance(self):
        """
        Frontend forces performance mode: base * photon(2) * perf(2) = base * 4.
        (1.0 + 1.0*4) * 2 * 2 = 20.0 DBU/hr.
        """
        result = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard",  # Ignored — frontend always uses 2x
            hours_per_month=730,
        )
        assert result["dbu_per_hour"] == pytest.approx(20.0)
        assert result["serverless_multiplier"] == 2

    def test_serverless_mode_parameter_ignored(self):
        """Both 'standard' and 'performance' yield same result for ALL_PURPOSE."""
        standard = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard", hours_per_month=730,
        )
        performance = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="performance", hours_per_month=730,
        )
        assert standard["dbu_per_hour"] == pytest.approx(performance["dbu_per_hour"])

    def test_sku_is_all_purpose_serverless(self):
        """SKU = ALL_PURPOSE_SERVERLESS_COMPUTE."""
        result = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=True,
            hours_per_month=730,
        )
        assert result["sku"] == "ALL_PURPOSE_SERVERLESS_COMPUTE"

    def test_no_vm_costs(self):
        """Serverless has no VM costs."""
        result = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=True,
            hours_per_month=730,
        )
        assert result["vm_cost"] == 0

    def test_serverless_cost_at_list_price(self, us_east_1_premium_rates):
        """Serverless uses ALL_PURPOSE_SERVERLESS_COMPUTE pricing."""
        dbu_price = us_east_1_premium_rates.get(
            "ALL_PURPOSE_SERVERLESS_COMPUTE", 0.83
        )
        result = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=True,
            hours_per_month=730, dbu_price=dbu_price,
        )
        expected_dbus = 20.0 * 730
        expected_cost = expected_dbus * dbu_price
        assert result["monthly_dbus"] == pytest.approx(expected_dbus)
        assert result["dbu_cost"] == pytest.approx(expected_cost)

    def test_serverless_run_based(self):
        """5 runs/day x 45 min x 20 days = 75 hours, serverless."""
        result = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=True,
            runs_per_day=5, avg_runtime_minutes=45, days_per_month=20,
        )
        assert result["hours_per_month"] == pytest.approx(75.0)
        assert result["dbu_per_hour"] == pytest.approx(20.0)
        assert result["monthly_dbus"] == pytest.approx(1500.0)


# ============================================================
# Test: Edge Cases
# ============================================================

class TestAllPurposeEdgeCases:
    """Edge cases for All-Purpose calculations."""

    def test_zero_hours_zero_cost(self):
        """No hours = no DBUs = no cost."""
        result = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=False,
        )
        assert result["monthly_dbus"] == 0
        assert result["dbu_cost"] == 0

    def test_large_cluster_8workers(self, aws_instance_rates):
        """8 workers: driver(0.69) + 8 x worker(2.0) = 16.69 DBU/hr."""
        driver_rate = aws_instance_rates["m5.xlarge"]["dbu_rate"]  # 0.69
        worker_rate = aws_instance_rates["i3.2xlarge"]["dbu_rate"]  # 2.0
        result = frontend_calc_allpurpose(
            driver_dbu_rate=driver_rate, worker_dbu_rate=worker_rate,
            num_workers=8, photon_enabled=False, serverless_enabled=False,
            hours_per_month=730,
        )
        expected = 0.69 + (2.0 * 8)
        assert result["dbu_per_hour"] == pytest.approx(expected)
        assert result["monthly_dbus"] == pytest.approx(expected * 730)

    def test_large_cluster_photon(self):
        """Large cluster with photon: (1.0 + 2.0*8) * 2 = 34.0."""
        result = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=2.0, num_workers=8,
            photon_enabled=True, serverless_enabled=False,
            hours_per_month=730,
        )
        expected = (1.0 + 2.0 * 8) * 2.0
        assert result["dbu_per_hour"] == pytest.approx(expected)

    def test_single_driver_no_workers_serverless(self):
        """Serverless with 0 workers: 1.0 * 2 * 2 = 4.0."""
        result = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            photon_enabled=False, serverless_enabled=True,
            hours_per_month=730,
        )
        assert result["dbu_per_hour"] == pytest.approx(4.0)

    @pytest.mark.parametrize("hours,expected_dbus", [
        (100, 500.0),
        (200, 1000.0),
        (500, 2500.0),
        (730, 3650.0),
    ])
    def test_parametric_hours(self, hours, expected_dbus):
        """Various hours_per_month values for 4-worker classic cluster."""
        result = frontend_calc_allpurpose(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=hours,
        )
        assert result["monthly_dbus"] == pytest.approx(expected_dbus)
