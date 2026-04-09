"""Tests: Non-vector-search requests should NOT produce VECTOR_SEARCH type."""
import pytest


class TestVectorSearchNegativeModel:
    """Model deployment request must NOT be classified as VECTOR_SEARCH (AC-15)."""

    def test_not_vector_search_type(self, non_vs_model_proposal):
        wt = non_vs_model_proposal["workload_type"]
        assert wt != "VECTOR_SEARCH", (
            f"Model deployment request should NOT be VECTOR_SEARCH, got {wt}"
        )

    def test_is_model_serving(self, non_vs_model_proposal):
        wt = non_vs_model_proposal["workload_type"]
        assert wt == "MODEL_SERVING", (
            f"Model deployment should be MODEL_SERVING, got {wt}"
        )


class TestVectorSearchNegativeSql:
    """SQL analytics request must NOT be classified as VECTOR_SEARCH (AC-16)."""

    def test_not_vector_search_type(self, non_vs_sql_proposal):
        wt = non_vs_sql_proposal["workload_type"]
        assert wt != "VECTOR_SEARCH", (
            f"SQL analytics request should NOT be VECTOR_SEARCH, got {wt}"
        )

    def test_is_dbsql(self, non_vs_sql_proposal):
        wt = non_vs_sql_proposal["workload_type"]
        assert wt == "DBSQL", (
            f"SQL analytics should be DBSQL, got {wt}"
        )
