"""E2E tests: DLT Classic — API calculation vs Excel export verification.

Tests every combination of:
  - 6 cloud/region configs (3 clouds x 2 regions)
  - 3 DLT editions (CORE, PRO, ADVANCED)
  - first instance pair per cloud (for brevity)
  - photon on/off
  - run-based vs hourly usage
  = ~72 test cases per run

Run: pytest tests/e2e/export/test_dlt_classic.py -v --timeout=600
"""
import pytest
from tests.e2e.helpers.test_data import (
    ESTIMATE_CONFIGS, INSTANCE_TYPES, DLT_EDITIONS,
    USAGE_RUN_BASED, USAGE_HOURLY, config_id,
)
from tests.e2e.helpers.assertions import assert_costs_match, save_test_results
from tests.e2e.helpers.excel_parser import parse_estimate_excel


# ── Parametrize: all config combos ────────────────────────────────────────

def _generate_dlt_classic_params():
    """Generate all (config, edition, driver, worker, photon, usage_label, usage) combos."""
    params = []
    for cfg in ESTIMATE_CONFIGS:
        cloud = cfg["cloud"]
        instances = INSTANCE_TYPES[cloud]
        # Use first instance pair per cloud for brevity
        driver = instances["driver"][0]
        worker = instances["worker"][0]
        for edition in DLT_EDITIONS:
            for photon in [False, True]:
                for usage_label, usage in [("run_based", USAGE_RUN_BASED), ("hourly", USAGE_HOURLY)]:
                    test_id = f"{config_id(cfg)}-{edition}-photon{photon}-{usage_label}"
                    params.append(pytest.param(
                        cfg, edition, driver, worker, photon, usage_label, usage,
                        id=test_id,
                    ))
    return params


@pytest.fixture(scope="module")
def dlt_classic_results():
    """Collect results across all tests in this module."""
    results = []
    yield results
    save_test_results(results, "test_results/e2e_dlt_classic.json")


class TestDLTClassicCalculation:
    """Verify DLT Classic API calculation returns valid results."""

    @pytest.mark.parametrize(
        "cfg, edition, driver, worker, photon, usage_label, usage",
        _generate_dlt_classic_params(),
    )
    def test_calculation_succeeds(self, e2e_client, cfg, edition, driver, worker,
                                   photon, usage_label, usage, dlt_classic_results):
        result = e2e_client.calculate_dlt_classic(
            cloud=cfg["cloud"], region=cfg["region"], tier=cfg["tier"],
            edition=edition, driver=driver, worker=worker, num_workers=4,
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

        dlt_classic_results.append({
            "config": config_id(cfg), "edition": edition,
            "driver": driver, "worker": worker,
            "photon": photon, "usage": usage_label,
            "dbu_per_hour": result["dbu_calculation"]["dbu_per_hour"],
            "dbu_per_month": result["dbu_calculation"]["dbu_per_month"],
            "total_cost": result["total_cost"]["cost_per_month"],
            "status": "PASS",
        })


class TestDLTClassicExcelExport:
    """Create estimates with DLT Classic workloads, export to Excel,
    verify API numbers match Excel numbers exactly."""

    @pytest.mark.parametrize("cfg", ESTIMATE_CONFIGS, ids=[config_id(c) for c in ESTIMATE_CONFIGS])
    def test_export_run_based(self, e2e_client, cfg):
        """Test run-based DLT Classic: create estimate, add line items, export, verify."""
        cloud, region, tier = cfg["cloud"], cfg["region"], cfg["tier"]
        instances = INSTANCE_TYPES[cloud]
        driver = instances["driver"][0]
        worker = instances["worker"][0]

        # Create estimate
        estimate = e2e_client.create_estimate(
            name=f"E2E-DLT-Classic-RunBased-{config_id(cfg)}",
            cloud=cloud, region=region, tier=tier,
        )
        eid = estimate["estimate_id"]

        # Add line items (one per edition x photon)
        calc_results = []
        for edition in DLT_EDITIONS:
            for photon in [False, True]:
                # Calculate via API
                api_result = e2e_client.calculate_dlt_classic(
                    cloud=cloud, region=region, tier=tier,
                    edition=edition, driver=driver, worker=worker, num_workers=4,
                    photon=photon, usage=USAGE_RUN_BASED,
                )
                calc_results.append(api_result)

                # Add line item
                e2e_client.add_line_item(eid, {
                    "workload_name": f"DLT-{edition}-photon{photon}",
                    "workload_type": "DLT",
                    "serverless_enabled": False,
                    "dlt_edition": edition,
                    "driver_node_type": driver,
                    "worker_node_type": worker,
                    "num_workers": 4,
                    "photon_enabled": photon,
                    "runs_per_day": USAGE_RUN_BASED["runs_per_day"],
                    "avg_runtime_minutes": USAGE_RUN_BASED["avg_runtime_minutes"],
                    "days_per_month": USAGE_RUN_BASED["days_per_month"],
                })

        # Export to Excel
        excel_bytes = e2e_client.export_excel(eid)
        parsed = parse_estimate_excel(excel_bytes)

        # Verify each row matches its API result
        assert len(parsed["rows"]) == len(calc_results), (
            f"Expected {len(calc_results)} rows, got {len(parsed['rows'])}"
        )
        for row, api_result in zip(parsed["rows"], calc_results):
            assert_costs_match(api_result, row, workload_label=row.name)

        # Cleanup
        e2e_client.delete_estimate(eid)

    @pytest.mark.parametrize("cfg", ESTIMATE_CONFIGS, ids=[config_id(c) for c in ESTIMATE_CONFIGS])
    def test_export_hourly(self, e2e_client, cfg):
        """Test hourly DLT Classic: create estimate, add line items, export, verify."""
        cloud, region, tier = cfg["cloud"], cfg["region"], cfg["tier"]
        instances = INSTANCE_TYPES[cloud]
        driver = instances["driver"][0]
        worker = instances["worker"][0]

        estimate = e2e_client.create_estimate(
            name=f"E2E-DLT-Classic-Hourly-{config_id(cfg)}",
            cloud=cloud, region=region, tier=tier,
        )
        eid = estimate["estimate_id"]

        calc_results = []
        for edition in DLT_EDITIONS:
            api_result = e2e_client.calculate_dlt_classic(
                cloud=cloud, region=region, tier=tier,
                edition=edition, driver=driver, worker=worker, num_workers=4,
                photon=False, usage=USAGE_HOURLY,
            )
            calc_results.append(api_result)

            e2e_client.add_line_item(eid, {
                "workload_name": f"DLT-Hourly-{edition}",
                "workload_type": "DLT",
                "serverless_enabled": False,
                "dlt_edition": edition,
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
