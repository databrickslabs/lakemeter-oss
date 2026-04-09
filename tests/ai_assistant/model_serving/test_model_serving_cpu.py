"""Tests: AI proposes MODEL_SERVING with CPU compute type."""
import pytest

from tests.ai_assistant.model_serving.prompts import VALID_SERVING_TYPES


class TestModelServingCpu:
    """AI proposes a MODEL_SERVING CPU workload (AC-8 through AC-11)."""

    def test_workload_type_is_model_serving(self, cpu_proposal):
        assert cpu_proposal["workload_type"] == "MODEL_SERVING", (
            f"Expected MODEL_SERVING, got {cpu_proposal['workload_type']}"
        )

    def test_serving_type_is_cpu(self, cpu_proposal):
        st = (cpu_proposal.get("model_serving_type") or "").lower()
        assert "cpu" in st, (
            f"model_serving_type should contain 'cpu', got "
            f"'{cpu_proposal.get('model_serving_type')}'"
        )

    def test_serving_type_valid_enum(self, cpu_proposal):
        st = cpu_proposal.get("model_serving_type", "")
        assert st in VALID_SERVING_TYPES, (
            f"model_serving_type '{st}' not in {VALID_SERVING_TYPES}"
        )

    def test_hours_per_month_present(self, cpu_proposal):
        hours = cpu_proposal.get("hours_per_month")
        assert hours is not None and hours > 0, (
            f"hours_per_month should be > 0, got {hours}"
        )

    def test_scale_to_zero_is_boolean_when_present(self, cpu_proposal):
        stz = cpu_proposal.get("model_serving_scale_to_zero")
        if stz is not None:
            assert isinstance(stz, bool), (
                f"model_serving_scale_to_zero should be bool, got {type(stz).__name__}: {stz}"
            )

    def test_workload_name_non_empty(self, cpu_proposal):
        name = cpu_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_reason_populated(self, cpu_proposal):
        reason = cpu_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_proposal_id_present(self, cpu_proposal):
        pid = cpu_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present for confirm/reject flow"
