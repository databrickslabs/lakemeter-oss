"""Tests: AI proposes VECTOR_SEARCH with Standard endpoint and correct fields."""
import pytest

from tests.ai_assistant.vector_search.prompts import VALID_ENDPOINT_TYPES


class TestVectorSearchStandard:
    """AI proposes a VECTOR_SEARCH Standard workload (AC-1 through AC-7)."""

    def test_workload_type_is_vector_search(self, standard_proposal):
        assert standard_proposal["workload_type"] == "VECTOR_SEARCH", (
            f"Expected VECTOR_SEARCH, got {standard_proposal['workload_type']}"
        )

    def test_endpoint_type_is_standard(self, standard_proposal):
        et = (standard_proposal.get("vector_search_endpoint_type") or "").upper()
        assert "STANDARD" in et, (
            f"vector_search_endpoint_type should contain 'STANDARD', got "
            f"'{standard_proposal.get('vector_search_endpoint_type')}'"
        )

    def test_endpoint_type_valid_enum(self, standard_proposal):
        et = standard_proposal.get("vector_search_endpoint_type", "")
        assert et in VALID_ENDPOINT_TYPES, (
            f"vector_search_endpoint_type '{et}' not in {VALID_ENDPOINT_TYPES}"
        )

    def test_capacity_approximately_50m(self, standard_proposal):
        cap = standard_proposal.get("vector_capacity_millions")
        assert cap is not None and cap > 0, (
            f"vector_capacity_millions should be > 0, got {cap}"
        )
        assert 5 <= cap <= 500, (
            f"vector_capacity_millions should be roughly 50 (range 5-500), "
            f"got {cap}"
        )

    def test_workload_name_non_empty(self, standard_proposal):
        name = standard_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_reason_populated(self, standard_proposal):
        reason = standard_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_notes_populated(self, standard_proposal):
        notes = standard_proposal.get("notes", "")
        assert notes and len(notes) >= 1, (
            f"notes should be populated: '{notes}'"
        )

    def test_proposal_id_present(self, standard_proposal):
        pid = standard_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present for confirm/reject flow"
