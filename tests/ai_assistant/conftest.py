"""Shared fixtures for AI assistant end-to-end tests.

Uses FastAPI TestClient against the local backend. The backend uses
Databricks CLI token for FMAPI calls (model-serving scope) and
service principal for Lakebase DB access.

Run explicitly with:  pytest tests/ai_assistant/ --timeout=300
(AI tests are excluded from default `pytest` via pyproject.toml addopts.)
"""
import os
import sys
import uuid

import pytest

from tests.ai_assistant.chat_helpers import (  # noqa: F401 — re-export
    send_chat_message,
    extract_proposal,
    send_chat_until_proposal,
    confirm_proposal,
    reject_proposal,
    get_conversation_state,
    AUTH_EMAIL,
    AUTH_HEADERS,
)


def _fmapi_reachable() -> bool:
    """Quick check: can we reach the Databricks host?"""
    import socket
    host = os.environ.get("DATABRICKS_HOST", "")
    hostname = host.replace("https://", "").replace("http://", "").strip("/")
    if not hostname:
        return False
    try:
        socket.create_connection((hostname, 443), timeout=5)
        return True
    except (socket.timeout, OSError):
        return False


_FMAPI_AVAILABLE = _fmapi_reachable()

# Ensure backend is importable
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


@pytest.fixture(autouse=True)
def _skip_if_fmapi_unreachable():
    """Auto-skip AI tests when FMAPI endpoint is unreachable."""
    if not _FMAPI_AVAILABLE:
        pytest.skip("FMAPI unreachable — skipping AI assistant test")


@pytest.fixture(scope="session")
def http_client():
    """FastAPI TestClient wrapping the real backend (with Lakebase + FMAPI)."""
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

    from app.database import engine
    if engine:
        engine.dispose()


@pytest.fixture(scope="session")
def test_estimate(http_client):
    """Create a test estimate for the session, delete it afterwards."""
    payload = {
        "estimate_name": f"AI-Test-{uuid.uuid4().hex[:8]}",
        "cloud": "AWS",
        "region": "us-east-1",
        "tier": "PREMIUM",
    }
    resp = http_client.post(
        "/api/v1/estimates/", json=payload, headers=AUTH_HEADERS
    )
    assert resp.status_code == 201, f"Failed to create estimate: {resp.text}"
    estimate = resp.json()
    yield estimate
    http_client.delete(
        f"/api/v1/estimates/{estimate['estimate_id']}",
        headers=AUTH_HEADERS,
    )
