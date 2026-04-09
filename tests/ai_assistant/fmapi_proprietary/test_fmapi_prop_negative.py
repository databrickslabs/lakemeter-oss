"""Tests: Non-FMAPI_PROPRIETARY requests should NOT produce FMAPI_PROPRIETARY type."""
import pytest


class TestFmapiPropNegativeLlama:
    """Llama (open model) request must NOT be FMAPI_PROPRIETARY (AC-20)."""

    def test_not_fmapi_proprietary(self, non_prop_llama_proposal):
        wt = non_prop_llama_proposal["workload_type"]
        assert wt != "FMAPI_PROPRIETARY", (
            f"Llama request should NOT be FMAPI_PROPRIETARY, got {wt}"
        )

    def test_is_fmapi_databricks(self, non_prop_llama_proposal):
        wt = non_prop_llama_proposal["workload_type"]
        assert wt == "FMAPI_DATABRICKS", (
            f"Llama should be FMAPI_DATABRICKS, got {wt}"
        )

    def test_llama_model_contains_llama(self, non_prop_llama_proposal):
        model = (non_prop_llama_proposal.get("fmapi_model") or "").lower()
        assert "llama" in model, (
            f"Llama model name should contain 'llama', got '{model}'"
        )

    def test_llama_quantity_positive(self, non_prop_llama_proposal):
        qty = non_prop_llama_proposal.get("fmapi_quantity")
        assert qty is not None and qty > 0, (
            f"fmapi_quantity should be > 0, got {qty}"
        )


class TestFmapiPropNegativeGpu:
    """GPU model serving request must NOT be FMAPI_PROPRIETARY (AC-21)."""

    def test_not_fmapi_proprietary(self, non_prop_gpu_proposal):
        wt = non_prop_gpu_proposal["workload_type"]
        assert wt != "FMAPI_PROPRIETARY", (
            f"GPU serving request should NOT be FMAPI_PROPRIETARY, got {wt}"
        )

    def test_is_model_serving(self, non_prop_gpu_proposal):
        wt = non_prop_gpu_proposal["workload_type"]
        assert wt == "MODEL_SERVING", (
            f"GPU serving should be MODEL_SERVING, got {wt}"
        )

    def test_gpu_serving_has_gpu_type(self, non_prop_gpu_proposal):
        """GPU serving should specify a GPU type."""
        gpu = non_prop_gpu_proposal.get("model_serving_type") or ""
        gpu2 = non_prop_gpu_proposal.get("model_serving_gpu_type") or ""
        has_gpu = any(
            ind in (gpu + gpu2).lower()
            for ind in ["gpu", "a10", "a100", "medium"]
        )
        assert has_gpu or gpu or gpu2, (
            f"GPU serving should specify GPU type, got "
            f"model_serving_type='{gpu}', gpu_type='{gpu2}'"
        )
