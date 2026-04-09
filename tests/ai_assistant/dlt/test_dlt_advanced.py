"""Tests: AI proposes DLT/SDP workload with Advanced edition (full monitoring)."""
import pytest


class TestDltAdvancedEdition:
    """AI proposes DLT with Advanced edition for full monitoring."""

    def test_workload_type_is_dlt(self, dlt_advanced_proposal):
        assert dlt_advanced_proposal["workload_type"] == "DLT", (
            f"Expected DLT, got {dlt_advanced_proposal['workload_type']}"
        )

    def test_dlt_edition_is_advanced(self, dlt_advanced_proposal):
        edition = (dlt_advanced_proposal.get("dlt_edition") or "").upper()
        assert "ADVANCED" in edition, (
            f"dlt_edition should contain ADVANCED, "
            f"got '{dlt_advanced_proposal.get('dlt_edition')}'"
        )

    def test_workload_name_non_empty(self, dlt_advanced_proposal):
        name = dlt_advanced_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_proposal_id_present(self, dlt_advanced_proposal):
        pid = dlt_advanced_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present"

    def test_reason_populated(self, dlt_advanced_proposal):
        reason = dlt_advanced_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_notes_populated(self, dlt_advanced_proposal):
        notes = dlt_advanced_proposal.get("notes", "")
        assert notes and len(notes) >= 1, (
            f"notes should be populated: '{notes}'"
        )

    def test_serverless_explicitly_set(self, dlt_advanced_proposal):
        se = dlt_advanced_proposal.get("serverless_enabled")
        assert se is not None, "serverless_enabled should be explicitly set"

    def test_scheduling_fields_present(self, dlt_advanced_proposal):
        has_runs = dlt_advanced_proposal.get("runs_per_day") is not None
        has_hours = dlt_advanced_proposal.get("hours_per_month") is not None
        assert has_runs or has_hours, (
            "DLT Advanced proposal should have scheduling fields"
        )
