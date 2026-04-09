"""Integration validation: SP OAuth flow and app health.

Tests are skip-guarded — they only run when the Databricks host is reachable.
This mirrors the guard pattern in test_lakebase_permissions.py.
"""
import os
import socket
import sys

import pytest

# Ensure backend is importable
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Set required env vars before importing app modules
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


def _host_reachable() -> bool:
    host = os.environ.get("DATABRICKS_HOST", "")
    hostname = host.replace("https://", "").replace("http://", "").strip("/")
    if not hostname:
        return False
    try:
        socket.create_connection((hostname, 443), timeout=5)
        return True
    except (socket.timeout, OSError):
        return False


_REACHABLE = _host_reachable()

pytestmark = pytest.mark.skipif(
    not _REACHABLE, reason="Databricks host unreachable — skipping live integration tests"
)


class TestSPOAuthFlow:
    """End-to-end SP OAuth flow: token → connect → query."""

    def test_full_oauth_flow(self):
        """Token generation → DB connection → query execution in one flow."""
        from app.auth.token_manager import LakebaseTokenManager
        import psycopg2

        # Step 1: Generate token
        tm = LakebaseTokenManager()
        token = tm.get_token()
        assert token is not None, "Token generation failed"
        assert len(token) > 100, f"Token suspiciously short: {len(token)}"

        # Step 2: Connect to DB
        params = tm.get_connection_params()
        conn = psycopg2.connect(**params)
        assert conn is not None, "Connection failed"

        # Step 3: Execute query
        cur = conn.cursor()
        cur.execute("SELECT current_database(), current_schema()")
        db, schema = cur.fetchone()
        assert db == "lakemeter_pricing", f"Unexpected database: {db}"

        cur.close()
        conn.close()

    def test_token_reuse_across_connections(self):
        """Same token manager can serve multiple connections."""
        from app.auth.token_manager import LakebaseTokenManager
        import psycopg2

        tm = LakebaseTokenManager()

        # First connection
        conn1 = psycopg2.connect(**tm.get_connection_params())
        cur1 = conn1.cursor()
        cur1.execute("SELECT 1")
        assert cur1.fetchone()[0] == 1
        cur1.close()
        conn1.close()

        # Second connection (token should be cached)
        conn2 = psycopg2.connect(**tm.get_connection_params())
        cur2 = conn2.cursor()
        cur2.execute("SELECT 1")
        assert cur2.fetchone()[0] == 1
        cur2.close()
        conn2.close()


class TestAppHealthEndpoint:
    """Verify FastAPI health endpoint with DB integration."""

    def test_health_returns_200(self):
        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/health")
            assert resp.status_code == 200, (
                f"Health endpoint returned {resp.status_code}: {resp.text}"
            )

    def test_health_response_structure(self):
        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/health")
            if resp.status_code == 200:
                data = resp.json()
                assert "status" in data, "Health response missing 'status' field"
                assert data["status"] == "healthy"


class TestPricingDataAccess:
    """Verify DB has pricing data accessible via SP credentials."""

    def test_workload_types_count(self):
        from app.auth.token_manager import LakebaseTokenManager
        import psycopg2

        tm = LakebaseTokenManager()
        conn = psycopg2.connect(**tm.get_connection_params())
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM lakemeter.ref_workload_types")
        count = cur.fetchone()[0]
        assert count == 9, f"Expected 9 workload types, got {count}"
        cur.close()
        conn.close()

    def test_all_workload_type_names(self):
        from app.auth.token_manager import LakebaseTokenManager
        import psycopg2

        tm = LakebaseTokenManager()
        conn = psycopg2.connect(**tm.get_connection_params())
        cur = conn.cursor()
        cur.execute(
            "SELECT workload_type FROM lakemeter.ref_workload_types ORDER BY workload_type"
        )
        types = sorted([row[0] for row in cur.fetchall()])
        expected = sorted([
            "ALL_PURPOSE", "DBSQL", "DLT", "FMAPI_DATABRICKS",
            "FMAPI_PROPRIETARY", "JOBS", "LAKEBASE",
            "MODEL_SERVING", "VECTOR_SEARCH",
        ])
        assert types == expected, f"Workload types mismatch: {types}"
        cur.close()
        conn.close()

    def test_dbu_rates_populated(self):
        from app.auth.token_manager import LakebaseTokenManager
        import psycopg2

        tm = LakebaseTokenManager()
        conn = psycopg2.connect(**tm.get_connection_params())
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM lakemeter.sync_pricing_dbu_rates")
        count = cur.fetchone()[0]
        assert count > 100, f"Expected many DBU rates, got {count}"
        cur.close()
        conn.close()
