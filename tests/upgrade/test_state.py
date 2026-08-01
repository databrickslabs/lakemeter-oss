import base64
from types import SimpleNamespace

import pytest

from upgrader.state import UpgradeRunConflict, WorkspaceStateStore


class FakeWorkspaceFiles:
    def __init__(self):
        self.files = {}

    def mkdirs(self, _path):
        return None

    def import_(self, path, content, overwrite=True, **_kwargs):
        if not overwrite and path in self.files:
            raise RuntimeError("already exists")
        self.files[path] = content

    def export(self, path):
        if path not in self.files:
            raise RuntimeError("not found")
        return SimpleNamespace(content=self.files[path])

    def delete(self, path):
        if path not in self.files:
            raise RuntimeError("not found")
        del self.files[path]


def fake_client():
    return SimpleNamespace(workspace=FakeWorkspaceFiles())


def test_run_state_is_workspace_backed_and_resumable():
    client = fake_client()
    store = WorkspaceStateStore(client, "/Workspace/apps/lakemeter/.lakemeter")

    run = store.start_run("v0.1.1", {"target_version": "0.1.1"})
    store.complete_phase(run, "runtime_staged", release_path="/releases/v0.1.1")

    resumed = store.start_run("v0.1.1", {"target_version": "ignored"})
    assert resumed["completed_phases"] == ["runtime_staged"]
    assert resumed["release_path"] == "/releases/v0.1.1"


def test_concurrent_run_is_rejected():
    client = fake_client()
    store = WorkspaceStateStore(client, "/Workspace/apps/lakemeter/.lakemeter")
    store.start_run("first", {"target_version": "0.1.1"})

    with pytest.raises(UpgradeRunConflict, match="first"):
        store.start_run("second", {"target_version": "0.1.2"})


def test_finished_run_allows_next_run():
    client = fake_client()
    store = WorkspaceStateStore(client, "/Workspace/apps/lakemeter/.lakemeter")
    first = store.start_run("first", {"target_version": "0.1.1"})
    store.finish_run(first)

    second = store.start_run("second", {"target_version": "0.1.2"})
    assert second["run_id"] == "second"

