"""Tests: AI assistant proposes ALL_PURPOSE workloads from natural language.

Uses module-scoped fixtures to minimise expensive AI calls.
Interactive cluster proposal fixture is shared across TestAllPurposeBasic.
Edge case test uses a separate conversation.
"""
import uuid
import pytest

from tests.ai_assistant.conftest import send_chat_until_proposal

# -- Prompt sequences ----------------------------------------------------------

ALLPURPOSE_PRIMARY = (
    "I need an interactive all-purpose cluster for data science work. "
    "8 workers, running about 8 hours a day on weekdays on AWS us-east-1."
)
ALLPURPOSE_FOLLOWUP = (
    "Use classic compute with m6i.xlarge for the driver and i3.xlarge "
    "for workers. Standard pricing tier (not Photon). "
    "About 22 working days per month, so ~176 hours/month. "
    "Please propose the all-purpose compute workload now."
)
ALLPURPOSE_FINAL = (
    "Yes, please go ahead and propose the interactive All-Purpose Compute "
    "workload with those specifications."
)

# Edge case: ambiguous prompt that should still pick ALL_PURPOSE over JOBS
INTERACTIVE_AMBIGUOUS_PRIMARY = (
    "I need an interactive notebook environment for ad-hoc data exploration "
    "and development. My team uses it for about 6 hours a day with 4 workers."
)
INTERACTIVE_AMBIGUOUS_FOLLOWUP = (
    "This is for interactive use — not scheduled batch jobs. "
    "Standard All-Purpose Compute cluster, 4 workers, ~132 hours/month. "
    "Use m5.xlarge instances, standard pricing tier, no Photon. "
    "Please propose the workload."
)
INTERACTIVE_AMBIGUOUS_FINAL = (
    "Please go ahead and propose the All-Purpose Compute workload with "
    "4 workers, m5.xlarge instances, 132 hours per month, standard tier, "
    "no Photon. This is interactive compute, not a batch job."
)


# -- Module-scoped fixtures (one AI call per variant) --------------------------


@pytest.fixture(scope="module")
def allpurpose_proposal(http_client, test_estimate):
    """Single AI call for interactive ALL_PURPOSE — shared by all basic tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [ALLPURPOSE_PRIMARY, ALLPURPOSE_FOLLOWUP, ALLPURPOSE_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def interactive_edge_proposal(http_client, test_estimate):
    """AI call with ambiguous 'interactive' prompt — should still be ALL_PURPOSE."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [INTERACTIVE_AMBIGUOUS_PRIMARY, INTERACTIVE_AMBIGUOUS_FOLLOWUP, INTERACTIVE_AMBIGUOUS_FINAL],
        test_estimate,
    )
    return proposal


# -- ALL_PURPOSE basic tests ---------------------------------------------------


class TestAllPurposeBasic:
    """AI proposes an ALL_PURPOSE workload with correct fields."""

    def test_workload_type_is_allpurpose(self, allpurpose_proposal):
        assert allpurpose_proposal["workload_type"] == "ALL_PURPOSE", (
            f"Expected ALL_PURPOSE, got {allpurpose_proposal['workload_type']}"
        )

    def test_workload_name_non_empty(self, allpurpose_proposal):
        name = allpurpose_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_num_workers_present(self, allpurpose_proposal):
        nw = allpurpose_proposal.get("num_workers")
        assert nw is not None, "num_workers missing"
        assert nw >= 1, f"num_workers should be >= 1, got {nw}"

    def test_hours_per_month_reasonable(self, allpurpose_proposal):
        hpm = allpurpose_proposal.get("hours_per_month")
        assert hpm is not None, "hours_per_month missing"
        assert 50 <= hpm <= 750, (
            f"hours_per_month={hpm} outside reasonable range for ~8hr/day"
        )

    def test_driver_node_type_populated(self, allpurpose_proposal):
        dnt = allpurpose_proposal.get("driver_node_type", "")
        assert dnt, "driver_node_type should be populated"

    def test_worker_node_type_populated(self, allpurpose_proposal):
        wnt = allpurpose_proposal.get("worker_node_type", "")
        assert wnt, "worker_node_type should be populated"

    def test_pricing_tier_present(self, allpurpose_proposal):
        has_tier = (
            allpurpose_proposal.get("driver_pricing_tier")
            or allpurpose_proposal.get("worker_pricing_tier")
        )
        assert has_tier, "At least one pricing tier field should be present"

    def test_reason_populated(self, allpurpose_proposal):
        reason = allpurpose_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_notes_populated(self, allpurpose_proposal):
        notes = allpurpose_proposal.get("notes", "")
        assert notes and len(notes) >= 1, (
            f"notes should be populated: '{notes}'"
        )

    def test_proposal_id_present(self, allpurpose_proposal):
        pid = allpurpose_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present for confirm/reject flow"

    def test_serverless_explicitly_set(self, allpurpose_proposal):
        se = allpurpose_proposal.get("serverless_enabled")
        assert se is not None, "serverless_enabled should be explicitly set"


# -- Edge case: interactive vs batch distinction -------------------------------


class TestAllPurposeEdgeCase:
    """AI correctly picks ALL_PURPOSE (not JOBS) for interactive use cases."""

    def test_interactive_maps_to_allpurpose(self, interactive_edge_proposal):
        wt = interactive_edge_proposal["workload_type"]
        assert wt == "ALL_PURPOSE", (
            f"Interactive notebook use should map to ALL_PURPOSE, got {wt}"
        )

    def test_has_hours_per_month(self, interactive_edge_proposal):
        hpm = interactive_edge_proposal.get("hours_per_month")
        assert hpm is not None, (
            "ALL_PURPOSE should use hours_per_month (not runs_per_day)"
        )
        assert hpm > 0
