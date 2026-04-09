"""
Sprint 3: DLT Serverless & Edge Case Calculation Tests

Tests for DLT Serverless (Standard + Performance) and edge cases.
Split from test_dlt_calculations.py to stay under 200-line limit.
"""
import math
import pytest

from tests.export.dlt.dlt_calc_helpers import frontend_calc_dlt


class TestDLTServerlessStandard:
    """DLT Serverless Standard mode — photon built-in (2x), standard (1x)."""

    def test_serverless_standard_dbu(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", serverless_enabled=True,
            serverless_mode="standard", hours_per_month=730,
        )
        assert result["dbu_per_hour"] == pytest.approx(10.0)
        assert result["serverless_multiplier"] == 1

    def test_serverless_sku(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", serverless_enabled=True,
            serverless_mode="standard", hours_per_month=730,
        )
        assert result["sku"] == "JOBS_SERVERLESS_COMPUTE"

    def test_no_vm_costs(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", serverless_enabled=True,
            hours_per_month=730,
        )
        assert result["vm_cost"] == 0

    def test_serverless_edition_ignored_for_sku(self):
        for edition in ["CORE", "PRO", "ADVANCED"]:
            result = frontend_calc_dlt(
                driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
                dlt_edition=edition, serverless_enabled=True,
                hours_per_month=730,
            )
            assert result["sku"] == "JOBS_SERVERLESS_COMPUTE"


class TestDLTServerlessPerformance:
    """DLT Serverless Performance mode — photon (2x) * performance (2x)."""

    def test_serverless_performance_dbu(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", serverless_enabled=True,
            serverless_mode="performance", hours_per_month=730,
        )
        assert result["dbu_per_hour"] == pytest.approx(20.0)
        assert result["serverless_multiplier"] == 2

    def test_performance_doubles_standard(self):
        standard = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", serverless_enabled=True,
            serverless_mode="standard", hours_per_month=730,
        )
        performance = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", serverless_enabled=True,
            serverless_mode="performance", hours_per_month=730,
        )
        assert performance["dbu_per_hour"] == pytest.approx(standard["dbu_per_hour"] * 2.0)


class TestDLTEdgeCases:
    """Edge cases for DLT calculations."""

    def test_zero_workers_driver_only(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            dlt_edition="CORE", hours_per_month=730,
        )
        assert result["dbu_per_hour"] == pytest.approx(1.0)

    def test_large_cluster_8workers(self, aws_instance_rates):
        driver_rate = aws_instance_rates["m5.xlarge"]["dbu_rate"]
        worker_rate = aws_instance_rates["i3.2xlarge"]["dbu_rate"]
        result = frontend_calc_dlt(
            driver_dbu_rate=driver_rate, worker_dbu_rate=worker_rate,
            num_workers=8, dlt_edition="ADVANCED",
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730,
        )
        assert result["dbu_per_hour"] == pytest.approx(0.69 + (2.0 * 8))

    def test_large_cluster_photon(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=2.0, num_workers=8,
            dlt_edition="ADVANCED", photon_enabled=True,
            hours_per_month=730,
        )
        assert result["dbu_per_hour"] == pytest.approx((1.0 + 2.0 * 8) * 2.0)

    def test_single_driver_serverless_performance(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            dlt_edition="CORE", serverless_enabled=True,
            serverless_mode="performance", hours_per_month=730,
        )
        assert result["dbu_per_hour"] == pytest.approx(4.0)

    @pytest.mark.parametrize("hours,expected_dbus", [
        (100, 500.0), (200, 1000.0), (500, 2500.0), (730, 3650.0),
    ])
    def test_parametric_hours(self, hours, expected_dbus):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", hours_per_month=hours,
        )
        assert result["monthly_dbus"] == pytest.approx(expected_dbus)

    def test_edition_defaults_to_core(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=None, hours_per_month=730,
        )
        assert result["sku"] == "DLT_CORE_COMPUTE"


class TestDLTNaNGuard:
    """BUG-S3-E3: Explicit NaN guard across all 12 DLT variants."""

    @pytest.mark.parametrize("edition,photon,serverless,mode", [
        ("CORE", False, False, "standard"),
        ("PRO", False, False, "standard"),
        ("ADVANCED", False, False, "standard"),
        ("CORE", True, False, "standard"),
        ("PRO", True, False, "standard"),
        ("ADVANCED", True, False, "standard"),
        ("CORE", False, True, "standard"),
        ("PRO", False, True, "standard"),
        ("ADVANCED", False, True, "standard"),
        ("CORE", False, True, "performance"),
        ("PRO", False, True, "performance"),
        ("ADVANCED", False, True, "performance"),
    ])
    def test_no_nan_in_results(self, edition, photon, serverless, mode):
        """No NaN in any numeric field for valid DLT config."""
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=edition,
            photon_enabled=photon,
            serverless_enabled=serverless,
            serverless_mode=mode,
            hours_per_month=730,
        )
        for key in ("dbu_per_hour", "monthly_dbus", "dbu_cost", "total_cost"):
            assert not math.isnan(result[key]), \
                f"{edition} photon={photon} sl={serverless} mode={mode}: {key} is NaN"
            assert result[key] > 0, \
                f"{edition} photon={photon} sl={serverless} mode={mode}: {key} should be > 0"
