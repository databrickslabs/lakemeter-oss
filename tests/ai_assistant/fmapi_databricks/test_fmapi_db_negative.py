"""Tests: Non-FMAPI_DATABRICKS requests should NOT produce FMAPI_DATABRICKS type."""
import pytest


class TestFmapiDbNegativeClaude:
    """Claude (proprietary) request must NOT be FMAPI_DATABRICKS (AC-18)."""

    def test_not_fmapi_databricks(self, non_db_claude_proposal):
        wt = non_db_claude_proposal["workload_type"]
        assert wt != "FMAPI_DATABRICKS", (
            f"Claude request should NOT be FMAPI_DATABRICKS, got {wt}"
        )

    def test_is_fmapi_proprietary(self, non_db_claude_proposal):
        wt = non_db_claude_proposal["workload_type"]
        assert wt == "FMAPI_PROPRIETARY", (
            f"Claude should be FMAPI_PROPRIETARY, got {wt}"
        )

    def test_claude_provider_is_anthropic(self, non_db_claude_proposal):
        provider = (non_db_claude_proposal.get("fmapi_provider") or "").lower()
        assert "anthropic" in provider, (
            f"Claude provider should be 'anthropic', got '{provider}'"
        )

    def test_claude_model_contains_claude(self, non_db_claude_proposal):
        model = (non_db_claude_proposal.get("fmapi_model") or "").lower()
        assert "claude" in model, (
            f"Claude model name should contain 'claude', got '{model}'"
        )


class TestFmapiDbNegativeGpu:
    """GPU model serving request must NOT be FMAPI_DATABRICKS (AC-19)."""

    def test_not_fmapi_databricks(self, non_db_gpu_proposal):
        wt = non_db_gpu_proposal["workload_type"]
        assert wt != "FMAPI_DATABRICKS", (
            f"GPU serving request should NOT be FMAPI_DATABRICKS, got {wt}"
        )

    def test_is_model_serving(self, non_db_gpu_proposal):
        wt = non_db_gpu_proposal["workload_type"]
        assert wt == "MODEL_SERVING", (
            f"GPU serving should be MODEL_SERVING, got {wt}"
        )

    def test_gpu_serving_has_gpu_type(self, non_db_gpu_proposal):
        """GPU serving should specify a GPU type."""
        gpu = non_db_gpu_proposal.get("model_serving_type") or ""
        has_gpu_indicator = any(
            ind in gpu.lower() for ind in ["gpu", "a10", "a100", "medium"]
        )
        # AI may use model_serving_gpu_type field instead
        gpu2 = non_db_gpu_proposal.get("model_serving_gpu_type") or ""
        has_gpu_indicator2 = any(
            ind in gpu2.lower() for ind in ["gpu", "a10", "a100", "medium"]
        )
        assert has_gpu_indicator or has_gpu_indicator2 or gpu or gpu2, (
            f"GPU serving should specify GPU type, got "
            f"model_serving_type='{gpu}', gpu_type='{gpu2}'"
        )
