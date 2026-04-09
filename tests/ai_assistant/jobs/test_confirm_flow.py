"""Tests: confirm / reject proposed workloads and verify conversation state."""
import uuid
import pytest

from tests.ai_assistant.conftest import (
    send_chat_until_proposal,
    confirm_proposal,
    reject_proposal,
    get_conversation_state,
)

JOBS_PROMPT = (
    "I need a Lakeflow Jobs workload for a daily ETL pipeline. "
    "Medium complexity (MERGE/upsert, 3-5 joins) on a 1TB base table. "
    "Running 5 times a day for 20 minutes each, 4 workers, "
    "classic compute with Photon on AWS us-east-1 Premium tier."
)
JOBS_FOLLOWUP = (
    "Use Lakeflow Jobs (not SDP). m6i.xlarge driver, i3.xlarge workers, "
    "spot pricing for workers, 22 days/month. "
    "Please propose the workload configuration now."
)
JOBS_FINAL = (
    "Yes, that looks right. Please go ahead and propose it."
)


class TestConfirmWorkflow:
    """Full confirm-workload lifecycle."""

    @pytest.fixture(autouse=True)
    def _setup(self, http_client, test_estimate):
        self.client = http_client
        self.estimate = test_estimate

    def test_confirm_proposal_success(self):
        cid = str(uuid.uuid4())
        proposal, resp = send_chat_until_proposal(
            self.client,
            [JOBS_PROMPT, JOBS_FOLLOWUP, JOBS_FINAL],
            self.estimate,
            conversation_id=cid,
        )

        pid = proposal["proposal_id"]
        result = confirm_proposal(self.client, cid, pid)

        assert result["success"] is True
        assert result["action"] == "confirmed"
        assert "workload_config" in result

    def test_confirmed_proposal_removed_from_pending(self):
        """After confirming, the proposal is popped from proposed_workloads."""
        cid = str(uuid.uuid4())
        proposal, _ = send_chat_until_proposal(
            self.client,
            [JOBS_PROMPT, JOBS_FOLLOWUP, JOBS_FINAL],
            self.estimate,
            conversation_id=cid,
        )

        pid = proposal["proposal_id"]

        # Before confirm: proposal should be pending
        state_before = get_conversation_state(self.client, cid)
        pending_before = [
            w for w in (state_before.get("proposed_workloads") or [])
            if w.get("proposal_id") == pid
        ]
        assert len(pending_before) >= 1, (
            "Proposal should be in proposed_workloads before confirm"
        )

        confirm_proposal(self.client, cid, pid)

        # After confirm: proposal is removed from proposed_workloads
        state_after = get_conversation_state(self.client, cid)
        remaining = [
            w for w in (state_after.get("proposed_workloads") or [])
            if w.get("proposal_id") == pid
        ]
        assert len(remaining) == 0, (
            f"Confirmed proposal should be removed from pending list. "
            f"Still found: {remaining}"
        )

    def test_reject_proposal(self):
        cid = str(uuid.uuid4())
        proposal, _ = send_chat_until_proposal(
            self.client,
            [JOBS_PROMPT, JOBS_FOLLOWUP, JOBS_FINAL],
            self.estimate,
            conversation_id=cid,
        )

        pid = proposal["proposal_id"]
        result = reject_proposal(self.client, cid, pid)

        assert result["success"] is True
        assert result["action"] == "rejected"
