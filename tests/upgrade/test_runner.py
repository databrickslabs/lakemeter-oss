from types import SimpleNamespace

import pytest

from upgrader.database import DatabaseBackup
from upgrader.models import (
    Installation,
    ReleaseAction,
    ReleaseManifest,
    SemVer,
    UpgradePlan,
)
from upgrader.runner import (
    UpgradeExecutionError,
    apply_upgrade,
    rollback_upgrade,
    run_command,
)
from upgrader.state import WorkspaceStateStore

from .test_state import FakeWorkspaceFiles


def test_code_only_patch_never_touches_database(monkeypatch, tmp_path):
    client = SimpleNamespace(workspace=FakeWorkspaceFiles())
    installation = Installation(
        app_name="lakemeter",
        app_url="https://lakemeter.example",
        source_path="/Workspace/apps/lakemeter",
        active_source_path="/Workspace/apps/lakemeter/releases/v0.1.0",
        installed_version=SemVer.parse("0.1.0"),
        workspace_user="owner@example.com",
    )
    manifest = ReleaseManifest(
        version=SemVer.parse("0.1.1"),
        operation="code_only",
        minimum_version=SemVer.parse("0.1.0"),
    )
    plan = UpgradePlan(
        installation=installation,
        manifest=manifest,
        transition="patch",
        run_id="lakemeter-v0.1.1",
    )

    calls = []
    monkeypatch.setattr(
        "upgrader.runner.read_workspace_file",
        lambda *_args: b"live: app-yaml",
    )
    monkeypatch.setattr(
        "upgrader.runner.stage_runtime",
        lambda *_args, **_kwargs: calls.append("stage") or {"uploaded_files": 1},
    )
    monkeypatch.setattr(
        "upgrader.runner.deploy_app",
        lambda *_args, **_kwargs: calls.append("deploy") or "deployment-1",
    )
    monkeypatch.setattr(
        "upgrader.runner.verify_app",
        lambda *_args, **_kwargs: calls.append("verify") or {"ok": True},
    )
    monkeypatch.setattr(
        "upgrader.runner.create_database_backup",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("database backup must not run")
        ),
    )
    monkeypatch.setattr(
        "upgrader.runner.connect_as_owner",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("database connection must not run")
        ),
    )

    result = apply_upgrade(client, plan, tmp_path)

    assert result["status"] == "succeeded"
    assert calls == ["stage", "deploy", "verify"]
    state = WorkspaceStateStore(
        client,
        installation.management_path,
    ).load_installation()
    assert state["installed_version"] == "0.1.1"


def test_failed_patch_restores_previous_metadata_and_releases_lock(
    monkeypatch,
    tmp_path,
):
    client = SimpleNamespace(workspace=FakeWorkspaceFiles())
    installation = Installation(
        app_name="lakemeter",
        app_url="https://lakemeter.example",
        source_path="/Workspace/apps/lakemeter",
        active_source_path="/Workspace/apps/lakemeter/releases/v0.1.0",
        installed_version=SemVer.parse("0.1.0"),
        workspace_user="owner@example.com",
    )
    plan = UpgradePlan(
        installation=installation,
        manifest=ReleaseManifest(
            version=SemVer.parse("0.1.1"),
            operation="code_only",
            minimum_version=SemVer.parse("0.1.0"),
        ),
        transition="patch",
        run_id="lakemeter-v0.1.1",
    )
    store = WorkspaceStateStore(client, installation.management_path)
    store.save_installation(
        {
            "app_name": "lakemeter",
            "installed_version": "0.1.0",
            "release_path": installation.active_source_path,
            "applied_data_updates": ["seed"],
        }
    )
    deployments = []
    monkeypatch.setattr(
        "upgrader.runner.read_workspace_file",
        lambda *_args: b"live: app-yaml",
    )
    monkeypatch.setattr(
        "upgrader.runner.stage_runtime",
        lambda *_args, **_kwargs: {"uploaded_files": 1},
    )
    monkeypatch.setattr(
        "upgrader.runner.deploy_app",
        lambda _client, _app, source: deployments.append(source)
        or f"deployment-{len(deployments)}",
    )
    monkeypatch.setattr(
        "upgrader.runner.verify_app",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("verification failed")
        ),
    )

    with pytest.raises(UpgradeExecutionError, match="verification failed"):
        apply_upgrade(client, plan, tmp_path)

    assert deployments == [
        "/Workspace/apps/lakemeter/releases/v0.1.1",
        "/Workspace/apps/lakemeter/releases/v0.1.0",
    ]
    assert store.load_installation()["installed_version"] == "0.1.0"
    assert store.load_installation()["applied_data_updates"] == ["seed"]
    assert store.load_current_run()["status"] == "rolled_back"
    assert store._read_json(store.lock_path) is None


def test_database_upgrade_restarts_app_before_deployment(monkeypatch, tmp_path):
    client = SimpleNamespace(workspace=FakeWorkspaceFiles())
    installation = Installation(
        app_name="lakemeter",
        app_url="https://lakemeter.example",
        source_path="/Workspace/apps/lakemeter",
        active_source_path="/Workspace/apps/lakemeter/releases/v0.1.2",
        installed_version=SemVer.parse("0.1.2"),
        workspace_user="owner@example.com",
        database_host="primary.example",
        database_host_secret_scope="scope",
        database_host_secret_key="host",
        lakebase_project="projects/meter",
        lakebase_branch="projects/meter/branches/production",
        lakebase_branch_secret_scope="scope",
        lakebase_branch_secret_key="branch",
        lakebase_endpoint=(
            "projects/meter/branches/production/endpoints/primary"
        ),
        lakebase_endpoint_secret_scope="scope",
        lakebase_endpoint_secret_key="endpoint",
    )
    action = ReleaseAction(
        action_id="refresh",
        path="scripts/upgrades/data_updates/refresh.sql",
        sha256="a" * 64,
    )
    plan = UpgradePlan(
        installation=installation,
        manifest=ReleaseManifest(
            version=SemVer.parse("0.2.0"),
            operation="data_update",
            minimum_version=SemVer.parse("0.1.0"),
            data_updates=(action,),
        ),
        transition="minor",
        run_id="lakemeter-v0.2.0",
    )
    calls = []
    connection = SimpleNamespace(
        close=lambda: calls.append("close"),
    )
    backup = DatabaseBackup(
        kind="lakebase_branch",
        resource_name="projects/meter/branches/backup",
        endpoint_name="projects/meter/branches/backup/endpoints/primary",
        host="backup.example",
        original_host="primary.example",
    )

    monkeypatch.setattr(
        "upgrader.runner.read_workspace_file",
        lambda *_args: b"live: app-yaml",
    )
    monkeypatch.setattr(
        "upgrader.runner.connect_as_owner",
        lambda *_args: connection,
    )
    monkeypatch.setattr(
        "upgrader.runner.acquire_advisory_lock",
        lambda *_args: calls.append("lock"),
    )
    monkeypatch.setattr(
        "upgrader.runner.release_advisory_lock",
        lambda *_args: calls.append("unlock"),
    )
    monkeypatch.setattr(
        "upgrader.runner.set_app_running",
        lambda _client, _app, running: calls.append(
            "start" if running else "stop"
        ),
    )
    monkeypatch.setattr(
        "upgrader.runner.create_database_backup",
        lambda *_args: calls.append("backup") or backup,
    )
    monkeypatch.setattr(
        "upgrader.runner.execute_sql_actions",
        lambda **_kwargs: calls.append("data") or ["refresh"],
    )
    monkeypatch.setattr(
        "upgrader.runner.stage_runtime",
        lambda *_args, **_kwargs: calls.append("stage")
        or {"uploaded_files": 1},
    )

    def deploy(_client, _app, _source):
        assert "start" in calls
        calls.append("deploy")
        return "deployment-1"

    monkeypatch.setattr("upgrader.runner.deploy_app", deploy)
    monkeypatch.setattr(
        "upgrader.runner.verify_app",
        lambda *_args, **_kwargs: calls.append("verify") or {"ok": True},
    )

    result = apply_upgrade(client, plan, tmp_path)

    assert result["status"] == "succeeded"
    assert calls.index("stop") < calls.index("data")
    assert calls.index("data") < calls.index("start")
    assert calls.index("start") < calls.index("deploy")


def test_database_failure_restarts_app_before_recovery_deployment(
    monkeypatch,
    tmp_path,
):
    client = SimpleNamespace(workspace=FakeWorkspaceFiles())
    installation = Installation(
        app_name="lakemeter",
        app_url="https://lakemeter.example",
        source_path="/Workspace/apps/lakemeter",
        active_source_path="/Workspace/apps/lakemeter/releases/v0.1.2",
        installed_version=SemVer.parse("0.1.2"),
        workspace_user="owner@example.com",
        database_host="primary.example",
        database_host_secret_scope="scope",
        database_host_secret_key="host",
        lakebase_project="projects/meter",
        lakebase_branch="projects/meter/branches/production",
        lakebase_branch_secret_scope="scope",
        lakebase_branch_secret_key="branch",
        lakebase_endpoint=(
            "projects/meter/branches/production/endpoints/primary"
        ),
        lakebase_endpoint_secret_scope="scope",
        lakebase_endpoint_secret_key="endpoint",
    )
    action = ReleaseAction(
        action_id="refresh",
        path="scripts/upgrades/data_updates/refresh.sql",
        sha256="a" * 64,
    )
    plan = UpgradePlan(
        installation=installation,
        manifest=ReleaseManifest(
            version=SemVer.parse("0.2.0"),
            operation="data_update",
            minimum_version=SemVer.parse("0.1.0"),
            data_updates=(action,),
        ),
        transition="minor",
        run_id="lakemeter-v0.2.0",
    )
    calls = []
    connection = SimpleNamespace(close=lambda: calls.append("close"))
    backup = DatabaseBackup(
        kind="lakebase_branch",
        resource_name="projects/meter/branches/backup",
        endpoint_name="projects/meter/branches/backup/endpoints/primary",
        host="backup.example",
        original_host="primary.example",
    )

    monkeypatch.setattr(
        "upgrader.runner.read_workspace_file",
        lambda *_args: b"live: app-yaml",
    )
    monkeypatch.setattr(
        "upgrader.runner.connect_as_owner",
        lambda *_args: connection,
    )
    monkeypatch.setattr(
        "upgrader.runner.acquire_advisory_lock",
        lambda *_args: calls.append("lock"),
    )
    monkeypatch.setattr(
        "upgrader.runner.release_advisory_lock",
        lambda *_args: calls.append("unlock"),
    )
    monkeypatch.setattr(
        "upgrader.runner.set_app_running",
        lambda _client, _app, running: calls.append(
            "start" if running else "stop"
        ),
    )
    monkeypatch.setattr(
        "upgrader.runner.create_database_backup",
        lambda *_args: calls.append("backup") or backup,
    )
    monkeypatch.setattr(
        "upgrader.runner.execute_sql_actions",
        lambda **_kwargs: calls.append("data")
        or (_ for _ in ()).throw(RuntimeError("database update failed")),
    )
    monkeypatch.setattr(
        "upgrader.runner.point_app_to_backup",
        lambda *_args: calls.append("point-backup"),
    )

    def deploy(_client, _app, source):
        assert source == installation.active_source_path
        assert "start" in calls
        calls.append("deploy-previous")
        return "rollback-deployment"

    monkeypatch.setattr("upgrader.runner.deploy_app", deploy)

    with pytest.raises(UpgradeExecutionError, match="database update failed"):
        apply_upgrade(client, plan, tmp_path)

    assert calls.index("stop") < calls.index("data")
    assert calls.index("point-backup") < calls.index("start")
    assert calls.index("start") < calls.index("deploy-previous")
    state = WorkspaceStateStore(
        client,
        installation.management_path,
    ).load_current_run()
    assert state["status"] == "rolled_back"
    assert state["rollback_errors"] == []


def test_manual_rollback_starts_app_before_deployment(monkeypatch):
    client = SimpleNamespace(workspace=FakeWorkspaceFiles())
    installation = Installation(
        app_name="lakemeter",
        app_url="https://lakemeter.example",
        source_path="/Workspace/apps/lakemeter",
        active_source_path="/Workspace/apps/lakemeter/releases/v0.2.0",
        installed_version=SemVer.parse("0.2.0"),
        workspace_user="owner@example.com",
    )
    store = WorkspaceStateStore(client, installation.management_path)
    store.save_run(
        {
            "run_id": "lakemeter-v0.2.0",
            "previous_source_path": (
                "/Workspace/apps/lakemeter/releases/v0.1.2"
            ),
            "status": "succeeded",
        }
    )
    calls = []
    monkeypatch.setattr(
        "upgrader.runner.discover_installation",
        lambda *_args: installation,
    )
    monkeypatch.setattr(
        "upgrader.runner.set_app_running",
        lambda _client, _app, running: calls.append(
            "start" if running else "stop"
        ),
    )

    def deploy(_client, _app, source):
        assert calls == ["start"]
        calls.append(("deploy", source))
        return "rollback-deployment"

    monkeypatch.setattr("upgrader.runner.deploy_app", deploy)

    result = rollback_upgrade(client, "lakemeter")

    assert result["status"] == "rolled_back"
    assert calls == [
        "start",
        ("deploy", "/Workspace/apps/lakemeter/releases/v0.1.2"),
    ]


def test_doctor_is_blocked_before_database_upgrade_without_branch(
    monkeypatch,
    tmp_path,
):
    installation = Installation(
        app_name="lakemeter",
        app_url="https://lakemeter.example",
        source_path="/Workspace/apps/lakemeter",
        active_source_path="/Workspace/apps/lakemeter/releases/v0.1.1",
        installed_version=SemVer.parse("0.1.1"),
        workspace_user="owner@example.com",
        lakebase_instance="legacy-provisioned-instance",
    )
    plan = UpgradePlan(
        installation=installation,
        manifest=ReleaseManifest(
            version=SemVer.parse("0.2.0"),
            operation="data_update",
            minimum_version=SemVer.parse("0.1.0"),
            data_updates=(
                ReleaseAction(
                    action_id="refresh",
                    path="scripts/upgrades/data_updates/refresh.sql",
                    sha256="a" * 64,
                ),
            ),
        ),
        transition="minor",
        run_id="lakemeter-v0.2.0",
    )
    monkeypatch.setattr("upgrader.runner.build_plan", lambda *_args: plan)

    result = run_command(
        SimpleNamespace(),
        "doctor",
        "lakemeter",
        tmp_path,
    )

    assert result["status"] == "blocked"
    assert "Lakebase project" in result["blockers"]


def test_doctor_allows_resolved_legacy_database_with_host_secret(
    monkeypatch,
    tmp_path,
):
    installation = Installation(
        app_name="lakemeter",
        app_url="https://lakemeter.example",
        source_path="/Workspace/apps/lakemeter",
        active_source_path="/Workspace/apps/lakemeter",
        installed_version=SemVer.parse("0.1.0"),
        workspace_user="owner@example.com",
        database_host="primary.example",
        database_host_secret_scope="scope",
        database_host_secret_key="host",
        lakebase_project="projects/meter",
        lakebase_branch="projects/meter/branches/production",
        lakebase_endpoint=(
            "projects/meter/branches/production/endpoints/primary"
        ),
        lakebase_instance="legacy-instance",
        legacy_baseline=True,
    )
    plan = UpgradePlan(
        installation=installation,
        manifest=ReleaseManifest(
            version=SemVer.parse("0.2.0"),
            operation="data_update",
            minimum_version=SemVer.parse("0.1.0"),
            data_updates=(
                ReleaseAction(
                    action_id="refresh",
                    path="scripts/upgrades/data_updates/refresh.sql",
                    sha256="a" * 64,
                ),
            ),
        ),
        transition="minor",
        run_id="lakemeter-v0.2.0",
    )
    monkeypatch.setattr("upgrader.runner.build_plan", lambda *_args: plan)

    result = run_command(
        SimpleNamespace(),
        "doctor",
        "lakemeter",
        tmp_path,
    )

    assert result["status"] == "ok"
    assert result["checks"]["database_backup_capable"] == "ok"

