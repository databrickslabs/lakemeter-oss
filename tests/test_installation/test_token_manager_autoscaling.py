import importlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from google.protobuf.timestamp_pb2 import Timestamp


def test_token_manager_prefers_direct_autoscaling_endpoint(monkeypatch):
    backend_dir = str(Path(__file__).resolve().parents[2] / "backend")
    monkeypatch.syspath_prepend(backend_dir)
    endpoint_name = (
        "projects/lakemeter/branches/production/endpoints/primary"
    )
    monkeypatch.setenv("DATABRICKS_HOST", "https://workspace.example")
    monkeypatch.setenv("LAKEBASE_PROJECT", "projects/lakemeter")
    monkeypatch.setenv(
        "LAKEBASE_BRANCH",
        "projects/lakemeter/branches/production",
    )
    monkeypatch.setenv("LAKEBASE_ENDPOINT", endpoint_name)
    monkeypatch.delenv("LAKEBASE_INSTANCE_NAME", raising=False)

    calls = []

    class Postgres:
        def generate_database_credential(self, endpoint):
            calls.append(endpoint)
            expire_time = Timestamp()
            expire_time.FromDatetime(
                datetime.now(timezone.utc) + timedelta(hours=1)
            )
            return SimpleNamespace(
                token="direct-token",
                expire_time=expire_time,
            )

    class LegacyDatabase:
        def generate_database_credential(self, **_kwargs):
            raise AssertionError("legacy Database Instance API was called")

    class CurrentUser:
        def me(self):
            return SimpleNamespace(user_name="app-client-id")

    class FakeWorkspaceClient:
        def __init__(self, *_args, **_kwargs):
            self.postgres = Postgres()
            self.database = LegacyDatabase()
            self.current_user = CurrentUser()

    import databricks.sdk

    monkeypatch.setattr(databricks.sdk, "WorkspaceClient", FakeWorkspaceClient)
    sys.modules.pop("app.auth.token_manager", None)
    token_manager_module = importlib.import_module("app.auth.token_manager")

    manager = token_manager_module.LakebaseTokenManager()

    assert manager.get_token() == "direct-token"
    assert manager.db_user == "app-client-id"
    assert calls and all(call == endpoint_name for call in calls)


def test_source_install_uses_app_identity_for_oauth(monkeypatch):
    from app.auth.token_manager import LakebaseTokenManager

    monkeypatch.setenv("LAKEBASE_ENDPOINT", "projects/p/branches/b/endpoints/e")
    monkeypatch.setenv("DB_USER", "lakemeter_sync_role")
    monkeypatch.delenv("PGUSER", raising=False)

    expire_time = Timestamp()
    expire_time.FromDatetime(
        datetime.now(timezone.utc) + timedelta(hours=1)
    )
    client = SimpleNamespace(
        postgres=SimpleNamespace(
            generate_database_credential=lambda **_kwargs: SimpleNamespace(
                token="source-oauth-token",
                expire_time=expire_time,
            )
        ),
        current_user=SimpleNamespace(
            me=lambda: SimpleNamespace(user_name="source-app-client-id")
        ),
    )

    def init_client(self):
        self._workspace_client = client

    monkeypatch.setattr(
        LakebaseTokenManager,
        "_init_workspace_client",
        init_client,
    )

    manager = LakebaseTokenManager()

    assert manager.db_user == "source-app-client-id"
    assert manager.get_connection_params()["password"] == "source-oauth-token"


def test_marketplace_preserves_postgres_binding_user(monkeypatch):
    from app.auth.token_manager import LakebaseTokenManager

    monkeypatch.setenv("LAKEBASE_ENDPOINT", "projects/p/branches/b/endpoints/e")
    monkeypatch.setenv("PGUSER", "marketplace-binding-role")
    monkeypatch.setenv("DB_USER", "lakemeter_sync_role")

    expire_time = Timestamp()
    expire_time.FromDatetime(
        datetime.now(timezone.utc) + timedelta(hours=1)
    )
    client = SimpleNamespace(
        postgres=SimpleNamespace(
            generate_database_credential=lambda **_kwargs: SimpleNamespace(
                token="marketplace-oauth-token",
                expire_time=expire_time,
            )
        ),
        current_user=SimpleNamespace(
            me=lambda: SimpleNamespace(user_name="app-client-id")
        ),
    )

    def init_client(self):
        self._workspace_client = client

    monkeypatch.setattr(
        LakebaseTokenManager,
        "_init_workspace_client",
        init_client,
    )

    manager = LakebaseTokenManager()

    assert manager.db_user == "marketplace-binding-role"
    assert manager.get_connection_params()["password"] == (
        "marketplace-oauth-token"
    )

