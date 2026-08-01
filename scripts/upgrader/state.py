"""Workspace-backed upgrade state and resumable run journals."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any


class UpgradeRunConflict(RuntimeError):
    """Raised when another non-terminal upgrade run is active."""


TERMINAL_STATES = {"succeeded", "failed", "rolled_back", "cancelled"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorkspaceStateStore:
    """Persist state outside the application database using Workspace Files."""

    def __init__(self, workspace_client: Any, management_path: str):
        self.workspace_client = workspace_client
        self.management_path = management_path.rstrip("/")
        self.runs_path = f"{self.management_path}/upgrade-runs"

    def _read_json(self, path: str) -> dict[str, Any] | None:
        try:
            exported = self.workspace_client.workspace.export(path=path)
        except Exception as exc:
            message = str(exc).lower()
            if (
                "not found" in message
                or "does not exist" in message
                or "doesn't exist" in message
            ):
                return None
            raise
        content = getattr(exported, "content", None)
        if not content:
            return None
        decoded = base64.b64decode(content).decode("utf-8")
        return json.loads(decoded)

    def _write_json(
        self,
        path: str,
        data: dict[str, Any],
        *,
        overwrite: bool = True,
    ) -> None:
        from databricks.sdk.service.workspace import ImportFormat

        parent = path.rsplit("/", 1)[0]
        self.workspace_client.workspace.mkdirs(parent)
        content = json.dumps(data, indent=2, sort_keys=True).encode("utf-8")
        self.workspace_client.workspace.import_(
            path=path,
            content=base64.b64encode(content).decode("ascii"),
            format=ImportFormat.AUTO,
            overwrite=overwrite,
        )

    @property
    def lock_path(self) -> str:
        return f"{self.management_path}/upgrade-lock.json"

    def acquire_run_lock(self, run_id: str) -> None:
        """Atomically acquire the installation-wide workspace upgrade lock."""
        existing = self._read_json(self.lock_path)
        if existing:
            if existing.get("run_id") == run_id:
                return
            raise UpgradeRunConflict(
                f"Upgrade run {existing.get('run_id')} holds the installation lock."
            )
        try:
            self._write_json(
                self.lock_path,
                {"run_id": run_id, "acquired_at": utc_now()},
                overwrite=False,
            )
        except Exception as exc:
            existing = self._read_json(self.lock_path)
            if existing and existing.get("run_id") == run_id:
                return
            holder = existing.get("run_id") if existing else "unknown"
            raise UpgradeRunConflict(
                f"Upgrade run {holder} acquired the installation lock."
            ) from exc

    def release_run_lock(self, run_id: str) -> None:
        existing = self._read_json(self.lock_path)
        if not existing or existing.get("run_id") != run_id:
            return
        try:
            self.workspace_client.workspace.delete(self.lock_path)
        except Exception as exc:
            if "not found" not in str(exc).lower():
                raise

    def load_installation(self) -> dict[str, Any] | None:
        return self._read_json(f"{self.management_path}/installation.json")

    def save_installation(self, data: dict[str, Any]) -> None:
        payload = dict(data)
        payload["updated_at"] = utc_now()
        self._write_json(f"{self.management_path}/installation.json", payload)

    def load_current_run(self) -> dict[str, Any] | None:
        return self._read_json(f"{self.management_path}/current-run.json")

    def start_run(self, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.acquire_run_lock(run_id)
        try:
            current = self.load_current_run()
            if current and current.get("status") not in TERMINAL_STATES:
                if current.get("run_id") != run_id:
                    self.release_run_lock(run_id)
                    raise UpgradeRunConflict(
                        f"Upgrade run {current.get('run_id')} is already "
                        f"{current.get('status', 'active')}."
                    )
                return current

            state = {
                **payload,
                "run_id": run_id,
                "status": "running",
                "phase": "planned",
                "started_at": utc_now(),
                "updated_at": utc_now(),
                "completed_phases": [],
            }
            self.save_run(state)
            return state
        except Exception:
            try:
                self.release_run_lock(run_id)
            except Exception:
                pass
            raise

    def save_run(self, state: dict[str, Any]) -> None:
        state["updated_at"] = utc_now()
        run_path = f"{self.runs_path}/{state['run_id']}.json"
        self._write_json(run_path, state)
        self._write_json(f"{self.management_path}/current-run.json", state)

    def complete_phase(
        self,
        state: dict[str, Any],
        phase: str,
        **updates: Any,
    ) -> None:
        completed = list(state.get("completed_phases", []))
        if phase not in completed:
            completed.append(phase)
        state.update(updates)
        state["completed_phases"] = completed
        state["phase"] = phase
        self.save_run(state)

    def fail_run(self, state: dict[str, Any], error: Exception) -> None:
        state["status"] = "failed"
        state["error"] = f"{type(error).__name__}: {error}"
        state["failed_at"] = utc_now()
        self.save_run(state)

    def finish_run(self, state: dict[str, Any]) -> None:
        state["status"] = "succeeded"
        state["phase"] = "complete"
        state["completed_at"] = utc_now()
        self.save_run(state)
        self.release_run_lock(str(state["run_id"]))

