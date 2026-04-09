"""E2E tests: All-Purpose Classic — API calculation vs Excel export verification.

Tests every combination of:
  - 6 cloud/region configs (3 clouds x 2 regions)
  - hours_per_day+days vs hours_per_month usage
  - photon on/off
  - 3 instance combos per cloud
  = ~72 test cases per run

Run: pytest tests/e2e/export/test_allpurpose_classic.py -v --timeout=600
"""
import pytest
from tests.e2e.helpers.test_data import (
    ESTIMATE_CONFIGS, INSTANCE_TYPES,
    USAGE_HOURLY, USAGE_HOURS_PER_DAY, config_id,
)
from tests.e2e.helpers.assertions import assert_costs_match, save_test_results
from tests.e2e.helpers.excel_parser import parse_estimate_excel


# ── Parametrize: all config combos ────────────────────────────────────────

def _generate_allpurpose_classic_params():
    """Generate all (config, driver, worker, photon, usage_label, usage) combos."""
    params = []
    for cfg in ESTIMATE_CONFIGS:
        cloud = cfg["cloud"]
        instances = INSTANCE_TYPES[cloud]
        for i, (driver, worker) in enumerate(zip(instances["driver"], instances["worker"])):
            for photon in [False, True]:
                for usage_label, usage in [("hours_per_day", USAGE_HOURS_PER_DAY),
                                           ("hourly", USAGE_HOURLY)]:
                    test_id = f"{config_id(cfg)}-inst{i}-photon{photon}-{usage_label}"
                    params.append(pytest.param(
                        cfg, driver, worker, photon, usage_label, usage,
                        id=test_id,
                    ))
    return params


@pytest.fixture(scope="module")
def allpurpose_classic_results():
    """Collect results across all tests in this module."""
    results = []
    yield results
    save_test_results(results, "test_results/e2e_allpurpose_classic.json")


class TestAllPurposeClassicCalculation:
    """Verify All-Purpose Classic API calculation returns valid results."""

    @pytest.mark.parametrize(
        "cfg, driver, worker, photon, usage_label, usage",
        _generate_allpurpose_classic_params(),
    )
    def test_calculation_succeeds(self, e2e_client, cfg, driver, worker,
                                   photon, usage_label, usage, allpurpose_classic_results):
        result = e2e_client.calculate_allpurpose_classic(
            cloud=cfg["cloud"], region=cfg["region"], tier=cfg["tier"],
            driver=driver, worker=worker, num_workers=4,
            photon=photon, usage=usage,
        )
        # Verify structure
        assert "dbu_calculation" in result
        assert "vm_costs" in result
        assert "total_cost" in result
        assert result["dbu_calculation"]["dbu_per_hour"] > 0
        assert result["dbu_calculation"]["dbu_per_month"] > 0
        assert result["dbu_calculation"]["dbu_price"] > 0
        assert result["total_cost"]["cost_per_month"] > 0

        allpurpose_classic_results.append({
            "config": config_id(cfg), "driver": driver, "worker": worker,
            "photon": photon, "usage": usage_label,
            "dbu_per_hour": result["dbu_calculation"]["dbu_per_hour"],
            "dbu_per_month": result["dbu_calculation"]["dbu_per_month"],
            "total_cost": result["total_cost"]["cost_per_month"],
            "status": "PASS",
        })


class TestAllPurposeClassicExcelExport:
    """Create estimates with All-Purpose Classic workloads, export to Excel,
    verify API numbers match Excel numbers exactly."""

    @pytest.mark.parametrize("cfg", ESTIMATE_CONFIGS, ids=[config_id(c) for c in ESTIMATE_CONFIGS])
    def test_export_run_based(self, e2e_client, cfg):
        """Test run-based All-Purpose Classic: create estimate, add line items, export, verify."""
        cloud, region, tier = cfg["cloud"], cfg["region"], cfg["tier"]
        instances = INSTANCE_TYPES[cloud]

        estimate = e2e_client.create_estimate(
            name=f"E2E-AP-Classic-HoursPerDay-{config_id(cfg)}",
            cloud=cloud, region=region, tier=tier,
        )
        eid = estimate["estimate_id"]

        calc_results = []
        for i, (driver, worker) in enumerate(zip(instances["driver"], instances["worker"])):
            for photon in [False, True]:
                api_result = e2e_client.calculate_allpurpose_classic(
                    cloud=cloud, region=region, tier=tier,
                    driver=driver, worker=worker, num_workers=4,
                    photon=photon, usage=USAGE_HOURS_PER_DAY,
                )
                calc_results.append(api_result)

                e2e_client.add_line_item(eid, {
                    "workload_name": f"AP-{driver}-photon{photon}",
                    "workload_type": "ALL_PURPOSE",
                    "serverless_enabled": False,
                    "driver_node_type": driver,
                    "worker_node_type": worker,
                    "num_workers": 4,
                    "photon_enabled": photon,
                    "hours_per_month": int(USAGE_HOURS_PER_DAY["hours_per_day"] * USAGE_HOURS_PER_DAY["days_per_month"]),
                    "days_per_month": USAGE_HOURS_PER_DAY["days_per_month"],
                })

        excel_bytes = e2e_client.export_excel(eid)
        parsed = parse_estimate_excel(excel_bytes)

        assert len(parsed["rows"]) == len(calc_results), (
            f"Expected {len(calc_results)} rows, got {len(parsed['rows'])}"
        )
        for row, api_result in zip(parsed["rows"], calc_results):
            assert_costs_match(api_result, row, workload_label=row.name)

        e2e_client.delete_estimate(eid)

    @pytest.mark.parametrize("cfg", ESTIMATE_CONFIGS, ids=[config_id(c) for c in ESTIMATE_CONFIGS])
    def test_export_hourly(self, e2e_client, cfg):
        """Test hourly All-Purpose Classic: create estimate, add line items, export, verify."""
        cloud, region, tier = cfg["cloud"], cfg["region"], cfg["tier"]
        instances = INSTANCE_TYPES[cloud]

        estimate = e2e_client.create_estimate(
            name=f"E2E-AP-Classic-Hourly-{config_id(cfg)}",
            cloud=cloud, region=region, tier=tier,
        )
        eid = estimate["estimate_id"]

        calc_results = []
        for i, (driver, worker) in enumerate(zip(instances["driver"], instances["worker"])):
            api_result = e2e_client.calculate_allpurpose_classic(
                cloud=cloud, region=region, tier=tier,
                driver=driver, worker=worker, num_workers=4,
                photon=False, usage=USAGE_HOURLY,
            )
            calc_results.append(api_result)

            e2e_client.add_line_item(eid, {
                "workload_name": f"AP-Hourly-{driver}",
                "workload_type": "ALL_PURPOSE",
                "serverless_enabled": False,
                "driver_node_type": driver,
                "worker_node_type": worker,
                "num_workers": 4,
                "photon_enabled": False,
                "hours_per_month": USAGE_HOURLY["hours_per_month"],
            })

        excel_bytes = e2e_client.export_excel(eid)
        parsed = parse_estimate_excel(excel_bytes)

        assert len(parsed["rows"]) == len(calc_results)
        for row, api_result in zip(parsed["rows"], calc_results):
            assert_costs_match(api_result, row, workload_label=row.name)

        e2e_client.delete_estimate(eid)
