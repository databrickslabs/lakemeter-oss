"""Tests: 3-workload conversation — JOBS + ALL_PURPOSE + DBSQL.

AC-1 through AC-5: verify types, fields, and proposal_ids across turns.
"""
import pytest


class TestThreeWorkloadTypes:
    """Verify the 3-workload conversation covers JOBS, ALL_PURPOSE, DBSQL."""

    def test_three_proposals_collected(self, three_workload_session):
        """AC-1/AC-2: conversation produced exactly 3 proposals."""
        assert len(three_workload_session["proposals"]) == 3

    def test_first_proposal_is_jobs(self, three_workload_session):
        """AC-3: first workload should be JOBS."""
        wt = three_workload_session["proposals"][0]["workload_type"]
        assert wt == "JOBS", f"Expected JOBS, got {wt}"

    def test_second_proposal_is_all_purpose(self, three_workload_session):
        """AC-3: second workload should be ALL_PURPOSE."""
        wt = three_workload_session["proposals"][1]["workload_type"]
        assert wt == "ALL_PURPOSE", f"Expected ALL_PURPOSE, got {wt}"

    def test_third_proposal_is_dbsql(self, three_workload_session):
        """AC-3: third workload should be DBSQL."""
        wt = three_workload_session["proposals"][2]["workload_type"]
        assert wt == "DBSQL", f"Expected DBSQL, got {wt}"

    def test_all_three_types_covered(self, three_workload_session):
        """AC-2: the set of types covers JOBS, ALL_PURPOSE, DBSQL."""
        types = {p["workload_type"] for p in three_workload_session["proposals"]}
        expected = {"JOBS", "ALL_PURPOSE", "DBSQL"}
        assert expected.issubset(types), (
            f"Expected types {expected}, got {types}"
        )


class TestThreeWorkloadFields:
    """AC-4/AC-5: each proposal has required fields."""

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_workload_name_populated(self, three_workload_session, idx):
        name = three_workload_session["proposals"][idx].get("workload_name", "")
        assert name and len(name) >= 3, (
            f"Proposal {idx}: workload_name too short: '{name}'"
        )

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_reason_populated(self, three_workload_session, idx):
        reason = three_workload_session["proposals"][idx].get("reason", "")
        assert reason and len(reason) >= 10, (
            f"Proposal {idx}: reason too short: '{reason}'"
        )

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_notes_populated(self, three_workload_session, idx):
        notes = three_workload_session["proposals"][idx].get("notes", "")
        assert notes and len(notes) >= 1, (
            f"Proposal {idx}: notes should be populated: '{notes}'"
        )

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_proposal_id_present(self, three_workload_session, idx):
        pid = three_workload_session["proposals"][idx].get("proposal_id", "")
        assert pid, f"Proposal {idx}: proposal_id must be present"


class TestThreeWorkloadJobsFields:
    """JOBS-specific field assertions for the first proposal."""

    def test_runs_per_day_positive(self, three_workload_session):
        p = three_workload_session["proposals"][0]
        rpd = p.get("runs_per_day", 0)
        assert rpd > 0, f"JOBS runs_per_day should be > 0, got {rpd}"

    def test_avg_runtime_minutes_positive(self, three_workload_session):
        p = three_workload_session["proposals"][0]
        arm = p.get("avg_runtime_minutes", 0)
        assert arm > 0, f"JOBS avg_runtime_minutes should be > 0, got {arm}"

    def test_days_per_month_positive(self, three_workload_session):
        p = three_workload_session["proposals"][0]
        dpm = p.get("days_per_month", 0)
        assert dpm > 0, f"JOBS days_per_month should be > 0, got {dpm}"


class TestThreeWorkloadAllPurposeFields:
    """ALL_PURPOSE-specific field assertions for the second proposal."""

    def test_hours_per_month_positive(self, three_workload_session):
        p = three_workload_session["proposals"][1]
        hpm = p.get("hours_per_month", 0)
        assert hpm > 0, f"ALL_PURPOSE hours_per_month should be > 0, got {hpm}"

    def test_num_workers_positive(self, three_workload_session):
        p = three_workload_session["proposals"][1]
        nw = p.get("num_workers", 0)
        assert nw > 0, f"ALL_PURPOSE num_workers should be > 0, got {nw}"


class TestThreeWorkloadDbsqlFields:
    """DBSQL-specific field assertions for the third proposal."""

    def test_warehouse_type_populated(self, three_workload_session):
        p = three_workload_session["proposals"][2]
        wt = p.get("dbsql_warehouse_type", "")
        assert wt, f"DBSQL dbsql_warehouse_type should be populated, got '{wt}'"

    def test_warehouse_size_populated(self, three_workload_session):
        p = three_workload_session["proposals"][2]
        ws = p.get("dbsql_warehouse_size", "")
        assert ws, f"DBSQL dbsql_warehouse_size should be populated, got '{ws}'"

    def test_num_clusters_positive(self, three_workload_session):
        p = three_workload_session["proposals"][2]
        nc = p.get("dbsql_num_clusters", 0)
        assert nc >= 1, f"DBSQL dbsql_num_clusters should be >= 1, got {nc}"
