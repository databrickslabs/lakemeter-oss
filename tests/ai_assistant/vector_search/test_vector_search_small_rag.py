"""Tests: AI proposes VECTOR_SEARCH for a small RAG chatbot use case."""
import pytest

from tests.ai_assistant.vector_search.prompts import VALID_ENDPOINT_TYPES


class TestVectorSearchSmallRag:
    """AI proposes a VECTOR_SEARCH workload for small RAG (AC-12 to AC-14)."""

    def test_workload_type_is_vector_search(self, small_rag_proposal):
        assert small_rag_proposal["workload_type"] == "VECTOR_SEARCH", (
            f"Expected VECTOR_SEARCH, got {small_rag_proposal['workload_type']}"
        )

    def test_capacity_present_and_positive(self, small_rag_proposal):
        cap = small_rag_proposal.get("vector_capacity_millions")
        assert cap is not None and cap > 0, (
            f"vector_capacity_millions should be > 0, got {cap}"
        )

    def test_capacity_reasonable_for_5m(self, small_rag_proposal):
        cap = small_rag_proposal.get("vector_capacity_millions", 0)
        assert 1 <= cap <= 100, (
            f"vector_capacity_millions should be roughly 5 (range 1-100), "
            f"got {cap}"
        )

    def test_endpoint_type_populated(self, small_rag_proposal):
        et = small_rag_proposal.get("vector_search_endpoint_type", "")
        assert et, (
            f"vector_search_endpoint_type should be populated, got '{et}'"
        )

    def test_endpoint_type_valid_enum(self, small_rag_proposal):
        et = small_rag_proposal.get("vector_search_endpoint_type", "")
        assert et in VALID_ENDPOINT_TYPES, (
            f"vector_search_endpoint_type '{et}' not in {VALID_ENDPOINT_TYPES}"
        )

    def test_workload_name_non_empty(self, small_rag_proposal):
        name = small_rag_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_proposal_id_present(self, small_rag_proposal):
        pid = small_rag_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present for confirm/reject flow"
