"""Parity tests: LAKEBASE workload — backend vs frontend equivalence."""
import pytest
from .conftest import make_item
from .frontend_calc import (
    fe_lakebase_dbu_per_hour, fe_lakebase_storage_cost,
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
    # Storage cost
    storage_gb = float(item.lakebase_storage_gb or 0)
    storage_cost = storage_gb * 15 * 0.023  # DSU pricing
    return dict(dbu_hr=dbu_hr, hours=hours, sku=sku, dbu_price=dbu_price,
                monthly_dbus=monthly_dbus, dbu_cost=dbu_cost,
                storage_cost=storage_cost,
                total_cost=dbu_cost + storage_cost)


class TestLakebaseBasic:
    """Basic Lakebase CU-based compute."""

    def test_basic_1cu(self, pricing):
        """1 CU, 1 node, 730 hours."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=1, lakebase_ha_nodes=1,
            hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_lakebase_dbu_per_hour(cu=1, ha_nodes=1)
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(1.0, abs=TOL)
        assert be['sku'] == 'DATABASE_SERVERLESS_COMPUTE'

    def test_basic_2cu(self, pricing):
        """2 CU, 1 node."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=2, lakebase_ha_nodes=1,
            hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_lakebase_dbu_per_hour(cu=2, ha_nodes=1)
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(2.0, abs=TOL)

    def test_basic_4cu(self, pricing):
        """4 CU, 1 node, 730 hours."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=4, lakebase_ha_nodes=1,
            hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_lakebase_dbu_per_hour(cu=4, ha_nodes=1)
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(4.0, abs=TOL)
        assert be['sku'] == 'DATABASE_SERVERLESS_COMPUTE'
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=730, dbu_price=be['dbu_price'],
        )
        assert be['dbu_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_basic_8cu(self, pricing):
        """8 CU, 1 node."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=8, lakebase_ha_nodes=1,
            hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_lakebase_dbu_per_hour(cu=8, ha_nodes=1)
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(8.0, abs=TOL)

    def test_basic_16cu(self, pricing):
        """16 CU, 1 node."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=16, lakebase_ha_nodes=1,
            hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_lakebase_dbu_per_hour(cu=16, ha_nodes=1)
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(16.0, abs=TOL)


class TestLakebaseHA:
    """Lakebase with HA nodes."""

    def test_ha_2_nodes(self, pricing):
        """4 CU, 2 HA nodes → 8 DBU/hr."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=4, lakebase_ha_nodes=2,
            hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_lakebase_dbu_per_hour(cu=4, ha_nodes=2)
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(8.0, abs=TOL)

    def test_ha_3_nodes(self, pricing):
        """8 CU, 3 HA nodes → 24 DBU/hr."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=8, lakebase_ha_nodes=3,
            hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_lakebase_dbu_per_hour(cu=8, ha_nodes=3)
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(24.0, abs=TOL)
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=730, dbu_price=be['dbu_price'],
        )
        assert be['dbu_cost'] == pytest.approx(fe_cost, abs=TOL)

    def test_ha_1_node_default(self, pricing):
        """16 CU, default 1 node → 16 DBU/hr."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=16, lakebase_ha_nodes=1,
            hours_per_month=400,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_lakebase_dbu_per_hour(cu=16, ha_nodes=1)
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(16.0, abs=TOL)

    @pytest.mark.parametrize("cu,nodes,expected_dbu_hr", [
        (1, 1, 1.0),
        (2, 2, 4.0),
        (4, 3, 12.0),
        (8, 2, 16.0),
        (16, 3, 48.0),
    ])
    def test_parametrized_cu_nodes(self, pricing, cu, nodes, expected_dbu_hr):
        """Parametrized: CU × HA_nodes = DBU/hr."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=cu, lakebase_ha_nodes=nodes,
            hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_lakebase_dbu_per_hour(cu=cu, ha_nodes=nodes)
        assert be['dbu_hr'] == pytest.approx(fe_dbu_hr, abs=TOL)
        assert be['dbu_hr'] == pytest.approx(expected_dbu_hr, abs=TOL)


class TestLakebaseStorage:
    """Lakebase with storage costs."""

    def test_with_storage_500gb(self, pricing):
        """4 CU + 500 GB storage."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=4, lakebase_ha_nodes=1,
            lakebase_storage_gb=500, hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_storage = fe_lakebase_storage_cost(storage_gb=500)
        # 500 GB * 15 DSU/GB * $0.023/DSU = $172.50
        assert be['storage_cost'] == pytest.approx(fe_storage, abs=TOL)
        assert be['storage_cost'] == pytest.approx(172.50, abs=TOL)
        fe_dbu_cost = fe_monthly_dbu_cost(
            dbu_per_hour=4.0, hours_per_month=730, dbu_price=be['dbu_price'],
        )
        fe_total = fe_total_monthly_cost(
            dbu_cost=fe_dbu_cost, storage_cost=fe_storage,
        )
        assert be['total_cost'] == pytest.approx(fe_total, abs=TOL)

    def test_with_storage_1000gb(self, pricing):
        """8 CU + 1000 GB storage → 1000 * 15 * 0.023 = $345."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=8, lakebase_ha_nodes=1,
            lakebase_storage_gb=1000, hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_storage = fe_lakebase_storage_cost(storage_gb=1000)
        assert be['storage_cost'] == pytest.approx(fe_storage, abs=TOL)
        assert be['storage_cost'] == pytest.approx(345.0, abs=TOL)

    def test_with_storage_100gb(self, pricing):
        """4 CU + 100 GB → 100 * 15 * 0.023 = $34.50."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=4, lakebase_ha_nodes=1,
            lakebase_storage_gb=100, hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_storage = fe_lakebase_storage_cost(storage_gb=100)
        assert be['storage_cost'] == pytest.approx(fe_storage, abs=TOL)
        assert be['storage_cost'] == pytest.approx(34.50, abs=TOL)

    def test_zero_storage(self, pricing):
        """No storage — storage cost should be 0."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=2, lakebase_ha_nodes=1,
            lakebase_storage_gb=0, hours_per_month=160,
        )
        be = _get_be_results(item)
        assert be['storage_cost'] == pytest.approx(0.0, abs=TOL)

    def test_max_storage_8192gb(self, pricing):
        """Max storage 8192 GB → 8192 * 15 * 0.023 = $2826.24."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=16, lakebase_ha_nodes=3,
            lakebase_storage_gb=8192, hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_storage = fe_lakebase_storage_cost(storage_gb=8192)
        expected = 8192 * 15 * 0.023  # $2826.24
        assert be['storage_cost'] == pytest.approx(fe_storage, abs=TOL)
        assert be['storage_cost'] == pytest.approx(expected, abs=TOL)


class TestLakebaseTotalCost:
    """Total cost = compute DBU cost + storage cost."""

    def test_total_compute_plus_storage(self, pricing):
        """8 CU, 2 nodes, 500 GB, 730 hrs."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=8, lakebase_ha_nodes=2,
            lakebase_storage_gb=500, hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_lakebase_dbu_per_hour(cu=8, ha_nodes=2)
        fe_dbu_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=730, dbu_price=be['dbu_price'],
        )
        fe_storage = fe_lakebase_storage_cost(storage_gb=500)
        fe_total = fe_total_monthly_cost(
            dbu_cost=fe_dbu_cost, storage_cost=fe_storage,
        )
        assert be['total_cost'] == pytest.approx(fe_total, abs=TOL)

    def test_total_no_storage(self, pricing):
        """4 CU, 1 node, no storage → total = DBU cost only."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=4, lakebase_ha_nodes=1,
            lakebase_storage_gb=0, hours_per_month=730,
        )
        be = _get_be_results(item)
        fe_dbu_hr = fe_lakebase_dbu_per_hour(cu=4, ha_nodes=1)
        fe_dbu_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=730, dbu_price=be['dbu_price'],
        )
        assert be['total_cost'] == pytest.approx(fe_dbu_cost, abs=TOL)


class TestLakebaseRunBased:
    """Lakebase with run-based usage config."""

    def test_runs_per_day(self, pricing):
        """4 CU, 1 node, 8 runs/day × 60 min × 22 days = 176 hrs."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=4, lakebase_ha_nodes=1,
            runs_per_day=8, avg_runtime_minutes=60, days_per_month=22,
        )
        be = _get_be_results(item)
        expected_hours = 8 * (60 / 60) * 22  # 176
        assert be['hours'] == pytest.approx(expected_hours, abs=TOL)
        fe_dbu_hr = fe_lakebase_dbu_per_hour(cu=4, ha_nodes=1)
        fe_cost = fe_monthly_dbu_cost(
            dbu_per_hour=fe_dbu_hr, hours_per_month=expected_hours, dbu_price=be['dbu_price'],
        )
        assert be['dbu_cost'] == pytest.approx(fe_cost, abs=TOL)


class TestLakebaseEdgeCases:
    """Edge cases for Lakebase."""

    def test_zero_cu(self, pricing):
        """CU=0 → 0 DBU/hr."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=0, lakebase_ha_nodes=1,
            hours_per_month=730,
        )
        be = _get_be_results(item)
        assert be['dbu_hr'] == pytest.approx(0.0, abs=TOL)
        assert be['dbu_cost'] == pytest.approx(0.0, abs=TOL)

    def test_none_storage(self, pricing):
        """lakebase_storage_gb=None → 0 storage cost."""
        item = make_item(
            workload_type='LAKEBASE', lakebase_cu=4, lakebase_ha_nodes=1,
            lakebase_storage_gb=None, hours_per_month=730,
        )
        be = _get_be_results(item)
        assert be['storage_cost'] == pytest.approx(0.0, abs=TOL)
