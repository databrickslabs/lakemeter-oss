"""E2E tests: AI Assistant Accept Button — DBSQL (Classic, Pro, Serverless).

Verifies that confirmed DBSQL workloads preserve warehouse_type, warehouse_size,
num_clusters, and other non-default configuration values.

Run: pytest tests/e2e/ai_assistant/test_accept_dbsql.py -v
"""
import pytest
from tests.e2e.helpers.assertions import save_test_results


@pytest.fixture(scope="module")
def results():
    data = []
    yield data
    save_test_results(data, "test_results/e2e_ai_accept_dbsql.json")


WAREHOUSE_SIZES = ["2X-Small", "X-Small", "Small", "Medium", "Large",
                    "X-Large", "2X-Large", "3X-Large", "4X-Large"]


class TestAcceptDBSQLClassic:
    """Verify confirm-workload preserves DBSQL Classic config."""

    @pytest.mark.parametrize("size", ["Small", "Medium", "Large", "X-Large"])
    def test_warehouse_size_preserved(self, inject_proposal, confirm_workload, size, results):
        """Each warehouse size must survive confirm."""
        pid = inject_proposal(
            workload_type="DBSQL",
            workload_name=f"DBSQL-Classic-{size}",
            dbsql_warehouse_type="CLASSIC",
            dbsql_warehouse_size=size,
            dbsql_num_clusters=1,
            serverless_enabled=False,
            hours_per_month=200,
        )
        config = confirm_workload(pid)

        assert config["workload_type"] == "DBSQL"
        assert config["dbsql_warehouse_type"] == "CLASSIC", \
            f"Warehouse type should be CLASSIC, got {config.get('dbsql_warehouse_type')}"
        assert config["dbsql_warehouse_size"] == size, \
            f"Warehouse size should be {size}, got {config.get('dbsql_warehouse_size')}"
        assert config["dbsql_num_clusters"] == 1
        assert config["hours_per_month"] == 200

        results.append({"test": f"dbsql_classic_{size}", "status": "PASS",
                        "config": config})

    def test_multi_cluster_preserved(self, inject_proposal, confirm_workload, results):
        """Multiple clusters config must survive confirm."""
        pid = inject_proposal(
            workload_type="DBSQL",
            workload_name="DBSQL-Classic-MultiCluster",
            dbsql_warehouse_type="CLASSIC",
            dbsql_warehouse_size="Large",
            dbsql_num_clusters=5,
            serverless_enabled=False,
            hours_per_month=500,
        )
        config = confirm_workload(pid)

        assert config["dbsql_num_clusters"] == 5, \
            f"Num clusters should be 5, got {config.get('dbsql_num_clusters')}"
        assert config["dbsql_warehouse_size"] == "Large"
        assert config["hours_per_month"] == 500

        results.append({"test": "dbsql_classic_multi_cluster", "status": "PASS",
                        "config": config})


class TestAcceptDBSQLPro:
    """Verify confirm-workload preserves DBSQL Pro config."""

    def test_pro_config_preserved(self, inject_proposal, confirm_workload, results):
        """Pro warehouse type and size must survive confirm."""
        pid = inject_proposal(
            workload_type="DBSQL",
            workload_name="DBSQL-Pro-Medium",
            dbsql_warehouse_type="PRO",
            dbsql_warehouse_size="Medium",
            dbsql_num_clusters=2,
            serverless_enabled=False,
            hours_per_month=400,
        )
        config = confirm_workload(pid)

        assert config["dbsql_warehouse_type"] == "PRO"
        assert config["dbsql_warehouse_size"] == "Medium"
        assert config["dbsql_num_clusters"] == 2

        results.append({"test": "dbsql_pro_medium", "status": "PASS",
                        "config": config})


class TestAcceptDBSQLServerless:
    """Verify confirm-workload preserves DBSQL Serverless config."""

    @pytest.mark.parametrize("size", ["Small", "Medium", "Large"])
    def test_serverless_size_preserved(self, inject_proposal, confirm_workload, size, results):
        """Serverless warehouse size must survive confirm."""
        pid = inject_proposal(
            workload_type="DBSQL",
            workload_name=f"DBSQL-Serverless-{size}",
            dbsql_warehouse_type="SERVERLESS",
            dbsql_warehouse_size=size,
            serverless_enabled=True,
            hours_per_month=300,
        )
        config = confirm_workload(pid)

        assert config["dbsql_warehouse_type"] == "SERVERLESS"
        assert config["dbsql_warehouse_size"] == size
        assert config["serverless_enabled"] is True

        results.append({"test": f"dbsql_serverless_{size}", "status": "PASS",
                        "config": config})
