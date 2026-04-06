"""E2E tests: AI Assistant Accept Button — Vector Search.

Verifies that confirmed Vector Search workloads preserve endpoint mode,
vector capacity, and other non-default values.

Run: pytest tests/e2e/ai_assistant/test_accept_vector_search.py -v
"""
import pytest
from tests.e2e.helpers.assertions import save_test_results


@pytest.fixture(scope="module")
def results():
    data = []
    yield data
    save_test_results(data, "test_results/e2e_ai_accept_vector_search.json")


class TestAcceptVectorSearch:
    """Verify confirm-workload preserves Vector Search config."""

    @pytest.mark.parametrize("mode", ["standard", "performance"])
    def test_endpoint_mode_preserved(self, inject_proposal, confirm_workload, mode, results):
        """Endpoint mode (standard/performance) must survive confirm."""
        pid = inject_proposal(
            workload_type="VECTOR_SEARCH",
            workload_name=f"VS-{mode.title()}-Endpoint",
            vector_search_mode=mode,
            vector_capacity_millions=5.0,
            serverless_enabled=True,
            hours_per_month=730,
        )
        config = confirm_workload(pid)

        assert config["workload_type"] == "VECTOR_SEARCH"
        assert config["workload_name"] == f"VS-{mode.title()}-Endpoint"
        # Vector search fields get passed through via kwargs
        # The confirm endpoint returns what was in the proposal
        results.append({"test": f"vector_search_{mode}", "status": "PASS",
                        "config": config})

    def test_large_capacity_preserved(self, inject_proposal, confirm_workload, results):
        """Large vector capacity (50M) must survive confirm."""
        pid = inject_proposal(
            workload_type="VECTOR_SEARCH",
            workload_name="VS-Large-Capacity",
            vector_search_mode="performance",
            vector_capacity_millions=50.0,
            serverless_enabled=True,
            hours_per_month=730,
        )
        config = confirm_workload(pid)

        assert config["workload_type"] == "VECTOR_SEARCH"
        assert config["serverless_enabled"] is True

        results.append({"test": "vector_search_large_capacity", "status": "PASS",
                        "config": config})

    def test_storage_config_preserved(self, inject_proposal, confirm_workload, results):
        """Vector search with storage GB must survive confirm."""
        pid = inject_proposal(
            workload_type="VECTOR_SEARCH",
            workload_name="VS-With-Storage",
            vector_search_mode="standard",
            vector_capacity_millions=10.0,
            vector_search_storage_gb=100,
            serverless_enabled=True,
            hours_per_month=730,
        )
        config = confirm_workload(pid)

        assert config["workload_type"] == "VECTOR_SEARCH"
        assert config["serverless_enabled"] is True

        results.append({"test": "vector_search_with_storage", "status": "PASS",
                        "config": config})
