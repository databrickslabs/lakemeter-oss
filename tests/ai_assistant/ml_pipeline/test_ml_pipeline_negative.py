"""Tests: negative discrimination — model serving only.

AC-12: a prompt for "model serving endpoint for ML inference" should
produce MODEL_SERVING, not VECTOR_SEARCH or FMAPI_PROPRIETARY.
"""
import pytest


class TestNegativeModelServingOnly:
    """Single-workload prompt should produce MODEL_SERVING only."""

    def test_workload_type_is_model_serving(
        self, negative_ms_only_proposal
    ):
        wt = negative_ms_only_proposal["workload_type"]
        assert wt == "MODEL_SERVING", (
            f"ML inference prompt should produce MODEL_SERVING, got {wt}"
        )

    def test_not_vector_search(self, negative_ms_only_proposal):
        wt = negative_ms_only_proposal["workload_type"]
        assert wt != "VECTOR_SEARCH", (
            "ML inference prompt should NOT produce VECTOR_SEARCH"
        )

    def test_not_fmapi_proprietary(self, negative_ms_only_proposal):
        wt = negative_ms_only_proposal["workload_type"]
        assert wt != "FMAPI_PROPRIETARY", (
            "ML inference prompt should NOT produce FMAPI_PROPRIETARY"
        )

    def test_workload_name_populated(self, negative_ms_only_proposal):
        name = negative_ms_only_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short: '{name}'"
        )

    def test_reason_populated(self, negative_ms_only_proposal):
        reason = negative_ms_only_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short: '{reason}'"
        )

    def test_serving_type_populated(self, negative_ms_only_proposal):
        mst = negative_ms_only_proposal.get("model_serving_type", "")
        assert mst, (
            f"model_serving_type should be populated, got '{mst}'"
        )

    def test_proposal_id_present(self, negative_ms_only_proposal):
        pid = negative_ms_only_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present"
