import json
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "release_integration.py"
)
SPEC = importlib.util.spec_from_file_location(
    "release_integration",
    MODULE_PATH,
)
assert SPEC and SPEC.loader
release_integration = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_integration)


def ai_parse_item():
    return {
        "ai_parse_mode": "pages",
        "ai_parse_pages_thousands": 2.5,
        "ai_parse_calculation_method": "pages_based",
        "ai_parse_complexity": "high",
        "ai_parse_dbu_quantity": None,
        "ai_parse_num_pages": 2500.0,
    }


def agent_evaluation_item():
    return {
        "agent_evaluation_labels_enabled": True,
        "agent_evaluation_input_tokens_millions": 2.0,
        "agent_evaluation_output_tokens_millions": 3.0,
        "agent_evaluation_synthetic_data_enabled": True,
        "agent_evaluation_synthetic_questions": 4,
    }


def test_ai_parse_persistence_check_reports_mismatches():
    release_integration._assert_ai_parse_persisted(
        ai_parse_item(),
        "item",
    )

    broken = ai_parse_item()
    broken["ai_parse_mode"] = None
    with pytest.raises(
        release_integration.IntegrationFailure,
        match="ai_parse_mode",
    ):
        release_integration._assert_ai_parse_persisted(broken, "item")


def test_agent_evaluation_persistence_check_reports_mismatches():
    release_integration._assert_agent_evaluation_persisted(
        agent_evaluation_item(),
        "item",
    )
    broken = agent_evaluation_item()
    broken["agent_evaluation_output_tokens_millions"] = None
    with pytest.raises(
        release_integration.IntegrationFailure,
        match="agent_evaluation_output_tokens_millions",
    ):
        release_integration._assert_agent_evaluation_persisted(
            broken,
            "item",
        )


def test_seed_records_baseline_source_and_cross_version_ids(
    monkeypatch,
    tmp_path,
):
    state_path = tmp_path / "state.json"

    class FakeAppClient:
        def __init__(self, _workspace_client, _app_name):
            self.app = SimpleNamespace(
                url="https://meter.example",
                active_deployment=SimpleNamespace(
                    source_code_path="/Workspace/apps/meter"
                ),
            )

        def json(self, method, path, *, expected_status=200, **_kwargs):
            if path == "/calculate/ai-parse":
                return {
                    "data": {
                        "dbu_calculation": {"dbu_per_month": 218.75}
                    }
                }
            if method == "POST" and path == "/estimates/":
                assert expected_status == 201
                return {"estimate_id": "estimate-1"}
            if method == "POST" and path == "/line-items/":
                assert expected_status == 201
                return {"line_item_id": "line-1"}
            if method == "GET" and path == "/line-items/line-1":
                return {"ai_parse_mode": None}
            raise AssertionError(f"Unexpected request: {method} {path}")

    monkeypatch.setattr(
        release_integration,
        "AppClient",
        FakeAppClient,
    )

    result = release_integration.seed_baseline(
        SimpleNamespace(),
        "meter",
        state_path,
    )

    assert result["estimate_id"] == "estimate-1"
    assert result["line_item_id"] == "line-1"
    assert result["baseline_source_path"] == "/Workspace/apps/meter"
    assert json.loads(state_path.read_text()) == result


def test_candidate_verifies_health_persistence_clone_and_export(
    monkeypatch,
    tmp_path,
):
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "estimate_id": "estimate-1",
                "line_item_id": "original-1",
                "baseline_source_path": "/Workspace/apps/meter",
            }
        )
    )

    class FakeAppClient:
        def __init__(self, _workspace_client, _app_name):
            self.app = SimpleNamespace(
                active_deployment=SimpleNamespace(
                    source_code_path="/Workspace/apps/meter/releases/v0.1.1"
                )
            )
            self.deleted = False

        def json(self, method, path, *, expected_status=200, **_kwargs):
            if path == "/system/health":
                return {
                    "status": "healthy",
                    "database": "connected",
                    "app_version": "0.1.1",
                }
            if path == "/system/version":
                return {"app_version": "0.1.1"}
            if path == "/regions":
                assert _kwargs["params"] == {"cloud": "AWS"}
                return {"success": True, "data": {"regions": ["us-east-1"]}}
            if path == "/calculate/ai-parse":
                return {
                    "data": {
                        "dbu_calculation": {"dbu_per_month": 218.75}
                    }
                }
            if path == "/calculate/agent-evaluation":
                return {
                    "data": {
                        "dbu_calculation": {"dbu_per_month": 49.999}
                    }
                }
            if method == "POST" and path == "/line-items/":
                assert expected_status == 201
                workload_type = _kwargs["json"]["workload_type"]
                if workload_type == "AGENT_EVALUATION":
                    return {"line_item_id": "agent-1"}
                return {"line_item_id": "fresh-1"}
            if method == "POST" and path == "/line-items/fresh-1/clone":
                assert expected_status == 201
                return {"line_item_id": "clone-1"}
            if method == "POST" and path == "/line-items/agent-1/clone":
                assert expected_status == 201
                return {"line_item_id": "agent-clone-1"}
            if method == "GET" and path.startswith("/line-items/"):
                if "agent" in path:
                    return agent_evaluation_item()
                return ai_parse_item()
            if method == "PUT" and path == "/line-items/original-1":
                return ai_parse_item()
            raise AssertionError(f"Unexpected JSON request: {method} {path}")

        def request(self, method, path, *, expected_status=200, **_kwargs):
            if method == "GET" and path.endswith("/excel"):
                return SimpleNamespace(content=b"x" * 1200)
            if method == "DELETE" and path == "/estimates/estimate-1":
                assert expected_status == 204
                self.deleted = True
                return SimpleNamespace(content=b"")
            raise AssertionError(f"Unexpected request: {method} {path}")

    monkeypatch.setattr(
        release_integration,
        "AppClient",
        FakeAppClient,
    )

    result = release_integration.verify_candidate(
        SimpleNamespace(),
        "meter",
        "0.1.1",
        state_path,
    )

    assert result["status"] == "passed"
    assert result["excel_bytes"] == 1200
    assert result["agent_evaluation_item"] == agent_evaluation_item()
    assert result["agent_evaluation_clone"] == agent_evaluation_item()
    saved = json.loads(state_path.read_text())
    assert saved["test_data_deleted"] is True
    assert saved["candidate_source_path"].endswith("/releases/v0.1.1")


def test_rollback_requires_exact_baseline_source(tmp_path):
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {"baseline_source_path": "/Workspace/apps/meter"}
        )
    )
    matching_client = SimpleNamespace(
        apps=SimpleNamespace(
            get=lambda _name: SimpleNamespace(
                active_deployment=SimpleNamespace(
                    source_code_path="/Workspace/apps/meter"
                )
            )
        )
    )

    result = release_integration.verify_rollback(
        matching_client,
        "meter",
        state_path,
    )
    assert result["status"] == "passed"

    mismatching_client = SimpleNamespace(
        apps=SimpleNamespace(
            get=lambda _name: SimpleNamespace(
                active_deployment=SimpleNamespace(
                    source_code_path="/Workspace/apps/meter/releases/v0.1.1"
                )
            )
        )
    )
    with pytest.raises(
        release_integration.IntegrationFailure,
        match="Rollback restored",
    ):
        release_integration.verify_rollback(
            mismatching_client,
            "meter",
            state_path,
        )
