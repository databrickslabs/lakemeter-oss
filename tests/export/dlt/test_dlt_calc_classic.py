"""Sprint 3: DLT Classic Standard & Photon Calculation Tests."""
import pytest

from tests.export.dlt.dlt_calc_helpers import frontend_calc_dlt


class TestDLTHoursCalculation:
    """Verify hours/month calculation for DLT workloads."""

    def test_direct_hours_24x7(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", hours_per_month=730,
        )
        assert result["hours_per_month"] == pytest.approx(730.0)

    def test_run_based_24_runs_60min_30days(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE",
            runs_per_day=24, avg_runtime_minutes=60, days_per_month=30,
        )
        assert result["hours_per_month"] == pytest.approx(720.0)

    def test_run_based_priority_over_hours(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            dlt_edition="CORE",
            runs_per_day=10, avg_runtime_minutes=30, days_per_month=22,
            hours_per_month=730,
        )
        assert result["hours_per_month"] == pytest.approx(110.0)

    def test_default_days_per_month(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            dlt_edition="CORE",
            runs_per_day=10, avg_runtime_minutes=60,
        )
        assert result["hours_per_month"] == pytest.approx(220.0)

    def test_zero_hours_zero_cost(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE",
        )
        assert result["monthly_dbus"] == 0
        assert result["dbu_cost"] == 0


class TestDLTCoreClassicStandard:
    """DLT Core Classic Standard — no photon, $/DBU = $0.20."""

    def test_dbu_per_hour_4workers(self, aws_instance_rates):
        driver_rate = aws_instance_rates["i3.xlarge"]["dbu_rate"]
        worker_rate = aws_instance_rates["i3.xlarge"]["dbu_rate"]
        result = frontend_calc_dlt(
            driver_dbu_rate=driver_rate, worker_dbu_rate=worker_rate,
            num_workers=4, dlt_edition="CORE",
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730,
        )
        assert result["dbu_per_hour"] == pytest.approx(5.0)
        assert result["monthly_dbus"] == pytest.approx(3650.0)

    def test_sku_is_dlt_core_compute(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE",
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=100,
        )
        assert result["sku"] == "DLT_CORE_COMPUTE"

    def test_dbu_cost_at_core_price(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE",
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730, dbu_price=0.20,
        )
        expected_dbus = 5.0 * 730
        assert result["monthly_dbus"] == pytest.approx(expected_dbus)
        assert result["dbu_cost"] == pytest.approx(expected_dbus * 0.20)


class TestDLTProClassicStandard:
    """DLT Pro Classic Standard — no photon, $/DBU = $0.25."""

    def test_sku_is_dlt_pro_compute(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="PRO",
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=100,
        )
        assert result["sku"] == "DLT_PRO_COMPUTE"

    def test_dbu_cost_at_pro_price(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="PRO",
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730, dbu_price=0.25,
        )
        assert result["dbu_cost"] == pytest.approx((5.0 * 730) * 0.25)

    def test_pro_more_expensive_than_core(self):
        core = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", hours_per_month=730, dbu_price=0.20,
        )
        pro = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="PRO", hours_per_month=730, dbu_price=0.25,
        )
        assert pro["dbu_cost"] > core["dbu_cost"]


class TestDLTAdvancedClassicStandard:
    """DLT Advanced Classic Standard — no photon, $/DBU = $0.36."""

    def test_sku_is_dlt_advanced_compute(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="ADVANCED",
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=100,
        )
        assert result["sku"] == "DLT_ADVANCED_COMPUTE"

    def test_dbu_cost_at_advanced_price(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="ADVANCED",
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=730, dbu_price=0.36,
        )
        assert result["dbu_cost"] == pytest.approx((5.0 * 730) * 0.36)

    def test_edition_price_ordering(self):
        prices = [0.20, 0.25, 0.36]
        editions = ["CORE", "PRO", "ADVANCED"]
        costs = []
        for edition, price in zip(editions, prices):
            r = frontend_calc_dlt(
                driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
                dlt_edition=edition, hours_per_month=730, dbu_price=price,
            )
            costs.append(r["dbu_cost"])
        assert costs[0] < costs[1] < costs[2]


class TestDLTClassicPhoton:
    """DLT Classic with Photon — 2x multiplier, all editions."""

    def test_core_photon_doubles_dbu(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", photon_enabled=True, serverless_enabled=False,
            hours_per_month=730,
        )
        assert result["dbu_per_hour"] == pytest.approx(10.0)
        assert result["monthly_dbus"] == pytest.approx(7300.0)

    def test_core_photon_sku(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="CORE", photon_enabled=True, serverless_enabled=False,
            hours_per_month=100,
        )
        assert result["sku"] == "DLT_CORE_COMPUTE_(PHOTON)"

    def test_advanced_photon_sku(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="ADVANCED", photon_enabled=True, serverless_enabled=False,
            hours_per_month=100,
        )
        assert result["sku"] == "DLT_ADVANCED_COMPUTE_(PHOTON)"

    def test_pro_photon_sku(self):
        result = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition="PRO", photon_enabled=True, serverless_enabled=False,
            hours_per_month=100,
        )
        assert result["sku"] == "DLT_PRO_COMPUTE_(PHOTON)"

    @pytest.mark.parametrize("edition", ["CORE", "PRO", "ADVANCED"])
    def test_photon_doubles_for_all_editions(self, edition):
        no_photon = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=edition, photon_enabled=False, hours_per_month=730,
        )
        with_photon = frontend_calc_dlt(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=4,
            dlt_edition=edition, photon_enabled=True, hours_per_month=730,
        )
        assert with_photon["dbu_per_hour"] == pytest.approx(no_photon["dbu_per_hour"] * 2.0)
