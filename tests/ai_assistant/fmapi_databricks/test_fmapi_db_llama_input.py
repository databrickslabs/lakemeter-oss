"""Tests: AI proposes FMAPI_DATABRICKS with Llama model and input tokens."""
import pytest

from tests.ai_assistant.fmapi_databricks.prompts import VALID_ENDPOINT_TYPES, VALID_RATE_TYPES


class TestFmapiDbLlamaInput:
    """AI proposes FMAPI_DATABRICKS for Llama 4 Maverick input tokens (AC-1 to AC-8)."""

    def test_workload_type_is_fmapi_databricks(self, llama_input_proposal):
        wt = llama_input_proposal["workload_type"]
        assert wt == "FMAPI_DATABRICKS", (
            f"Expected FMAPI_DATABRICKS, got {wt}"
        )

    def test_model_contains_llama(self, llama_input_proposal):
        model = (llama_input_proposal.get("fmapi_model") or "").lower()
        assert "llama" in model, (
            f"fmapi_model should contain 'llama', got "
            f"'{llama_input_proposal.get('fmapi_model')}'"
        )

    def test_rate_type_is_valid_token_type(self, llama_input_proposal):
        """AI may propose input_token or output_token — both are valid for Llama."""
        rt = llama_input_proposal.get("fmapi_rate_type", "")
        assert rt in VALID_RATE_TYPES, (
            f"fmapi_rate_type should be a valid rate type, got '{rt}'. "
            f"Valid: {VALID_RATE_TYPES}"
        )

    def test_quantity_in_range(self, llama_input_proposal):
        qty = llama_input_proposal.get("fmapi_quantity")
        assert qty is not None and qty > 0, (
            f"fmapi_quantity should be > 0, got {qty}"
        )
        assert 1 <= qty <= 100, (
            f"fmapi_quantity should be roughly 10 (range 1-100), got {qty}"
        )

    def test_endpoint_type_valid(self, llama_input_proposal):
        et = llama_input_proposal.get("fmapi_endpoint_type", "")
        assert et in VALID_ENDPOINT_TYPES, (
            f"fmapi_endpoint_type '{et}' not in {VALID_ENDPOINT_TYPES}"
        )

    def test_workload_name_non_empty(self, llama_input_proposal):
        name = llama_input_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_reason_populated(self, llama_input_proposal):
        reason = llama_input_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_proposal_id_present(self, llama_input_proposal):
        pid = llama_input_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present for confirm/reject flow"
