"""Tests: AI proposes MODEL_SERVING with GPU Medium (A10G) and correct fields."""
import pytest

from tests.ai_assistant.model_serving.prompts import VALID_SERVING_TYPES


class TestModelServingGpuMedium:
    """AI proposes a MODEL_SERVING GPU Medium workload (AC-1 through AC-7)."""

    def test_workload_type_is_model_serving(self, gpu_medium_proposal):
        assert gpu_medium_proposal["workload_type"] == "MODEL_SERVING", (
            f"Expected MODEL_SERVING, got {gpu_medium_proposal['workload_type']}"
        )

    def test_serving_type_is_gpu_medium(self, gpu_medium_proposal):
        st = (gpu_medium_proposal.get("model_serving_type") or "").lower()
        assert "gpu_medium" in st, (
            f"model_serving_type should contain 'gpu_medium', got "
            f"'{gpu_medium_proposal.get('model_serving_type')}'"
        )

    def test_serving_type_valid_enum(self, gpu_medium_proposal):
        st = gpu_medium_proposal.get("model_serving_type", "")
        assert st in VALID_SERVING_TYPES, (
            f"model_serving_type '{st}' not in {VALID_SERVING_TYPES}"
        )

    def test_hours_per_month_approximately_200(self, gpu_medium_proposal):
        hours = gpu_medium_proposal.get("hours_per_month")
        assert hours is not None and hours > 0, (
            f"hours_per_month should be > 0, got {hours}"
        )
        assert 100 <= hours <= 744, (
            f"hours_per_month should be roughly 200 (range 100-744), got {hours}"
        )

    def test_workload_name_non_empty(self, gpu_medium_proposal):
        name = gpu_medium_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_reason_populated(self, gpu_medium_proposal):
        reason = gpu_medium_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_notes_populated(self, gpu_medium_proposal):
        notes = gpu_medium_proposal.get("notes", "")
        assert notes and len(notes) >= 1, (
            f"notes should be populated: '{notes}'"
        )

    def test_proposal_id_present(self, gpu_medium_proposal):
        pid = gpu_medium_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present for confirm/reject flow"
