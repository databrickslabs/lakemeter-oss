"""Parity tests for standard and OpenTelemetry Zerobus metering."""
import pytest

from app.routes.export.pricing import _get_dbu_price
from app.services.zerobus_pricing import calculate_zerobus_usage
from tests.parity.frontend_calc import fe_zerobus_cost


@pytest.mark.parametrize("mode", ["standard", "otel"])
@pytest.mark.parametrize(
    ("cloud", "region", "tier"),
    [
        ("aws", "us-east-1", "PREMIUM"),
        ("azure", "eastus", "PREMIUM"),
        ("gcp", "us-central1", "ENTERPRISE"),
    ],
)
def test_backend_frontend_zerobus_cost_parity(
    mode,
    cloud,
    region,
    tier,
):
    usage = calculate_zerobus_usage(12_345.67, mode)
    dbu_price, found = _get_dbu_price(
        cloud,
        region,
        tier,
        "JOBS_SERVERLESS_COMPUTE",
    )
    assert found is True
    backend_cost = usage["monthly_dbus"] * dbu_price
    frontend_cost = fe_zerobus_cost(
        monthly_ingested_gb=12_345.67,
        mode=mode,
        dbu_price=dbu_price,
    )
    assert backend_cost == pytest.approx(frontend_cost)
