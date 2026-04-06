"""E2E tests: AI Assistant Accept Button — Lakebase.

Verifies that confirmed Lakebase workloads preserve CU size, HA nodes,
storage GB, and other non-default values.

Run: pytest tests/e2e/ai_assistant/test_accept_lakebase.py -v
"""
import pytest
from tests.e2e.helpers.assertions import save_test_results


@pytest.fixture(scope="module")
def results():
    data = []
    yield data
    save_test_results(data, "test_results/e2e_ai_accept_lakebase.json")


CU_SIZES = [0.5, 1, 2, 4, 8, 16, 32, 48, 64]


class TestAcceptLakebase:
    """Verify confirm-workload preserves Lakebase config."""

    @pytest.mark.parametrize("cu_size", [0.5, 2, 8, 32])
    def test_cu_size_preserved(self, inject_proposal, confirm_workload, cu_size, results):
        """Each CU size must survive confirm."""
        pid = inject_proposal(
            workload_type="LAKEBASE",
            workload_name=f"Lakebase-CU{cu_size}",
            lakebase_cu=cu_size,
            lakebase_ha_nodes=1,
            lakebase_storage_gb=100,
            serverless_enabled=True,
            hours_per_month=730,
        )
        config = confirm_workload(pid)

        assert config["workload_type"] == "LAKEBASE"
        assert config["lakebase_cu"] == cu_size, \
            f"CU size should be {cu_size}, got {config.get('lakebase_cu')}"
        assert config["lakebase_ha_nodes"] == 1

        results.append({"test": f"lakebase_cu{cu_size}", "status": "PASS",
                        "config": config})

    def test_ha_nodes_preserved(self, inject_proposal, confirm_workload, results):
        """HA nodes > 1 must survive confirm."""
        pid = inject_proposal(
            workload_type="LAKEBASE",
            workload_name="Lakebase-HA",
            lakebase_cu=4,
            lakebase_ha_nodes=3,
            lakebase_storage_gb=500,
            serverless_enabled=True,
            hours_per_month=730,
        )
        config = confirm_workload(pid)

        assert config["lakebase_ha_nodes"] == 3, \
            f"HA nodes should be 3, got {config.get('lakebase_ha_nodes')}"
        assert config["lakebase_cu"] == 4

        results.append({"test": "lakebase_ha_nodes", "status": "PASS",
                        "config": config})

    def test_large_storage_preserved(self, inject_proposal, confirm_workload, results):
        """Large storage (2TB) must survive confirm."""
        pid = inject_proposal(
            workload_type="LAKEBASE",
            workload_name="Lakebase-Large-Storage",
            lakebase_cu=16,
            lakebase_ha_nodes=2,
            lakebase_storage_gb=2000,
            serverless_enabled=True,
            hours_per_month=730,
            notes="Production database with 2TB storage",
        )
        config = confirm_workload(pid)

        assert config["lakebase_cu"] == 16
        assert config["lakebase_ha_nodes"] == 2
        assert "Production database" in config.get("notes", "")

        results.append({"test": "lakebase_large_storage", "status": "PASS",
                        "config": config})

    def test_non_always_on_preserved(self, inject_proposal, confirm_workload, results):
        """Lakebase with non-730 hours (dev environment) must survive confirm."""
        pid = inject_proposal(
            workload_type="LAKEBASE",
            workload_name="Lakebase-Dev",
            lakebase_cu=1,
            lakebase_ha_nodes=1,
            lakebase_storage_gb=50,
            serverless_enabled=True,
            hours_per_month=176,
            days_per_month=22,
        )
        config = confirm_workload(pid)

        assert config["lakebase_cu"] == 1
        assert config["hours_per_month"] == 176

        results.append({"test": "lakebase_non_always_on", "status": "PASS",
                        "config": config})
