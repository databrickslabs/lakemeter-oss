"""Database backup, migration, and rollback primitives."""

from __future__ import annotations

import hashlib
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import psycopg2

from .models import Installation, ReleaseAction, UpgradePolicyError


ADVISORY_LOCK_ID = 5_234_676_539_921_001
SAFE_ID = re.compile(r"[^a-z0-9-]+")


class DatabaseUpgradeError(RuntimeError):
    """Raised when database backup or upgrade operations fail safely."""


@dataclass(frozen=True)
class DatabaseBackup:
    """Rollback point created before a database-changing release."""

    kind: str
    resource_name: str
    endpoint_name: str | None
    host: str | None
    original_host: str | None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "kind": self.kind,
            "resource_name": self.resource_name,
            "endpoint_name": self.endpoint_name,
            "host": self.host,
            "original_host": self.original_host,
        }


def _resource_name(project: str, branch: str) -> tuple[str, str]:
    project_name = (
        project if project.startswith("projects/") else f"projects/{project}"
    )
    branch_name = (
        branch
        if branch.startswith("projects/")
        else f"{project_name}/branches/{branch}"
    )
    return project_name, branch_name


def create_database_backup(
    workspace_client: Any,
    installation: Installation,
    target_version: str,
    ttl_seconds: int | None = None,
) -> DatabaseBackup:
    """Create a copy-on-write Lakebase branch before database mutation."""
    if not installation.lakebase_project or not installation.lakebase_branch:
        raise DatabaseUpgradeError(
            "This installation does not expose a Lakebase Autoscaling project "
            "and branch. A database-changing upgrade cannot continue without "
            "an automatic copy-on-write rollback point."
        )

    try:
        from databricks.sdk.service.postgres import (
            Branch,
            BranchSpec,
            Duration,
            Endpoint,
            EndpointSpec,
        )
    except ImportError as exc:
        raise DatabaseUpgradeError(
            "Lakebase branch backup requires databricks-sdk>=0.81.0."
        ) from exc

    project_name, source_branch = _resource_name(
        installation.lakebase_project,
        installation.lakebase_branch,
    )
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    version_slug = SAFE_ID.sub("-", target_version.lower()).strip("-")
    branch_id = f"lakemeter-pre-{version_slug}-{timestamp}"[:63]

    branch_spec = BranchSpec(source_branch=source_branch)
    if ttl_seconds is None:
        branch_spec.no_expiry = True
    else:
        branch_spec.ttl = Duration(seconds=ttl_seconds)

    operation = workspace_client.postgres.create_branch(
        parent=project_name,
        branch=Branch(spec=branch_spec),
        branch_id=branch_id,
    )
    branch = operation.wait()
    branch_name = str(getattr(branch, "name", "") or f"{project_name}/branches/{branch_id}")

    endpoints = list(workspace_client.postgres.list_endpoints(parent=branch_name))
    if not endpoints:
        if not installation.lakebase_endpoint:
            raise DatabaseUpgradeError(
                f"Backup branch {branch_name} has no compute endpoint and the "
                "source endpoint was not discovered."
            )
        source_endpoint = workspace_client.postgres.get_endpoint(
            name=installation.lakebase_endpoint
        )
        source_spec = getattr(source_endpoint, "spec", None)
        endpoint_type = getattr(source_spec, "endpoint_type", None)
        if endpoint_type is None:
            raise DatabaseUpgradeError(
                "Source Lakebase endpoint type could not be determined."
            )
        backup_spec = EndpointSpec(
            endpoint_type=endpoint_type,
            autoscaling_limit_max_cu=getattr(
                source_spec, "autoscaling_limit_max_cu", None
            ),
            autoscaling_limit_min_cu=getattr(
                source_spec, "autoscaling_limit_min_cu", None
            ),
            disabled=False,
            no_suspension=getattr(source_spec, "no_suspension", None),
            settings=getattr(source_spec, "settings", None),
            suspend_timeout_duration=getattr(
                source_spec, "suspend_timeout_duration", None
            ),
        )
        endpoint_operation = workspace_client.postgres.create_endpoint(
            parent=branch_name,
            endpoint=Endpoint(spec=backup_spec),
            endpoint_id="lakemeter-rollback",
        )
        endpoint = endpoint_operation.wait()
    else:
        endpoint = endpoints[0]
    endpoint_name = str(getattr(endpoint, "name", "") or "")
    deadline = time.monotonic() + 600
    host = None
    while endpoint_name and time.monotonic() < deadline:
        endpoint = workspace_client.postgres.get_endpoint(name=endpoint_name)
        status = getattr(endpoint, "status", None)
        hosts = getattr(status, "hosts", None)
        host = getattr(hosts, "host", None) if hosts else None
        if host:
            break
        time.sleep(5)
    if not endpoint_name or not host:
        raise DatabaseUpgradeError(
            f"Backup endpoint for {branch_name} did not become ready."
        )
    credential = workspace_client.postgres.generate_database_credential(
        endpoint=endpoint_name
    )
    connection_deadline = time.monotonic() + 120
    backup_connection = None
    last_connection_error: Exception | None = None
    while time.monotonic() < connection_deadline:
        try:
            backup_connection = psycopg2.connect(
                host=str(host),
                port=5432,
                database=installation.database_name or "databricks_postgres",
                user=str(workspace_client.current_user.me().user_name),
                password=credential.token,
                sslmode="require",
                connect_timeout=10,
            )
            break
        except Exception as exc:
            last_connection_error = exc
            time.sleep(5)
    if backup_connection is None:
        raise DatabaseUpgradeError(
            f"Backup endpoint {endpoint_name} is not queryable: "
            f"{last_connection_error}"
        )
    try:
        with backup_connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    finally:
        backup_connection.close()

    return DatabaseBackup(
        kind="lakebase_branch",
        resource_name=branch_name,
        endpoint_name=endpoint_name,
        host=str(host),
        original_host=installation.database_host,
    )


def connect_as_owner(
    workspace_client: Any,
    installation: Installation,
):
    """Connect using a short-lived Databricks OAuth database credential."""
    current_user = str(workspace_client.current_user.me().user_name)
    database_name = installation.database_name or "databricks_postgres"

    if installation.lakebase_endpoint:
        endpoint_name = installation.lakebase_endpoint
        endpoint = workspace_client.postgres.get_endpoint(name=endpoint_name)
        status = getattr(endpoint, "status", None)
        hosts = getattr(status, "hosts", None)
        host = getattr(hosts, "host", None) if hosts else None
        credential = workspace_client.postgres.generate_database_credential(
            endpoint=endpoint_name
        )
    elif installation.lakebase_instance:
        host = installation.database_host
        credential = workspace_client.database.generate_database_credential(
            request_id=str(uuid.uuid4()),
            instance_names=[installation.lakebase_instance],
        )
    else:
        raise DatabaseUpgradeError(
            "Unable to determine the Lakebase endpoint or instance for migration."
        )

    if not host:
        raise DatabaseUpgradeError("Lakebase host could not be resolved.")

    return psycopg2.connect(
        host=host,
        port=5432,
        database=database_name,
        user=current_user,
        password=credential.token,
        sslmode="require",
    )


def acquire_advisory_lock(connection: Any) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", (ADVISORY_LOCK_ID,))
        locked = cursor.fetchone()[0]
    if not locked:
        raise DatabaseUpgradeError(
            "Another Lakemeter database upgrade currently holds the advisory lock."
        )


def release_advisory_lock(connection: Any) -> None:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK_ID,))
    except Exception:
        pass


def ensure_migration_history(connection: Any) -> None:
    """Create migration history during a major schema upgrade only."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS lakemeter.schema_migrations (
                migration_id VARCHAR(255) PRIMARY KEY,
                checksum CHAR(64) NOT NULL,
                app_version VARCHAR(50) NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    connection.commit()


def applied_migrations(connection: Any) -> dict[str, str]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT migration_id, checksum
            FROM lakemeter.schema_migrations
            ORDER BY applied_at
            """
        )
        return {str(row[0]): str(row[1]) for row in cursor.fetchall()}


def execute_sql_actions(
    connection: Any,
    repository_root: Path,
    actions: Iterable[ReleaseAction],
    app_version: str,
    record_migrations: bool,
    completed_action_ids: set[str] | None = None,
) -> list[str]:
    """Execute checksummed SQL actions in order and stop on the first failure."""
    completed = completed_action_ids or set()
    executed: list[str] = []
    recorded = applied_migrations(connection) if record_migrations else {}

    for action in actions:
        if action.action_id in completed:
            continue
        path = (repository_root / action.path).resolve()
        sql = path.read_text()
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != action.sha256:
            raise UpgradePolicyError(
                f"Checksum mismatch for database action {action.action_id}."
            )
        previous_checksum = recorded.get(action.action_id)
        if previous_checksum:
            if previous_checksum != action.sha256:
                raise DatabaseUpgradeError(
                    f"Applied migration {action.action_id} has checksum "
                    "different from this release."
                )
            continue

        connection.autocommit = not action.transactional
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                if record_migrations:
                    cursor.execute(
                        """
                        INSERT INTO lakemeter.schema_migrations
                            (migration_id, checksum, app_version)
                        VALUES (%s, %s, %s)
                        """,
                        (action.action_id, action.sha256, app_version),
                    )
            if action.transactional:
                connection.commit()
        except Exception:
            if action.transactional:
                connection.rollback()
            raise
        finally:
            connection.autocommit = False
        executed.append(action.action_id)

    return executed


def point_app_to_backup(
    workspace_client: Any,
    installation: Installation,
    backup: DatabaseBackup,
) -> None:
    """Repoint the app's DB host secret to a pre-upgrade branch."""
    if not backup.host:
        raise DatabaseUpgradeError(
            "Cannot rollback database connection: backup endpoint host is missing."
        )
    if (
        not installation.database_host_secret_scope
        or not installation.database_host_secret_key
    ):
        raise DatabaseUpgradeError(
            "Cannot rollback database connection: the DB host secret binding "
            "was not discovered."
        )
    secret_updates = [
        (
            installation.database_host_secret_scope,
            installation.database_host_secret_key,
            backup.host,
        )
    ]
    if installation.lakebase_endpoint:
        if (
            not backup.endpoint_name
            or not installation.lakebase_endpoint_secret_scope
            or not installation.lakebase_endpoint_secret_key
        ):
            raise DatabaseUpgradeError(
                "Cannot rollback database connection: the endpoint secret "
                "binding or backup endpoint is missing."
            )
        secret_updates.append(
            (
                installation.lakebase_endpoint_secret_scope,
                installation.lakebase_endpoint_secret_key,
                backup.endpoint_name,
            )
        )
    if installation.lakebase_branch:
        if (
            not installation.lakebase_branch_secret_scope
            or not installation.lakebase_branch_secret_key
        ):
            raise DatabaseUpgradeError(
                "Cannot rollback database connection: the branch secret binding "
                "is missing."
            )
        secret_updates.append(
            (
                installation.lakebase_branch_secret_scope,
                installation.lakebase_branch_secret_key,
                backup.resource_name,
            )
        )
    for scope, key, value in secret_updates:
        workspace_client.secrets.put_secret(
            scope=scope,
            key=key,
            string_value=value,
        )

