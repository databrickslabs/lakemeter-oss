"""
Harness test fixtures — provides a live TestClient against the real FastAPI app
with a real Lakebase database connection.

These are integration tests that verify the full stack: API → Lakebase → response.
They require DATABASE_URL or Databricks credentials to be configured.
"""
import os
import uuid
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    """Create a TestClient bound to the real FastAPI app."""
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def db_session():
    """Get a raw SQLAlchemy session for direct DB operations."""
    from app.database import get_db
    gen = get_db()
    db = next(gen)
    yield db
    try:
        next(gen)
    except StopIteration:
        pass


@pytest.fixture(scope="session")
def test_user_id(client, db_session):
    """Create or fetch a test user and return user_id."""
    from app.models.user import User
    email = "harness-test@databricks.com"
    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            user_id=uuid.uuid4(),
            email=email,
            display_name="Harness Test User",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return str(user.user_id)


# ── Cloud / Region / Tier combos for the 6 estimates ─────────────────────────

ESTIMATE_CONFIGS = [
    {"name": "AWS US East PREMIUM", "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM"},
    {"name": "AWS EU West ENTERPRISE", "cloud": "AWS", "region": "eu-west-1", "tier": "ENTERPRISE"},
    {"name": "Azure East US PREMIUM", "cloud": "AZURE", "region": "eastus", "tier": "PREMIUM"},
    {"name": "Azure West Europe ENTERPRISE", "cloud": "AZURE", "region": "westeurope", "tier": "ENTERPRISE"},
    {"name": "GCP US Central PREMIUM", "cloud": "GCP", "region": "us-central1", "tier": "PREMIUM"},
    {"name": "GCP Europe West ENTERPRISE", "cloud": "GCP", "region": "europe-west1", "tier": "ENTERPRISE"},
]


@pytest.fixture(scope="session")
def estimate_configs():
    """Return the 6 estimate configurations (2 per cloud)."""
    return ESTIMATE_CONFIGS


# ── Workload definitions for generating ~100 line items per estimate ──────────

# Instance types per cloud for classic workloads
INSTANCE_TYPES = {
    "AWS": {
        "driver": ["i3.xlarge", "m5d.xlarge", "r5.xlarge"],
        "worker": ["i3.2xlarge", "m5d.2xlarge", "r5.2xlarge"],
    },
    "AZURE": {
        "driver": ["Standard_DS3_v2", "Standard_D4s_v3", "Standard_E4s_v3"],
        "worker": ["Standard_DS4_v2", "Standard_D8s_v3", "Standard_E8s_v3"],
    },
    "GCP": {
        "driver": ["n1-standard-4", "n2-standard-4", "n1-highmem-4"],
        "worker": ["n1-standard-8", "n2-standard-8", "n1-highmem-8"],
    },
}

DBSQL_WAREHOUSE_SIZES = ["2X-Small", "X-Small", "Small", "Medium", "Large", "X-Large"]
DLT_EDITIONS = ["CORE", "PRO", "ADVANCED"]
VECTOR_SEARCH_MODES = ["standard", "storage_optimized"]
LAKEBASE_CU_SIZES = [0.5, 1, 2, 4, 8, 16, 32]
GPU_TYPES = ["gpu_small_t4", "gpu_medium_a10g_1x", "gpu_large_a100_1x"]
MODEL_SERVING_SCALE_OUTS = ["small", "medium", "large"]


@pytest.fixture(scope="session")
def instance_types():
    return INSTANCE_TYPES
