"""Direct Lakebase Autoscaling project provisioning helpers."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any


PROJECT_ID_PATTERN = re.compile(r"[^a-z0-9-]+")


class LakebaseProvisioningError(RuntimeError):
    """Raised when an Autoscaling project cannot become connection-ready."""


@dataclass(frozen=True)
class AutoscalingResources:
    project_id: str
    project_name: str
    branch_name: str
    endpoint_name: str
    host: str
    project_uid: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "branch_name": self.branch_name,
            "endpoint_name": self.endpoint_name,
            "host": self.host,
            "project_uid": self.project_uid,
        }


def normalize_project_id(value: str) -> str:
    project_id = PROJECT_ID_PATTERN.sub("-", value.strip().lower()).strip("-")
    if not project_id:
        raise LakebaseProvisioningError("Lakebase project ID cannot be empty.")
    if len(project_id) > 63:
        raise LakebaseProvisioningError(
            "Lakebase project ID must be at most 63 characters."
        )
    return project_id


def project_resource_names(project_id: str) -> tuple[str, str, str]:
    normalized = normalize_project_id(project_id)
    project_name = f"projects/{normalized}"
    branch_name = f"{project_name}/branches/production"
    endpoint_name = f"{branch_name}/endpoints/primary"
    return project_name, branch_name, endpoint_name


def _endpoint_host(endpoint: Any) -> str | None:
    status = getattr(endpoint, "status", None)
    hosts = getattr(status, "hosts", None)
    host = getattr(hosts, "host", None) if hosts else None
    return str(host) if host else None


def ensure_autoscaling_project(
    workspace_client: Any,
    project_id: str,
    *,
    display_name: str = "Lakemeter",
    min_cu: float = 1.0,
    max_cu: float = 16.0,
    suspend_after_seconds: int = 300,
    timeout_seconds: int = 900,
) -> tuple[AutoscalingResources, bool]:
    """Create or reuse a direct project and wait for its primary endpoint."""
    from databricks.sdk.errors import NotFound
    from databricks.sdk.service.postgres import (
        Duration,
        Project,
        ProjectDefaultEndpointSettings,
        ProjectSpec,
    )

    normalized = normalize_project_id(project_id)
    project_name, branch_name, endpoint_name = project_resource_names(normalized)
    created = False
    try:
        project = workspace_client.postgres.get_project(name=project_name)
    except NotFound:
        project = workspace_client.postgres.create_project(
            project=Project(
                spec=ProjectSpec(
                    display_name=display_name,
                    pg_version=17,
                    enable_pg_native_login=True,
                    default_endpoint_settings=ProjectDefaultEndpointSettings(
                        autoscaling_limit_min_cu=min_cu,
                        autoscaling_limit_max_cu=max_cu,
                        suspend_timeout_duration=Duration(
                            seconds=suspend_after_seconds
                        ),
                    ),
                )
            ),
            project_id=normalized,
        ).wait()
        created = True

    deadline = time.monotonic() + timeout_seconds
    last_endpoint = None
    while time.monotonic() < deadline:
        try:
            last_endpoint = workspace_client.postgres.get_endpoint(
                name=endpoint_name
            )
        except NotFound:
            time.sleep(5)
            continue
        host = _endpoint_host(last_endpoint)
        if host:
            return (
                AutoscalingResources(
                    project_id=normalized,
                    project_name=project_name,
                    branch_name=branch_name,
                    endpoint_name=endpoint_name,
                    host=host,
                    project_uid=str(getattr(project, "uid", "") or "") or None,
                ),
                created,
            )
        time.sleep(5)

    state = getattr(getattr(last_endpoint, "status", None), "current_state", None)
    raise LakebaseProvisioningError(
        f"Lakebase endpoint {endpoint_name} did not become ready within "
        f"{timeout_seconds} seconds (state={state or 'unknown'})."
    )


def generate_database_credential(
    workspace_client: Any,
    endpoint_name: str,
) -> Any:
    return workspace_client.postgres.generate_database_credential(
        endpoint=endpoint_name
    )

