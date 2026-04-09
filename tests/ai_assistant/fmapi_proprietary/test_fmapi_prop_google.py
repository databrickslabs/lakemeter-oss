"""Tests: AI proposes FMAPI_PROPRIETARY with Gemini/Google model."""
import pytest

from tests.ai_assistant.fmapi_proprietary.prompts import VALID_ENDPOINT_TYPES, VALID_RATE_TYPES


class TestFmapiPropGoogle:
    """AI proposes FMAPI_PROPRIETARY for Gemini 2.5 Flash (AC-15 to AC-19)."""

    def test_workload_type_is_fmapi_proprietary(self, gemini_input_proposal):
        wt = gemini_input_proposal["workload_type"]
        assert wt == "FMAPI_PROPRIETARY", (
            f"Expected FMAPI_PROPRIETARY, got {wt}"
        )

    def test_provider_is_google(self, gemini_input_proposal):
        provider = (gemini_input_proposal.get("fmapi_provider") or "").lower()
        assert "google" in provider, (
            f"fmapi_provider should contain 'google', got "
            f"'{gemini_input_proposal.get('fmapi_provider')}'"
        )

    def test_model_contains_gemini(self, gemini_input_proposal):
        model = (gemini_input_proposal.get("fmapi_model") or "").lower()
        assert "gemini" in model, (
            f"fmapi_model should contain 'gemini', got "
            f"'{gemini_input_proposal.get('fmapi_model')}'"
        )

    def test_rate_type_is_valid(self, gemini_input_proposal):
        rt = gemini_input_proposal.get("fmapi_rate_type", "")
        assert rt in VALID_RATE_TYPES, (
            f"fmapi_rate_type should be valid, got '{rt}'. "
            f"Valid: {VALID_RATE_TYPES}"
        )

    def test_quantity_positive(self, gemini_input_proposal):
        qty = gemini_input_proposal.get("fmapi_quantity")
        assert qty is not None and qty > 0, (
            f"fmapi_quantity should be > 0, got {qty}"
        )
        assert 1 <= qty <= 200, (
            f"fmapi_quantity should be roughly 15 (range 1-200), got {qty}"
        )

    def test_endpoint_type_valid(self, gemini_input_proposal):
        et = gemini_input_proposal.get("fmapi_endpoint_type", "")
        assert et in VALID_ENDPOINT_TYPES, (
            f"fmapi_endpoint_type '{et}' not in {VALID_ENDPOINT_TYPES}"
        )

    def test_workload_name_non_empty(self, gemini_input_proposal):
        name = gemini_input_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_reason_populated(self, gemini_input_proposal):
        reason = gemini_input_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_proposal_id_present(self, gemini_input_proposal):
        pid = gemini_input_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present for confirm/reject flow"
