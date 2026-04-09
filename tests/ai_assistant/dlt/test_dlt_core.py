"""Tests: AI proposes DLT/SDP workload with Core edition (basic ETL)."""
import pytest


class TestDltCoreEdition:
    """AI proposes DLT with Core edition for basic ETL pipelines."""

    def test_workload_type_is_dlt(self, dlt_core_proposal):
        assert dlt_core_proposal["workload_type"] == "DLT", (
            f"Expected DLT, got {dlt_core_proposal['workload_type']}"
        )

    def test_dlt_edition_is_core(self, dlt_core_proposal):
        edition = (dlt_core_proposal.get("dlt_edition") or "").upper()
        assert "CORE" in edition, (
            f"dlt_edition should contain CORE for basic pipeline, "
            f"got '{dlt_core_proposal.get('dlt_edition')}'"
        )

    def test_workload_name_non_empty(self, dlt_core_proposal):
        name = dlt_core_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_proposal_id_present(self, dlt_core_proposal):
        pid = dlt_core_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present"

    def test_reason_populated(self, dlt_core_proposal):
        reason = dlt_core_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_notes_populated(self, dlt_core_proposal):
        notes = dlt_core_proposal.get("notes", "")
        assert notes and len(notes) >= 1, (
            f"notes should be populated: '{notes}'"
        )

    def test_serverless_explicitly_set(self, dlt_core_proposal):
        se = dlt_core_proposal.get("serverless_enabled")
        assert se is not None, "serverless_enabled should be explicitly set"

    def test_classic_compute_fields(self, dlt_core_proposal):
        """Core classic should have node types and worker count."""
        if dlt_core_proposal.get("serverless_enabled"):
            pytest.skip("AI chose serverless — classic compute fields N/A")
        has_nodes = (
            dlt_core_proposal.get("driver_node_type")
            or dlt_core_proposal.get("worker_node_type")
        )
        assert has_nodes, "Classic DLT should have node types"
        nw = dlt_core_proposal.get("num_workers")
        assert nw is not None and nw >= 1, (
            f"Classic DLT should have num_workers >= 1, got {nw}"
        )

    def test_photon_set_for_classic(self, dlt_core_proposal):
        """If classic compute, photon_enabled should be set."""
        if dlt_core_proposal.get("serverless_enabled"):
            pytest.skip("AI chose serverless — photon check N/A")
        pe = dlt_core_proposal.get("photon_enabled")
        assert pe is not None, "photon_enabled should be set for classic"

    def test_scheduling_fields_present(self, dlt_core_proposal):
        has_runs = dlt_core_proposal.get("runs_per_day") is not None
        has_hours = dlt_core_proposal.get("hours_per_month") is not None
        assert has_runs or has_hours, (
            "DLT Core proposal should have runs_per_day or hours_per_month"
        )
