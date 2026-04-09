"""Tests: AI proposes FMAPI_DATABRICKS with output_token rate type."""
import pytest

from tests.ai_assistant.fmapi_databricks.prompts import VALID_ENDPOINT_TYPES


class TestFmapiDbOutputTokens:
    """AI proposes FMAPI_DATABRICKS for output tokens (AC-9 to AC-13)."""

    def test_workload_type_is_fmapi_databricks(self, output_token_proposal):
        wt = output_token_proposal["workload_type"]
        assert wt == "FMAPI_DATABRICKS", (
            f"Expected FMAPI_DATABRICKS, got {wt}"
        )

    def test_rate_type_is_output_token(self, output_token_proposal):
        rt = output_token_proposal.get("fmapi_rate_type", "")
        assert rt == "output_token", (
            f"fmapi_rate_type should be 'output_token', got '{rt}'"
        )

    def test_quantity_in_range(self, output_token_proposal):
        qty = output_token_proposal.get("fmapi_quantity")
        assert qty is not None and qty > 0, (
            f"fmapi_quantity should be > 0, got {qty}"
        )
        assert 1 <= qty <= 50, (
            f"fmapi_quantity should be roughly 5 (range 1-50), got {qty}"
        )

    def test_model_populated(self, output_token_proposal):
        model = output_token_proposal.get("fmapi_model", "")
        assert model and len(model) >= 2, (
            f"fmapi_model should be populated, got '{model}'"
        )

    def test_endpoint_type_valid(self, output_token_proposal):
        et = output_token_proposal.get("fmapi_endpoint_type", "")
        assert et in VALID_ENDPOINT_TYPES, (
            f"fmapi_endpoint_type '{et}' not in {VALID_ENDPOINT_TYPES}"
        )

    def test_workload_name_non_empty(self, output_token_proposal):
        name = output_token_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_reason_populated(self, output_token_proposal):
        reason = output_token_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_proposal_id_present(self, output_token_proposal):
        pid = output_token_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present for confirm/reject flow"
