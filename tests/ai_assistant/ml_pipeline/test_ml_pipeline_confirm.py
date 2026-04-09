"""Tests: confirm all ML pipeline proposals and verify conversation state.

AC-7 through AC-9: multi-workload confirm flow for the ML pipeline.
"""
import pytest

from tests.ai_assistant.chat_helpers import get_conversation_state

EXPECTED_TYPES = {"VECTOR_SEARCH", "FMAPI_PROPRIETARY", "MODEL_SERVING"}


class TestConfirmAllThree:
    """AC-7: all 3 confirmations succeed."""

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_confirmation_success(self, ml_pipeline_session, idx):
        result = ml_pipeline_session["confirmations"][idx]
        assert result["success"] is True, (
            f"Confirmation {idx} should succeed: {result}"
        )

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_confirmation_action_confirmed(self, ml_pipeline_session, idx):
        result = ml_pipeline_session["confirmations"][idx]
        assert result["action"] == "confirmed", (
            f"Confirmation {idx} action should be 'confirmed', "
            f"got {result.get('action')}"
        )

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_confirmation_has_workload_config(
        self, ml_pipeline_session, idx
    ):
        result = ml_pipeline_session["confirmations"][idx]
        assert "workload_config" in result, (
            f"Confirmation {idx} should include workload_config"
        )


class TestConversationStateAfterConfirm:
    """AC-8: conversation state reflects all confirmed workloads."""

    def test_state_has_confirmed_workloads(
        self, http_client, ml_pipeline_session
    ):
        cid = ml_pipeline_session["conversation_id"]
        state = get_conversation_state(http_client, cid)
        confirmed = state.get("confirmed_workloads") or []
        assert len(confirmed) >= 3, (
            f"Expected >= 3 confirmed workloads, got {len(confirmed)}"
        )

    def test_state_confirmed_types_match(
        self, http_client, ml_pipeline_session
    ):
        cid = ml_pipeline_session["conversation_id"]
        state = get_conversation_state(http_client, cid)
        confirmed = state.get("confirmed_workloads") or []
        types = {w.get("workload_type") for w in confirmed}
        assert EXPECTED_TYPES.issubset(types), (
            f"Confirmed types should include {EXPECTED_TYPES}, got {types}"
        )

    def test_no_pending_proposals_remaining(
        self, http_client, ml_pipeline_session
    ):
        """After confirming all, no proposals should be pending."""
        cid = ml_pipeline_session["conversation_id"]
        state = get_conversation_state(http_client, cid)
        pending = state.get("proposed_workloads") or []
        assert len(pending) == 0, (
            f"Expected 0 pending proposals, got {len(pending)}"
        )


class TestConversationContinuity:
    """AC-9: distinct proposal IDs within the conversation."""

    def test_conversation_id_consistent(self, ml_pipeline_session):
        cid = ml_pipeline_session["conversation_id"]
        assert cid and len(cid) > 0

    def test_distinct_proposal_ids(self, ml_pipeline_session):
        pids = [
            p["proposal_id"]
            for p in ml_pipeline_session["proposals"]
        ]
        assert len(set(pids)) == 3, (
            f"Expected 3 distinct proposal_ids, got {pids}"
        )
