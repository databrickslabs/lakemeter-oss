"""Tests: AI assistant proposes JOBS workloads from natural language.

Uses module-scoped fixtures to minimise expensive AI calls.
Classic proposal fixture is shared across TestJobsProposalBasic.
Serverless proposal gets its own fixture.
"""
import uuid
import pytest

from tests.ai_assistant.conftest import send_chat_until_proposal

# ── Prompt sequences ───────────────────────────────────────────────

JOBS_PRIMARY = (
    "I need a daily ETL job processing 1TB of data with 4 workers, "
    "running 10 times a day for 30 minutes each on AWS us-east-1."
)
JOBS_FOLLOWUP = (
    "Use classic compute with Photon enabled, m6i.xlarge for driver "
    "and i3.xlarge for workers. Run every weekday (22 days/month). "
    "Please propose the workload now."
)

JOBS_SERVERLESS_PRIMARY = (
    "I need a serverless Lakeflow Jobs workload for nightly ETL data processing. "
    "It's a medium complexity job (MERGE/upsert, 3-5 joins) on a 1TB base table. "
    "Running once a day for about 45 minutes, on AWS us-east-1 Premium tier."
)
JOBS_SERVERLESS_FOLLOWUP = (
    "Use Lakeflow Jobs (not SDP). Serverless compute in standard mode "
    "with Photon enabled. 1 run per day, 45 minutes each, 30 days/month. "
    "Please propose the workload configuration now."
)
JOBS_SERVERLESS_FINAL = (
    "That looks good. Please go ahead and propose the serverless Lakeflow Jobs "
    "workload with those settings."
)


# ── Module-scoped fixtures (one AI call per variant) ──────────────


@pytest.fixture(scope="module")
def classic_proposal(http_client, test_estimate):
    """Single AI call for classic JOBS — shared by all basic tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [JOBS_PRIMARY, JOBS_FOLLOWUP],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def serverless_proposal(http_client, test_estimate):
    """Single AI call for serverless JOBS."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [JOBS_SERVERLESS_PRIMARY, JOBS_SERVERLESS_FOLLOWUP, JOBS_SERVERLESS_FINAL],
        test_estimate,
    )
    return proposal


# ── Classic JOBS tests ────────────────────────────────────────────


class TestJobsProposalBasic:
    """AI proposes a classic JOBS workload with correct fields."""

    def test_workload_type_is_jobs(self, classic_proposal):
        assert classic_proposal["workload_type"] == "JOBS"

    def test_workload_name_non_empty(self, classic_proposal):
        name = classic_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_runs_per_day(self, classic_proposal):
        rpd = classic_proposal.get("runs_per_day")
        assert rpd is not None, "runs_per_day missing"
        assert rpd > 0

    def test_avg_runtime_minutes(self, classic_proposal):
        arm = classic_proposal.get("avg_runtime_minutes")
        assert arm is not None, "avg_runtime_minutes missing"
        assert arm > 0

    def test_days_per_month(self, classic_proposal):
        dpm = classic_proposal.get("days_per_month")
        assert dpm is not None, "days_per_month missing"
        assert dpm > 0

    def test_num_workers(self, classic_proposal):
        nw = classic_proposal.get("num_workers")
        assert nw is not None, "num_workers missing"
        assert nw >= 1

    def test_reason_populated(self, classic_proposal):
        reason = classic_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_notes_populated(self, classic_proposal):
        notes = classic_proposal.get("notes", "")
        assert notes and len(notes) >= 1, (
            f"notes should be populated: '{notes}'"
        )

    def test_proposal_id_present(self, classic_proposal):
        pid = classic_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present for confirm/reject flow"

    def test_serverless_explicitly_set(self, classic_proposal):
        se = classic_proposal.get("serverless_enabled")
        assert se is not None, "serverless_enabled should be set"

    def test_photon_set_for_classic(self, classic_proposal):
        """If classic compute, photon_enabled should be set."""
        if not classic_proposal.get("serverless_enabled"):
            pe = classic_proposal.get("photon_enabled")
            assert pe is not None, "photon_enabled should be set"

    def test_node_types_for_classic(self, classic_proposal):
        """If classic compute, node types should be populated."""
        if not classic_proposal.get("serverless_enabled"):
            has_nodes = (
                classic_proposal.get("driver_node_type")
                or classic_proposal.get("worker_node_type")
            )
            assert has_nodes, "Classic JOBS should have node types"


# ── Serverless JOBS tests ─────────────────────────────────────────


class TestJobsServerlessProposal:
    """AI proposes a serverless JOBS workload."""

    def test_workload_type_is_jobs(self, serverless_proposal):
        assert serverless_proposal["workload_type"] == "JOBS"

    def test_serverless_enabled(self, serverless_proposal):
        assert serverless_proposal.get("serverless_enabled") is True, (
            "serverless_enabled should be True for serverless request"
        )

    def test_has_scheduling_fields(self, serverless_proposal):
        assert serverless_proposal.get("runs_per_day") is not None
        assert serverless_proposal["runs_per_day"] >= 1
        assert serverless_proposal.get("avg_runtime_minutes") is not None
        assert serverless_proposal["avg_runtime_minutes"] > 0
