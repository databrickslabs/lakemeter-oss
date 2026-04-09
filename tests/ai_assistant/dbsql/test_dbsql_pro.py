"""Tests: AI proposes DBSQL Pro warehouse with correct fields."""
import pytest

from tests.ai_assistant.dbsql.prompts import VALID_WAREHOUSE_SIZES


class TestDbsqlPro:
    """AI proposes a DBSQL Pro workload with Large size and 2 clusters."""

    def test_workload_type_is_dbsql(self, dbsql_pro_proposal):
        assert dbsql_pro_proposal["workload_type"] == "DBSQL", (
            f"Expected DBSQL, got {dbsql_pro_proposal['workload_type']}"
        )

    def test_warehouse_type_is_pro(self, dbsql_pro_proposal):
        wt = (dbsql_pro_proposal.get("dbsql_warehouse_type") or "").upper()
        assert "PRO" in wt, (
            f"dbsql_warehouse_type should be PRO, got "
            f"'{dbsql_pro_proposal.get('dbsql_warehouse_type')}'"
        )

    def test_warehouse_size_valid(self, dbsql_pro_proposal):
        size = dbsql_pro_proposal.get("dbsql_warehouse_size", "")
        assert size in VALID_WAREHOUSE_SIZES, (
            f"dbsql_warehouse_size '{size}' not in valid sizes"
        )

    def test_warehouse_size_large_or_bigger(self, dbsql_pro_proposal):
        size = dbsql_pro_proposal.get("dbsql_warehouse_size", "")
        large_or_bigger = ["Large", "X-Large", "2X-Large", "3X-Large", "4X-Large"]
        assert size in large_or_bigger, (
            f"Asked for Large, got '{size}'"
        )

    def test_num_clusters_populated(self, dbsql_pro_proposal):
        nc = dbsql_pro_proposal.get("dbsql_num_clusters")
        assert nc is not None and nc >= 1, (
            f"dbsql_num_clusters should be >= 1, got {nc}"
        )

    def test_workload_name_non_empty(self, dbsql_pro_proposal):
        name = dbsql_pro_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_reason_populated(self, dbsql_pro_proposal):
        reason = dbsql_pro_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_proposal_id_present(self, dbsql_pro_proposal):
        pid = dbsql_pro_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present"
