"""Parity tests: MODEL_SERVING workload — backend vs frontend equivalence."""
import pytest
from .conftest import make_item
from .frontend_calc import fe_model_serving_dbu_per_hour, fe_monthly_dbu_cost

CLOUD = 'aws'
REGION = 'us-east-1'
TIER = 'PREMIUM'
TOL = 0.01


def _get_be_results(item):
    from app.routes.export.calculations import _calculate_dbu_per_hour, _calculate_hours_per_month
    from app.routes.export.pricing import _get_dbu_price, _get_sku_type

    dbu_hr, _ = _calculate_dbu_per_hour(item, CLOUD)
    hours = _calculate_hours_per_month(item)
    sku = _get_sku_type(item, CLOUD)
    dbu_price, _ = _get_dbu_price(CLOUD, REGION, TIER, sku)
    monthly_dbus = dbu_hr * hours
    return dict(dbu_hr=dbu_hr, hours=hours, sku=sku, dbu_price=dbu_price,
                monthly_dbus=monthly_dbus, monthly_cost=monthly_dbus * dbu_price)


class TestModelServingCPU:
    """CPU-based model serving."""

    def test_cpu(self, pricing):
        ms_info = pricing['model_serving_rates']['aws:cpu']
        item = make_item(
            workload_type='MODEL_SERVING', model_serving_gpu_type='cpu',
            hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_model_serving_dbu_per_hour(gpu_dbu_rate=ms_info['dbu_rate'])
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(1.0, abs=TOL)
        assert be['sku'] == 'SERVERLESS_REAL_TIME_INFERENCE'
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=730, dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_cpu_short_hours(self, pricing):
        """CPU with 160 hours/month."""
        ms_info = pricing['model_serving_rates']['aws:cpu']
        item = make_item(
            workload_type='MODEL_SERVING', model_serving_gpu_type='cpu',
            hours_per_month=160,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_model_serving_dbu_per_hour(gpu_dbu_rate=ms_info['dbu_rate'])
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=160, dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)


class TestModelServingGPU:
    """GPU-based model serving — all AWS GPU types."""

    def test_gpu_small_t4(self, pricing):
        ms_info = pricing['model_serving_rates']['aws:gpu_small_t4']
        item = make_item(
            workload_type='MODEL_SERVING', model_serving_gpu_type='gpu_small_t4',
            hours_per_month=500,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_model_serving_dbu_per_hour(gpu_dbu_rate=ms_info['dbu_rate'])
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(10.48, abs=TOL)

    def test_gpu_medium_a10g_1x(self, pricing):
        ms_info = pricing['model_serving_rates']['aws:gpu_medium_a10g_1x']
        item = make_item(
            workload_type='MODEL_SERVING', model_serving_gpu_type='gpu_medium_a10g_1x',
            hours_per_month=300,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_model_serving_dbu_per_hour(gpu_dbu_rate=ms_info['dbu_rate'])
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(20.0, abs=TOL)
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=300, dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_gpu_medium_a10g_4x(self, pricing):
        ms_info = pricing['model_serving_rates']['aws:gpu_medium_a10g_4x']
        item = make_item(
            workload_type='MODEL_SERVING', model_serving_gpu_type='gpu_medium_a10g_4x',
            hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_model_serving_dbu_per_hour(gpu_dbu_rate=ms_info['dbu_rate'])
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(112.0, abs=TOL)
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=730, dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_gpu_medium_a10g_8x(self, pricing):
        ms_info = pricing['model_serving_rates']['aws:gpu_medium_a10g_8x']
        item = make_item(
            workload_type='MODEL_SERVING', model_serving_gpu_type='gpu_medium_a10g_8x',
            hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_model_serving_dbu_per_hour(gpu_dbu_rate=ms_info['dbu_rate'])
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(290.8, abs=TOL)

    def test_gpu_xlarge_a100_40gb_8x(self, pricing):
        ms_info = pricing['model_serving_rates']['aws:gpu_xlarge_a100_40gb_8x']
        item = make_item(
            workload_type='MODEL_SERVING', model_serving_gpu_type='gpu_xlarge_a100_40gb_8x',
            hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_model_serving_dbu_per_hour(gpu_dbu_rate=ms_info['dbu_rate'])
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(538.4, abs=TOL)
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=730, dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_gpu_xlarge_a100_80gb_8x(self, pricing):
        ms_info = pricing['model_serving_rates']['aws:gpu_xlarge_a100_80gb_8x']
        item = make_item(
            workload_type='MODEL_SERVING', model_serving_gpu_type='gpu_xlarge_a100_80gb_8x',
            hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_model_serving_dbu_per_hour(gpu_dbu_rate=ms_info['dbu_rate'])
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(628.0, abs=TOL)

    def test_gpu_type_case_insensitive(self, pricing):
        """Backend lowercases gpu_type — test with uppercase input."""
        ms_info = pricing['model_serving_rates']['aws:gpu_small_t4']
        item = make_item(
            workload_type='MODEL_SERVING', model_serving_gpu_type='GPU_SMALL_T4',
            hours_per_month=100,
        )
        be = _get_be_results(item)
        assert be['dbu_hr'] == pytest.approx(ms_info['dbu_rate'], abs=TOL)


class TestModelServingRunBased:
    """Model serving with run-based usage config."""

    def test_runs_per_day(self, pricing):
        """Model serving with 10 runs/day, 30 min each, 22 days."""
        ms_info = pricing['model_serving_rates']['aws:gpu_small_t4']
        item = make_item(
            workload_type='MODEL_SERVING', model_serving_gpu_type='gpu_small_t4',
            runs_per_day=10, avg_runtime_minutes=30, days_per_month=22,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_model_serving_dbu_per_hour(gpu_dbu_rate=ms_info['dbu_rate'])
        # hours = 10 * 30/60 * 22 = 110
        expected_hours = 10 * (30 / 60) * 22
        assert be['hours'] == pytest.approx(expected_hours, abs=TOL)
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=expected_hours, dbu_price=be['dbu_price'],
        )
        assert be['monthly_cost'] == pytest.approx(fe_cost, abs=TOL)


class TestModelServingMonthlyCost:
    """Verify end-to-end monthly cost for various configs."""

    @pytest.mark.parametrize("gpu_type,expected_dbu_hr", [
        ('cpu', 1.0),
        ('gpu_small_t4', 10.48),
        ('gpu_medium_a10g_1x', 20.0),
        ('gpu_medium_a10g_4x', 112.0),
        ('gpu_medium_a10g_8x', 290.8),
        ('gpu_xlarge_a100_40gb_8x', 538.4),
        ('gpu_xlarge_a100_80gb_8x', 628.0),
    ])
    def test_parametrized_gpu_costs(self, pricing, gpu_type, expected_dbu_hr):
        """Parametrized test: DBU/hr matches for each GPU type."""
        ms_key = f'aws:{gpu_type}'
        ms_info = pricing['model_serving_rates'][ms_key]
        item = make_item(
            workload_type='MODEL_SERVING', model_serving_gpu_type=gpu_type,
            hours_per_month=730,
        )
        be = _get_be_results(item)
        assert be['dbu_hr'] == pytest.approx(expected_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(ms_info['dbu_rate'], abs=TOL)
        assert be['sku'] == 'SERVERLESS_REAL_TIME_INFERENCE'
