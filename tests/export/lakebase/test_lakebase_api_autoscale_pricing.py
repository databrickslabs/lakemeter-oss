from types import SimpleNamespace

import pytest

from app.routes.calculate import lakebase_calc
from app.routes.calculate.lakebase_calc import calculate_lakebase_cost
from app.routes.calculate.schemas import LakebaseCalculationRequest


class _Result:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _FakeDb:
    def execute(self, *_args, **_kwargs):
        return _Result(SimpleNamespace(price_per_dbu=0.63))


class _MissingPriceDb:
    def execute(self, *_args, **_kwargs):
        return _Result(None)


@pytest.fixture(autouse=True)
def _patch_validation(monkeypatch):
    monkeypatch.setattr(lakebase_calc, "validate_cloud", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(lakebase_calc, "validate_region", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(lakebase_calc, "validate_tier", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(lakebase_calc, "get_product_type_for_pricing", lambda *_args, **_kwargs: "DATABASE_SERVERLESS_COMPUTE")


def _calculate(**overrides):
    payload = {
        "cloud": "AWS",
        "region": "us-east-1",
        "tier": "PREMIUM",
        "cu_size": 1,
        "compute_mode": "autoscale",
        "min_cu": 1,
        "max_cu": 16,
        "scale_to_zero_enabled": False,
        "active_hours_per_month": 730,
        "scale_up_hours_per_month": 50,
        "always_on_discount_pct": 25,
        "num_nodes": 1,
        "storage_gb": 0,
        "pitr_gb": 0,
        "snapshot_gb": 0,
    }
    payload.update(overrides)
    db = payload.pop("_db", _FakeDb())
    return calculate_lakebase_cost(LakebaseCalculationRequest(**payload), db=db)["data"]


def test_api_splits_always_on_minimum_and_normal_scale_up_skus():
    data = _calculate()

    min_dbu_before_discount = 1 * 0.230 * (730 - 50)
    min_billable_dbu = min_dbu_before_discount * 0.75
    max_dbu = 16 * 0.230 * 50
    normal_price = 0.63

    calc = data["dbu_calculation"]
    assert calc["dbu_per_month"] == pytest.approx(min_billable_dbu + max_dbu)
    assert calc["baseline_dbu_before_discount"] == pytest.approx(min_dbu_before_discount)
    assert calc["baseline_billable_dbu"] == pytest.approx(min_billable_dbu)
    assert calc["scale_up_dbu"] == pytest.approx(max_dbu)
    assert calc["baseline_sku_price"] == pytest.approx(normal_price)
    assert calc["scale_up_sku_price"] == pytest.approx(normal_price)
    assert calc["baseline_effective_dbu_per_cu_hour"] == pytest.approx(0.230 * 0.75)
    assert calc["scale_up_effective_dbu_per_cu_hour"] == pytest.approx(0.230)
    assert calc["baseline_cu_hour_price"] == pytest.approx(0.230 * 0.75 * normal_price)
    assert calc["scale_up_cu_hour_price"] == pytest.approx(0.230 * normal_price)
    assert calc["dbu_cost_per_month"] == pytest.approx((min_billable_dbu + max_dbu) * normal_price, abs=0.01)

    compute_lines = [line for line in data["sku_breakdown"] if line["type"] == "dbu"]
    assert len(compute_lines) == 2
    assert compute_lines[0]["sku"] == "DATABASE_SERVERLESS_COMPUTE"
    assert compute_lines[0]["rate_type"] == "always_on_minimum"
    assert compute_lines[0]["qty"] == pytest.approx(min_billable_dbu)
    assert compute_lines[0]["unit_price_before_discount"] == pytest.approx(normal_price)
    assert compute_lines[1]["sku"] == "DATABASE_SERVERLESS_COMPUTE"
    assert compute_lines[1]["rate_type"] == "scale_up_max"
    assert compute_lines[1]["qty"] == pytest.approx(max_dbu)
    assert compute_lines[1]["unit_price_before_discount"] == pytest.approx(normal_price)


def test_api_does_not_discount_minimum_when_scale_to_zero_is_on():
    data = _calculate(
        scale_to_zero_enabled=True,
        active_hours_per_month=200,
        scale_up_hours_per_month=50,
    )

    min_dbu = 1 * 0.230 * (200 - 50)
    max_dbu = 16 * 0.230 * 50

    calc = data["dbu_calculation"]
    assert calc["baseline_discount_pct"] == 0
    assert calc["baseline_sku_price"] == pytest.approx(0.63)
    assert calc["scale_up_sku_price"] == pytest.approx(0.63)
    assert calc["dbu_cost_per_month"] == pytest.approx((min_dbu + max_dbu) * 0.63, abs=0.01)

    compute_lines = [line for line in data["sku_breakdown"] if line["type"] == "dbu"]
    assert len(compute_lines) == 2
    assert compute_lines[0]["sku"] == "DATABASE_SERVERLESS_COMPUTE"
    assert compute_lines[0]["rate_type"] == "always_on_minimum"
    assert compute_lines[0]["qty"] == pytest.approx(min_dbu)
    assert compute_lines[0]["unit_price_before_discount"] == pytest.approx(0.63)
    assert compute_lines[1]["sku"] == "DATABASE_SERVERLESS_COMPUTE"
    assert compute_lines[1]["rate_type"] == "scale_up_max"
    assert compute_lines[1]["qty"] == pytest.approx(max_dbu)
    assert compute_lines[1]["unit_price_before_discount"] == pytest.approx(0.63)


def test_api_falls_back_to_static_lookup_when_database_price_is_missing():
    data = _calculate(
        _db=_MissingPriceDb(),
        region="eu-north-1",
        tier="PREMIUM",
        min_cu=1,
        max_cu=1,
        scale_up_hours_per_month=0,
    )

    calc = data["dbu_calculation"]
    assert calc["dbu_price"] == pytest.approx(0.412)
    assert calc["baseline_sku_price"] == pytest.approx(0.412)
    assert calc["baseline_effective_dbu_per_cu_hour"] == pytest.approx(0.230 * 0.75)
    assert calc["baseline_cu_hour_price"] == pytest.approx(0.230 * 0.75 * 0.412)
    assert calc["dbu_cost_per_month"] == pytest.approx(1 * 0.230 * 0.75 * 730 * 0.412, abs=0.01)
