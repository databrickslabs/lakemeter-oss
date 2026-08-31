"""End-to-end Lakemeter upgrade orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .database import (
    DatabaseBackup,
    acquire_advisory_lock,
    connect_as_owner,
    create_database_backup,
    ensure_migration_history,
    execute_sql_actions,
    point_app_to_backup,
    release_advisory_lock,
)
from .deployment import (
    deploy_app,
    read_workspace_file,
    set_app_running,
    stage_runtime,
    verify_app,
)
from .discovery import discover_installation, installation_as_json
from .integrity import verify_release_payload
from .models import (
    ReleaseManifest,
    UpgradePlan,
    UpgradePolicyError,
    validate_release_policy,
)
from .state import WorkspaceStateStore


class UpgradeExecutionError(RuntimeError):
    """Raised after an upgrade fails and rollback is attempted."""


def _database_backup_blockers(plan: UpgradePlan) -> list[str]:
    if not plan.requires_database_backup:
        return []
    installation = plan.installation
    required = {
        "Lakebase project": installation.lakebase_project,
        "Lakebase branch": installation.lakebase_branch,
        "Lakebase endpoint": installation.lakebase_endpoint,
        "database host secret binding": (
            installation.database_host_secret_scope
            and installation.database_host_secret_key
        ),
    }
    return [name for name, value in required.items() if not value]


def _previous_installation_metadata(
    store: WorkspaceStateStore,
    plan: UpgradePlan,
) -> dict[str, Any]:
    persisted = store.load_installation()
    if persisted:
        return persisted
    return {
        "app_name": plan.installation.app_name,
        "installed_version": str(plan.installation.installed_version),
        "release_path": plan.installation.active_source_path,
        "applied_data_updates": [],
    }


def _restore_installation_metadata(
    store: WorkspaceStateStore,
    state: dict[str, Any],
) -> None:
    previous = state.get("previous_installation")
    if isinstance(previous, dict):
        store.save_installation(previous)


def build_plan(
    workspace_client: Any,
    app_name: str,
    payload_root: Path,
) -> UpgradePlan:
    manifest = ReleaseManifest.load(payload_root / "scripts/upgrades/release.json")
    runtime_path = payload_root / "app_source"
    verify_release_payload(payload_root, runtime_path, manifest)
    installation = discover_installation(workspace_client, app_name)
    transition = validate_release_policy(
        installation.installed_version,
        manifest,
    )
    return UpgradePlan(
        installation=installation,
        manifest=manifest,
        transition=transition,
        run_id=f"{app_name}-v{manifest.version}".replace("/", "-"),
    )


def _backup_from_state(data: dict[str, Any] | None) -> DatabaseBackup | None:
    if not data:
        return None
    return DatabaseBackup(
        kind=str(data["kind"]),
        resource_name=str(data["resource_name"]),
        endpoint_name=data.get("endpoint_name"),
        host=data.get("host"),
        original_host=data.get("original_host"),
    )


def _persist_success(
    store: WorkspaceStateStore,
    plan: UpgradePlan,
    release_path: str,
    deployment_id: str,
    state: dict[str, Any],
) -> None:
    previous = store.load_installation() or {}
    applied_updates = set(previous.get("applied_data_updates", []))
    applied_updates.update(state.get("executed_data_updates", []))
    store.save_installation(
        {
            "app_name": plan.installation.app_name,
            "installed_version": str(plan.manifest.version),
            "release_path": release_path,
            "deployment_id": deployment_id,
            "previous_release_path": plan.installation.active_source_path,
            "applied_data_updates": sorted(applied_updates),
            "last_upgrade_run_id": plan.run_id,
        }
    )


def apply_upgrade(
    workspace_client: Any,
    plan: UpgradePlan,
    payload_root: Path,
) -> dict[str, Any]:
    if plan.transition == "same":
        return {
            "status": "no_change",
            "message": f"Lakemeter {plan.manifest.version} is already installed.",
            "plan": plan.as_dict(),
        }

    installation = plan.installation
    store = WorkspaceStateStore(workspace_client, installation.management_path)
    blockers = _database_backup_blockers(plan)
    if blockers:
        raise UpgradeExecutionError(
            "Database-changing upgrade is blocked because discovery did not find: "
            + ", ".join(blockers)
            + "."
        )
    current_source = installation.active_source_path or installation.source_path
    existing_app_yaml = read_workspace_file(
        workspace_client,
        f"{current_source.rstrip('/')}/app.yaml",
    )
    if existing_app_yaml is None:
        raise UpgradeExecutionError(
            f"Cannot read {current_source}/app.yaml; refusing to replace "
            "the installation's resource bindings with defaults."
        )
    previous_installation = _previous_installation_metadata(store, plan)
    state = store.start_run(
        plan.run_id,
        {
            "status": "running",
            "installed_version": str(installation.installed_version),
            "target_version": str(plan.manifest.version),
            "operation": plan.manifest.operation,
            "transition": plan.transition,
            "previous_source_path": installation.active_source_path,
            "previous_installation": previous_installation,
        },
    )
    release_path = (
        f"{installation.source_path.rstrip('/')}/releases/v{plan.manifest.version}"
    )
    app_was_stopped = False
    connection = None

    try:
        backup = _backup_from_state(state.get("database_backup"))
        if plan.requires_database_backup and "database_changes" not in state.get(
            "completed_phases", []
        ):
            connection = connect_as_owner(workspace_client, installation)
            acquire_advisory_lock(connection)
            if "database_backup" not in state.get("completed_phases", []):
                set_app_running(
                    workspace_client,
                    installation.app_name,
                    running=False,
                )
                app_was_stopped = True
                state["app_stopped"] = True
                store.save_run(state)
                backup = create_database_backup(
                    workspace_client,
                    installation,
                    str(plan.manifest.version),
                )
                store.complete_phase(
                    state,
                    "database_backup",
                    database_backup=backup.as_dict(),
                )

            action_status = dict(state.get("database_action_status", {}))
            executed_migrations = list(state.get("executed_migrations", []))
            if plan.manifest.migrations:
                if plan.transition != "major":
                    raise UpgradePolicyError(
                        "Schema migrations can execute only during a major upgrade."
                    )
                ensure_migration_history(connection)
            persisted = store.load_installation() or {}
            completed_updates = set(persisted.get("applied_data_updates", []))
            executed_updates = list(state.get("executed_data_updates", []))

            for action, record_migration, executed in (
                *(
                    (action, True, executed_migrations)
                    for action in plan.manifest.migrations
                ),
                *(
                    (action, False, executed_updates)
                    for action in plan.manifest.data_updates
                ),
            ):
                status = action_status.get(action.action_id)
                if status == "completed":
                    continue
                if status == "started":
                    raise UpgradeExecutionError(
                        f"Database action {action.action_id} has an uncertain "
                        "commit state after an interrupted run; rolling back "
                        "instead of replaying it."
                    )
                if not record_migration and action.action_id in completed_updates:
                    action_status[action.action_id] = "completed"
                    continue
                action_status[action.action_id] = "started"
                state["database_action_status"] = action_status
                store.save_run(state)
                completed = execute_sql_actions(
                    connection=connection,
                    repository_root=payload_root,
                    actions=[action],
                    app_version=str(plan.manifest.version),
                    record_migrations=record_migration,
                    completed_action_ids=(
                        completed_updates if not record_migration else None
                    ),
                )
                if completed and action.action_id not in executed:
                    executed.append(action.action_id)
                action_status[action.action_id] = "completed"
                state["database_action_status"] = action_status
                state["executed_migrations"] = executed_migrations
                state["executed_data_updates"] = executed_updates
                store.save_run(state)
            store.complete_phase(
                state,
                "database_changes",
                executed_migrations=executed_migrations,
                executed_data_updates=executed_updates,
            )
            release_advisory_lock(connection)
            connection.close()
            connection = None

        if "runtime_staged" not in state.get("completed_phases", []):
            upload_summary = stage_runtime(
                workspace_client,
                payload_root / "app_source",
                release_path,
                app_yaml_content=existing_app_yaml,
                release_fingerprint=plan.manifest.runtime_sha256,
            )
            store.complete_phase(
                state,
                "runtime_staged",
                release_path=release_path,
                upload_summary=upload_summary,
            )

        if app_was_stopped or state.get("app_stopped"):
            set_app_running(
                workspace_client,
                installation.app_name,
                running=True,
            )
            app_was_stopped = False
            state["app_stopped"] = False
            store.save_run(state)

        if "app_deployed" not in state.get("completed_phases", []):
            deployment_id = deploy_app(
                workspace_client,
                installation.app_name,
                release_path,
            )
            store.complete_phase(
                state,
                "app_deployed",
                deployment_id=deployment_id,
            )
        else:
            deployment_id = str(state.get("deployment_id", ""))

        verification = verify_app(
            workspace_client,
            installation.app_name,
            installation.app_url,
            str(plan.manifest.version),
        )
        store.complete_phase(state, "verified", verification=verification)
        _persist_success(store, plan, release_path, deployment_id, state)
        store.finish_run(state)
        return {
            "status": "succeeded",
            "run_id": plan.run_id,
            "deployment_id": deployment_id,
            "release_path": release_path,
            "app_url": installation.app_url,
        }
    except Exception as exc:
        rollback_errors: list[str] = []
        recovery_succeeded = True
        if connection is not None:
            try:
                release_advisory_lock(connection)
                connection.close()
            except Exception as rollback_exc:
                rollback_errors.append(f"database lock: {rollback_exc}")
        try:
            store.fail_run(state, exc)
        except Exception as rollback_exc:
            rollback_errors.append(f"upgrade journal: {rollback_exc}")

        backup = _backup_from_state(state.get("database_backup"))
        if backup:
            try:
                point_app_to_backup(workspace_client, installation, backup)
            except Exception as rollback_exc:
                rollback_errors.append(f"database: {rollback_exc}")
                recovery_succeeded = False

        if app_was_stopped or state.get("app_stopped"):
            try:
                set_app_running(
                    workspace_client,
                    installation.app_name,
                    running=True,
                )
                app_was_stopped = False
                state["app_stopped"] = False
            except Exception as rollback_exc:
                rollback_errors.append(f"app start: {rollback_exc}")
                recovery_succeeded = False

        previous_source = state.get("previous_source_path")
        if previous_source:
            try:
                deploy_app(
                    workspace_client,
                    installation.app_name,
                    str(previous_source),
                )
            except Exception as rollback_exc:
                rollback_errors.append(f"application: {rollback_exc}")
                recovery_succeeded = False

        if recovery_succeeded:
            try:
                _restore_installation_metadata(store, state)
            except Exception as rollback_exc:
                rollback_errors.append(f"installation metadata: {rollback_exc}")
        state["status"] = "rolled_back" if not rollback_errors else "failed"
        state["rollback_errors"] = rollback_errors
        try:
            store.save_run(state)
        except Exception as rollback_exc:
            rollback_errors.append(f"upgrade journal: {rollback_exc}")
        try:
            store.release_run_lock(str(state["run_id"]))
        except Exception as rollback_exc:
            rollback_errors.append(f"workspace lock: {rollback_exc}")
            state["status"] = "failed"
            state["rollback_errors"] = rollback_errors
            store.save_run(state)
        detail = f"Upgrade failed: {exc}"
        if rollback_errors:
            detail += f"; rollback errors: {'; '.join(rollback_errors)}"
        raise UpgradeExecutionError(detail) from exc


def rollback_upgrade(
    workspace_client: Any,
    app_name: str,
) -> dict[str, Any]:
    installation = discover_installation(workspace_client, app_name)
    store = WorkspaceStateStore(workspace_client, installation.management_path)
    state = store.load_current_run()
    if not state:
        raise UpgradeExecutionError("No upgrade run is available to roll back.")

    lock_id = f"{state.get('run_id', 'unknown')}-rollback"
    store.acquire_run_lock(lock_id)
    previous_source = state.get("previous_source_path")
    if not previous_source:
        store.release_run_lock(lock_id)
        raise UpgradeExecutionError(
            "The recorded upgrade run has no previous application source."
        )
    try:
        backup = _backup_from_state(state.get("database_backup"))
        if backup:
            point_app_to_backup(workspace_client, installation, backup)
        set_app_running(workspace_client, app_name, running=True)
        deployment_id = deploy_app(
            workspace_client,
            app_name,
            str(previous_source),
        )
        state["status"] = "rolled_back"
        state["rollback_deployment_id"] = deployment_id
        _restore_installation_metadata(store, state)
        store.save_run(state)
        return {
            "status": "rolled_back",
            "run_id": state.get("run_id"),
            "deployment_id": deployment_id,
            "source_path": previous_source,
        }
    finally:
        store.release_run_lock(lock_id)


def run_command(
    workspace_client: Any,
    command: str,
    app_name: str,
    payload_root: Path,
) -> dict[str, Any]:
    if command == "status":
        installation = discover_installation(workspace_client, app_name)
        store = WorkspaceStateStore(workspace_client, installation.management_path)
        return {
            "installation": json.loads(installation_as_json(installation)),
            "current_run": store.load_current_run(),
        }
    if command == "rollback":
        return rollback_upgrade(workspace_client, app_name)

    plan = build_plan(workspace_client, app_name, payload_root)
    if command in {"plan", "doctor"}:
        result = {"status": "ok", "plan": plan.as_dict()}
        if command == "doctor":
            blockers = _database_backup_blockers(plan)
            result["checks"] = {
                "workspace": "ok",
                "app": "ok",
                "release_policy": "ok",
                "payload_integrity": "ok",
                "database_backup_capable": "blocked" if blockers else "ok",
            }
            if blockers:
                result["status"] = "blocked"
                result["blockers"] = blockers
        return result
    if command == "apply":
        return apply_upgrade(workspace_client, plan, payload_root)
    raise ValueError(f"Unknown upgrade command: {command}")

