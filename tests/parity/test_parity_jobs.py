"""Parity tests: JOBS workload — backend vs frontend calculation equivalence."""
import pytest
from .conftest import make_item
from .frontend_calc import (
    fe_compute_dbu_per_hour, fe_hours_per_month, fe_monthly_dbu_cost,
)

CLOUD = 'aws'
REGION = 'us-east-1'
TIER = 'PREMIUM'
TOL = 0.01  # 1 cent tolerance


def _get_be_results(item, pricing):
    """Run backend calculation and return results dict."""
    from app.routes.export.calculations import _calculate_dbu_per_hour, _calculate_hours_per_month
    from app.routes.export.pricing import _get_dbu_price, _get_sku_type

    dbu_hr, warnings = _calculate_dbu_per_hour(item, CLOUD)
    hours = _calculate_hours_per_month(item)
    sku = _get_sku_type(item, CLOUD)
    dbu_price, _ = _get_dbu_price(CLOUD, REGION, TIER, sku)
    monthly_dbus = dbu_hr * hours
    monthly_cost = monthly_dbus * dbu_price
    return dict(dbu_hr=dbu_hr, hours=hours, sku=sku, dbu_price=dbu_price,
                monthly_dbus=monthly_dbus, monthly_cost=monthly_cost)


class TestJobsClassic:
    """JOBS classic (no photon, no serverless)."""

    def test_basic_2_workers(self, pricing):
        """JOBS classic with m5d.xlarge driver, i3.xlarge workers x2."""
        driver_dbu = pricing['instance_dbu_rates']['aws']['m5d.xlarge']['dbu_rate']
        worker_dbu = pricing['instance_dbu_rates']['aws']['i3.xlarge']['dbu_rate']
        item = make_item(
            workload_type='JOBS', driver_node_type='m5d.xlarge',
            worker_node_type='i3.xlarge', num_workers=2,
            hours_per_month=100,
        )
        be = _get_be_results(item, pricing)
        fe_dbu_hr = fe_compute_dbu_per_hour(
            driver_dbu_rate=driver_dbu, worker_dbu_rate=worker_dbu,
            num_workers=2, workload_type='JOBS',
        )
        fe_hours = fe_hours_per_month(hours_per_month=100)
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['hours'] == pytest.approx(fe_hours, abs=TOL)
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=fe_hours,
            dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_run_based_hours(self, pricing):
        """JOBS classic using runs_per_day * avg_runtime calculation."""
        driver_dbu = pricing['instance_dbu_rates']['aws']['m5d.xlarge']['dbu_rate']
        worker_dbu = pricing['instance_dbu_rates']['aws']['r5.xlarge']['dbu_rate']
        item = make_item(
            workload_type='JOBS', driver_node_type='m5d.xlarge',
            worker_node_type='r5.xlarge', num_workers=4,
            runs_per_day=10, avg_runtime_minutes=30, days_per_month=22,
        )
        be = _get_be_results(item, pricing)
        fe_hours = fe_hours_per_month(
            runs_per_day=10, avg_runtime_minutes=30, days_per_month=22,
        )
        fe_dbu_hr = fe_compute_dbu_per_hour(
            driver_dbu_rate=driver_dbu, worker_dbu_rate=worker_dbu,
            num_workers=4, workload_type='JOBS',
        )
        assert be['hours'] == pytest.approx(fe_hours, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['sku'] == 'JOBS_COMPUTE'

    def test_zero_workers(self, pricing):
        """JOBS classic with driver only (0 workers)."""
        driver_dbu = pricing['instance_dbu_rates']['aws']['m5d.2xlarge']['dbu_rate']
        item = make_item(
            workload_type='JOBS', driver_node_type='m5d.2xlarge',
            num_workers=0, hours_per_month=730,
        )
        be = _get_be_results(item, pricing)
        fe_dbu_hr = fe_compute_dbu_per_hour(
            driver_dbu_rate=driver_dbu, worker_dbu_rate=0.5,
            num_workers=0, workload_type='JOBS',
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)


class TestJobsPhoton:
    """JOBS with photon enabled."""

    def test_photon_multiplier(self, pricing):
        """JOBS photon uses photon multiplier from JSON."""
        driver_dbu = pricing['instance_dbu_rates']['aws']['m5d.xlarge']['dbu_rate']
        worker_dbu = pricing['instance_dbu_rates']['aws']['i3.xlarge']['dbu_rate']
        photon_mult = pricing['dbu_multipliers']['aws:JOBS_COMPUTE:photon']['multiplier']
        item = make_item(
            workload_type='JOBS', driver_node_type='m5d.xlarge',
            worker_node_type='i3.xlarge', num_workers=2,
            photon_enabled=True, hours_per_month=200,
        )
        be = _get_be_results(item, pricing)
        fe_dbu_hr = fe_compute_dbu_per_hour(
            driver_dbu_rate=driver_dbu, worker_dbu_rate=worker_dbu,
            num_workers=2, photon_enabled=True, workload_type='JOBS',
            photon_multiplier=photon_mult,
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['sku'] == 'JOBS_COMPUTE_(PHOTON)'


class TestJobsServerless:
    """JOBS serverless mode."""

    def test_serverless_standard(self, pricing):
        """JOBS serverless standard mode (multiplier=1)."""
        item = make_item(
            workload_type='JOBS', driver_node_type='m5d.xlarge',
            worker_node_type='i3.xlarge', num_workers=2,
            serverless_enabled=True, serverless_mode='standard',
            hours_per_month=50,
        )
        driver_dbu = pricing['instance_dbu_rates']['aws']['m5d.xlarge']['dbu_rate']
        worker_dbu = pricing['instance_dbu_rates']['aws']['i3.xlarge']['dbu_rate']
        photon_mult = pricing['dbu_multipliers']['aws:JOBS_COMPUTE:photon']['multiplier']
        be = _get_be_results(item, pricing)
        fe_dbu_hr = fe_compute_dbu_per_hour(
            driver_dbu_rate=driver_dbu, worker_dbu_rate=worker_dbu,
            num_workers=2, serverless_enabled=True, serverless_mode='standard',
            workload_type='JOBS', photon_multiplier=photon_mult,
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['sku'] == 'JOBS_SERVERLESS_COMPUTE'

    def test_serverless_performance(self, pricing):
        """JOBS serverless performance mode (multiplier=2)."""
        item = make_item(
            workload_type='JOBS', driver_node_type='m5d.xlarge',
            worker_node_type='i3.xlarge', num_workers=2,
            serverless_enabled=True, serverless_mode='performance',
            hours_per_month=50,
        )
        driver_dbu = pricing['instance_dbu_rates']['aws']['m5d.xlarge']['dbu_rate']
        worker_dbu = pricing['instance_dbu_rates']['aws']['i3.xlarge']['dbu_rate']
        photon_mult = pricing['dbu_multipliers']['aws:JOBS_COMPUTE:photon']['multiplier']
        be = _get_be_results(item, pricing)
        fe_dbu_hr = fe_compute_dbu_per_hour(
            driver_dbu_rate=driver_dbu, worker_dbu_rate=worker_dbu,
            num_workers=2, serverless_enabled=True, serverless_mode='performance',
            workload_type='JOBS', photon_multiplier=photon_mult,
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=50,
            dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)


class TestJobsEdgeCases:
    """Edge cases for JOBS workload parity."""

    def test_unknown_instance_fallback(self, pricing):
        """Unknown instance types should use fallback 0.5 DBU for both driver and worker."""
        item = make_item(
            workload_type='JOBS', driver_node_type='unknown.type',
            worker_node_type='also.unknown', num_workers=3,
            hours_per_month=100,
        )
        be = _get_be_results(item, pricing)
        # Frontend uses 0.5 fallback for both driver and worker
        fe_dbu_hr = fe_compute_dbu_per_hour(
            driver_dbu_rate=0.5, worker_dbu_rate=0.5,
            num_workers=3, workload_type='JOBS',
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['sku'] == 'JOBS_COMPUTE'

    def test_eight_workers(self, pricing):
        """JOBS with 8 workers — high worker count."""
        driver_dbu = pricing['instance_dbu_rates']['aws']['m5d.xlarge']['dbu_rate']
        worker_dbu = pricing['instance_dbu_rates']['aws']['i3.xlarge']['dbu_rate']
        item = make_item(
            workload_type='JOBS', driver_node_type='m5d.xlarge',
            worker_node_type='i3.xlarge', num_workers=8,
            hours_per_month=730,
        )
        be = _get_be_results(item, pricing)
        fe_dbu_hr = fe_compute_dbu_per_hour(
            driver_dbu_rate=driver_dbu, worker_dbu_rate=worker_dbu,
            num_workers=8, workload_type='JOBS',
        )
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=730,
            dbu_price=be['dbu_price'],
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_photon_with_many_workers(self, pricing):
        """JOBS photon with 6 workers — ensures multiplier applies to full base."""
        driver_dbu = pricing['instance_dbu_rates']['aws']['m5d.xlarge']['dbu_rate']
        worker_dbu = pricing['instance_dbu_rates']['aws']['r5.xlarge']['dbu_rate']
        photon_mult = pricing['dbu_multipliers']['aws:JOBS_COMPUTE:photon']['multiplier']
        item = make_item(
            workload_type='JOBS', driver_node_type='m5d.xlarge',
            worker_node_type='r5.xlarge', num_workers=6,
            photon_enabled=True, hours_per_month=500,
        )
        be = _get_be_results(item, pricing)
        fe_dbu_hr = fe_compute_dbu_per_hour(
            driver_dbu_rate=driver_dbu, worker_dbu_rate=worker_dbu,
            num_workers=6, photon_enabled=True, workload_type='JOBS',
            photon_multiplier=photon_mult,
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)

    def test_days_per_month_default(self, pricing):
        """Run-based hours use days_per_month=22 as default."""
        driver_dbu = pricing['instance_dbu_rates']['aws']['m5d.xlarge']['dbu_rate']
        worker_dbu = pricing['instance_dbu_rates']['aws']['i3.xlarge']['dbu_rate']
        item = make_item(
            workload_type='JOBS', driver_node_type='m5d.xlarge',
            worker_node_type='i3.xlarge', num_workers=2,
            runs_per_day=5, avg_runtime_minutes=60,
            # days_per_month not set — should default to 22
        )
        be = _get_be_results(item, pricing)
        fe_hours = fe_hours_per_month(
            runs_per_day=5, avg_runtime_minutes=60, days_per_month=22,
        )
        assert be['hours'] == pytest.approx(fe_hours, abs=TOL)
