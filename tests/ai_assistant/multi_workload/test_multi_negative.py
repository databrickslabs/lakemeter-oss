"""Tests: negative discrimination — single-workload should not produce extras.

AC-8: a prompt for "data science notebooks" should produce ALL_PURPOSE,
not JOBS or DBSQL.
"""
import pytest


class TestNegativeDataScienceOnly:
    """Single-workload prompt should produce ALL_PURPOSE only."""

    def test_workload_type_is_all_purpose(self, negative_ds_only_proposal):
        wt = negative_ds_only_proposal["workload_type"]
        assert wt == "ALL_PURPOSE", (
            f"Data science prompt should produce ALL_PURPOSE, got {wt}"
        )

    def test_not_jobs(self, negative_ds_only_proposal):
        wt = negative_ds_only_proposal["workload_type"]
        assert wt != "JOBS", "Data science prompt should NOT produce JOBS"

    def test_not_dbsql(self, negative_ds_only_proposal):
        wt = negative_ds_only_proposal["workload_type"]
        assert wt != "DBSQL", "Data science prompt should NOT produce DBSQL"

    def test_workload_name_populated(self, negative_ds_only_proposal):
        name = negative_ds_only_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short: '{name}'"
        )

    def test_reason_populated(self, negative_ds_only_proposal):
        reason = negative_ds_only_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short: '{reason}'"
        )

    def test_hours_per_month_positive(self, negative_ds_only_proposal):
        hpm = negative_ds_only_proposal.get("hours_per_month", 0)
        assert hpm > 0, f"ALL_PURPOSE hours_per_month should be > 0, got {hpm}"

    def test_num_workers_positive(self, negative_ds_only_proposal):
        nw = negative_ds_only_proposal.get("num_workers", 0)
        assert nw > 0, f"ALL_PURPOSE num_workers should be > 0, got {nw}"

    def test_proposal_id_present(self, negative_ds_only_proposal):
        pid = negative_ds_only_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present"
