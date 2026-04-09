"""Tests: AI proposes DBSQL Classic warehouse when explicitly requested."""
import pytest

from tests.ai_assistant.dbsql.prompts import VALID_WAREHOUSE_SIZES


class TestDbsqlClassic:
    """AI proposes a DBSQL Classic workload when user explicitly requests legacy."""

    def test_workload_type_is_dbsql(self, dbsql_classic_proposal):
        assert dbsql_classic_proposal["workload_type"] == "DBSQL", (
            f"Expected DBSQL, got {dbsql_classic_proposal['workload_type']}"
        )

    def test_warehouse_type_is_classic(self, dbsql_classic_proposal):
        wt = (dbsql_classic_proposal.get("dbsql_warehouse_type") or "").upper()
        assert "CLASSIC" in wt, (
            f"dbsql_warehouse_type should be CLASSIC, got "
            f"'{dbsql_classic_proposal.get('dbsql_warehouse_type')}'"
        )

    def test_warehouse_size_valid(self, dbsql_classic_proposal):
        size = dbsql_classic_proposal.get("dbsql_warehouse_size", "")
        assert size in VALID_WAREHOUSE_SIZES, (
            f"dbsql_warehouse_size '{size}' not in valid sizes"
        )

    def test_num_clusters_at_least_one(self, dbsql_classic_proposal):
        nc = dbsql_classic_proposal.get("dbsql_num_clusters")
        assert nc is not None and nc >= 1, (
            f"dbsql_num_clusters should be >= 1, got {nc}"
        )

    def test_workload_name_non_empty(self, dbsql_classic_proposal):
        name = dbsql_classic_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_reason_populated(self, dbsql_classic_proposal):
        reason = dbsql_classic_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_proposal_id_present(self, dbsql_classic_proposal):
        pid = dbsql_classic_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present"
