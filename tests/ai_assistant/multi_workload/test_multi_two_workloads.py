"""Tests: 2-workload conversation — JOBS + DBSQL.

AC-9: ETL pipeline + SQL analytics produces JOBS + DBSQL (no ALL_PURPOSE).
"""
import pytest


class TestTwoWorkloadTypes:
    """Verify the 2-workload conversation covers JOBS and DBSQL."""

    def test_two_proposals_collected(self, two_workload_session):
        assert len(two_workload_session["proposals"]) == 2

    def test_first_proposal_is_jobs(self, two_workload_session):
        wt = two_workload_session["proposals"][0]["workload_type"]
        assert wt == "JOBS", f"Expected JOBS, got {wt}"

    def test_second_proposal_is_dbsql(self, two_workload_session):
        wt = two_workload_session["proposals"][1]["workload_type"]
        assert wt == "DBSQL", f"Expected DBSQL, got {wt}"

    def test_types_cover_jobs_and_dbsql(self, two_workload_session):
        types = {p["workload_type"] for p in two_workload_session["proposals"]}
        expected = {"JOBS", "DBSQL"}
        assert expected.issubset(types), (
            f"Expected types {expected}, got {types}"
        )


class TestTwoWorkloadFields:
    """Required fields on both proposals."""

    @pytest.mark.parametrize("idx", [0, 1])
    def test_workload_name_populated(self, two_workload_session, idx):
        name = two_workload_session["proposals"][idx].get("workload_name", "")
        assert name and len(name) >= 3, (
            f"Proposal {idx}: workload_name too short: '{name}'"
        )

    @pytest.mark.parametrize("idx", [0, 1])
    def test_reason_populated(self, two_workload_session, idx):
        reason = two_workload_session["proposals"][idx].get("reason", "")
        assert reason and len(reason) >= 10, (
            f"Proposal {idx}: reason too short: '{reason}'"
        )

    @pytest.mark.parametrize("idx", [0, 1])
    def test_proposal_id_present(self, two_workload_session, idx):
        pid = two_workload_session["proposals"][idx].get("proposal_id", "")
        assert pid, f"Proposal {idx}: proposal_id must be present"


class TestTwoWorkloadConfirmations:
    """Both confirmations succeed."""

    @pytest.mark.parametrize("idx", [0, 1])
    def test_confirmation_success(self, two_workload_session, idx):
        result = two_workload_session["confirmations"][idx]
        assert result["success"] is True

    @pytest.mark.parametrize("idx", [0, 1])
    def test_confirmation_action(self, two_workload_session, idx):
        result = two_workload_session["confirmations"][idx]
        assert result["action"] == "confirmed"

    def test_distinct_proposal_ids(self, two_workload_session):
        pids = [p["proposal_id"] for p in two_workload_session["proposals"]]
        assert len(set(pids)) == 2, f"Expected 2 distinct IDs, got {pids}"
