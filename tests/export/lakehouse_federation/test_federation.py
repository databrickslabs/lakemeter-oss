"""Lakehouse Federation export calculation tests.

Federation has no separate SKU — it bills as the Serverless SQL warehouse that runs the
federated queries. Serverless SQL bills warehouse *uptime*, so cost is driven by query volume
and auto-stop behaviour rather than a fixed hours figure.
"""
import pytest

from tests.export.lakehouse_federation.conftest import make_federation_item
from app.routes.export.calculations import (
    _calculate_dbu_per_hour, _is_serverless_workload, _calculate_hours_per_month,
)
from app.routes.export.excel_item_helpers import calc_item_values
from app.routes.export.pricing import _get_sku_type
from app.routes.export.helpers import _get_workload_display_name, _get_workload_config_details


class TestFederationBasics:
    def test_sku_is_serverless_sql(self):
        assert _get_sku_type(make_federation_item(), 'aws') == 'SERVERLESS_SQL_COMPUTE'

    def test_is_serverless(self):
        assert _is_serverless_workload(make_federation_item()) is True

    def test_display_name(self):
        assert _get_workload_display_name('LAKEHOUSE_FEDERATION') == 'Lakehouse Federation'

    @pytest.mark.parametrize("size,expected_dbu_hr", [
        ('2X-Small', 4), ('X-Small', 6), ('Small', 12), ('Medium', 24),
        ('Large', 40), ('X-Large', 80), ('2X-Large', 144),
    ])
    def test_dbu_per_hour_by_warehouse_size(self, size, expected_dbu_hr):
        item = make_federation_item(federation_size='custom', federation_warehouse_size=size)
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws', 'PREMIUM')
        assert dbu_hr == pytest.approx(expected_dbu_hr, abs=0.01)


class TestTierSizing:
    @pytest.mark.parametrize("size,users,qpd,warehouse", [
        ('S', 10, 20, '2X-Small'),
        ('M', 50, 100, '2X-Small'),
        ('L', 150, 500, 'X-Small'),
        ('XL', 500, 2000, 'Small'),
    ])
    def test_tier_values(self, size, users, qpd, warehouse):
        from app.services.lakehouse_federation_sizing import resolve_federation_config
        cfg = resolve_federation_config(size)
        assert cfg['num_users'] == users
        assert cfg['queries_per_day'] == pytest.approx(qpd)
        assert cfg['warehouse_size'] == warehouse

    @pytest.mark.parametrize("size", ['S', 'M', 'L', 'XL', 'custom', 'bogus', None, '', 'm', 'xl'])
    def test_tier_resolution_never_crashes(self, size):
        from app.services.lakehouse_federation_sizing import resolve_federation_config
        cfg = resolve_federation_config(size)
        assert cfg['num_users'] > 0 and cfg['queries_per_day'] > 0 and cfg['warehouse_size']

    def test_config_details_resolve_tier(self):
        details = _get_workload_config_details(make_federation_item(federation_size='L'))
        assert 'Users: 150' in details, details
        assert '500/day' in details, details
        assert 'X-Small' in details, details


class TestUptimeModel:
    def test_hours_derived_from_queries_not_always_on(self):
        """A stored hours_per_month must never reintroduce always-on billing."""
        item = make_federation_item(federation_size='M', hours_per_month=730)
        hours = _calculate_hours_per_month(item)
        assert hours < 730, f"Federation billed as always-on ({hours}h)"
        assert hours == pytest.approx(35.4, abs=0.5)

    def test_light_workload_not_billed_as_always_on(self):
        """Guards the original defect: light querying billed as a continuously-on warehouse."""
        item = make_federation_item(
            federation_size='custom', federation_queries_per_period=1000,
            federation_query_period='month', federation_avg_query_seconds=30,
        )
        assert _calculate_hours_per_month(item) < 8 * 22 * 0.5

    def test_uptime_monotonic_and_capped(self):
        from app.services.lakehouse_federation_sizing import federation_warehouse_hours
        ceiling = 8 * 22
        prev = -1.0
        for q in (0.5, 1, 5, 10, 50, 100, 500, 5000, 1_000_000):
            h = federation_warehouse_hours(q)['hours_per_month']
            assert h >= prev - 1e-9, f"uptime decreased at {q} q/day"
            assert h <= ceiling + 1e-9, f"uptime {h} exceeded ceiling at {q} q/day"
            prev = h

    def test_auto_stop_floor_is_exact(self):
        """Each cold start holds the warehouse for auto_stop + query duration."""
        from app.services.lakehouse_federation_sizing import federation_warehouse_hours
        for auto_stop in (1, 5, 10):
            r = federation_warehouse_hours(1, avg_query_seconds=10,
                                           auto_stop_minutes=auto_stop, days_per_month=22)
            assert r['hours_per_month'] == pytest.approx(22 * (auto_stop + 10 / 60) / 60, abs=0.01)

    def test_shorter_auto_stop_reduces_cost(self):
        from app.services.lakehouse_federation_sizing import federation_warehouse_hours
        long_h = federation_warehouse_hours(20, auto_stop_minutes=10)['hours_per_month']
        short_h = federation_warehouse_hours(20, auto_stop_minutes=1)['hours_per_month']
        assert short_h < long_h

    def test_light_usage_absolute_cost_is_sane(self):
        from app.services.lakehouse_federation_sizing import (
            federation_warehouse_hours, warehouse_dbu_per_hour,
        )
        h = federation_warehouse_hours(1, avg_query_seconds=10)['hours_per_month']
        cost = warehouse_dbu_per_hour('2X-Small') * h * 0.70
        assert cost < 25, f"1 query/day should not cost ${cost:.2f}/mo"

    def test_uptime_never_below_execution_time(self):
        from app.services.lakehouse_federation_sizing import federation_warehouse_hours
        ceiling = 8 * 22
        for q, sec in [(10, 10), (100, 30), (1000, 60), (5, 300)]:
            r = federation_warehouse_hours(q, avg_query_seconds=sec)
            assert r['hours_per_month'] + 1e-9 >= min(r['execution_hours_per_month'], ceiling)

    def test_more_queries_costs_more(self):
        totals = []
        for qpd in (5, 20, 100, 500):
            item = make_federation_item(
                federation_size='custom', federation_queries_per_period=qpd,
                federation_query_period='day', federation_warehouse_size='2X-Small',
            )
            dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws', 'PREMIUM')
            totals.append(calc_item_values(item, False, False, dbu_hr, 'aws', [])[3])
        assert totals == sorted(totals), f"cost not monotonic: {totals}"

    def test_zero_queries_is_zero(self):
        from app.services.lakehouse_federation_sizing import federation_warehouse_hours
        assert federation_warehouse_hours(0)['hours_per_month'] == 0


class TestPeriodNormalization:
    @pytest.mark.parametrize("period,value,expected", [
        ('day', 20, 20), ('week', 100, 20), ('month', 440, 20),
        ('fortnight', 20, 20),  # unknown -> treated as per-day
    ])
    def test_normalization(self, period, value, expected):
        from app.services.lakehouse_federation_sizing import normalize_queries_per_day
        assert normalize_queries_per_day(value, period) == pytest.approx(expected, abs=0.01)


class TestDecimalCoercion:
    """Postgres NUMERIC arrives as Decimal; mixing with float raises TypeError.

    Regression guard: this broke the Excel export with
    "unsupported operand type(s) for /: 'decimal.Decimal' and 'float'".
    """

    def test_federation_accepts_decimal(self):
        from decimal import Decimal
        from app.services.lakehouse_federation_sizing import federation_warehouse_hours
        r = federation_warehouse_hours(Decimal('100.00'), avg_query_seconds=Decimal('10.00'))
        assert r['hours_per_month'] == pytest.approx(35.444, abs=0.01)

    def test_resolve_config_accepts_decimal(self):
        from decimal import Decimal
        from app.services.lakehouse_federation_sizing import resolve_federation_config
        cfg = resolve_federation_config('custom', queries_per_period=Decimal('1000'),
                                       query_period='month', num_users=Decimal('30'))
        assert cfg['num_users'] == 30
        assert isinstance(cfg['queries_per_day'], float)

    def test_none_inputs_do_not_raise(self):
        from app.services.lakehouse_federation_sizing import (
            federation_warehouse_hours, normalize_queries_per_day,
        )
        assert federation_warehouse_hours(None)['hours_per_month'] == 0
        assert normalize_queries_per_day(None, None) == 0

    def test_end_to_end_export_path_with_decimal(self):
        from decimal import Decimal
        item = make_federation_item(
            federation_size='custom',
            federation_queries_per_period=Decimal('1000'),
            federation_query_period='month',
            federation_avg_query_seconds=Decimal('30.00'),
        )
        hours = _calculate_hours_per_month(item)
        assert 0 < hours < 8 * 22
