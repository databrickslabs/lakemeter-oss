"""Tests: 3-workload ML pipeline — VECTOR_SEARCH + FMAPI_PROPRIETARY + MODEL_SERVING.

AC-1 through AC-6: verify types, type-specific fields, and common fields.
"""
import pytest

# Expected workload types for the ML pipeline
EXPECTED_TYPES = {"VECTOR_SEARCH", "FMAPI_PROPRIETARY", "MODEL_SERVING"}


def _find_by_type(proposals, workload_type):
    """Find the first proposal matching a workload type."""
    for p in proposals:
        if p.get("workload_type") == workload_type:
            return p
    return None


class TestMlPipelineProposalCount:
    """AC-1: conversation produces 3 proposals."""

    def test_three_proposals_collected(self, ml_pipeline_session):
        assert len(ml_pipeline_session["proposals"]) == 3


class TestMlPipelineWorkloadTypes:
    """AC-2: the set of types covers all 3 expected types."""

    def test_all_three_types_present(self, ml_pipeline_session):
        types = {
            p["workload_type"]
            for p in ml_pipeline_session["proposals"]
        }
        assert EXPECTED_TYPES.issubset(types), (
            f"Expected {EXPECTED_TYPES}, got {types}"
        )

    def test_vector_search_present(self, ml_pipeline_session):
        p = _find_by_type(
            ml_pipeline_session["proposals"], "VECTOR_SEARCH"
        )
        assert p is not None, "VECTOR_SEARCH proposal missing"

    def test_fmapi_proprietary_present(self, ml_pipeline_session):
        p = _find_by_type(
            ml_pipeline_session["proposals"], "FMAPI_PROPRIETARY"
        )
        assert p is not None, "FMAPI_PROPRIETARY proposal missing"

    def test_model_serving_present(self, ml_pipeline_session):
        p = _find_by_type(
            ml_pipeline_session["proposals"], "MODEL_SERVING"
        )
        assert p is not None, "MODEL_SERVING proposal missing"


class TestMlPipelineCommonFields:
    """AC-3: each proposal has name, reason, notes, proposal_id."""

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_workload_name_populated(self, ml_pipeline_session, idx):
        name = ml_pipeline_session["proposals"][idx].get(
            "workload_name", ""
        )
        assert name and len(name) >= 3, (
            f"Proposal {idx}: workload_name too short: '{name}'"
        )

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_reason_populated(self, ml_pipeline_session, idx):
        reason = ml_pipeline_session["proposals"][idx].get("reason", "")
        assert reason and len(reason) >= 10, (
            f"Proposal {idx}: reason too short: '{reason}'"
        )

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_notes_populated(self, ml_pipeline_session, idx):
        notes = ml_pipeline_session["proposals"][idx].get("notes", "")
        assert notes and len(notes) >= 1, (
            f"Proposal {idx}: notes should be populated"
        )

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_proposal_id_present(self, ml_pipeline_session, idx):
        pid = ml_pipeline_session["proposals"][idx].get("proposal_id", "")
        assert pid, f"Proposal {idx}: proposal_id missing"


class TestVectorSearchFields:
    """AC-4: VECTOR_SEARCH has endpoint_type populated."""

    def test_endpoint_type_populated(self, ml_pipeline_session):
        p = _find_by_type(
            ml_pipeline_session["proposals"], "VECTOR_SEARCH"
        )
        assert p is not None, "VECTOR_SEARCH proposal missing"
        ept = p.get("vector_search_endpoint_type", "")
        assert ept, (
            f"vector_search_endpoint_type should be populated, got '{ept}'"
        )


class TestFmapiProprietaryFields:
    """AC-5: FMAPI_PROPRIETARY has anthropic provider and claude model."""

    def test_provider_is_anthropic(self, ml_pipeline_session):
        p = _find_by_type(
            ml_pipeline_session["proposals"], "FMAPI_PROPRIETARY"
        )
        assert p is not None, "FMAPI_PROPRIETARY proposal missing"
        provider = (p.get("fmapi_provider") or "").lower()
        assert "anthropic" in provider, (
            f"fmapi_provider should contain 'anthropic', got '{provider}'"
        )

    def test_model_contains_claude(self, ml_pipeline_session):
        p = _find_by_type(
            ml_pipeline_session["proposals"], "FMAPI_PROPRIETARY"
        )
        assert p is not None, "FMAPI_PROPRIETARY proposal missing"
        model = (p.get("fmapi_model") or "").lower()
        assert "claude" in model, (
            f"fmapi_model should contain 'claude', got '{model}'"
        )


class TestModelServingFields:
    """AC-6: MODEL_SERVING has model_serving_type populated."""

    def test_serving_type_populated(self, ml_pipeline_session):
        p = _find_by_type(
            ml_pipeline_session["proposals"], "MODEL_SERVING"
        )
        assert p is not None, "MODEL_SERVING proposal missing"
        mst = p.get("model_serving_type", "")
        assert mst, (
            f"model_serving_type should be populated, got '{mst}'"
        )
