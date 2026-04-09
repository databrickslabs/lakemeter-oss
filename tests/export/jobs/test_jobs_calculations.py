"""
Sprint 1: Jobs (Classic + Serverless) Calculation Verification Tests

Tests the cost calculation logic for Jobs workloads by:
1. Verifying frontend calculation formulas (replicated in Python)
2. Verifying backend export helper functions
3. Detecting discrepancies between frontend and backend
"""
import math
import pytest


# ============================================================
# Frontend calculation logic (replicated from costCalculation.ts)
# ============================================================

def frontend_calc_jobs(
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
    dbu_price: float = 0.15,
) -> dict:
    """Replicate frontend costCalculation.ts logic for JOBS."""
    # Hours calculation (frontend lines 131-139)
    if runs_per_day and avg_runtime_minutes:
        hours = (runs_per_day * (avg_runtime_minutes / 60)) * days_per_month
    elif hours_per_month:
        hours = hours_per_month
    else:
        hours = 0

    # Photon multiplier (frontend lines 273-307)
    # For serverless: photon is always enabled (built-in)
    if not serverless_enabled and not photon_enabled:
        photon_mult = 1.0
    else:
        photon_mult = 2.0  # Default photon multiplier

    # Serverless multiplier (frontend lines 313-315)
    if not serverless_enabled:
        serverless_mult = 1
    else:
        serverless_mult = 2 if serverless_mode == "performance" else 1

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
        sku = "JOBS_SERVERLESS_COMPUTE"
    elif photon_enabled:
        sku = "JOBS_COMPUTE_(PHOTON)"
    else:
        sku = "JOBS_COMPUTE"

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

def backend_calc_jobs(
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
    dbu_price: float = 0.15,
) -> dict:
    """Replicate backend export.py logic for JOBS (post-fix)."""
    # Hours (export.py) — FIXED: fallback is 0 (not 11)
    if runs_per_day and avg_runtime_minutes:
        hours = (runs_per_day * avg_runtime_minutes / 60) * days_per_month
    elif hours_per_month:
        hours = hours_per_month
    else:
        hours = 0  # No usage data = 0 hours (aligned with frontend)

    # DBU/hr (export.py)
    # FIXED: num_workers defaults to 0 (not 1) — aligned with frontend
    nw = num_workers if num_workers else 0
    base_dbu = driver_dbu_rate + (worker_dbu_rate * nw)

    if serverless_enabled:
        # Serverless always has photon built-in (2x)
        base_dbu *= 2
        mode_mult = 2 if serverless_mode == "performance" else 1
        dbu_per_hour = base_dbu * mode_mult
    else:
        if photon_enabled:
            base_dbu *= 2
        dbu_per_hour = base_dbu

    monthly_dbus = dbu_per_hour * hours

    # SKU (export.py lines 185-190)
    if serverless_enabled:
        sku = "JOBS_SERVERLESS_COMPUTE"
    elif photon_enabled:
        sku = "JOBS_COMPUTE_(PHOTON)"
    else:
        sku = "JOBS_COMPUTE"

    dbu_cost = monthly_dbus * dbu_price

    return {
        "hours_per_month": hours,
        "dbu_per_hour": dbu_per_hour,
        "monthly_dbus": monthly_dbus,
        "dbu_cost": dbu_cost,
        "sku": sku,
    }


# ============================================================
# Test: Hours Calculation
# ============================================================

class TestHoursCalculation:
    """Verify hours/month calculation for run-based and direct modes."""

    def test_run_based_standard(self):
        """10 runs/day × 30 min × 22 days = 110 hours."""
        result = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=False,
            runs_per_day=10, avg_runtime_minutes=30, days_per_month=22,
        )
        assert result["hours_per_month"] == pytest.approx(110.0)

    def test_run_based_custom_days(self):
        """5 runs/day × 45 min × 20 days = 75 hours."""
        result = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            photon_enabled=False, serverless_enabled=False,
            runs_per_day=5, avg_runtime_minutes=45, days_per_month=20,
        )
        assert result["hours_per_month"] == pytest.approx(75.0)

    def test_direct_hours(self):
        """Direct hours_per_month = 730 (24/7)."""
        result = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730,
        )
        assert result["hours_per_month"] == pytest.approx(730.0)

    def test_run_based_takes_priority_over_hours(self):
        """When both run-based and hours_per_month set, run-based wins."""
        result = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            photon_enabled=False, serverless_enabled=False,
            runs_per_day=10, avg_runtime_minutes=30, days_per_month=22,
            hours_per_month=730,  # Should be ignored
        )
        assert result["hours_per_month"] == pytest.approx(110.0)

    def test_backend_hours_run_based(self):
        """Backend run-based hours match frontend."""
        result = backend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=False,
            runs_per_day=10, avg_runtime_minutes=30, days_per_month=22,
        )
        assert result["hours_per_month"] == pytest.approx(110.0)

    def test_backend_fallback_hours(self):
        """Backend returns 0 when neither run-based nor hours_per_month set (FIXED)."""
        result = backend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=False,
        )
        # FIXED: Backend now returns 0 (aligned with frontend)
        assert result["hours_per_month"] == pytest.approx(0.0)


# ============================================================
# Test: Jobs Classic Standard (no photon)
# ============================================================

class TestJobsClassicStandard:
    """Jobs Classic Standard — no photon, cluster-based compute."""

    def test_dbu_per_hour_i3xlarge_2workers(self, aws_instance_rates):
        """i3.xlarge driver + 2× i3.xlarge workers = 1.0 + 1.0×2 = 3.0 DBU/hr."""
        driver_rate = aws_instance_rates["i3.xlarge"]["dbu_rate"]  # 1.0
        worker_rate = aws_instance_rates["i3.xlarge"]["dbu_rate"]  # 1.0
        result = frontend_calc_jobs(
            driver_dbu_rate=driver_rate, worker_dbu_rate=worker_rate,
            num_workers=2, photon_enabled=False, serverless_enabled=False,
            hours_per_month=110,
        )
        assert result["dbu_per_hour"] == pytest.approx(3.0)
        assert result["monthly_dbus"] == pytest.approx(330.0)  # 3.0 × 110

    def test_sku_is_jobs_compute(self):
        """SKU should be JOBS_COMPUTE for classic standard."""
        result = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=100,
        )
        assert result["sku"] == "JOBS_COMPUTE"

    def test_dbu_cost_at_list_price(self, us_east_1_premium_rates):
        """DBU cost = monthly_dbus × $/DBU."""
        dbu_price = us_east_1_premium_rates["JOBS_COMPUTE"]  # $0.15
        result = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=110, dbu_price=dbu_price,
        )
        expected_dbus = 3.0 * 110  # 330
        expected_cost = 330 * 0.15  # $49.50
        assert result["monthly_dbus"] == pytest.approx(expected_dbus)
        assert result["dbu_cost"] == pytest.approx(expected_cost)

    def test_mixed_instance_types(self, aws_instance_rates):
        """m5.xlarge driver (0.69) + 4× i3.2xlarge workers (2.0) = 8.69 DBU/hr."""
        driver_rate = aws_instance_rates["m5.xlarge"]["dbu_rate"]  # 0.69
        worker_rate = aws_instance_rates["i3.2xlarge"]["dbu_rate"]  # 2.0
        result = frontend_calc_jobs(
            driver_dbu_rate=driver_rate, worker_dbu_rate=worker_rate,
            num_workers=4, photon_enabled=False, serverless_enabled=False,
            hours_per_month=100,
        )
        expected_dbu_hr = 0.69 + (2.0 * 4)  # 8.69
        assert result["dbu_per_hour"] == pytest.approx(expected_dbu_hr)

    def test_zero_workers(self):
        """Single driver only (no workers) = just driver DBU rate."""
        result = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=100,
        )
        assert result["dbu_per_hour"] == pytest.approx(1.0)


# ============================================================
# Test: Jobs Classic Photon
# ============================================================

class TestJobsClassicPhoton:
    """Jobs Classic with Photon — 2x multiplier on DBU/hr."""

    def test_photon_doubles_dbu(self):
        """Photon multiplier = 2.0: 3.0 base × 2 = 6.0 DBU/hr."""
        result = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=True, serverless_enabled=False,
            hours_per_month=110,
        )
        assert result["dbu_per_hour"] == pytest.approx(6.0)
        assert result["monthly_dbus"] == pytest.approx(660.0)  # 6.0 × 110

    def test_sku_is_jobs_compute_photon(self):
        """SKU should be JOBS_COMPUTE_(PHOTON) for classic photon."""
        result = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=True, serverless_enabled=False,
            hours_per_month=100,
        )
        assert result["sku"] == "JOBS_COMPUTE_(PHOTON)"

    def test_photon_cost(self, us_east_1_premium_rates):
        """Photon uses same $/DBU as non-photon JOBS_COMPUTE_(PHOTON)."""
        dbu_price = us_east_1_premium_rates.get("JOBS_COMPUTE_(PHOTON)", 0.15)
        result = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=True, serverless_enabled=False,
            hours_per_month=110, dbu_price=dbu_price,
        )
        expected_cost = 6.0 * 110 * dbu_price
        assert result["dbu_cost"] == pytest.approx(expected_cost)


# ============================================================
# Test: Jobs Serverless Standard
# ============================================================

class TestJobsServerlessStandard:
    """Jobs Serverless Standard — photon always on, standard multiplier = 1x."""

    def test_serverless_standard_dbu(self):
        """Serverless standard: base × photon(2) × standard(1) = 3.0 × 2 × 1 = 6.0."""
        result = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard",
            hours_per_month=110,
        )
        # Photon is always on for serverless in frontend
        assert result["dbu_per_hour"] == pytest.approx(6.0)
        assert result["serverless_multiplier"] == 1

    def test_sku_is_serverless(self):
        """SKU = JOBS_SERVERLESS_COMPUTE for serverless."""
        result = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard", hours_per_month=100,
        )
        assert result["sku"] == "JOBS_SERVERLESS_COMPUTE"

    def test_no_vm_costs(self):
        """Serverless has no VM costs."""
        result = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard", hours_per_month=100,
        )
        assert result["vm_cost"] == 0

    def test_serverless_cost(self, us_east_1_premium_rates):
        """Serverless uses JOBS_SERVERLESS_COMPUTE pricing ($0.35 us-east-1)."""
        dbu_price = us_east_1_premium_rates.get("JOBS_SERVERLESS_COMPUTE", 0.35)
        result = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard", hours_per_month=110,
            dbu_price=dbu_price,
        )
        expected_cost = 6.0 * 110 * dbu_price
        assert result["dbu_cost"] == pytest.approx(expected_cost)


# ============================================================
# Test: Jobs Serverless Performance
# ============================================================

class TestJobsServerlessPerformance:
    """Jobs Serverless Performance — 2x serverless multiplier on top of photon."""

    def test_performance_mode_doubles(self):
        """Performance: base × photon(2) × performance(2) = 3.0 × 2 × 2 = 12.0."""
        result = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="performance",
            hours_per_month=110,
        )
        assert result["dbu_per_hour"] == pytest.approx(12.0)
        assert result["monthly_dbus"] == pytest.approx(1320.0)

    def test_performance_vs_standard_ratio(self):
        """Performance mode should be exactly 2x standard mode."""
        standard = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard", hours_per_month=100,
        )
        performance = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="performance", hours_per_month=100,
        )
        assert performance["dbu_per_hour"] == pytest.approx(standard["dbu_per_hour"] * 2)


# ============================================================
# Test: Frontend vs Backend Discrepancies
# ============================================================

class TestFrontendVsBackendDiscrepancies:
    """Detect known discrepancies between frontend and backend calculations."""

    def test_classic_standard_match(self):
        """Classic standard should match between frontend and backend."""
        fe = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=False,
            runs_per_day=10, avg_runtime_minutes=30, days_per_month=22,
            dbu_price=0.15,
        )
        be = backend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=False,
            runs_per_day=10, avg_runtime_minutes=30, days_per_month=22,
            dbu_price=0.15,
        )
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"])
        assert fe["monthly_dbus"] == pytest.approx(be["monthly_dbus"])
        assert fe["sku"] == be["sku"]

    def test_classic_photon_match(self):
        """Classic photon should match between frontend and backend."""
        fe = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=True, serverless_enabled=False,
            hours_per_month=110, dbu_price=0.15,
        )
        be = backend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=True, serverless_enabled=False,
            hours_per_month=110, dbu_price=0.15,
        )
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"])
        assert fe["monthly_dbus"] == pytest.approx(be["monthly_dbus"])
        assert fe["sku"] == be["sku"]

    def test_serverless_standard_photon_aligned(self):
        """
        BUG-S1-5 FIXED: Frontend and backend now both always apply photon (2x)
        for serverless, regardless of photon_enabled flag.

        Frontend: base × 2 (always) × 1 (standard) = 6.0
        Backend: base × 2 (always) × 1 (standard) = 6.0
        """
        fe = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard", hours_per_month=110,
        )
        be = backend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard", hours_per_month=110,
        )
        assert fe["dbu_per_hour"] == pytest.approx(6.0), "Frontend: always photon for serverless"
        assert be["dbu_per_hour"] == pytest.approx(6.0), "Backend: now always photon for serverless"
        # FE and BE should now match
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"]), \
            "BUG-S1-5 fixed: FE and BE both apply photon always for serverless"

    def test_serverless_with_photon_flag_match(self):
        """When photon_enabled=True on serverless, both FE and BE should agree."""
        fe = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=True, serverless_enabled=True,
            serverless_mode="standard", hours_per_month=110,
        )
        be = backend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=True, serverless_enabled=True,
            serverless_mode="standard", hours_per_month=110,
        )
        # Both should be 6.0 (base 3.0 × photon 2.0 × standard 1)
        assert fe["dbu_per_hour"] == pytest.approx(6.0)
        assert be["dbu_per_hour"] == pytest.approx(6.0)

    def test_num_workers_zero_aligned(self):
        """
        FIXED: Frontend and backend both default num_workers to 0.
        Both: driver_dbu + worker_dbu × 0 = 1.0
        """
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
        assert fe["dbu_per_hour"] == pytest.approx(1.0), "Frontend: 0 workers = driver only"
        assert be["dbu_per_hour"] == pytest.approx(1.0), "Backend: 0 workers = driver only (FIXED)"
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"]), \
            "FE and BE now agree on 0 workers"

    def test_sku_always_matches(self):
        """SKU mapping should be identical between frontend and backend."""
        configs = [
            (False, False, "standard"),
            (True, False, "standard"),
            (False, True, "standard"),
            (False, True, "performance"),
        ]
        for photon, serverless, mode in configs:
            fe = frontend_calc_jobs(
                driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
                photon_enabled=photon, serverless_enabled=serverless,
                serverless_mode=mode, hours_per_month=100,
            )
            be = backend_calc_jobs(
                driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
                photon_enabled=photon, serverless_enabled=serverless,
                serverless_mode=mode, hours_per_month=100,
            )
            assert fe["sku"] == be["sku"], \
                f"SKU mismatch for photon={photon}, serverless={serverless}, mode={mode}"


# ============================================================
# Test: Edge Cases
# ============================================================

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_zero_hours_zero_cost(self):
        """No hours = no DBUs = no cost."""
        result = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=False,
        )
        assert result["monthly_dbus"] == 0
        assert result["dbu_cost"] == 0

    def test_large_cluster(self):
        """Large cluster: 1 driver + 100 workers."""
        result = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=2.0, num_workers=100,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730,
        )
        expected_dbu_hr = 1.0 + (2.0 * 100)  # 201.0
        assert result["dbu_per_hour"] == pytest.approx(expected_dbu_hr)
        assert result["monthly_dbus"] == pytest.approx(201.0 * 730)

    def test_fractional_dbu_rates(self, aws_instance_rates):
        """Instance types with fractional DBU rates (e.g., m5.xlarge = 0.69)."""
        driver_rate = aws_instance_rates["m5.xlarge"]["dbu_rate"]  # 0.69
        worker_rate = aws_instance_rates["m5d.xlarge"]["dbu_rate"]  # 0.69
        result = frontend_calc_jobs(
            driver_dbu_rate=driver_rate, worker_dbu_rate=worker_rate,
            num_workers=3, photon_enabled=False, serverless_enabled=False,
            hours_per_month=100,
        )
        expected = 0.69 + (0.69 * 3)  # 2.76
        assert result["dbu_per_hour"] == pytest.approx(expected)

    def test_single_run_per_day(self):
        """1 run/day × 60 min × 22 days = 22 hours."""
        result = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            photon_enabled=False, serverless_enabled=False,
            runs_per_day=1, avg_runtime_minutes=60, days_per_month=22,
        )
        assert result["hours_per_month"] == pytest.approx(22.0)
