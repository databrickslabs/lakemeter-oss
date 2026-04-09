"""E2E tests: AI Assistant Accept Button — All-Purpose Classic & Serverless.

Verifies that confirmed All-Purpose workloads preserve non-default configuration.

Run: pytest tests/e2e/ai_assistant/test_accept_allpurpose.py -v
"""
import pytest
from tests.e2e.helpers.assertions import save_test_results


@pytest.fixture(scope="module")
def results():
    data = []
    yield data
    save_test_results(data, "test_results/e2e_ai_accept_allpurpose.json")


class TestAcceptAllPurposeClassic:
    """Verify confirm-workload preserves non-default All-Purpose Classic config."""

    def test_custom_instances_preserved(self, inject_proposal, confirm_workload, results):
        """Non-default instance types for interactive clusters must survive confirm."""
        pid = inject_proposal(
            workload_type="ALL_PURPOSE",
            workload_name="Dev-Interactive-Cluster",
            driver_node_type="r5.xlarge",
            worker_node_type="r5.2xlarge",
            num_workers=6,
            photon_enabled=True,
            serverless_enabled=False,
            hours_per_month=176,
            days_per_month=22,
            driver_pricing_tier="on_demand",
            worker_pricing_tier="on_demand",
        )
        config = confirm_workload(pid)

        assert config["workload_type"] == "ALL_PURPOSE"
        assert config["driver_node_type"] == "r5.xlarge"
        assert config["worker_node_type"] == "r5.2xlarge"
        assert config["num_workers"] == 6
        assert config["photon_enabled"] is True
        assert config["serverless_enabled"] is False
        assert config["hours_per_month"] == 176
        assert config["driver_pricing_tier"] == "on_demand"
        assert config["worker_pricing_tier"] == "on_demand"

        results.append({"test": "ap_classic_custom_instances", "status": "PASS",
                        "config": config})

    def test_photon_disabled_preserved(self, inject_proposal, confirm_workload, results):
        """Explicitly disabling photon must survive confirm (default is True)."""
        pid = inject_proposal(
            workload_type="ALL_PURPOSE",
            workload_name="No-Photon-Cluster",
            driver_node_type="m6i.xlarge",
            worker_node_type="m6i.2xlarge",
            num_workers=2,
            photon_enabled=False,
            serverless_enabled=False,
            hours_per_month=80,
        )
        config = confirm_workload(pid)

        assert config["photon_enabled"] is False, \
            f"Photon should be False, got {config.get('photon_enabled')}"
        assert config["num_workers"] == 2
        assert config["hours_per_month"] == 80

        results.append({"test": "ap_classic_photon_disabled", "status": "PASS",
                        "config": config})

    def test_spot_workers_preserved(self, inject_proposal, confirm_workload, results):
        """Spot pricing for workers must survive confirm."""
        pid = inject_proposal(
            workload_type="ALL_PURPOSE",
            workload_name="Spot-Worker-Cluster",
            driver_node_type="m6i.xlarge",
            worker_node_type="m6id.2xlarge",
            num_workers=8,
            photon_enabled=True,
            serverless_enabled=False,
            driver_pricing_tier="on_demand",
            worker_pricing_tier="spot",
            hours_per_month=500,
        )
        config = confirm_workload(pid)

        assert config["worker_pricing_tier"] == "spot"
        assert config["driver_pricing_tier"] == "on_demand"
        assert config["num_workers"] == 8

        results.append({"test": "ap_classic_spot_workers", "status": "PASS",
                        "config": config})


class TestAcceptAllPurposeServerless:
    """Verify confirm-workload preserves All-Purpose Serverless config."""

    def test_serverless_basic_preserved(self, inject_proposal, confirm_workload, results):
        pid = inject_proposal(
            workload_type="ALL_PURPOSE",
            workload_name="Serverless-Interactive",
            serverless_enabled=True,
            hours_per_month=160,
            days_per_month=20,
        )
        config = confirm_workload(pid)

        assert config["serverless_enabled"] is True
        assert config["workload_type"] == "ALL_PURPOSE"
        assert config["hours_per_month"] == 160

        results.append({"test": "ap_serverless_basic", "status": "PASS",
                        "config": config})

    def test_serverless_always_on_preserved(self, inject_proposal, confirm_workload, results):
        """Always-on serverless (730 hrs) must survive confirm."""
        pid = inject_proposal(
            workload_type="ALL_PURPOSE",
            workload_name="Always-On-Serverless",
            serverless_enabled=True,
            hours_per_month=730,
            days_per_month=30,
        )
        config = confirm_workload(pid)

        assert config["serverless_enabled"] is True
        assert config["hours_per_month"] == 730
        assert config["days_per_month"] == 30

        results.append({"test": "ap_serverless_always_on", "status": "PASS",
                        "config": config})
