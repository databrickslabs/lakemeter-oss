"""Shared test fixtures for Lakemeter calculation verification tests."""
import json
import os
import sys
import pytest

# Add backend to path so we can import app modules
BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, BACKEND_DIR)

PRICING_DIR = os.path.join(BACKEND_DIR, 'static', 'pricing')


@pytest.fixture(scope="session")
def instance_dbu_rates():
    """Load instance DBU rates from pricing JSON."""
    path = os.path.join(PRICING_DIR, 'instance-dbu-rates.json')
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def dbu_prices():
    """Load DBU $/DBU rates by region from pricing JSON."""
    path = os.path.join(PRICING_DIR, 'dbu-rates.json')
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def aws_instance_rates(instance_dbu_rates):
    """AWS-specific instance DBU rates."""
    return instance_dbu_rates.get('aws', {})


@pytest.fixture(scope="session")
def us_east_1_premium_rates(dbu_prices):
    """DBU $/DBU rates for aws:us-east-1:PREMIUM."""
    return dbu_prices.get('aws:us-east-1:PREMIUM', {})
