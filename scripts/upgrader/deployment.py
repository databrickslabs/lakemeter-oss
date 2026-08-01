"""Versioned workspace staging and Databricks App deployment."""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Any

import requests

from .payload import MAX_WORKSPACE_FILE_SIZE, should_exclude



class DeploymentError(RuntimeError):
    """Raised when staging, deployment, or smoke verification fails."""


def _state_value(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").upper()


def stage_runtime(
    workspace_client: Any,
    local_runtime_path: Path,
    release_path: str,
    app_yaml_content: bytes | None = None,
    release_fingerprint: str | None = None,
) -> dict[str, int]:
    """Upload a clean immutable runtime payload to a versioned workspace path."""
    from databricks.sdk.service.workspace import ImportFormat

    if not (local_runtime_path / "app.yaml").is_file():
        raise DeploymentError("Runtime payload is missing app.yaml.")
    if not (local_runtime_path / "backend/app/main.py").is_file():
        raise DeploymentError("Runtime payload is missing backend/app/main.py.")
    if not (local_runtime_path / "backend/static/index.html").is_file():
        raise DeploymentError("Runtime payload is missing backend/static/index.html.")

    marker_path = f"{release_path.rstrip('/')}/.lakemeter-release.json"
    if release_fingerprint:
        marker = read_workspace_file(workspace_client, marker_path)
        if marker is not None:
            try:
                existing_fingerprint = json.loads(marker).get("runtime_sha256")
            except Exception as exc:
                raise DeploymentError(
                    f"Release path {release_path} has an invalid integrity marker."
                ) from exc
            if existing_fingerprint != release_fingerprint:
                raise DeploymentError(
                    f"Release path {release_path} already contains a different "
                    "runtime payload; versioned releases are immutable."
                )
            return {
                "uploaded_files": 0,
                "skipped_files": 0,
                "uploaded_bytes": 0,
                "reused_release": 1,
            }

    try:
        workspace_client.workspace.delete(release_path, recursive=True)
    except Exception:
        pass
    workspace_client.workspace.mkdirs(release_path)

    uploaded = 0
    skipped = 0
    total_bytes = 0
    for path in sorted(local_runtime_path.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(local_runtime_path)
        if relative.as_posix() == "app.yaml" and app_yaml_content is not None:
            continue
        if should_exclude(relative):
            skipped += 1
            continue
        size = path.stat().st_size
        if size > MAX_WORKSPACE_FILE_SIZE:
            raise DeploymentError(
                f"Runtime file {relative} is {size} bytes, exceeding the "
                f"{MAX_WORKSPACE_FILE_SIZE}-byte workspace safety limit."
            )
        target = f"{release_path.rstrip('/')}/{relative.as_posix()}"
        parent = target.rsplit("/", 1)[0]
        workspace_client.workspace.mkdirs(parent)
        content = base64.b64encode(path.read_bytes()).decode("ascii")
        workspace_client.workspace.import_(
            path=target,
            content=content,
            format=ImportFormat.AUTO,
            overwrite=True,
        )
        uploaded += 1
        total_bytes += size

    if app_yaml_content is not None:
        target = f"{release_path.rstrip('/')}/app.yaml"
        workspace_client.workspace.import_(
            path=target,
            content=base64.b64encode(app_yaml_content).decode("ascii"),
            format=ImportFormat.AUTO,
            overwrite=True,
        )
        uploaded += 1
        total_bytes += len(app_yaml_content)

    result = {
        "uploaded_files": uploaded,
        "skipped_files": skipped,
        "uploaded_bytes": total_bytes,
    }
    if release_fingerprint:
        marker = json.dumps(
            {"runtime_sha256": release_fingerprint},
            sort_keys=True,
        ).encode("utf-8")
        workspace_client.workspace.import_(
            path=marker_path,
            content=base64.b64encode(marker).decode("ascii"),
            format=ImportFormat.AUTO,
            overwrite=False,
        )
        result["uploaded_files"] += 1
        result["uploaded_bytes"] += len(marker)
    return result


def read_workspace_file(
    workspace_client: Any,
    path: str,
) -> bytes | None:
    """Read an existing workspace file, returning None when it is absent."""
    try:
        exported = workspace_client.workspace.export(path=path)
        return base64.b64decode(exported.content)
    except Exception:
        return None


def deploy_app(
    workspace_client: Any,
    app_name: str,
    source_path: str,
    timeout_seconds: int = 900,
) -> str:
    """Deploy an existing Databricks App from a versioned workspace path."""
    host = workspace_client.config.host.rstrip("/")
    response = requests.post(
        f"{host}/api/2.0/apps/{app_name}/deployments",
        headers=workspace_client.config.authenticate(),
        json={"source_code_path": source_path},
        timeout=30,
    )
    if response.status_code >= 300:
        raise DeploymentError(
            f"Deploy request failed: HTTP {response.status_code} "
            f"{response.text[:300]}"
        )
    deployment_id = str(response.json().get("deployment_id", ""))
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        app = workspace_client.apps.get(app_name)
        pending = getattr(app, "pending_deployment", None)
        active = getattr(app, "active_deployment", None)
        deployment = pending or active
        if deployment:
            state = _state_value(getattr(deployment.status, "state", ""))
            current_id = str(getattr(deployment, "deployment_id", "") or "")
            if state in {"FAILED", "CANCELLED", "CANCELED"} and (
                not deployment_id or current_id == deployment_id
            ):
                message = getattr(deployment.status, "message", "Unknown error")
                raise DeploymentError(f"Deployment entered {state}: {message}")
            if state == "SUCCEEDED" and (
                not deployment_id or current_id == deployment_id
            ):
                return deployment_id or current_id
        time.sleep(10)

    raise DeploymentError(
        f"Deployment {deployment_id or '<unknown>'} did not finish within "
        f"{timeout_seconds} seconds."
    )


def _exchange_app_audience_token(
    workspace_client: Any,
    app_name: str,
    workspace_headers: dict[str, str],
    timeout_seconds: int,
) -> dict[str, str]:
    """Exchange a notebook token for an OAuth token scoped to the app."""
    authorization = workspace_headers.get("Authorization", "")
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise DeploymentError(
            "Workspace authentication did not provide a Bearer token for "
            "Databricks App token exchange."
        )

    app = workspace_client.apps.get(app_name)
    app_client_id = str(getattr(app, "oauth2_app_client_id", "") or "")
    if not app_client_id:
        raise DeploymentError(
            f"Databricks App '{app_name}' has no OAuth client ID."
        )

    host = workspace_client.config.host.rstrip("/")
    response = requests.post(
        f"{host}/oidc/v1/token",
        data={
            "grant_type": (
                "urn:ietf:params:oauth:grant-type:token-exchange"
            ),
            "subject_token": authorization[len(prefix):],
            "subject_token_type": (
                "urn:databricks:params:oauth:token-type:personal-access-token"
            ),
            "requested_token_type": (
                "urn:ietf:params:oauth:token-type:access_token"
            ),
            "scope": "all-apis",
            "audience": app_client_id,
        },
        timeout=timeout_seconds,
    )
    if response.status_code != 200:
        raise DeploymentError(
            "Databricks App token exchange failed: "
            f"HTTP {response.status_code} {response.text[:300]}"
        )
    access_token = str(response.json().get("access_token", "") or "")
    if not access_token:
        raise DeploymentError(
            "Databricks App token exchange returned no access token."
        )
    return {"Authorization": f"Bearer {access_token}"}


def verify_app(
    workspace_client: Any,
    app_name: str,
    app_url: str,
    expected_version: str,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """Verify authenticated health, database access, and exact app version."""
    headers = workspace_client.config.authenticate()
    health = requests.get(
        f"{app_url.rstrip('/')}/api/v1/system/health",
        headers=headers,
        timeout=timeout_seconds,
    )
    if health.status_code == 401:
        headers = _exchange_app_audience_token(
            workspace_client,
            app_name,
            headers,
            timeout_seconds,
        )
        health = requests.get(
            f"{app_url.rstrip('/')}/api/v1/system/health",
            headers=headers,
            timeout=timeout_seconds,
        )
    if health.status_code != 200:
        raise DeploymentError(
            f"Health check returned HTTP {health.status_code}."
        )
    health_data = health.json()
    if (
        health_data.get("status") != "healthy"
        or health_data.get("database") != "connected"
    ):
        raise DeploymentError(f"Health check failed: {health_data}")

    version_response = requests.get(
        f"{app_url.rstrip('/')}/api/v1/system/version",
        headers=headers,
        timeout=timeout_seconds,
    )
    if version_response.status_code != 200:
        raise DeploymentError(
            f"Version check returned HTTP {version_response.status_code}."
        )
    version_data = version_response.json()
    actual_version = str(version_data.get("app_version", ""))
    if actual_version != expected_version:
        raise DeploymentError(
            f"Deployed version is {actual_version or '<missing>'}; "
            f"expected {expected_version}."
        )
    return {"health": health_data, "version": version_data}


def set_app_running(
    workspace_client: Any,
    app_name: str,
    running: bool,
) -> None:
    """Start or stop app compute for a consistent database-change window."""
    operation = (
        workspace_client.apps.start
        if running
        else workspace_client.apps.stop
    )
    operation(app_name)
    desired = {"ACTIVE", "RUNNING"} if running else {"STOPPED", "INACTIVE"}
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        app = workspace_client.apps.get(app_name)
        compute = _state_value(getattr(app.compute_status, "state", ""))
        if compute in desired:
            return
        time.sleep(5)
    action = "start" if running else "stop"
    raise DeploymentError(f"App did not {action} within 600 seconds.")

