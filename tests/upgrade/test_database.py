from types import SimpleNamespace

from upgrader.database import create_database_backup, point_app_to_backup
from upgrader.models import Installation, SemVer


def installation():
    return Installation(
        app_name="meter",
        app_url="https://meter.example",
        source_path="/Workspace/apps/meter",
        active_source_path="/Workspace/apps/meter/releases/v0.2.0",
        installed_version=SemVer.parse("0.2.0"),
        workspace_user="owner@example.com",
        database_host="primary.example",
        database_host_secret_scope="custom-scope",
        database_host_secret_key="custom-host",
        lakebase_project="meter-project",
        lakebase_branch="production",
        lakebase_branch_secret_scope="custom-scope",
        lakebase_branch_secret_key="custom-branch",
        lakebase_endpoint=(
            "projects/meter-project/branches/production/endpoints/primary"
        ),
        lakebase_endpoint_secret_scope="custom-scope",
        lakebase_endpoint_secret_key="custom-endpoint",
    )


def test_backup_creates_ready_non_expiring_endpoint(monkeypatch):
    captured = {}
    branch_name = "projects/meter-project/branches/backup"
    endpoint_name = f"{branch_name}/endpoints/lakemeter-rollback"

    class Operation:
        def __init__(self, value):
            self.value = value

        def wait(self):
            return self.value

    class Postgres:
        def create_branch(self, **kwargs):
            captured["branch"] = kwargs["branch"]
            return Operation(SimpleNamespace(name=branch_name))

        def list_endpoints(self, parent):
            assert parent == branch_name
            return []

        def get_endpoint(self, name):
            if name.endswith("/production/endpoints/primary"):
                return SimpleNamespace(
                    spec=SimpleNamespace(
                        endpoint_type="READ_WRITE",
                        autoscaling_limit_min_cu=1.0,
                        autoscaling_limit_max_cu=4.0,
                        no_suspension=False,
                        settings=None,
                        suspend_timeout_duration=None,
                    )
                )
            assert name == endpoint_name
            return SimpleNamespace(
                name=endpoint_name,
                status=SimpleNamespace(
                    hosts=SimpleNamespace(host="backup.example")
                ),
            )

        def create_endpoint(self, **kwargs):
            captured["endpoint"] = kwargs["endpoint"]
            return Operation(SimpleNamespace(name=endpoint_name))

        def generate_database_credential(self, endpoint):
            assert endpoint == endpoint_name
            return SimpleNamespace(token="credential")

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def execute(self, statement):
            assert statement == "SELECT 1"

        def fetchone(self):
            return (1,)

    connection = SimpleNamespace(
        cursor=lambda: Cursor(),
        close=lambda: captured.update(connection_closed=True),
    )
    monkeypatch.setattr(
        "upgrader.database.psycopg2.connect",
        lambda **kwargs: captured.update(connection=kwargs) or connection,
    )
    client = SimpleNamespace(
        postgres=Postgres(),
        current_user=SimpleNamespace(
            me=lambda: SimpleNamespace(user_name="owner@example.com")
        ),
    )

    backup = create_database_backup(client, installation(), "0.3.0")

    assert captured["branch"].spec.no_expiry is True
    assert captured["endpoint"].spec.disabled is False
    assert backup.host == "backup.example"
    assert backup.endpoint_name == endpoint_name
    assert captured["connection"]["password"] == "credential"
    assert captured["connection_closed"]


def test_database_rollback_updates_custom_host_endpoint_and_branch_secrets():
    writes = []
    client = SimpleNamespace(
        secrets=SimpleNamespace(
            put_secret=lambda **kwargs: writes.append(kwargs)
        )
    )
    backup = SimpleNamespace(
        host="backup.example",
        endpoint_name="projects/p/branches/backup/endpoints/primary",
        resource_name="projects/p/branches/backup",
    )

    point_app_to_backup(client, installation(), backup)

    assert {(item["key"], item["string_value"]) for item in writes} == {
        ("custom-host", "backup.example"),
        (
            "custom-endpoint",
            "projects/p/branches/backup/endpoints/primary",
        ),
        ("custom-branch", "projects/p/branches/backup"),
    }

