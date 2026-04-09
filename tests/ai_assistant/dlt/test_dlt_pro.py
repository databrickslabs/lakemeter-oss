"""Tests: AI proposes DLT/SDP workload with Pro edition (serverless CDC)."""
import pytest


class TestDltProposalBasic:
    """AI proposes a DLT/SDP workload with Pro edition and correct fields."""

    def test_workload_type_is_dlt(self, dlt_pro_proposal):
        assert dlt_pro_proposal["workload_type"] == "DLT", (
            f"Expected DLT, got {dlt_pro_proposal['workload_type']}"
        )

    def test_workload_name_non_empty(self, dlt_pro_proposal):
        name = dlt_pro_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_dlt_edition_is_pro(self, dlt_pro_proposal):
        edition = (dlt_pro_proposal.get("dlt_edition") or "").upper()
        assert "PRO" in edition, (
            f"dlt_edition should contain PRO, got '{dlt_pro_proposal.get('dlt_edition')}'"
        )

    def test_serverless_enabled(self, dlt_pro_proposal):
        assert dlt_pro_proposal.get("serverless_enabled") is True, (
            "serverless_enabled should be True for serverless DLT request"
        )

    def test_reason_populated(self, dlt_pro_proposal):
        reason = dlt_pro_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_notes_populated(self, dlt_pro_proposal):
        notes = dlt_pro_proposal.get("notes", "")
        assert notes and len(notes) >= 1, (
            f"notes should be populated: '{notes}'"
        )

    def test_proposal_id_present(self, dlt_pro_proposal):
        pid = dlt_pro_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present for confirm/reject flow"

    def test_scheduling_fields_present(self, dlt_pro_proposal):
        has_runs = dlt_pro_proposal.get("runs_per_day") is not None
        has_hours = dlt_pro_proposal.get("hours_per_month") is not None
        assert has_runs or has_hours, (
            "DLT proposal should have runs_per_day or hours_per_month"
        )

    def test_serverless_explicitly_set(self, dlt_pro_proposal):
        se = dlt_pro_proposal.get("serverless_enabled")
        assert se is not None, "serverless_enabled should be explicitly set"
