"""Tests: AI proposes FMAPI_PROPRIETARY with GPT/OpenAI model."""
import pytest

from tests.ai_assistant.fmapi_proprietary.prompts import VALID_ENDPOINT_TYPES, VALID_RATE_TYPES


class TestFmapiPropOpenai:
    """AI proposes FMAPI_PROPRIETARY for GPT-5 mini (AC-10 to AC-14)."""

    def test_workload_type_is_fmapi_proprietary(self, gpt_input_proposal):
        wt = gpt_input_proposal["workload_type"]
        assert wt == "FMAPI_PROPRIETARY", (
            f"Expected FMAPI_PROPRIETARY, got {wt}"
        )

    def test_provider_is_openai(self, gpt_input_proposal):
        provider = (gpt_input_proposal.get("fmapi_provider") or "").lower()
        assert "openai" in provider, (
            f"fmapi_provider should contain 'openai', got "
            f"'{gpt_input_proposal.get('fmapi_provider')}'"
        )

    def test_model_contains_gpt(self, gpt_input_proposal):
        model = (gpt_input_proposal.get("fmapi_model") or "").lower()
        assert "gpt" in model, (
            f"fmapi_model should contain 'gpt', got "
            f"'{gpt_input_proposal.get('fmapi_model')}'"
        )

    def test_rate_type_is_valid(self, gpt_input_proposal):
        rt = gpt_input_proposal.get("fmapi_rate_type", "")
        assert rt in VALID_RATE_TYPES, (
            f"fmapi_rate_type should be valid, got '{rt}'. "
            f"Valid: {VALID_RATE_TYPES}"
        )

    def test_quantity_positive(self, gpt_input_proposal):
        qty = gpt_input_proposal.get("fmapi_quantity")
        assert qty is not None and qty > 0, (
            f"fmapi_quantity should be > 0, got {qty}"
        )
        assert 1 <= qty <= 200, (
            f"fmapi_quantity should be roughly 20 (range 1-200), got {qty}"
        )

    def test_endpoint_type_valid(self, gpt_input_proposal):
        et = gpt_input_proposal.get("fmapi_endpoint_type", "")
        assert et in VALID_ENDPOINT_TYPES, (
            f"fmapi_endpoint_type '{et}' not in {VALID_ENDPOINT_TYPES}"
        )

    def test_workload_name_non_empty(self, gpt_input_proposal):
        name = gpt_input_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_reason_populated(self, gpt_input_proposal):
        reason = gpt_input_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_proposal_id_present(self, gpt_input_proposal):
        pid = gpt_input_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present for confirm/reject flow"
