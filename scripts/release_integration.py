#!/usr/bin/env python3
"""Cross-version integration checks for a Lakemeter release candidate."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from databricks.sdk import WorkspaceClient


AI_PARSE_FIELDS = (
    "ai_parse_mode",
    "ai_parse_pages_thousands",
    "ai_parse_calculation_method",
    "ai_parse_complexity",
    "ai_parse_dbu_quantity",
    "ai_parse_num_pages",
)


class IntegrationFailure(RuntimeError):
    """Raised when a release-candidate integration assertion fails."""


class AppClient:
    """Authenticated HTTP client for a deployed Databricks App."""

    def __init__(
        self,
        workspace_client: WorkspaceClient,
        app_name: str,
    ) -> None:
        self.workspace_client = workspace_client
        self.app = workspace_client.apps.get(app_name)
        if not self.app.url:
            raise IntegrationFailure(f"App '{app_name}' has no URL.")
        self.base_url = f"{self.app.url.rstrip('/')}/api/v1"
        self.headers = {
            **workspace_client.config.authenticate(),
            "Content-Type": "application/json",
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        expected_status: int = 200,
        **kwargs: Any,
    ) -> requests.Response:
        response = requests.request(
            method,
            f"{self.base_url}{path}",
            headers=self.headers,
            timeout=60,
            **kwargs,
        )
        if response.status_code != expected_status:
            raise IntegrationFailure(
                f"{method} {path} returned HTTP {response.status_code}; "
                f"expected {expected_status}: {response.text[:500]}"
            )
        return response

    def json(
        self,
        method: str,
        path: str,
        *,
        expected_status: int = 200,
        **kwargs: Any,
    ) -> dict[str, Any]:
        response = self.request(
            method,
            path,
            expected_status=expected_status,
            **kwargs,
        )
        data = response.json()
        if not isinstance(data, dict):
            raise IntegrationFailure(
                f"{method} {path} did not return a JSON object."
            )
        return data


def _workspace_client(profile: str | None) -> WorkspaceClient:
    if profile:
        return WorkspaceClient(profile=profile)
    return WorkspaceClient()


def _selected_ai_parse(item: dict[str, Any]) -> dict[str, Any]:
    return {field: item.get(field) for field in AI_PARSE_FIELDS}


def _assert_ai_parse_persisted(item: dict[str, Any], label: str) -> None:
    values = _selected_ai_parse(item)
    expected = {
        "ai_parse_mode": "pages",
        "ai_parse_pages_thousands": 2.5,
        "ai_parse_calculation_method": "pages_based",
        "ai_parse_complexity": "high",
        "ai_parse_num_pages": 2500.0,
    }
    mismatches = {
        field: {"expected": value, "actual": values.get(field)}
        for field, value in expected.items()
        if values.get(field) != value
    }
    if mismatches:
        raise IntegrationFailure(
            f"{label} did not persist AI Parse fields: {mismatches}"
        )


def _ai_parse_calculation(client: AppClient) -> dict[str, Any]:
    calculation = client.json(
        "POST",
        "/calculate/ai-parse",
        json={
            "cloud": "AWS",
            "region": "ap-southeast-1",
            "tier": "ENTERPRISE",
            "mode": "pages",
            "complexity": "high",
            "pages_thousands": 2.5,
        },
    )
    monthly_dbu = (
        calculation.get("data", {})
        .get("dbu_calculation", {})
        .get("dbu_per_month")
    )
    if monthly_dbu != 218.75:
        raise IntegrationFailure(
            f"AI Parse returned {monthly_dbu} DBU/month; expected 218.75."
        )
    return calculation


def seed_baseline(
    workspace_client: WorkspaceClient,
    app_name: str,
    state_path: Path,
) -> dict[str, Any]:
    """Create data on the previous release for post-upgrade verification."""
    client = AppClient(workspace_client, app_name)
    calculation = _ai_parse_calculation(client)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    estimate = client.json(
        "POST",
        "/estimates/",
        expected_status=201,
        json={
            "estimate_name": f"Release candidate integration {stamp}",
            "cloud": "AWS",
            "region": "ap-southeast-1",
            "tier": "ENTERPRISE",
            "status": "draft",
        },
    )
    estimate_id = str(estimate["estimate_id"])
    line_item = client.json(
        "POST",
        "/line-items/",
        expected_status=201,
        json={
            "estimate_id": estimate_id,
            "workload_name": "Cross-version AI Parse regression",
            "workload_type": "AI_PARSE",
            "cloud": "AWS",
            "ai_parse_mode": "pages",
            "ai_parse_complexity": "high",
            "ai_parse_pages_thousands": 2.5,
            "cost_calculation_response": calculation,
            "calculation_completed_at": datetime.now(
                timezone.utc
            ).isoformat(),
        },
    )
    line_item_id = str(line_item["line_item_id"])
    reloaded = client.json("GET", f"/line-items/{line_item_id}")
    active = getattr(client.app, "active_deployment", None)
    baseline_source = str(
        getattr(active, "source_code_path", "") or ""
    )
    if not baseline_source:
        raise IntegrationFailure("Baseline app has no active source path.")

    state = {
        "app_name": app_name,
        "app_url": client.app.url,
        "baseline_source_path": baseline_source,
        "estimate_id": estimate_id,
        "line_item_id": line_item_id,
        "baseline_ai_parse": _selected_ai_parse(reloaded),
    }
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True))
    return state


def verify_candidate(
    workspace_client: WorkspaceClient,
    app_name: str,
    expected_version: str,
    state_path: Path,
) -> dict[str, Any]:
    """Verify the upgraded app, full persistence path, clone, and export."""
    state = json.loads(state_path.read_text())
    client = AppClient(workspace_client, app_name)

    health = client.json("GET", "/system/health")
    if (
        health.get("status") != "healthy"
        or health.get("database") != "connected"
        or health.get("app_version") != expected_version
    ):
        raise IntegrationFailure(f"Candidate health check failed: {health}")
    version = client.json("GET", "/system/version")
    if version.get("app_version") != expected_version:
        raise IntegrationFailure(
            f"Candidate reports {version.get('app_version')}; "
            f"expected {expected_version}."
        )

    regions = client.json(
        "GET",
        "/regions",
        params={"cloud": "AWS"},
    )
    if not regions.get("success") or not regions.get("data", {}).get("regions"):
        raise IntegrationFailure("Reference-data integration check failed.")

    calculation = _ai_parse_calculation(client)
    fields = {
        "ai_parse_mode": "pages",
        "ai_parse_complexity": "high",
        "ai_parse_pages_thousands": 2.5,
        "cost_calculation_response": calculation,
        "calculation_completed_at": datetime.now(timezone.utc).isoformat(),
    }
    original_id = str(state["line_item_id"])
    client.json("PUT", f"/line-items/{original_id}", json=fields)
    original = client.json("GET", f"/line-items/{original_id}")
    _assert_ai_parse_persisted(original, "Upgraded baseline item")

    estimate_id = str(state["estimate_id"])
    fresh = client.json(
        "POST",
        "/line-items/",
        expected_status=201,
        json={
            "estimate_id": estimate_id,
            "workload_name": "Candidate AI Parse item",
            "workload_type": "AI_PARSE",
            "cloud": "AWS",
            **fields,
        },
    )
    fresh_id = str(fresh["line_item_id"])
    fresh_reloaded = client.json("GET", f"/line-items/{fresh_id}")
    _assert_ai_parse_persisted(fresh_reloaded, "New candidate item")

    cloned = client.json(
        "POST",
        f"/line-items/{fresh_id}/clone",
        expected_status=201,
        json={"new_name": "Candidate AI Parse clone"},
    )
    clone_id = str(cloned["line_item_id"])
    clone_reloaded = client.json("GET", f"/line-items/{clone_id}")
    _assert_ai_parse_persisted(clone_reloaded, "Cloned candidate item")

    exported = client.request(
        "GET",
        f"/export/estimate/{estimate_id}/excel",
    )
    if len(exported.content) < 1000:
        raise IntegrationFailure(
            f"Excel export was unexpectedly small: {len(exported.content)} bytes."
        )

    client.request(
        "DELETE",
        f"/estimates/{estimate_id}",
        expected_status=204,
    )
    state["candidate_source_path"] = str(
        getattr(client.app.active_deployment, "source_code_path", "") or ""
    )
    state["test_data_deleted"] = True
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True))
    return {
        "status": "passed",
        "version": expected_version,
        "health": health,
        "baseline_item": _selected_ai_parse(original),
        "fresh_item": _selected_ai_parse(fresh_reloaded),
        "cloned_item": _selected_ai_parse(clone_reloaded),
        "excel_bytes": len(exported.content),
    }


def verify_rollback(
    workspace_client: WorkspaceClient,
    app_name: str,
    state_path: Path,
) -> dict[str, Any]:
    """Verify rollback restored the exact pre-upgrade application source."""
    state = json.loads(state_path.read_text())
    app = workspace_client.apps.get(app_name)
    active = getattr(app, "active_deployment", None)
    active_source = str(getattr(active, "source_code_path", "") or "")
    expected_source = str(state["baseline_source_path"])
    if active_source != expected_source:
        raise IntegrationFailure(
            f"Rollback restored {active_source or '<missing>'}; "
            f"expected {expected_source}."
        )
    return {
        "status": "passed",
        "active_source_path": active_source,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("seed", "verify", "rollback"))
    parser.add_argument("--app-name", required=True)
    parser.add_argument("--state-file", type=Path, required=True)
    parser.add_argument("--expected-version")
    parser.add_argument("--profile")
    args = parser.parse_args()

    workspace_client = _workspace_client(args.profile)
    if args.command == "seed":
        result = seed_baseline(
            workspace_client,
            args.app_name,
            args.state_file,
        )
    elif args.command == "verify":
        if not args.expected_version:
            parser.error("--expected-version is required for verify")
        result = verify_candidate(
            workspace_client,
            args.app_name,
            args.expected_version,
            args.state_file,
        )
    else:
        result = verify_rollback(
            workspace_client,
            args.app_name,
            args.state_file,
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
