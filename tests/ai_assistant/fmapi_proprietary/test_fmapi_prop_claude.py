"""Tests: AI proposes FMAPI_PROPRIETARY with Claude/Anthropic model."""
import pytest

from tests.ai_assistant.fmapi_proprietary.prompts import VALID_ENDPOINT_TYPES, VALID_RATE_TYPES


class TestFmapiPropClaude:
    """AI proposes FMAPI_PROPRIETARY for Claude Sonnet 4.5 (AC-1 to AC-9)."""

    def test_workload_type_is_fmapi_proprietary(self, claude_input_proposal):
        wt = claude_input_proposal["workload_type"]
        assert wt == "FMAPI_PROPRIETARY", (
            f"Expected FMAPI_PROPRIETARY, got {wt}"
        )

    def test_provider_is_anthropic(self, claude_input_proposal):
        provider = (claude_input_proposal.get("fmapi_provider") or "").lower()
        assert "anthropic" in provider, (
            f"fmapi_provider should contain 'anthropic', got "
            f"'{claude_input_proposal.get('fmapi_provider')}'"
        )

    def test_model_contains_claude(self, claude_input_proposal):
        model = (claude_input_proposal.get("fmapi_model") or "").lower()
        assert "claude" in model, (
            f"fmapi_model should contain 'claude', got "
            f"'{claude_input_proposal.get('fmapi_model')}'"
        )

    def test_rate_type_is_valid(self, claude_input_proposal):
        rt = claude_input_proposal.get("fmapi_rate_type", "")
        assert rt in VALID_RATE_TYPES, (
            f"fmapi_rate_type should be valid, got '{rt}'. "
            f"Valid: {VALID_RATE_TYPES}"
        )

    def test_quantity_in_range(self, claude_input_proposal):
        qty = claude_input_proposal.get("fmapi_quantity")
        assert qty is not None and qty > 0, (
            f"fmapi_quantity should be > 0, got {qty}"
        )
        assert 1 <= qty <= 100, (
            f"fmapi_quantity should be roughly 5 (range 1-100), got {qty}"
        )

    def test_endpoint_type_valid(self, claude_input_proposal):
        et = claude_input_proposal.get("fmapi_endpoint_type", "")
        assert et in VALID_ENDPOINT_TYPES, (
            f"fmapi_endpoint_type '{et}' not in {VALID_ENDPOINT_TYPES}"
        )

    def test_workload_name_non_empty(self, claude_input_proposal):
        name = claude_input_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_reason_populated(self, claude_input_proposal):
        reason = claude_input_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_proposal_id_present(self, claude_input_proposal):
        pid = claude_input_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present for confirm/reject flow"
