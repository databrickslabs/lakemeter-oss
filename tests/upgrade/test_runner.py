from types import SimpleNamespace

import pytest

from upgrader.models import (
    Installation,
    ReleaseAction,
    ReleaseManifest,
    SemVer,
    UpgradePlan,
)
from upgrader.runner import UpgradeExecutionError, apply_upgrade, run_command
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

