"""Unit tests for exact VM price resolution."""
from types import SimpleNamespace

import pytest

from app.services.vm_pricing_resolver import resolve_vm_hourly_rate


class _Result:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class PricingDB:
    def __init__(self, rates):
        self.rates = rates
        self.calls = []

    def execute(self, statement, params):
        assert "sync_pricing_vm_costs" in str(statement)
        self.calls.append(params)
        key = (
            params["cloud"],
            params["region"].lower(),
            params["instance_type"].lower(),
            params["pricing_tier"],
            params["payment_option"].lower(),
        )
        rate = self.rates.get(key)
        row = (
            SimpleNamespace(cost_per_hour=rate, source="test pricing")
            if rate is not None
            else None
        )
        return _Result(row)


def rate_key(cloud, region, instance_type, pricing_tier, payment_option):
    return (
        cloud.upper(),
        region.lower(),
        instance_type.lower(),
        pricing_tier,
        payment_option.lower(),
    )


def test_reserved_rate_uses_canonical_tier_and_payment_option():
    db = PricingDB({
        rate_key(
            "AWS", "us-east-1", "i3.xlarge", "reserved_1y", "all_upfront"
        ): 0.229909,
    })

    result = resolve_vm_hourly_rate(
        db,
        cloud="aws",
        region="us-east-1",
        instance_type="i3.xlarge",
        pricing_tier="reserved_1y",
        payment_option="all_upfront",
        fallback_prices={"on_demand": 0.312},
    )

    assert result.rate == pytest.approx(0.229909)
    assert result.warning is None
    assert db.calls[0]["pricing_tier"] == "reserved_1y"
    assert db.calls[0]["payment_option"] == "all_upfront"


def test_aws_reserved_na_payment_defaults_to_no_upfront():
    db = PricingDB({
        rate_key(
            "AWS", "us-east-1", "i3.2xlarge", "reserved_1y", "no_upfront"
        ): 0.405854,
    })

    result = resolve_vm_hourly_rate(
        db,
        cloud="aws",
        region="us-east-1",
        instance_type="i3.2xlarge",
        pricing_tier="reserved_1y",
        payment_option="NA",
        fallback_prices={"on_demand": 0.624},
    )

    assert result.rate == pytest.approx(0.405854)
    assert result.warning is None
    assert db.calls[0]["payment_option"] == "no_upfront"


@pytest.mark.parametrize(
    ("cloud", "instance_type", "spot_rate"),
    [
        ("AZURE", "Standard_DS3_v2", 0.1172),
        ("GCP", "n1-standard-4", 0.045),
    ],
)
def test_spot_rate_is_resolved_exactly_for_each_cloud(
    cloud,
    instance_type,
    spot_rate,
):
    db = PricingDB({
        rate_key(
            cloud, "us-east-1", instance_type, "spot", "NA"
        ): spot_rate,
    })

    result = resolve_vm_hourly_rate(
        db,
        cloud=cloud,
        region="us-east-1",
        instance_type=instance_type,
        pricing_tier="spot",
        payment_option=None,
        fallback_prices={"on_demand": 0.293},
    )

    assert result.rate == pytest.approx(spot_rate)
    assert result.warning is None
    assert db.calls[0]["payment_option"] == "NA"


def test_missing_spot_rate_uses_on_demand_without_inventing_discount():
    result = resolve_vm_hourly_rate(
        None,
        cloud="azure",
        region="eastus",
        instance_type="Standard_DS3_v2",
        pricing_tier="spot",
        fallback_prices={"on_demand": 0.293},
    )

    assert result.rate == pytest.approx(0.293)
    assert result.rate != pytest.approx(0.293 * 0.30)
    assert "conservative fallback" in result.warning


def test_estimated_database_rate_is_explicitly_annotated():
    class EstimatedDB(PricingDB):
        def execute(self, statement, params):
            self.calls.append(params)
            row = SimpleNamespace(
                cost_per_hour=0.0879,
                source="DEPRECATED - Estimated historical pricing",
            )
            return _Result(row)

    result = resolve_vm_hourly_rate(
        EstimatedDB({}),
        cloud="azure",
        region="eastus",
        instance_type="Standard_DS3_v2",
        pricing_tier="spot",
        fallback_prices={"on_demand": 0.293},
    )

    assert result.rate == pytest.approx(0.0879)
    assert "estimated pricing source" in result.warning
