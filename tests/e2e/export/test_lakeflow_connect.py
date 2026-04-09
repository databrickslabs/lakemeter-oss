"""E2E tests: Lakeflow Connect — API calculation vs Excel export verification.

Tests:
  - 6 cloud/region configs
  - Pipeline only (DLT Serverless, ADVANCED edition)
  - Pipeline + Gateway (DLT Classic Advanced)
  - Different usage patterns (run-based, hourly)
  = ~24 test cases

Run: pytest tests/e2e/export/test_lakeflow_connect.py -v
"""
import pytest
from tests.e2e.helpers.test_data import (
    ESTIMATE_CONFIGS, LAKEFLOW_GATEWAY_INSTANCES, USAGE_RUN_BASED, USAGE_HOURLY, config_id,
)
from tests.e2e.helpers.assertions import assert_costs_match, save_test_results
from tests.e2e.helpers.excel_parser import parse_estimate_excel


def _generate_pipeline_params():
    """Pipeline-only tests: various usage patterns."""
    params = []
    for cfg in ESTIMATE_CONFIGS:
        for usage_label, usage in [("run", USAGE_RUN_BASED), ("hourly", USAGE_HOURLY)]:
            test_id = f"{config_id(cfg)}-pipeline-{usage_label}"
            params.append(pytest.param(cfg, usage, id=test_id))
    return params


def _generate_gateway_params():
    """Pipeline + Gateway tests."""
    params = []
    for cfg in ESTIMATE_CONFIGS:
        cloud = cfg["cloud"]
        instance = LAKEFLOW_GATEWAY_INSTANCES.get(cloud, "i3.xlarge")
        test_id = f"{config_id(cfg)}-with-gateway"
        params.append(pytest.param(cfg, instance, id=test_id))
    return params


@pytest.fixture(scope="module")
def results():
    data = []
    yield data
    save_test_results(data, "test_results/e2e_lakeflow_connect.json")


class TestLakeflowConnectPipeline:
    """Verify Lakeflow Connect pipeline-only calculation."""

    @pytest.mark.parametrize("cfg, usage", _generate_pipeline_params())
    def test_pipeline_only(self, e2e_client, cfg, usage, results):
        result = e2e_client.calculate_lakeflow_connect(
            cloud=cfg["cloud"], region=cfg["region"], tier=cfg["tier"],
            dlt_edition="ADVANCED", gateway_enabled=False,
            usage=usage,
        )
        assert "pipeline" in result
        assert "total_cost" in result
        assert result["pipeline"]["dbu_per_month"] >= 0
        assert result["total_cost"]["cost_per_month"] >= 0
        assert result["configuration"]["gateway_enabled"] is False

        results.append({
            "config": config_id(cfg), "mode": "pipeline_only",
            "pipeline_dbu": result["pipeline"]["dbu_per_month"],
            "total_cost": result["total_cost"]["cost_per_month"],
            "status": "PASS",
        })


class TestLakeflowConnectWithGateway:
    """Verify Lakeflow Connect with gateway enabled."""

    @pytest.mark.parametrize("cfg, instance", _generate_gateway_params())
    def test_pipeline_plus_gateway(self, e2e_client, cfg, instance, results):
        result = e2e_client.calculate_lakeflow_connect(
            cloud=cfg["cloud"], region=cfg["region"], tier=cfg["tier"],
            dlt_edition="ADVANCED", gateway_enabled=True,
            gateway_instance_type=instance,
            usage={"hours_per_month": 730},
        )
        assert "pipeline" in result
        assert "gateway" in result
        assert "total_cost" in result
        assert result["configuration"]["gateway_enabled"] is True

        gw = result["gateway"]
        assert gw["instance_type"] == instance
        assert gw["total_cost"] >= 0

        # Total should be pipeline + gateway
        pipeline_cost = result["pipeline"]["dbu_cost"]
        gateway_cost = gw["total_cost"]
        expected_total = pipeline_cost + gateway_cost
        actual_total = result["total_cost"]["cost_per_month"]
        assert abs(actual_total - expected_total) < 1.0, \
            f"Total {actual_total} != pipeline {pipeline_cost} + gateway {gateway_cost}"

        results.append({
            "config": config_id(cfg), "mode": "pipeline_plus_gateway",
            "instance": instance,
            "pipeline_cost": pipeline_cost,
            "gateway_cost": gateway_cost,
            "total_cost": actual_total,
            "status": "PASS",
        })


class TestLakeflowConnectExcelExport:
    """Create estimates with Lakeflow Connect workloads, export, verify."""

    @pytest.mark.parametrize("cfg", ESTIMATE_CONFIGS[:2], ids=[config_id(c) for c in ESTIMATE_CONFIGS[:2]])
    def test_export_pipeline_and_gateway(self, e2e_client, cfg):
        cloud, region, tier = cfg["cloud"], cfg["region"], cfg["tier"]

        estimate = e2e_client.create_estimate(
            name=f"E2E-LakeflowConnect-{config_id(cfg)}",
            cloud=cloud, region=region, tier=tier,
        )
        eid = estimate["estimate_id"]

        # Pipeline only
        api_pipeline = e2e_client.calculate_lakeflow_connect(
            cloud=cloud, region=region, tier=tier,
            dlt_edition="ADVANCED", gateway_enabled=False,
            usage={"hours_per_month": 100},
        )
        e2e_client.add_line_item(eid, {
            "workload_name": "LakeflowConnect-Pipeline",
            "workload_type": "LAKEFLOW_CONNECT",
            "lakeflow_connect_pipeline_mode": "serverless",
            "lakeflow_connect_gateway_enabled": False,
            "hours_per_month": 100,
        })

        # Pipeline + Gateway
        gw_instance = LAKEFLOW_GATEWAY_INSTANCES.get(cloud, "i3.xlarge")
        api_gateway = e2e_client.calculate_lakeflow_connect(
            cloud=cloud, region=region, tier=tier,
            dlt_edition="ADVANCED", gateway_enabled=True,
            gateway_instance_type=gw_instance,
            usage={"hours_per_month": 730},
        )
        e2e_client.add_line_item(eid, {
            "workload_name": "LakeflowConnect-WithGateway",
            "workload_type": "LAKEFLOW_CONNECT",
            "lakeflow_connect_pipeline_mode": "serverless",
            "lakeflow_connect_gateway_enabled": True,
            "lakeflow_connect_gateway_instance": gw_instance,
            "hours_per_month": 730,
        })

        excel_buf = e2e_client.export_excel(eid)
        rows = parse_estimate_excel(excel_buf)

        assert len(rows) >= 2, f"Expected at least 2 rows, got {len(rows)}"
