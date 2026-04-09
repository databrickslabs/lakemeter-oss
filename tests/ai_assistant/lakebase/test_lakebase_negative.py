"""Tests: Non-Lakebase requests should NOT produce LAKEBASE type."""
import pytest


class TestLakebaseNegativeEtl:
    """ETL pipeline request must NOT be classified as LAKEBASE (AC-18, AC-19)."""

    def test_not_lakebase(self, non_lb_etl_proposal):
        wt = non_lb_etl_proposal["workload_type"]
        assert wt != "LAKEBASE", (
            f"ETL pipeline request should NOT be LAKEBASE, got {wt}"
        )

    def test_is_jobs(self, non_lb_etl_proposal):
        wt = non_lb_etl_proposal["workload_type"]
        assert wt == "JOBS", (
            f"ETL pipeline should be JOBS, got {wt}"
        )

    def test_etl_has_runs_per_day(self, non_lb_etl_proposal):
        """JOBS workload should have scheduling fields."""
        rpd = non_lb_etl_proposal.get("runs_per_day")
        assert rpd is not None and rpd > 0, (
            f"JOBS should have runs_per_day > 0, got {rpd}"
        )


class TestLakebaseNegativeSql:
    """SQL analytics request must NOT be classified as LAKEBASE (AC-20, AC-21)."""

    def test_not_lakebase(self, non_lb_sql_proposal):
        wt = non_lb_sql_proposal["workload_type"]
        assert wt != "LAKEBASE", (
            f"SQL analytics request should NOT be LAKEBASE, got {wt}"
        )

    def test_is_dbsql(self, non_lb_sql_proposal):
        wt = non_lb_sql_proposal["workload_type"]
        assert wt == "DBSQL", (
            f"SQL analytics should be DBSQL, got {wt}"
        )

    def test_sql_has_warehouse_type(self, non_lb_sql_proposal):
        """DBSQL workload should have warehouse configuration."""
        wh_type = non_lb_sql_proposal.get("dbsql_warehouse_type", "")
        assert wh_type, (
            f"DBSQL should have dbsql_warehouse_type, got '{wh_type}'"
        )
