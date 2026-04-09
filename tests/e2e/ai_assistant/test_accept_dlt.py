"""E2E tests: AI Assistant Accept Button — DLT Classic & Serverless.

Verifies that confirmed DLT workloads preserve non-default configuration,
including dlt_edition (CORE/PRO/ADVANCED).

Run: pytest tests/e2e/ai_assistant/test_accept_dlt.py -v
"""
import pytest
from tests.e2e.helpers.assertions import save_test_results


@pytest.fixture(scope="module")
def results():
    data = []
    yield data
    save_test_results(data, "test_results/e2e_ai_accept_dlt.json")


DLT_EDITIONS = ["CORE", "PRO", "ADVANCED"]


class TestAcceptDLTClassic:
    """Verify confirm-workload preserves non-default DLT Classic config."""

    @pytest.mark.parametrize("edition", DLT_EDITIONS)
    def test_edition_preserved(self, inject_proposal, confirm_workload, edition, results):
        """Each DLT edition must survive confirm."""
        pid = inject_proposal(
            workload_type="DLT",
            workload_name=f"DLT-{edition}-Pipeline",
            dlt_edition=edition,
            driver_node_type="m6i.xlarge",
            worker_node_type="m6id.2xlarge",
            num_workers=4,
            photon_enabled=True,
            serverless_enabled=False,
            hours_per_month=200,
        )
        config = confirm_workload(pid)

        assert config["workload_type"] == "DLT"
        assert config["dlt_edition"] == edition, \
            f"DLT edition should be {edition}, got {config.get('dlt_edition')}"
        assert config["driver_node_type"] == "m6i.xlarge"
        assert config["worker_node_type"] == "m6id.2xlarge"
        assert config["num_workers"] == 4
        assert config["photon_enabled"] is True
        assert config["hours_per_month"] == 200

        results.append({"test": f"dlt_classic_{edition.lower()}", "status": "PASS",
                        "config": config})

    def test_custom_cluster_preserved(self, inject_proposal, confirm_workload, results):
        """Large DLT cluster with custom instances must survive confirm."""
        pid = inject_proposal(
            workload_type="DLT",
            workload_name="Large-DLT-Pipeline",
            dlt_edition="ADVANCED",
            driver_node_type="r5.2xlarge",
            worker_node_type="r5.4xlarge",
            num_workers=16,
            photon_enabled=True,
            serverless_enabled=False,
            driver_pricing_tier="on_demand",
            worker_pricing_tier="spot",
            runs_per_day=3,
            avg_runtime_minutes=45,
            days_per_month=22,
        )
        config = confirm_workload(pid)

        assert config["dlt_edition"] == "ADVANCED"
        assert config["driver_node_type"] == "r5.2xlarge"
        assert config["worker_node_type"] == "r5.4xlarge"
        assert config["num_workers"] == 16
        assert config["driver_pricing_tier"] == "on_demand"
        assert config["worker_pricing_tier"] == "spot"
        assert config["runs_per_day"] == 3
        assert config["avg_runtime_minutes"] == 45

        results.append({"test": "dlt_classic_large_cluster", "status": "PASS",
                        "config": config})

    def test_photon_disabled_preserved(self, inject_proposal, confirm_workload, results):
        """DLT with photon explicitly disabled must survive confirm."""
        pid = inject_proposal(
            workload_type="DLT",
            workload_name="DLT-No-Photon",
            dlt_edition="CORE",
            driver_node_type="m6i.xlarge",
            worker_node_type="m6i.xlarge",
            num_workers=2,
            photon_enabled=False,
            serverless_enabled=False,
            hours_per_month=100,
        )
        config = confirm_workload(pid)

        assert config["photon_enabled"] is False
        assert config["dlt_edition"] == "CORE"
        assert config["num_workers"] == 2

        results.append({"test": "dlt_classic_photon_disabled", "status": "PASS",
                        "config": config})


class TestAcceptDLTServerless:
    """Verify confirm-workload preserves DLT Serverless config."""

    @pytest.mark.parametrize("edition", DLT_EDITIONS)
    def test_serverless_edition_preserved(self, inject_proposal, confirm_workload, edition, results):
        """DLT Serverless with each edition must survive confirm."""
        pid = inject_proposal(
            workload_type="DLT",
            workload_name=f"DLT-Serverless-{edition}",
            dlt_edition=edition,
            serverless_enabled=True,
            hours_per_month=300,
            days_per_month=22,
        )
        config = confirm_workload(pid)

        assert config["serverless_enabled"] is True
        assert config["dlt_edition"] == edition
        assert config["workload_type"] == "DLT"
        assert config["hours_per_month"] == 300

        results.append({"test": f"dlt_serverless_{edition.lower()}", "status": "PASS",
                        "config": config})

    def test_serverless_run_based_preserved(self, inject_proposal, confirm_workload, results):
        """DLT Serverless with run-based usage must survive confirm."""
        pid = inject_proposal(
            workload_type="DLT",
            workload_name="DLT-Serverless-RunBased",
            dlt_edition="PRO",
            serverless_enabled=True,
            runs_per_day=6,
            avg_runtime_minutes=20,
            days_per_month=22,
        )
        config = confirm_workload(pid)

        assert config["serverless_enabled"] is True
        assert config["dlt_edition"] == "PRO"
        assert config["runs_per_day"] == 6
        assert config["avg_runtime_minutes"] == 20
        assert config["days_per_month"] == 22

        results.append({"test": "dlt_serverless_run_based", "status": "PASS",
                        "config": config})
