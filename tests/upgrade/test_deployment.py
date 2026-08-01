import base64
from pathlib import Path
from types import SimpleNamespace

import pytest

from upgrader.deployment import (
    DeploymentError,
    set_app_running,
    stage_runtime,
    verify_app,
)


class FakeWorkspace:
    def __init__(self):
        self.files = {}

    def delete(self, path, recursive=False):
        assert recursive
        self.files = {
            name: value
            for name, value in self.files.items()
            if not name.startswith(f"{path.rstrip('/')}/")
        }

    def mkdirs(self, _path):
        return None

    def import_(self, path, content, **_kwargs):
        self.files[path] = base64.b64decode(content)

    def export(self, path):
        if path not in self.files:
            raise RuntimeError("not found")
        return SimpleNamespace(
            content=base64.b64encode(self.files[path]).decode()
        )


def create_runtime(root: Path):
    (root / "backend/app").mkdir(parents=True)
    (root / "backend/static/pricing").mkdir(parents=True)
    (root / "backend/static").mkdir(exist_ok=True)
    (root / "backend/app/main.py").write_text("app = object()")
    (root / "backend/static/index.html").write_text("<html></html>")
    (root / "backend/static/pricing/rates.json").write_text("{}")
    (root / "backend/static/pricing/large.csv").write_text("ignored")
    (root / "README.md").write_text("ignored")
    (root / "app.yaml").write_text("wrong: defaults")
    (root / "requirements.txt").write_text("fastapi")


def test_staging_is_versioned_clean_and_preserves_live_app_yaml(tmp_path):
    create_runtime(tmp_path)
    workspace = FakeWorkspace()
    client = type("Client", (), {"workspace": workspace})()

    summary = stage_runtime(
        client,
        tmp_path,
        "/Workspace/apps/lakemeter/releases/v0.1.1",
        app_yaml_content=b"live: bindings",
    )
    assert summary["uploaded_files"] == 5
    assert not any(path.endswith(".csv") for path in workspace.files)
    assert not any(path.endswith(".md") for path in workspace.files)
    assert (
        workspace.files[
            "/Workspace/apps/lakemeter/releases/v0.1.1/app.yaml"
        ]
        == b"live: bindings"
    )


def test_verification_is_authenticated_and_checks_database(monkeypatch):
    calls = []
    responses = iter(
        [
            {"status": "healthy", "database": "connected"},
            {"app_version": "0.1.1"},
        ]
    )

    class Response:
        status_code = 200

        def __init__(self, body):
            self.body = body

        def json(self):
            return self.body

    def fake_get(url, headers, timeout):
        calls.append((url, headers, timeout))
        return Response(next(responses))

    monkeypatch.setattr("upgrader.deployment.requests.get", fake_get)
    client = type(
        "Client",
        (),
        {
            "config": type(
                "Config",
                (),
                {"authenticate": lambda _self: {"Authorization": "Bearer token"}},
            )()
        },
    )()

    verify_app(client, "lakemeter", "https://meter.example", "0.1.1")

    assert calls[0][0].endswith("/api/v1/system/health")
    assert calls[1][0].endswith("/api/v1/system/version")
    assert all(call[1]["Authorization"] == "Bearer token" for call in calls)


def test_verification_exchanges_notebook_token_after_401(monkeypatch):
    calls = []
    responses = iter(
        [
            (401, {"error": "unauthorized"}),
            (200, {"status": "healthy", "database": "connected"}),
            (200, {"app_version": "0.1.1"}),
        ]
    )

    class Response:
        def __init__(self, status_code, body, text=""):
            self.status_code = status_code
            self.body = body
            self.text = text

        def json(self):
            return self.body

    def fake_get(url, headers, timeout):
        calls.append((url, headers, timeout))
        status_code, body = next(responses)
        return Response(status_code, body)

    def fake_post(url, data, timeout):
        assert url == "https://workspace.example/oidc/v1/token"
        assert data == {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "subject_token": "notebook-token",
            "subject_token_type": (
                "urn:databricks:params:oauth:token-type:personal-access-token"
            ),
            "requested_token_type": (
                "urn:ietf:params:oauth:token-type:access_token"
            ),
            "scope": "all-apis",
            "audience": "app-client-id",
        }
        assert timeout == 30
        return Response(200, {"access_token": "app-audience-token"})

    monkeypatch.setattr("upgrader.deployment.requests.get", fake_get)
    monkeypatch.setattr("upgrader.deployment.requests.post", fake_post)
    client = type(
        "Client",
        (),
        {
            "config": type(
                "Config",
                (),
                {
                    "host": "https://workspace.example",
                    "authenticate": lambda _self: {
                        "Authorization": "Bearer notebook-token"
                    },
                },
            )(),
            "apps": SimpleNamespace(
                get=lambda _name: SimpleNamespace(
                    oauth2_app_client_id="app-client-id"
                )
            ),
        },
    )()

    verify_app(client, "lakemeter", "https://meter.example", "0.1.1")

    assert len(calls) == 3
    assert calls[0][1]["Authorization"] == "Bearer notebook-token"
    assert all(
        call[1]["Authorization"] == "Bearer app-audience-token"
        for call in calls[1:]
    )


def test_verification_reports_app_token_exchange_failure(monkeypatch):
    class Response:
        def __init__(self, status_code, body, text=""):
            self.status_code = status_code
            self.body = body
            self.text = text

        def json(self):
            return self.body

    monkeypatch.setattr(
        "upgrader.deployment.requests.get",
        lambda *_args, **_kwargs: Response(401, {}),
    )
    monkeypatch.setattr(
        "upgrader.deployment.requests.post",
        lambda *_args, **_kwargs: Response(
            400,
            {"error": "invalid_request"},
            text="invalid token exchange",
        ),
    )
    client = type(
        "Client",
        (),
        {
            "config": type(
                "Config",
                (),
                {
                    "host": "https://workspace.example",
                    "authenticate": lambda _self: {
                        "Authorization": "Bearer notebook-token"
                    },
                },
            )(),
            "apps": SimpleNamespace(
                get=lambda _name: SimpleNamespace(
                    oauth2_app_client_id="app-client-id"
                )
            ),
        },
    )()

    with pytest.raises(DeploymentError, match="token exchange failed"):
        verify_app(
            client,
            "lakemeter",
            "https://meter.example",
            "0.1.1",
        )


def test_versioned_release_path_rejects_different_runtime(tmp_path):
    create_runtime(tmp_path)
    workspace = FakeWorkspace()
    client = type("Client", (), {"workspace": workspace})()
    release_path = "/Workspace/apps/lakemeter/releases/v0.1.1"

    stage_runtime(
        client,
        tmp_path,
        release_path,
        app_yaml_content=b"live: bindings",
        release_fingerprint="a" * 64,
    )

    with pytest.raises(DeploymentError, match="immutable"):
        stage_runtime(
            client,
            tmp_path,
            release_path,
            app_yaml_content=b"live: bindings",
            release_fingerprint="b" * 64,
        )


@pytest.mark.parametrize(
    ("running", "state"),
    [
        (True, "ACTIVE"),
        (False, "STOPPED"),
    ],
)
def test_set_app_running_is_idempotent(running, state):
    operations = []
    client = SimpleNamespace(
        apps=SimpleNamespace(
            get=lambda _name: SimpleNamespace(
                compute_status=SimpleNamespace(state=state)
            ),
            start=lambda name: operations.append(("start", name)),
            stop=lambda name: operations.append(("stop", name)),
        )
    )

    set_app_running(client, "lakemeter", running=running)

    assert operations == []

