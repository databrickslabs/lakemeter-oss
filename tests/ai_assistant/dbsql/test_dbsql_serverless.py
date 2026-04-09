"""Tests: AI proposes DBSQL Serverless warehouse with correct fields."""
import pytest

from tests.ai_assistant.dbsql.prompts import VALID_WAREHOUSE_SIZES


class TestDbsqlServerless:
    """AI proposes a DBSQL Serverless workload with correct configuration."""

    def test_workload_type_is_dbsql(self, dbsql_serverless_proposal):
        assert dbsql_serverless_proposal["workload_type"] == "DBSQL", (
            f"Expected DBSQL, got {dbsql_serverless_proposal['workload_type']}"
        )

    def test_warehouse_type_is_serverless(self, dbsql_serverless_proposal):
        wt = (dbsql_serverless_proposal.get("dbsql_warehouse_type") or "").upper()
        assert "SERVERLESS" in wt, (
            f"dbsql_warehouse_type should be SERVERLESS, got "
            f"'{dbsql_serverless_proposal.get('dbsql_warehouse_type')}'"
        )

    def test_warehouse_size_valid(self, dbsql_serverless_proposal):
        size = dbsql_serverless_proposal.get("dbsql_warehouse_size", "")
        assert size in VALID_WAREHOUSE_SIZES, (
            f"dbsql_warehouse_size '{size}' not in valid sizes: {VALID_WAREHOUSE_SIZES}"
        )

    def test_warehouse_size_medium(self, dbsql_serverless_proposal):
        size = (dbsql_serverless_proposal.get("dbsql_warehouse_size") or "").lower()
        assert "medium" in size, (
            f"Asked for Medium size, got '{dbsql_serverless_proposal.get('dbsql_warehouse_size')}'"
        )

    def test_num_clusters_at_least_one(self, dbsql_serverless_proposal):
        nc = dbsql_serverless_proposal.get("dbsql_num_clusters")
        assert nc is not None and nc >= 1, (
            f"dbsql_num_clusters should be >= 1, got {nc}"
        )

    def test_workload_name_non_empty(self, dbsql_serverless_proposal):
        name = dbsql_serverless_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_reason_populated(self, dbsql_serverless_proposal):
        reason = dbsql_serverless_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_notes_populated(self, dbsql_serverless_proposal):
        notes = dbsql_serverless_proposal.get("notes", "")
        assert notes and len(notes) >= 1, (
            f"notes should be populated: '{notes}'"
        )

    def test_proposal_id_present(self, dbsql_serverless_proposal):
        pid = dbsql_serverless_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present for confirm/reject flow"
