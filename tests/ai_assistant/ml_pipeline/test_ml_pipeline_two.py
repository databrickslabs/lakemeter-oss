"""Tests: 2-workload ML conversation — VECTOR_SEARCH + FMAPI_PROPRIETARY.

AC-10 through AC-11: RAG embeddings + Claude produces 2 proposals
without MODEL_SERVING.
"""
import pytest


class TestTwoMlWorkloadTypes:
    """AC-10: 2-workload conversation covers VS and FMAPI_PROP."""

    def test_two_proposals_collected(self, two_ml_session):
        assert len(two_ml_session["proposals"]) == 2

    def test_types_cover_vs_and_fmapi(self, two_ml_session):
        types = {
            p["workload_type"] for p in two_ml_session["proposals"]
        }
        expected = {"VECTOR_SEARCH", "FMAPI_PROPRIETARY"}
        assert expected.issubset(types), (
            f"Expected types {expected}, got {types}"
        )

    def test_vector_search_present(self, two_ml_session):
        types = {
            p["workload_type"] for p in two_ml_session["proposals"]
        }
        assert "VECTOR_SEARCH" in types

    def test_fmapi_proprietary_present(self, two_ml_session):
        types = {
            p["workload_type"] for p in two_ml_session["proposals"]
        }
        assert "FMAPI_PROPRIETARY" in types


class TestTwoMlWorkloadFields:
    """Required fields on both proposals."""

    @pytest.mark.parametrize("idx", [0, 1])
    def test_workload_name_populated(self, two_ml_session, idx):
        name = two_ml_session["proposals"][idx].get(
            "workload_name", ""
        )
        assert name and len(name) >= 3, (
            f"Proposal {idx}: workload_name too short: '{name}'"
        )

    @pytest.mark.parametrize("idx", [0, 1])
    def test_reason_populated(self, two_ml_session, idx):
        reason = two_ml_session["proposals"][idx].get("reason", "")
        assert reason and len(reason) >= 10, (
            f"Proposal {idx}: reason too short: '{reason}'"
        )

    @pytest.mark.parametrize("idx", [0, 1])
    def test_proposal_id_present(self, two_ml_session, idx):
        pid = two_ml_session["proposals"][idx].get("proposal_id", "")
        assert pid, f"Proposal {idx}: proposal_id missing"


class TestTwoMlConfirmations:
    """AC-11: both confirmations succeed."""

    @pytest.mark.parametrize("idx", [0, 1])
    def test_confirmation_success(self, two_ml_session, idx):
        result = two_ml_session["confirmations"][idx]
        assert result["success"] is True

    @pytest.mark.parametrize("idx", [0, 1])
    def test_confirmation_action(self, two_ml_session, idx):
        result = two_ml_session["confirmations"][idx]
        assert result["action"] == "confirmed"

    def test_distinct_proposal_ids(self, two_ml_session):
        pids = [
            p["proposal_id"] for p in two_ml_session["proposals"]
        ]
        assert len(set(pids)) == 2, (
            f"Expected 2 distinct IDs, got {pids}"
        )
