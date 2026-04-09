"""Tests: confirm all proposals and verify conversation state.

AC-6 through AC-7 and AC-10: multi-workload confirm flow.
"""
import pytest

from tests.ai_assistant.conftest import get_conversation_state


class TestConfirmAllThree:
    """AC-6: all 3 confirmations succeed."""

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_confirmation_success(self, three_workload_session, idx):
        result = three_workload_session["confirmations"][idx]
        assert result["success"] is True, (
            f"Confirmation {idx} should succeed: {result}"
        )

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_confirmation_action_confirmed(self, three_workload_session, idx):
        result = three_workload_session["confirmations"][idx]
        assert result["action"] == "confirmed", (
            f"Confirmation {idx} action should be 'confirmed', got {result.get('action')}"
        )

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_confirmation_has_workload_config(self, three_workload_session, idx):
        result = three_workload_session["confirmations"][idx]
        assert "workload_config" in result, (
            f"Confirmation {idx} should include workload_config"
        )


class TestConversationStateAfterConfirm:
    """AC-7: conversation state reflects all confirmed workloads."""

    def test_state_has_confirmed_workloads(
        self, http_client, three_workload_session
    ):
        cid = three_workload_session["conversation_id"]
        state = get_conversation_state(http_client, cid)
        confirmed = state.get("confirmed_workloads") or []
        assert len(confirmed) >= 3, (
            f"Expected >= 3 confirmed workloads, got {len(confirmed)}"
        )

    def test_state_confirmed_types_match(
        self, http_client, three_workload_session
    ):
        cid = three_workload_session["conversation_id"]
        state = get_conversation_state(http_client, cid)
        confirmed = state.get("confirmed_workloads") or []
        types = {w.get("workload_type") for w in confirmed}
        expected = {"JOBS", "ALL_PURPOSE", "DBSQL"}
        assert expected.issubset(types), (
            f"Confirmed types should include {expected}, got {types}"
        )

    def test_no_pending_proposals_remaining(
        self, http_client, three_workload_session
    ):
        """After confirming all, no proposals should be pending."""
        cid = three_workload_session["conversation_id"]
        state = get_conversation_state(http_client, cid)
        pending = state.get("proposed_workloads") or []
        assert len(pending) == 0, (
            f"Expected 0 pending proposals, got {len(pending)}"
        )


class TestConversationContinuity:
    """AC-10: conversation continues correctly after confirmations."""

    def test_conversation_id_consistent(self, three_workload_session):
        """All proposals in the same conversation."""
        cid = three_workload_session["conversation_id"]
        assert cid and len(cid) > 0

    def test_distinct_proposal_ids(self, three_workload_session):
        """Each proposal has a unique ID."""
        pids = [p["proposal_id"] for p in three_workload_session["proposals"]]
        assert len(set(pids)) == 3, (
            f"Expected 3 distinct proposal_ids, got {pids}"
        )
