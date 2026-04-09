"""E2E tests: AI Assistant Accept Button — Jobs Classic & Serverless.

Verifies that when the AI proposes a Jobs workload with specific non-default
values, clicking "accept" preserves those exact values in the confirmed config.

The bug this catches: previously, confirmed workloads got populated with
DEFAULT values instead of the AI-suggested non-default values.

Run: pytest tests/e2e/ai_assistant/test_accept_jobs.py -v
"""
import pytest
import json
from tests.e2e.helpers.assertions import save_test_results


@pytest.fixture(scope="module")
def results():
    data = []
    yield data
    save_test_results(data, "test_results/e2e_ai_accept_jobs.json")


class TestAcceptJobsClassic:
    """Verify confirm-workload preserves non-default Jobs Classic config."""

    def test_custom_instance_types_preserved(self, inject_proposal, confirm_workload, results):
        """Non-default driver/worker instance types must survive confirm."""
        pid = inject_proposal(
            workload_type="JOBS",
            workload_name="Custom-Instance-Job",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.2xlarge",
            num_workers=10,
            photon_enabled=True,
            serverless_enabled=False,
            hours_per_month=176,
            days_per_month=22,
        )
        config = confirm_workload(pid)

        assert config["workload_type"] == "JOBS"
        assert config["workload_name"] == "Custom-Instance-Job"
        assert config["driver_node_type"] == "i3.xlarge", \
            f"Driver should be i3.xlarge, got {config['driver_node_type']}"
        assert config["worker_node_type"] == "i3.2xlarge", \
            f"Worker should be i3.2xlarge, got {config['worker_node_type']}"
        assert config["num_workers"] == 10, \
            f"Num workers should be 10, got {config['num_workers']}"
        assert config["photon_enabled"] is True
        assert config["serverless_enabled"] is False
        assert config["hours_per_month"] == 176

        results.append({"test": "jobs_classic_custom_instances", "status": "PASS",
                        "config": config})

    def test_run_based_usage_preserved(self, inject_proposal, confirm_workload, results):
        """Run-based usage (runs_per_day, avg_runtime_minutes) must survive confirm."""
        pid = inject_proposal(
            workload_type="JOBS",
            workload_name="Run-Based-Job",
            driver_node_type="m6i.xlarge",
            worker_node_type="m6id.2xlarge",
            num_workers=4,
            photon_enabled=False,
            serverless_enabled=False,
            runs_per_day=5,
            avg_runtime_minutes=30,
            days_per_month=22,
        )
        config = confirm_workload(pid)

        assert config["runs_per_day"] == 5, \
            f"runs_per_day should be 5, got {config.get('runs_per_day')}"
        assert config["avg_runtime_minutes"] == 30, \
            f"avg_runtime_minutes should be 30, got {config.get('avg_runtime_minutes')}"
        assert config["days_per_month"] == 22
        assert config["photon_enabled"] is False

        results.append({"test": "jobs_classic_run_based", "status": "PASS",
                        "config": config})

    def test_pricing_tiers_preserved(self, inject_proposal, confirm_workload, results):
        """Non-default pricing tiers (1yr_reserved, spot) must survive confirm."""
        pid = inject_proposal(
            workload_type="JOBS",
            workload_name="Reserved-Pricing-Job",
            driver_node_type="m6i.xlarge",
            worker_node_type="m6id.2xlarge",
            num_workers=8,
            photon_enabled=True,
            serverless_enabled=False,
            driver_pricing_tier="1yr_reserved",
            worker_pricing_tier="spot",
            hours_per_month=500,
        )
        config = confirm_workload(pid)

        assert config["driver_pricing_tier"] == "1yr_reserved", \
            f"Driver tier should be 1yr_reserved, got {config.get('driver_pricing_tier')}"
        assert config["worker_pricing_tier"] == "spot", \
            f"Worker tier should be spot, got {config.get('worker_pricing_tier')}"
        assert config["num_workers"] == 8
        assert config["hours_per_month"] == 500

        results.append({"test": "jobs_classic_pricing_tiers", "status": "PASS",
                        "config": config})

    def test_large_cluster_preserved(self, inject_proposal, confirm_workload, results):
        """Large cluster config (20 workers, large instances) must survive confirm."""
        pid = inject_proposal(
            workload_type="JOBS",
            workload_name="Large-Cluster-Job",
            driver_node_type="r5.2xlarge",
            worker_node_type="r5.4xlarge",
            num_workers=20,
            photon_enabled=True,
            serverless_enabled=False,
            hours_per_month=730,
            days_per_month=30,
            notes="Large ETL pipeline for 10TB dataset",
        )
        config = confirm_workload(pid)

        assert config["driver_node_type"] == "r5.2xlarge"
        assert config["worker_node_type"] == "r5.4xlarge"
        assert config["num_workers"] == 20
        assert config["hours_per_month"] == 730
        assert "Large ETL" in config.get("notes", ""), \
            f"Notes should contain 'Large ETL', got: {config.get('notes')}"

        results.append({"test": "jobs_classic_large_cluster", "status": "PASS",
                        "config": config})


class TestAcceptJobsServerless:
    """Verify confirm-workload preserves non-default Jobs Serverless config."""

    def test_serverless_enabled_preserved(self, inject_proposal, confirm_workload, results):
        """serverless_enabled=True must survive confirm."""
        pid = inject_proposal(
            workload_type="JOBS",
            workload_name="Serverless-Job",
            serverless_enabled=True,
            hours_per_month=200,
            days_per_month=20,
        )
        config = confirm_workload(pid)

        assert config["serverless_enabled"] is True, \
            f"serverless_enabled should be True, got {config.get('serverless_enabled')}"
        assert config["hours_per_month"] == 200
        assert config["workload_type"] == "JOBS"

        results.append({"test": "jobs_serverless_basic", "status": "PASS",
                        "config": config})

    def test_serverless_run_based_preserved(self, inject_proposal, confirm_workload, results):
        """Serverless jobs with run-based usage must survive confirm."""
        pid = inject_proposal(
            workload_type="JOBS",
            workload_name="Serverless-Run-Job",
            serverless_enabled=True,
            runs_per_day=10,
            avg_runtime_minutes=15,
            days_per_month=22,
        )
        config = confirm_workload(pid)

        assert config["serverless_enabled"] is True
        assert config["runs_per_day"] == 10
        assert config["avg_runtime_minutes"] == 15
        assert config["days_per_month"] == 22

        results.append({"test": "jobs_serverless_run_based", "status": "PASS",
                        "config": config})
