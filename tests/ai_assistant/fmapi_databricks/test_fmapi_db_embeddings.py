"""Tests: AI proposes FMAPI_DATABRICKS for embeddings model (BGE/GTE)."""
import pytest


class TestFmapiDbEmbeddings:
    """AI proposes FMAPI_DATABRICKS for BGE-Large embeddings (AC-14 to AC-17)."""

    def test_workload_type_is_fmapi_databricks(self, embeddings_proposal):
        wt = embeddings_proposal["workload_type"]
        assert wt == "FMAPI_DATABRICKS", (
            f"Expected FMAPI_DATABRICKS, got {wt}"
        )

    def test_model_is_embeddings_related(self, embeddings_proposal):
        model = (embeddings_proposal.get("fmapi_model") or "").lower()
        # BGE-Large or GTE are the Databricks-hosted embedding models
        embeddings_indicators = ["bge", "gte", "embed"]
        has_match = any(ind in model for ind in embeddings_indicators)
        assert has_match, (
            f"fmapi_model should be an embeddings model (bge/gte/embed), "
            f"got '{embeddings_proposal.get('fmapi_model')}'"
        )

    def test_quantity_positive(self, embeddings_proposal):
        qty = embeddings_proposal.get("fmapi_quantity")
        assert qty is not None and qty > 0, (
            f"fmapi_quantity should be > 0, got {qty}"
        )

    def test_provider_present(self, embeddings_proposal):
        provider = embeddings_proposal.get("fmapi_provider", "")
        assert provider, (
            f"fmapi_provider should be present, got '{provider}'"
        )

    def test_endpoint_type_valid(self, embeddings_proposal):
        et = embeddings_proposal.get("fmapi_endpoint_type", "")
        assert et in ["global", "regional"], (
            f"fmapi_endpoint_type '{et}' not in ['global', 'regional']"
        )

    def test_workload_name_non_empty(self, embeddings_proposal):
        name = embeddings_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_reason_populated(self, embeddings_proposal):
        reason = embeddings_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )
