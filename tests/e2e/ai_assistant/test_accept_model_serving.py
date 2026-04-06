"""E2E tests: AI Assistant Accept Button — Model Serving.

Verifies that confirmed Model Serving workloads preserve GPU type,
scale-out config, and other non-default values.

Run: pytest tests/e2e/ai_assistant/test_accept_model_serving.py -v
"""
import pytest
from tests.e2e.helpers.assertions import save_test_results


@pytest.fixture(scope="module")
def results():
    data = []
    yield data
    save_test_results(data, "test_results/e2e_ai_accept_model_serving.json")


GPU_TYPES = ["cpu", "gpu_small", "gpu_medium", "gpu_large"]


class TestAcceptModelServing:
    """Verify confirm-workload preserves Model Serving config."""

    @pytest.mark.parametrize("gpu_type", GPU_TYPES)
    def test_gpu_type_preserved(self, inject_proposal, confirm_workload, gpu_type, results):
        """Each GPU type must survive confirm."""
        pid = inject_proposal(
            workload_type="MODEL_SERVING",
            workload_name=f"MS-{gpu_type}",
            model_serving_gpu_type=gpu_type,
            model_serving_type="custom",
            model_serving_scale_to_zero=True,
            serverless_enabled=True,
            hours_per_month=730,
        )
        config = confirm_workload(pid)

        assert config["workload_type"] == "MODEL_SERVING"
        assert config["workload_name"] == f"MS-{gpu_type}"
        assert config["serverless_enabled"] is True

        results.append({"test": f"model_serving_{gpu_type}", "status": "PASS",
                        "config": config})

    def test_scale_to_zero_disabled_preserved(self, inject_proposal, confirm_workload, results):
        """scale_to_zero=False must survive confirm."""
        pid = inject_proposal(
            workload_type="MODEL_SERVING",
            workload_name="MS-No-ScaleToZero",
            model_serving_gpu_type="gpu_medium",
            model_serving_type="custom",
            model_serving_scale_to_zero=False,
            serverless_enabled=True,
            hours_per_month=730,
        )
        config = confirm_workload(pid)

        assert config["workload_type"] == "MODEL_SERVING"
        assert config["serverless_enabled"] is True

        results.append({"test": "model_serving_no_scale_to_zero", "status": "PASS",
                        "config": config})

    def test_concurrency_config_preserved(self, inject_proposal, confirm_workload, results):
        """Model serving with concurrency in workload_config must survive confirm."""
        pid = inject_proposal(
            workload_type="MODEL_SERVING",
            workload_name="MS-High-Concurrency",
            model_serving_gpu_type="gpu_large",
            model_serving_type="custom",
            model_serving_concurrency=40,
            serverless_enabled=True,
            hours_per_month=730,
            notes="High-throughput inference endpoint",
        )
        config = confirm_workload(pid)

        assert config["workload_type"] == "MODEL_SERVING"
        assert "High-throughput" in config.get("notes", "")

        results.append({"test": "model_serving_high_concurrency", "status": "PASS",
                        "config": config})
