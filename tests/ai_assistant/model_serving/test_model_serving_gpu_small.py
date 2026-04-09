"""Tests: AI proposes MODEL_SERVING with GPU Small (T4) compute type."""
import pytest

from tests.ai_assistant.model_serving.prompts import VALID_SERVING_TYPES


class TestModelServingGpuSmall:
    """AI proposes a MODEL_SERVING GPU Small workload (AC-12 through AC-14)."""

    def test_workload_type_is_model_serving(self, gpu_small_proposal):
        assert gpu_small_proposal["workload_type"] == "MODEL_SERVING", (
            f"Expected MODEL_SERVING, got {gpu_small_proposal['workload_type']}"
        )

    def test_serving_type_is_gpu_small(self, gpu_small_proposal):
        st = (gpu_small_proposal.get("model_serving_type") or "").lower()
        assert "gpu_small" in st, (
            f"model_serving_type should contain 'gpu_small', got "
            f"'{gpu_small_proposal.get('model_serving_type')}'"
        )

    def test_serving_type_valid_enum(self, gpu_small_proposal):
        st = gpu_small_proposal.get("model_serving_type", "")
        assert st in VALID_SERVING_TYPES, (
            f"model_serving_type '{st}' not in {VALID_SERVING_TYPES}"
        )

    def test_hours_per_month_present(self, gpu_small_proposal):
        hours = gpu_small_proposal.get("hours_per_month")
        assert hours is not None and hours > 0, (
            f"hours_per_month should be > 0, got {hours}"
        )

    def test_workload_name_non_empty(self, gpu_small_proposal):
        name = gpu_small_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_reason_populated(self, gpu_small_proposal):
        reason = gpu_small_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_notes_populated(self, gpu_small_proposal):
        notes = gpu_small_proposal.get("notes", "")
        assert notes and len(notes) >= 1, (
            f"notes should be populated: '{notes}'"
        )

    def test_proposal_id_present(self, gpu_small_proposal):
        pid = gpu_small_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present for confirm/reject flow"
