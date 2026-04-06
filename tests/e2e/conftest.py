"""E2E test fixtures: TestClient, E2EClient, shared database session.

Uses the real Lakebase database via the OSS backend.
Run with: pytest tests/e2e/ -v --timeout=600
"""
import os
import sys
import uuid
import pytest

# Add backend to path
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Set required env vars before importing the app
_ENV_DEFAULTS = {
    "DATABRICKS_HOST": "https://fe-vm-lakemeter.cloud.databricks.com",
    "DATABRICKS_CONFIG_PROFILE": "lakemeter",
    "DATABRICKS_SECRETS_SCOPE": "lakemeter-secrets",
    "SP_CLIENT_ID_KEY": "sp_clientid",
    "SP_SECRET_KEY": "sp_secret",
    "LAKEBASE_INSTANCE_NAME": "lakemeter-customer",
    "DB_HOST": "ep-silent-fire-d1kv74l0.database.us-west-2.cloud.databricks.com",
    "DB_USER": "0a1a2461-5013-4110-94ff-f7157e7b8b8e",
    "DB_NAME": "lakemeter_pricing",
    "DB_PORT": "5432",
    "DB_SSLMODE": "require",
}
for key, default in _ENV_DEFAULTS.items():
    os.environ.setdefault(key, default)

from tests.e2e.helpers.api_client import E2EClient, AUTH_HEADERS  # noqa: E402


def _db_reachable() -> bool:
    """Quick check: can we connect to the Lakebase database?"""
    import socket
    host = os.environ.get("DB_HOST", "")
    if not host:
        return False
    try:
        socket.create_connection((host, 5432), timeout=5)
        return True
    except (socket.timeout, OSError):
        return False


_DB_AVAILABLE = _db_reachable()


@pytest.fixture(autouse=True)
def _skip_if_db_unreachable():
    """Auto-skip E2E tests when Lakebase is unreachable."""
    if not _DB_AVAILABLE:
        pytest.skip("Lakebase DB unreachable — skipping E2E test")


@pytest.fixture(scope="session")
def http_client():
    """FastAPI TestClient wrapping the real backend (with Lakebase)."""
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    from app.database import engine
    if engine:
        engine.dispose()


@pytest.fixture(scope="session")
def e2e_client(http_client):
    """E2EClient wrapper for convenient estimate/line-item/export operations."""
    client = E2EClient(http_client)
    yield client
    client.cleanup()


@pytest.fixture(scope="session")
def db_session():
    """Raw SQLAlchemy session for direct DB operations."""
    from app.database import get_db
    gen = get_db()
    db = next(gen)
    yield db
    try:
        next(gen)
    except StopIteration:
        pass
