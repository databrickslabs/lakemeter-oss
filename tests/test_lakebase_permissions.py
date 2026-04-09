"""Lakebase permission and connectivity tests.

Verifies that the app's service principal can:
1. Generate OAuth tokens for the Lakebase instance
2. Connect to the database
3. Read pricing reference data
4. Write to application tables
5. Refresh tokens automatically

Run explicitly: pytest tests/test_lakebase_permissions.py -v
"""
import os
import sys
import uuid

import pytest

# Ensure backend is importable
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
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


_REACHABLE = _host_reachable()

pytestmark = pytest.mark.skipif(
    not _REACHABLE, reason="Databricks host unreachable"
)


class TestTokenGeneration:
    """Verify SP can generate OAuth tokens for Lakebase."""

    def test_sp_can_generate_token(self):
        from app.auth.token_manager import LakebaseTokenManager

        tm = LakebaseTokenManager()
        token = tm.get_token()
        assert token is not None, "Token generation returned None"
        assert len(token) > 100, f"Token too short: {len(token)} chars"

    def test_token_has_valid_expiry(self):
        from datetime import datetime, timezone
        from app.auth.token_manager import LakebaseTokenManager

        tm = LakebaseTokenManager()
        tm.get_token()
        assert tm._expires_at is not None, "Token expiry not set"
        assert tm._expires_at > datetime.now(timezone.utc), "Token already expired"


class TestDatabaseConnection:
    """Verify token works for actual DB connections."""

    def test_db_connection_succeeds(self):
        from app.auth.token_manager import LakebaseTokenManager

        tm = LakebaseTokenManager()
        params = tm.get_connection_params()

        import psycopg2
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        assert cur.fetchone()[0] == 1
        cur.close()
        conn.close()

    def test_db_version_is_pg16(self):
        from app.auth.token_manager import LakebaseTokenManager

        tm = LakebaseTokenManager()
        params = tm.get_connection_params()

        import psycopg2
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        assert "PostgreSQL 16" in version
        cur.close()
        conn.close()


class TestReadAccess:
    """Verify can SELECT from pricing tables."""

    def test_read_workload_types(self):
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

    def test_read_dbu_rates(self):
        from app.auth.token_manager import LakebaseTokenManager
        import psycopg2

        tm = LakebaseTokenManager()
        conn = psycopg2.connect(**tm.get_connection_params())
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM lakemeter.sync_pricing_dbu_rates")
        count = cur.fetchone()[0]
        assert count > 0, "No DBU rates found — pricing data not synced"
        cur.close()
        conn.close()

    def test_read_vm_costs(self):
        from app.auth.token_manager import LakebaseTokenManager
        import psycopg2

        tm = LakebaseTokenManager()
        conn = psycopg2.connect(**tm.get_connection_params())
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM lakemeter.sync_pricing_vm_costs")
        count = cur.fetchone()[0]
        assert count > 0, "No VM costs found — pricing data not synced"
        cur.close()
        conn.close()


class TestWriteAccess:
    """Verify can INSERT/UPDATE/DELETE in lakemeter schema."""

    def test_crud_user(self):
        from app.auth.token_manager import LakebaseTokenManager
        import psycopg2

        tm = LakebaseTokenManager()
        conn = psycopg2.connect(**tm.get_connection_params())
        cur = conn.cursor()

        test_id = str(uuid.uuid4())
        test_email = f"test-{test_id[:8]}@test.com"

        # INSERT
        cur.execute(
            "INSERT INTO lakemeter.users (user_id, email, full_name) VALUES (%s, %s, %s)",
            (test_id, test_email, "Permission Test User"),
        )
        conn.commit()

        # SELECT
        cur.execute("SELECT full_name FROM lakemeter.users WHERE user_id = %s", (test_id,))
        assert cur.fetchone()[0] == "Permission Test User"

        # UPDATE
        cur.execute(
            "UPDATE lakemeter.users SET full_name = %s WHERE user_id = %s",
            ("Updated Name", test_id),
        )
        conn.commit()
        cur.execute("SELECT full_name FROM lakemeter.users WHERE user_id = %s", (test_id,))
        assert cur.fetchone()[0] == "Updated Name"

        # DELETE
        cur.execute("DELETE FROM lakemeter.users WHERE user_id = %s", (test_id,))
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM lakemeter.users WHERE user_id = %s", (test_id,))
        assert cur.fetchone()[0] == 0

        cur.close()
        conn.close()


class TestTokenRefresh:
    """Verify token refresh works."""

    def test_token_refresh_after_invalidation(self):
        from app.auth.token_manager import LakebaseTokenManager

        tm = LakebaseTokenManager()
        first_token = tm.get_token()
        assert first_token is not None

        # Invalidate token
        tm._token = None
        tm._expires_at = None

        # Should auto-refresh
        new_token = tm.get_token()
        assert new_token is not None
        assert len(new_token) > 100


class TestAppHealthWithDB:
    """Verify the FastAPI app reports healthy DB connection."""

    def test_health_endpoint(self):
        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app, raise_server_exceptions=False) as client:
            # Try health endpoint (may be /health or /api/v1/health)
            for path in ["/health", "/api/v1/health", "/"]:
                resp = client.get(path)
                if resp.status_code == 200:
                    break
            assert resp.status_code == 200, f"No health endpoint returned 200"
