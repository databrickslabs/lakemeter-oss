"""Tests: AI proposes VECTOR_SEARCH with Storage-Optimized endpoint."""
import pytest

from tests.ai_assistant.vector_search.prompts import VALID_ENDPOINT_TYPES


class TestVectorSearchStorageOptimized:
    """AI proposes a VECTOR_SEARCH Storage-Optimized workload (AC-8 to AC-11)."""

    def test_workload_type_is_vector_search(self, storage_optimized_proposal):
        assert storage_optimized_proposal["workload_type"] == "VECTOR_SEARCH", (
            f"Expected VECTOR_SEARCH, got "
            f"{storage_optimized_proposal['workload_type']}"
        )

    def test_endpoint_type_is_storage_optimized(self, storage_optimized_proposal):
        et = (
            storage_optimized_proposal.get("vector_search_endpoint_type") or ""
        ).upper()
        assert "STORAGE" in et, (
            f"vector_search_endpoint_type should contain 'STORAGE', got "
            f"'{storage_optimized_proposal.get('vector_search_endpoint_type')}'"
        )

    def test_endpoint_type_valid_enum(self, storage_optimized_proposal):
        et = storage_optimized_proposal.get(
            "vector_search_endpoint_type", ""
        )
        assert et in VALID_ENDPOINT_TYPES, (
            f"vector_search_endpoint_type '{et}' not in {VALID_ENDPOINT_TYPES}"
        )

    def test_capacity_present_and_positive(self, storage_optimized_proposal):
        cap = storage_optimized_proposal.get("vector_capacity_millions")
        assert cap is not None and cap > 0, (
            f"vector_capacity_millions should be > 0, got {cap}"
        )

    def test_capacity_reasonable_for_200m(self, storage_optimized_proposal):
        cap = storage_optimized_proposal.get("vector_capacity_millions", 0)
        assert 50 <= cap <= 500, (
            f"vector_capacity_millions should be roughly 200 (range 50-500), "
            f"got {cap}"
        )

    def test_workload_name_non_empty(self, storage_optimized_proposal):
        name = storage_optimized_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_proposal_id_present(self, storage_optimized_proposal):
        pid = storage_optimized_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present for confirm/reject flow"
