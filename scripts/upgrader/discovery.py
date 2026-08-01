"""Discovery of existing Lakemeter installations."""

from __future__ import annotations

import base64
import json
import re
from typing import Any

import requests

from .models import Installation, SemVer
from .state import WorkspaceStateStore


VERSION_ASSIGNMENT = re.compile(
    r"""APP_VERSION\s*=\s*["'](?P<version>[^"']+)["']"""
)
SECRET_RESOURCE_SUFFIXES = {
    "lakebase-instance-name": ("lakebase-instance", "db-instance"),
    "lakebase-project": ("lakebase-project", "db-project"),
    "lakebase-branch": ("lakebase-branch", "db-branch"),
    "lakebase-endpoint": ("lakebase-endpoint", "db-endpoint"),
    "lakebase-host": ("lakebase-host", "db-host"),
    "lakebase-database": ("lakebase-database", "db-name", "database-name"),
    "lakebase-user": ("lakebase-user", "db-user", "database-user"),
}


def _get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _secret_binding(resource: Any) -> tuple[str, str] | None:
    secret = _get(resource, "secret")
    if not secret:
        return None
    scope = _get(secret, "scope")
    key = _get(secret, "key")
    if scope and key:
        return str(scope), str(key)
    return None


def _logical_secret_name(resource: Any, key: str) -> str | None:
    """Map custom resource and secret names to Lakemeter configuration roles."""
    resource_name = str(_get(resource, "name", "") or "").lower()
    key_name = key.lower()
    for logical_name, suffixes in SECRET_RESOURCE_SUFFIXES.items():
        if key_name == logical_name:
            return logical_name
        if any(
            name == suffix or name.endswith(f"-{suffix}")
            for name in (resource_name, key_name)
            for suffix in suffixes
        ):
            return logical_name
    return None


def _decode_secret_value(secret_value: Any) -> str | None:
    raw = _get(secret_value, "value")
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    try:
        return base64.b64decode(raw).decode("utf-8")
    except Exception:
        return str(raw)


def _read_secret(workspace_client: Any, scope: str, key: str) -> str | None:
    try:
        value = workspace_client.secrets.get_secret(scope=scope, key=key)
    except Exception:
        return None
    return _decode_secret_value(value)


def _read_version_from_workspace(
    workspace_client: Any,
    source_path: str | None,
) -> str | None:
    if not source_path:
        return None
    path = f"{source_path.rstrip('/')}/backend/app/version.py"
    try:
        exported = workspace_client.workspace.export(path=path)
        content = base64.b64decode(exported.content).decode("utf-8")
    except Exception:
        return None
    match = VERSION_ASSIGNMENT.search(content)
    return match.group("version") if match else None


def _read_version_from_app(workspace_client: Any, app_url: str) -> str | None:
    if not app_url:
        return None
    try:
        response = requests.get(
            f"{app_url.rstrip('/')}/api/v1/system/version",
            headers=workspace_client.config.authenticate(),
            timeout=10,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        return data.get("app_version")
    except Exception:
        return None


def _installation_source_root(source_path: str) -> str:
    """Return the stable app root when the API reports a versioned release."""
    marker = "/releases/"
    if marker in source_path:
        return source_path.split(marker, 1)[0]
    return source_path.rstrip("/")


def _resolve_proxy_autoscaling_resources(
    workspace_client: Any,
    instance_name: str | None,
) -> dict[str, str]:
    """Resolve Database Instance API aliases to their project resources."""
    if not instance_name:
        return {}
    project_id = re.sub(
        r"[^a-z0-9-]+",
        "-",
        instance_name.strip().lower(),
    ).strip("-")
    project_name = f"projects/{project_id}"
    branch_name = f"{project_name}/branches/production"
    endpoint_name = f"{branch_name}/endpoints/primary"
    project = workspace_client.postgres.get_project(name=project_name)
    endpoint = workspace_client.postgres.get_endpoint(name=endpoint_name)
    status = _get(endpoint, "status")
    hosts = _get(status, "hosts")
    host = _get(hosts, "host")
    return {
        "project": str(_get(project, "name", project_name) or project_name),
        "branch": branch_name,
        "endpoint": str(_get(endpoint, "name", endpoint_name) or endpoint_name),
        "host": str(host or ""),
    }


def discover_installation(
    workspace_client: Any,
    app_name: str,
    legacy_version: str = "0.1.0",
) -> Installation:
    """Discover live names and version without mutating workspace or database."""
    app = workspace_client.apps.get(app_name)
    workspace_user = str(workspace_client.current_user.me().user_name)
    reported_source_path = str(
        _get(app, "default_source_code_path")
        or f"/Workspace/Users/{workspace_user}/apps/{app_name}"
    )
    source_path = _installation_source_root(reported_source_path)
    app_url = str(_get(app, "url", "") or "")

    active_deployment = _get(app, "active_deployment")
    active_source = _get(active_deployment, "source_code_path")
    resources = list(_get(app, "resources", []) or [])

    secret_bindings: dict[str, tuple[str, str]] = {}
    secret_scopes: set[str] = set()
    for resource in resources:
        binding = _secret_binding(resource)
        if not binding:
            continue
        scope, key = binding
        secret_scopes.add(scope)
        logical_name = _logical_secret_name(resource, key)
        if logical_name:
            secret_bindings[logical_name] = (scope, key)

    secret_scope = sorted(secret_scopes)[0] if secret_scopes else None
    secrets: dict[str, str | None] = {}
    candidate_keys = {
        "lakebase-instance-name",
        "lakebase-project",
        "lakebase-branch",
        "lakebase-endpoint",
        "lakebase-host",
        "lakebase-database",
        "lakebase-user",
    }
    for key in candidate_keys:
        binding = secret_bindings.get(key)
        if binding:
            secrets[key] = _read_secret(
                workspace_client,
                binding[0],
                binding[1],
            )

    state_store = WorkspaceStateStore(workspace_client, f"{source_path}/.lakemeter")
    persisted = state_store.load_installation() or {}
    persisted_version = persisted.get("installed_version")
    endpoint_version = _read_version_from_app(workspace_client, app_url)
    workspace_version = _read_version_from_workspace(
        workspace_client,
        str(active_source) if active_source else source_path,
    )

    installed_version_value = (
        endpoint_version
        or workspace_version
        or persisted_version
        or legacy_version
    )
    legacy_baseline = not any(
        (persisted_version, endpoint_version, workspace_version)
    )
    warnings: list[str] = []
    if legacy_baseline:
        warnings.append(
            f"No deployed version metadata found; treating installation as "
            f"legacy {legacy_version}."
        )
    if len(secret_scopes) > 1:
        warnings.append(
            "App resources reference multiple secret scopes; using "
            f"{secret_scope} for Lakemeter discovery."
        )
    resolved = {}
    if not all(
        (
            secrets.get("lakebase-project"),
            secrets.get("lakebase-branch"),
            secrets.get("lakebase-endpoint"),
        )
    ):
        try:
            resolved = _resolve_proxy_autoscaling_resources(
                workspace_client,
                secrets.get("lakebase-instance-name"),
            )
            if resolved:
                warnings.append(
                    "Resolved legacy Database Instance bindings to the "
                    "underlying Lakebase Autoscaling project."
                )
        except Exception as exc:
            warnings.append(
                "Could not resolve the Database Instance alias through the "
                f"Postgres API: {exc}"
            )
    host_binding = secret_bindings.get("lakebase-host")
    branch_binding = secret_bindings.get("lakebase-branch")
    endpoint_binding = secret_bindings.get("lakebase-endpoint")

    return Installation(
        app_name=app_name,
        app_url=app_url,
        source_path=source_path,
        active_source_path=str(active_source) if active_source else None,
        installed_version=SemVer.parse(str(installed_version_value)),
        workspace_user=workspace_user,
        secret_scope=secret_scope,
        database_name=secrets.get("lakebase-database"),
        database_host=secrets.get("lakebase-host") or resolved.get("host"),
        database_user=secrets.get("lakebase-user"),
        database_host_secret_scope=host_binding[0] if host_binding else None,
        database_host_secret_key=host_binding[1] if host_binding else None,
        lakebase_project=secrets.get("lakebase-project") or resolved.get("project"),
        lakebase_branch=secrets.get("lakebase-branch") or resolved.get("branch"),
        lakebase_branch_secret_scope=branch_binding[0] if branch_binding else None,
        lakebase_branch_secret_key=branch_binding[1] if branch_binding else None,
        lakebase_endpoint=secrets.get("lakebase-endpoint") or resolved.get("endpoint"),
        lakebase_endpoint_secret_scope=(
            endpoint_binding[0] if endpoint_binding else None
        ),
        lakebase_endpoint_secret_key=endpoint_binding[1] if endpoint_binding else None,
        lakebase_instance=secrets.get("lakebase-instance-name"),
        legacy_baseline=legacy_baseline,
        warnings=warnings,
    )


def installation_as_json(installation: Installation) -> str:
    """Render non-secret installation metadata for command output."""
    return json.dumps(
        {
            "app_name": installation.app_name,
            "app_url": installation.app_url,
            "source_path": installation.source_path,
            "active_source_path": installation.active_source_path,
            "installed_version": str(installation.installed_version),
            "secret_scope": installation.secret_scope,
            "database_name": installation.database_name,
            "lakebase_project": installation.lakebase_project,
            "lakebase_branch": installation.lakebase_branch,
            "lakebase_instance": installation.lakebase_instance,
            "legacy_baseline": installation.legacy_baseline,
            "warnings": installation.warnings,
        },
        indent=2,
        sort_keys=True,
    )

