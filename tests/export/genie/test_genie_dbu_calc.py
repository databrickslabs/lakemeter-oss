"""Test Genie / Genie Code and Lakehouse Federation export calculation logic.

Genie: LLM DBUs on the SRTI SKU, per-user model with a 150-DBU free allowance and a
25% intro promo applied to paid DBUs. Compute is billed separately (not here).

Lakehouse Federation: no separate SKU — bills as the Serverless SQL warehouse that runs
the federated queries.
"""
import pytest

from tests.export.genie.conftest import make_genie_item, make_federation_item
from app.routes.export.calculations import (
    _calculate_dbu_per_hour, _is_serverless_workload, _calculate_hours_per_month,
)
from app.routes.export.excel_item_helpers import calc_item_values
from app.routes.export.pricing import _get_sku_type
from app.routes.export.helpers import _get_workload_display_name, _get_workload_config_details


def _genie_total_dbus(item):
    """Run calc_item_values and return total monthly DBUs (index 3)."""
    dbu_per_hour, _ = _calculate_dbu_per_hour(item, 'aws', 'PREMIUM')
    return calc_item_values(item, False, False, dbu_per_hour, 'aws', [])[3]


class TestGenieBillableDBUs:
    """Billable = (max(0, per_user - free) * users + per_sp * sps) * (1 - promo)."""

    @pytest.mark.parametrize("users,per_user,promo,expected", [
        (10, 200, True, 375.0),    # 10 * 50 * 0.75
        (10, 200, False, 500.0),   # no promo: 10 * 50
        (1, 200, True, 37.5),      # matches go/geniepricing worked example
        (5, 100, True, 0.0),       # below the 150 free allowance
        (5, 150, True, 0.0),       # exactly at the free allowance
        (0, 999, True, 0.0),       # no users
    ])
    def test_user_billable(self, users, per_user, promo, expected):
        item = make_genie_item(
            genie_num_users=users, genie_dbus_per_user_per_month=per_user,
            genie_apply_promo=promo,
        )
        assert _genie_total_dbus(item) == pytest.approx(expected, abs=0.01)

    @pytest.mark.parametrize("size,users,dbus", [
        ('S', 10, 150), ('M', 50, 250), ('L', 150, 400), ('XL', 500, 600),
    ])
    def test_tier_drives_users_and_dbus(self, size, users, dbus):
        from app.services.genie_federation_sizing import resolve_genie_config
        cfg = resolve_genie_config(size)
        assert cfg['num_users'] == users
        assert cfg['dbus_per_user'] == dbus

    def test_service_principals_have_no_free_allowance(self):
        # 2 SPs * 100 DBU, no free, 25% promo -> 200 * 0.75 = 150
        item = make_genie_item(
            genie_num_users=0, genie_dbus_per_user_per_month=0,
            genie_num_service_principals=2, genie_dbus_per_sp_per_month=100,
        )
        assert _genie_total_dbus(item) == pytest.approx(150.0, abs=0.01)

    def test_users_and_sps_combined(self):
        # users: 10 * (200-150) = 500 ; sps: 2*100 = 200 ; total 700 * 0.75 = 525
        item = make_genie_item(
            genie_num_users=10, genie_dbus_per_user_per_month=200,
            genie_num_service_principals=2, genie_dbus_per_sp_per_month=100,
        )
        assert _genie_total_dbus(item) == pytest.approx(525.0, abs=0.01)


class TestGenieMetadata:
    """SKU, serverless classification, display name, config details."""

    def test_sku_is_srti(self):
        assert _get_sku_type(make_genie_item(), 'aws') == 'SERVERLESS_REAL_TIME_INFERENCE'

    def test_genie_code_sku_is_srti(self):
        item = make_genie_item(workload_type='GENIE_CODE', genie_product='genie_code')
        assert _get_sku_type(item, 'aws') == 'SERVERLESS_REAL_TIME_INFERENCE'

    def test_is_serverless(self):
        assert _is_serverless_workload(make_genie_item()) is True

    def test_no_hour_based_dbu(self):
        # Genie is quantity-based; hourly DBU rate is 0
        dbu_hr, _ = _calculate_dbu_per_hour(make_genie_item(), 'aws', 'PREMIUM')
        assert dbu_hr == 0

    def test_display_names(self):
        assert _get_workload_display_name('GENIE') == 'Genie'
        assert _get_workload_display_name('GENIE_CODE') == 'Genie Code'

    def test_config_details_include_users(self):
        details = _get_workload_config_details(make_genie_item())
        assert 'Users: 10' in details
        assert 'Promo' in details

    def test_config_details_resolve_tier(self):
        """Tier-based rows must show real users/DBUs, not the null override columns."""
        details = _get_workload_config_details(
            make_genie_item(genie_size='M', genie_num_users=None,
                            genie_dbus_per_user_per_month=None))
        assert 'Users: 50' in details, details
        assert 'DBUs/user: 250' in details, details
        assert '2X-Small' in details, details

    def test_genie_code_labels_developers(self):
        details = _get_workload_config_details(
            make_genie_item(workload_type='GENIE_CODE', genie_size='L',
                            genie_num_users=None, genie_dbus_per_user_per_month=None))
        assert 'Developers: 150' in details, details

    def test_reuse_existing_warehouse_shown(self):
        details = _get_workload_config_details(
            make_genie_item(genie_size='M', genie_reuse_existing_warehouse=True))
        assert 'reuses existing' in details, details


class TestLakehouseFederation:
    """Federation bills as Serverless SQL warehouse compute; no separate SKU."""

    @pytest.mark.parametrize("size,expected_dbu_hr", [
        ('2X-Small', 4), ('X-Small', 6), ('Small', 12), ('Medium', 24), ('Large', 40),
        ('X-Large', 80), ('2X-Large', 144),
    ])
    def test_dbu_per_hour_matches_serverless_sql(self, size, expected_dbu_hr):
        item = make_federation_item(federation_size='custom', federation_warehouse_size=size)
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws', 'PREMIUM')
        assert dbu_hr == pytest.approx(expected_dbu_hr, abs=0.01)

    def test_sku_is_serverless_sql(self):
        assert _get_sku_type(make_federation_item(), 'aws') == 'SERVERLESS_SQL_COMPUTE'

    def test_is_serverless(self):
        assert _is_serverless_workload(make_federation_item()) is True

    def test_hours_derived_from_queries_not_always_on(self):
        """Uptime must come from query volume, never a stored always-on hours figure.

        Regression guard: a legacy hours_per_month=730 must NOT reintroduce the
        "always-on warehouse" overestimate.
        """
        item = make_federation_item(federation_size='M', hours_per_month=730)
        hours = _calculate_hours_per_month(item)
        assert hours < 730, f"Federation billed as always-on ({hours}h) — overestimate regression"
        assert hours == pytest.approx(35.4, abs=0.5)

    def test_light_workload_not_billed_as_always_on(self):
        """1,000 queries/month must not bill a near-full month of warehouse uptime.

        Guards the original defect: 40h of "querying" was billed as a continuously-on
        warehouse ($672/mo). Uptime must stay well under the always-on ceiling.
        """
        item = make_federation_item(
            federation_size='custom', federation_queries_per_period=1000,
            federation_query_period='month', federation_avg_query_seconds=30,
        )
        hours = _calculate_hours_per_month(item)
        assert hours < 8 * 22 * 0.5, f"{hours:.1f}h is near always-on for a light workload"

    def test_monthly_dbus_from_tier(self):
        # M tier: 100 q/day on a 2X-Small (4 DBU/hr) -> ~35.4 hrs -> ~141 DBUs
        item = make_federation_item(federation_size='M')
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws', 'PREMIUM')
        total = calc_item_values(item, False, False, dbu_hr, 'aws', [])[3]
        assert dbu_hr == pytest.approx(4, abs=0.01)
        assert total == pytest.approx(141.7, abs=2.0)

    def test_more_queries_costs_more(self):
        """Cost must increase monotonically with query volume."""
        totals = []
        for qpd in (5, 20, 100, 500):
            item = make_federation_item(
                federation_size='custom', federation_queries_per_period=qpd,
                federation_query_period='day', federation_warehouse_size='2X-Small',
            )
            dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws', 'PREMIUM')
            totals.append(calc_item_values(item, False, False, dbu_hr, 'aws', [])[3])
        assert totals == sorted(totals), f"cost not monotonic in query volume: {totals}"

    @pytest.mark.parametrize("size,expected_qpd", [('S', 20), ('M', 100), ('L', 500), ('XL', 2000)])
    def test_tier_query_volumes(self, size, expected_qpd):
        from app.services.genie_federation_sizing import resolve_federation_config
        cfg = resolve_federation_config(size)
        assert cfg['queries_per_day'] == pytest.approx(expected_qpd)

    @pytest.mark.parametrize("period,value,expected_qpd", [
        ('day', 20, 20), ('week', 100, 20), ('month', 440, 20),
    ])
    def test_period_normalization(self, period, value, expected_qpd):
        from app.services.genie_federation_sizing import normalize_queries_per_day
        assert normalize_queries_per_day(value, period) == pytest.approx(expected_qpd, abs=0.01)

    def test_display_name(self):
        assert _get_workload_display_name('LAKEHOUSE_FEDERATION') == 'Lakehouse Federation'

    def test_config_details_resolve_tier(self):
        """Tier must drive the displayed warehouse/queries, not a stale raw column."""
        details = _get_workload_config_details(make_federation_item(federation_size='L'))
        assert 'Users: 150' in details, details
        assert '500/day' in details, details
        assert 'X-Small' in details, details


class TestSizingMathEdgeCases:
    """Edge cases and invariants for the shared sizing module."""

    def test_free_tier_boundary(self):
        from app.services.genie_federation_sizing import calculate_genie_llm_dbus
        assert calculate_genie_llm_dbus(10, 150)['billable_dbus'] == 0
        assert calculate_genie_llm_dbus(10, 150.01)['billable_dbus'] > 0

    def test_full_promo_zeroes_cost(self):
        from app.services.genie_federation_sizing import calculate_genie_llm_dbus
        assert calculate_genie_llm_dbus(10, 500, promo_pct=100)['billable_dbus'] == 0

    def test_service_principals_get_no_free_allowance(self):
        from app.services.genie_federation_sizing import calculate_genie_llm_dbus
        # 5 SPs x 100 DBU, all paid, 25% promo -> 500 * 0.75
        r = calculate_genie_llm_dbus(0, 0, num_service_principals=5, dbus_per_sp=100)
        assert r['billable_dbus'] == pytest.approx(375.0)

    @pytest.mark.parametrize("size", ['S', 'M', 'L', 'XL', 'custom', 'bogus', None, '', 'm', 'xl'])
    def test_tier_resolution_never_crashes(self, size):
        """Unknown/None/lowercase sizes must fall back to a usable config."""
        from app.services.genie_federation_sizing import (
            resolve_genie_config, resolve_federation_config,
        )
        g = resolve_genie_config(size)
        assert g['num_users'] > 0 and g['warehouse_size']
        f = resolve_federation_config(size)
        assert f['num_users'] > 0 and f['queries_per_day'] > 0 and f['warehouse_size']

    def test_unknown_warehouse_size_falls_back(self):
        from app.services.genie_federation_sizing import warehouse_dbu_per_hour
        assert warehouse_dbu_per_hour('Gigantic') == 4.0
        assert warehouse_dbu_per_hour(None) == 4.0

    def test_uptime_monotonic_and_capped(self):
        """Uptime rises with volume and never exceeds the active-hours ceiling."""
        from app.services.genie_federation_sizing import federation_warehouse_hours
        ceiling = 8 * 22
        prev = -1.0
        for q in (0.5, 1, 5, 10, 50, 100, 500, 5000, 1_000_000):
            h = federation_warehouse_hours(q)['hours_per_month']
            assert h >= prev - 1e-9, f"uptime decreased at {q} q/day"
            assert h <= ceiling + 1e-9, f"uptime {h} exceeded ceiling at {q} q/day"
            prev = h

    def test_auto_stop_floor_is_exact(self):
        """Each cold start holds the warehouse for auto_stop + query duration."""
        from app.services.genie_federation_sizing import federation_warehouse_hours
        for auto_stop in (1, 5, 10):
            r = federation_warehouse_hours(1, avg_query_seconds=10,
                                           auto_stop_minutes=auto_stop, days_per_month=22)
            expected = 22 * (auto_stop + 10 / 60) / 60
            assert r['hours_per_month'] == pytest.approx(expected, abs=0.01)

    def test_shorter_auto_stop_reduces_cost(self):
        """Auto-stop is a real cost lever, not a no-op."""
        from app.services.genie_federation_sizing import federation_warehouse_hours
        long_h = federation_warehouse_hours(20, auto_stop_minutes=10)['hours_per_month']
        short_h = federation_warehouse_hours(20, auto_stop_minutes=1)['hours_per_month']
        assert short_h < long_h

    def test_light_usage_absolute_cost_is_sane(self):
        """1 query/day must cost ~a few dollars, not hundreds."""
        from app.services.genie_federation_sizing import (
            federation_warehouse_hours, warehouse_dbu_per_hour,
        )
        h = federation_warehouse_hours(1, avg_query_seconds=10)['hours_per_month']
        cost = warehouse_dbu_per_hour('2X-Small') * h * 0.70
        assert cost < 25, f"1 query/day should not cost ${cost:.2f}/mo"

    def test_uptime_never_below_execution_time(self):
        """Cannot bill less warehouse time than the queries actually took."""
        from app.services.genie_federation_sizing import federation_warehouse_hours
        ceiling = 8 * 22
        for q, sec in [(10, 10), (100, 30), (1000, 60), (5, 300)]:
            r = federation_warehouse_hours(q, avg_query_seconds=sec)
            assert r['hours_per_month'] + 1e-9 >= min(r['execution_hours_per_month'], ceiling)

    def test_period_normalization_identity(self):
        from app.services.genie_federation_sizing import normalize_queries_per_day
        d = normalize_queries_per_day(20, 'day')
        assert normalize_queries_per_day(100, 'week') == pytest.approx(d)
        assert normalize_queries_per_day(440, 'month') == pytest.approx(d)
        assert normalize_queries_per_day(20, 'fortnight') == 20  # unknown -> day


class TestDecimalCoercion:
    """Postgres NUMERIC columns arrive as Decimal; mixing with float raises TypeError.

    Regression guard: this broke the Excel export with
    "unsupported operand type(s) for -: 'decimal.Decimal' and 'float'".
    """

    def test_genie_accepts_decimal(self):
        from decimal import Decimal
        from app.services.genie_federation_sizing import calculate_genie_llm_dbus
        r = calculate_genie_llm_dbus(50, Decimal('250.00'))
        assert r['billable_dbus'] == pytest.approx(3750.0)

    def test_federation_accepts_decimal(self):
        from decimal import Decimal
        from app.services.genie_federation_sizing import federation_warehouse_hours
        r = federation_warehouse_hours(Decimal('100.00'), avg_query_seconds=Decimal('10.00'))
        assert r['hours_per_month'] == pytest.approx(35.444, abs=0.01)

    def test_resolve_configs_accept_decimal(self):
        from decimal import Decimal
        from app.services.genie_federation_sizing import (
            resolve_genie_config, resolve_federation_config,
        )
        g = resolve_genie_config('custom', num_users=Decimal('25'),
                                 dbus_per_user_per_month=Decimal('500.00'),
                                 active_hours_per_month=Decimal('176.00'))
        assert g['num_users'] == 25
        assert isinstance(g['dbus_per_user'], float)
        f = resolve_federation_config('custom', queries_per_period=Decimal('1000'),
                                     query_period='month', num_users=Decimal('30'))
        assert f['num_users'] == 30
        assert isinstance(f['queries_per_day'], float)

    def test_none_and_garbage_inputs_do_not_raise(self):
        from app.services.genie_federation_sizing import (
            calculate_genie_llm_dbus, federation_warehouse_hours, normalize_queries_per_day,
        )
        assert calculate_genie_llm_dbus(None, None)['billable_dbus'] == 0
        assert federation_warehouse_hours(None)['hours_per_month'] == 0
        assert normalize_queries_per_day(None, None) == 0

    def test_end_to_end_export_path_with_decimal_item(self):
        """The exact shape the ORM hands to the export layer."""
        from decimal import Decimal
        item = make_genie_item(
            genie_size='custom',
            genie_num_users=25,
            genie_dbus_per_user_per_month=Decimal('500.00'),
            genie_active_hours_per_month=Decimal('176.00'),
            genie_promo_pct=Decimal('25.00'),
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, 'aws', 'PREMIUM')
        total = calc_item_values(item, False, False, dbu_hr, 'aws', [])[3]
        assert total == pytest.approx(6562.5, abs=1.0)  # 25*(500-150)*0.75

        fed = make_federation_item(
            federation_size='custom',
            federation_queries_per_period=Decimal('1000'),
            federation_query_period='month',
            federation_avg_query_seconds=Decimal('30.00'),
        )
        hours = _calculate_hours_per_month(fed)
        assert hours > 0 and hours < 8 * 22
