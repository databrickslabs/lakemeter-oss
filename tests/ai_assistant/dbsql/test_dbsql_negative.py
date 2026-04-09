"""Tests: Non-DBSQL requests should NOT produce DBSQL workload type."""
import pytest


class TestDbsqlNegativeInteractive:
    """Interactive compute request must NOT be classified as DBSQL (AC-12)."""

    def test_not_dbsql_type(self, non_dbsql_proposal):
        wt = non_dbsql_proposal["workload_type"]
        assert wt != "DBSQL", (
            f"Interactive compute request should NOT be DBSQL, got {wt}"
        )

    def test_is_allpurpose_or_jobs(self, non_dbsql_proposal):
        wt = non_dbsql_proposal["workload_type"]
        assert wt in ("ALL_PURPOSE", "JOBS"), (
            f"Interactive request should be ALL_PURPOSE or JOBS, got {wt}"
        )


class TestDbsqlNegativeEtl:
    """Batch ETL request must NOT be classified as DBSQL (AC-13)."""

    def test_not_dbsql_type(self, non_dbsql_etl_proposal):
        wt = non_dbsql_etl_proposal["workload_type"]
        assert wt != "DBSQL", (
            f"Batch ETL request should NOT be DBSQL, got {wt}"
        )

    def test_is_jobs_or_dlt(self, non_dbsql_etl_proposal):
        wt = non_dbsql_etl_proposal["workload_type"]
        assert wt in ("JOBS", "DLT"), (
            f"Batch ETL should be JOBS or DLT, got {wt}"
        )
