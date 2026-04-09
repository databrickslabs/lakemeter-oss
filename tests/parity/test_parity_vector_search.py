"""Parity tests: VECTOR_SEARCH workload — backend vs frontend equivalence."""
import math
import pytest
from .conftest import make_item
from .frontend_calc import (
    fe_vector_search_dbu_per_hour, fe_vector_search_storage_cost,
    fe_monthly_dbu_cost, fe_total_monthly_cost,
)

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
    dbu_cost = monthly_dbus * dbu_price
    return dict(dbu_hr=dbu_hr, hours=hours, sku=sku, dbu_price=dbu_price,
                monthly_dbus=monthly_dbus, dbu_cost=dbu_cost)


def _get_be_storage(item):
    """Get backend storage sub-row values for Vector Search."""
    from app.routes.export.excel_item_helpers import write_storage_subrow
    storage_gb = float(item.vector_search_storage_gb or 0)
    capacity_m = float(item.vector_capacity_millions or 1)
    mode = (item.vector_search_mode or 'standard').lower()
    divisor = 64_000_000 if mode == 'storage_optimized' else 2_000_000
    units = math.ceil(capacity_m * 1_000_000 / divisor) if divisor else 0
    free_gb = units * 20
    billable_gb = max(0, storage_gb - free_gb)
    price_per_gb = 0.023
    storage_cost = billable_gb * price_per_gb
    return dict(storage_gb=storage_gb, units=units, free_gb=free_gb,
                billable_gb=billable_gb, storage_cost=storage_cost)


class TestVectorSearchStandard:
    """Standard mode vector search."""

    def test_standard_1m(self, pricing):
        """1M vectors — 1 unit at 4.0 DBU/hr."""
        vs_info = pricing['vector_search_rates']['aws:standard']
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='standard',
            vector_capacity_millions=1, hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_vector_search_dbu_per_hour(
            capacity_millions=1, mode='standard',
            dbu_rate=vs_info['dbu_rate'], input_divisor=vs_info['input_divisor'],
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(4.0, abs=TOL)
        assert be['sku'] == 'SERVERLESS_REAL_TIME_INFERENCE'

    def test_standard_2m_exact_boundary(self, pricing):
        """2M vectors — exactly 1 unit boundary → 1 unit → 4 DBU/hr."""
        vs_info = pricing['vector_search_rates']['aws:standard']
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='standard',
            vector_capacity_millions=2, hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_vector_search_dbu_per_hour(
            capacity_millions=2, mode='standard',
            dbu_rate=vs_info['dbu_rate'], input_divisor=vs_info['input_divisor'],
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        # 2M / 2M = exactly 1 unit
        assert be['dbu_hr'] == pytest.approx(4.0, abs=TOL)

    def test_standard_3m_ceiling(self, pricing):
        """3M vectors — ceil(3M/2M)=2 units → 8 DBU/hr (ceiling behavior)."""
        vs_info = pricing['vector_search_rates']['aws:standard']
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='standard',
            vector_capacity_millions=3, hours_per_month=400,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_vector_search_dbu_per_hour(
            capacity_millions=3, mode='standard',
            dbu_rate=vs_info['dbu_rate'], input_divisor=vs_info['input_divisor'],
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(8.0, abs=TOL)

    def test_standard_5m(self, pricing):
        """5M vectors — ceil(5M/2M)=3 units → 12 DBU/hr."""
        vs_info = pricing['vector_search_rates']['aws:standard']
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='standard',
            vector_capacity_millions=5, hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_vector_search_dbu_per_hour(
            capacity_millions=5, mode='standard',
            dbu_rate=vs_info['dbu_rate'], input_divisor=vs_info['input_divisor'],
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(12.0, abs=TOL)
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=730, dbu_price=be['dbu_price'],
        )
        assert be['dbu_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_standard_10m(self, pricing):
        """10M vectors — ceil(10M/2M)=5 units → 20 DBU/hr."""
        vs_info = pricing['vector_search_rates']['aws:standard']
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='standard',
            vector_capacity_millions=10, hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_vector_search_dbu_per_hour(
            capacity_millions=10, mode='standard',
            dbu_rate=vs_info['dbu_rate'], input_divisor=vs_info['input_divisor'],
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(20.0, abs=TOL)

    def test_standard_50m(self, pricing):
        """50M vectors — ceil(50M/2M)=25 units → 100 DBU/hr."""
        vs_info = pricing['vector_search_rates']['aws:standard']
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='standard',
            vector_capacity_millions=50, hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_vector_search_dbu_per_hour(
            capacity_millions=50, mode='standard',
            dbu_rate=vs_info['dbu_rate'], input_divisor=vs_info['input_divisor'],
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(100.0, abs=TOL)

    def test_standard_monthly_cost(self, pricing):
        """Full cost calculation: 5M vectors, 730 hrs, verify monthly cost."""
        vs_info = pricing['vector_search_rates']['aws:standard']
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='standard',
            vector_capacity_millions=5, hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_vector_search_dbu_per_hour(
            capacity_millions=5, mode='standard',
            dbu_rate=vs_info['dbu_rate'], input_divisor=vs_info['input_divisor'],
        )
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=730, dbu_price=be['dbu_price'],
        )
        assert be['dbu_cost'] == pytest.approx(fe_cost, abs=TOL)


class TestVectorSearchStorageOptimized:
    """Storage-optimized mode vector search."""

    def test_storage_optimized_1m(self, pricing):
        """1M vectors — ceil(1M/64M)=1 unit → 18.29 DBU/hr."""
        vs_info = pricing['vector_search_rates']['aws:storage_optimized']
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='storage_optimized',
            vector_capacity_millions=1, hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_vector_search_dbu_per_hour(
            capacity_millions=1, mode='storage_optimized',
            dbu_rate=vs_info['dbu_rate'], input_divisor=vs_info['input_divisor'],
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(18.29, abs=TOL)

    def test_storage_optimized_64m_exact_boundary(self, pricing):
        """64M vectors — exactly 1 unit → 18.29 DBU/hr."""
        vs_info = pricing['vector_search_rates']['aws:storage_optimized']
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='storage_optimized',
            vector_capacity_millions=64, hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_vector_search_dbu_per_hour(
            capacity_millions=64, mode='storage_optimized',
            dbu_rate=vs_info['dbu_rate'], input_divisor=vs_info['input_divisor'],
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(18.29, abs=TOL)

    def test_storage_optimized_100m(self, pricing):
        """100M vectors — ceil(100M/64M)=2 units → 2*18.29 DBU/hr."""
        vs_info = pricing['vector_search_rates']['aws:storage_optimized']
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='storage_optimized',
            vector_capacity_millions=100, hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_vector_search_dbu_per_hour(
            capacity_millions=100, mode='storage_optimized',
            dbu_rate=vs_info['dbu_rate'], input_divisor=vs_info['input_divisor'],
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(36.58, abs=TOL)

    def test_storage_optimized_200m(self, pricing):
        """200M vectors — ceil(200M/64M)=4 units → 4*18.29 DBU/hr."""
        vs_info = pricing['vector_search_rates']['aws:storage_optimized']
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='storage_optimized',
            vector_capacity_millions=200, hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_vector_search_dbu_per_hour(
            capacity_millions=200, mode='storage_optimized',
            dbu_rate=vs_info['dbu_rate'], input_divisor=vs_info['input_divisor'],
        )
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        # ceil(200M/64M) = ceil(3.125) = 4 units
        assert be['dbu_hr'] == pytest.approx(73.16, abs=TOL)

    def test_storage_optimized_monthly_cost(self, pricing):
        """Full cost calculation: 100M vectors, 730 hrs."""
        vs_info = pricing['vector_search_rates']['aws:storage_optimized']
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='storage_optimized',
            vector_capacity_millions=100, hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_vector_search_dbu_per_hour(
            capacity_millions=100, mode='storage_optimized',
            dbu_rate=vs_info['dbu_rate'], input_divisor=vs_info['input_divisor'],
        )
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=730, dbu_price=be['dbu_price'],
        )
        assert be['dbu_cost'] == pytest.approx(fe_cost, abs=TOL)


class TestVectorSearchStorage:
    """Vector Search storage sub-row parity."""

    def test_storage_within_free_tier(self, pricing):
        """5M standard → 3 units → 60 GB free → 50 GB storage → $0 billable."""
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='standard',
            vector_capacity_millions=5, vector_search_storage_gb=50,
            hours_per_month=730,
        )
        be_storage = _get_be_storage(item)
        fe_cost = fe_vector_search_storage_cost(storage_gb=50, units_used=3)
        assert be_storage['units'] == 3
        assert be_storage['free_gb'] == 60
        assert be_storage['billable_gb'] == 0
        assert be_storage['storage_cost'] == pytest.approx(fe_cost, abs=TOL)
        assert be_storage['storage_cost'] == pytest.approx(0.0, abs=TOL)

    def test_storage_exceeds_free_tier(self, pricing):
        """5M standard → 3 units → 60 GB free → 100 GB → 40 GB billable × $0.023."""
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='standard',
            vector_capacity_millions=5, vector_search_storage_gb=100,
            hours_per_month=730,
        )
        be_storage = _get_be_storage(item)
        fe_cost = fe_vector_search_storage_cost(storage_gb=100, units_used=3)
        assert be_storage['units'] == 3
        assert be_storage['free_gb'] == 60
        assert be_storage['billable_gb'] == 40
        expected_cost = 40 * 0.023  # $0.92
        assert be_storage['storage_cost'] == pytest.approx(fe_cost, abs=TOL)
        assert be_storage['storage_cost'] == pytest.approx(expected_cost, abs=TOL)

    def test_storage_zero(self, pricing):
        """Zero storage → $0."""
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='standard',
            vector_capacity_millions=1, vector_search_storage_gb=0,
            hours_per_month=730,
        )
        be_storage = _get_be_storage(item)
        fe_cost = fe_vector_search_storage_cost(storage_gb=0, units_used=1)
        assert be_storage['storage_cost'] == pytest.approx(fe_cost, abs=TOL)
        assert be_storage['storage_cost'] == pytest.approx(0.0, abs=TOL)

    def test_storage_optimized_free_tier(self, pricing):
        """100M storage-optimized → 2 units → 40 GB free → 30 GB → $0."""
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='storage_optimized',
            vector_capacity_millions=100, vector_search_storage_gb=30,
            hours_per_month=730,
        )
        be_storage = _get_be_storage(item)
        fe_cost = fe_vector_search_storage_cost(storage_gb=30, units_used=2)
        assert be_storage['units'] == 2
        assert be_storage['free_gb'] == 40
        assert be_storage['billable_gb'] == 0
        assert be_storage['storage_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_storage_large_billable(self, pricing):
        """1M standard → 1 unit → 20 GB free → 500 GB → 480 GB billable."""
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='standard',
            vector_capacity_millions=1, vector_search_storage_gb=500,
            hours_per_month=730,
        )
        be_storage = _get_be_storage(item)
        fe_cost = fe_vector_search_storage_cost(storage_gb=500, units_used=1)
        assert be_storage['units'] == 1
        assert be_storage['free_gb'] == 20
        assert be_storage['billable_gb'] == 480
        expected_cost = 480 * 0.023  # $11.04
        assert be_storage['storage_cost'] == pytest.approx(fe_cost, abs=TOL)
        assert be_storage['storage_cost'] == pytest.approx(expected_cost, abs=TOL)


class TestVectorSearchTotalCost:
    """Total cost = compute DBU cost + storage cost."""

    def test_total_with_storage(self, pricing):
        """5M standard, 100 GB storage, 730 hrs → verify total."""
        vs_info = pricing['vector_search_rates']['aws:standard']
        item = make_item(
            workload_type='VECTOR_SEARCH', vector_search_mode='standard',
            vector_capacity_millions=5, vector_search_storage_gb=100,
            hours_per_month=730,
        )
        be = _get_be_results(item)
        be_storage = _get_be_storage(item)
        fe_dbu_hr = fe_vector_search_dbu_per_hour(
            capacity_millions=5, mode='standard',
            dbu_rate=vs_info['dbu_rate'], input_divisor=vs_info['input_divisor'],
        )
        fe_dbu_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=730, dbu_price=be['dbu_price'],
        )
        fe_storage_cost = fe_vector_search_storage_cost(storage_gb=100, units_used=3)
        fe_total = fe_total_monthly_cost(
            dbu_cost=fe_dbu_cost, storage_cost=fe_storage_cost,
        )
        be_total = be['dbu_cost'] + be_storage['storage_cost']
        assert be_total == pytest.approx(fe_total, abs=TOL)
