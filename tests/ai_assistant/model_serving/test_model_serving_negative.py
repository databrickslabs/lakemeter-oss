"""Tests: Non-model-serving requests should NOT produce MODEL_SERVING type."""
import pytest


class TestModelServingNegativeInteractive:
    """Interactive compute request must NOT be classified as MODEL_SERVING (AC-15)."""

    def test_not_model_serving_type(self, non_serving_interactive_proposal):
        wt = non_serving_interactive_proposal["workload_type"]
        assert wt != "MODEL_SERVING", (
            f"Interactive compute request should NOT be MODEL_SERVING, got {wt}"
        )

    def test_is_allpurpose_or_jobs(self, non_serving_interactive_proposal):
        wt = non_serving_interactive_proposal["workload_type"]
        assert wt in ("ALL_PURPOSE", "JOBS"), (
            f"Interactive request should be ALL_PURPOSE or JOBS, got {wt}"
        )


class TestModelServingNegativeEtl:
    """Batch ETL request must NOT be classified as MODEL_SERVING (AC-16)."""

    def test_not_model_serving_type(self, non_serving_etl_proposal):
        wt = non_serving_etl_proposal["workload_type"]
        assert wt != "MODEL_SERVING", (
            f"Batch ETL request should NOT be MODEL_SERVING, got {wt}"
        )

    def test_is_jobs_or_dlt(self, non_serving_etl_proposal):
        wt = non_serving_etl_proposal["workload_type"]
        assert wt in ("JOBS", "DLT"), (
            f"Batch ETL should be JOBS or DLT, got {wt}"
        )
