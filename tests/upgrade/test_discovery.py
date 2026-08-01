import base64
from types import SimpleNamespace

from upgrader.discovery import discover_installation


class FakeWorkspace:
    def __init__(self, files):
        self.files = files

    def export(self, path):
        if path not in self.files:
            raise RuntimeError("not found")
        return SimpleNamespace(
            content=base64.b64encode(self.files[path].encode()).decode()
        )


class FakeSecrets:
    def __init__(self, values):
        self.values = values

    def get_secret(self, scope, key):
        value = self.values[(scope, key)]
        return SimpleNamespace(
            value=base64.b64encode(value.encode()).decode()
        )


def make_client():
    source = "/Workspace/Users/owner/apps/custom-meter"
    active = f"{source}/releases/v0.2.0"
    resource_keys = {
        "custom-meter-lakebase-project": "project-secret",
        "custom-meter-lakebase-branch": "branch-secret",
        "custom-meter-lakebase-endpoint": "endpoint-secret",
        "custom-meter-db-host": "host-secret",
        "custom-meter-db-name": "database-secret",
        "custom-meter-db-user": "user-secret",
    }
    resources = [
        SimpleNamespace(
            name=name,
            secret=SimpleNamespace(scope="custom-secrets", key=key)
        )
        for name, key in resource_keys.items()
    ]
    app = SimpleNamespace(
        default_source_code_path=source,
        url="https://custom-meter.example",
        active_deployment=SimpleNamespace(source_code_path=active),
        resources=resources,
    )
    values = {
        ("custom-secrets", "project-secret"): "meter-project",
        ("custom-secrets", "branch-secret"): "production",
        ("custom-secrets", "endpoint-secret"): (
            "projects/meter-project/branches/production/endpoints/primary"
        ),
        ("custom-secrets", "host-secret"): "db.example",
        ("custom-secrets", "database-secret"): "meter_db",
        ("custom-secrets", "user-secret"): "meter_user",
    }
    return SimpleNamespace(
        apps=SimpleNamespace(get=lambda _name: app),
        current_user=SimpleNamespace(
            me=lambda: SimpleNamespace(user_name="owner@example.com")
        ),
        workspace=FakeWorkspace(
            {
                f"{active}/backend/app/version.py": 'APP_VERSION = "0.2.0"\n',
            }
        ),
        secrets=FakeSecrets(values),
    )


def test_discovery_preserves_custom_installation_names(monkeypatch):
    monkeypatch.setattr(
        "upgrader.discovery._read_version_from_app",
        lambda _client, _url: None,
    )
    installation = discover_installation(make_client(), "custom-meter")

    assert str(installation.installed_version) == "0.2.0"
    assert installation.source_path.endswith("/apps/custom-meter")
    assert installation.secret_scope == "custom-secrets"
    assert installation.database_name == "meter_db"
    assert installation.lakebase_project == "meter-project"
    assert installation.lakebase_branch == "production"
    assert installation.database_host_secret_key == "host-secret"
    assert installation.lakebase_endpoint_secret_key == "endpoint-secret"
    assert not installation.legacy_baseline


def test_unversioned_installation_uses_legacy_baseline(monkeypatch):
    client = make_client()
    client.workspace.files.clear()
    monkeypatch.setattr(
        "upgrader.discovery._read_version_from_app",
        lambda _client, _url: None,
    )
    installation = discover_installation(client, "custom-meter")

    assert str(installation.installed_version) == "0.1.0"
    assert installation.legacy_baseline
    assert installation.warnings


def test_versioned_default_source_keeps_stable_management_root(monkeypatch):
    client = make_client()
    app = client.apps.get("custom-meter")
    app.default_source_code_path = app.active_deployment.source_code_path
    monkeypatch.setattr(
        "upgrader.discovery._read_version_from_app",
        lambda _client, _url: None,
    )

    installation = discover_installation(client, "custom-meter")

    assert installation.source_path == (
        "/Workspace/Users/owner/apps/custom-meter"
    )
    assert installation.active_source_path.endswith("/releases/v0.2.0")
    assert installation.management_path.endswith(
        "/apps/custom-meter/.lakemeter"
    )

