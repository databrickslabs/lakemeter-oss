"""Sprint 3: DLT Excel Export — display names, config details, full pipeline, edition matrix."""
import os, sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
from tests.export.dlt.conftest import make_line_item
from app.routes.export import (
    _get_sku_type, _calculate_dbu_per_hour, _calculate_hours_per_month,
    _is_serverless_workload, _get_dbu_price,
    _get_workload_display_name, _get_workload_config_details,
)


class TestDLTDisplayFormatting:
    """Verify DLT display name and config details for Excel."""

    def test_display_name(self):
        assert _get_workload_display_name("DLT") == "Lakeflow Spark Declarative Pipelines"

    def test_config_details_core_no_photon(self):
        """Config shows 'Edition: CORE' without Photon."""
        item = make_line_item(dlt_edition="CORE", photon_enabled=False)
        details = _get_workload_config_details(item)
        assert "Edition: CORE" in details
        assert "Photon" not in details

    def test_config_details_advanced_photon(self):
        """Config shows 'Edition: ADVANCED | Photon'."""
        item = make_line_item(dlt_edition="ADVANCED", photon_enabled=True)
        details = _get_workload_config_details(item)
        assert "Edition: ADVANCED" in details
        assert "Photon" in details

    def test_config_details_serverless(self):
        """Config shows 'Mode: Standard' or 'Mode: Performance' for serverless."""
        item = make_line_item(
            dlt_edition="PRO", serverless_enabled=True,
            serverless_mode="performance",
        )
        details = _get_workload_config_details(item)
        assert "Mode: Performance" in details

    def test_config_details_serverless_standard(self):
        item = make_line_item(
            dlt_edition="CORE", serverless_enabled=True,
            serverless_mode="standard",
        )
        details = _get_workload_config_details(item)
        assert "Mode: Standard" in details


class TestDLTFullCalculationPipeline:
    """Test the full export calculation pipeline for DLT workloads."""

    def test_core_classic_full_pipeline(self):
        item = make_line_item(
            dlt_edition="CORE",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            photon_enabled=False,
            serverless_enabled=False,
            hours_per_month=730,
        )

        hours = _calculate_hours_per_month(item)
        assert hours == pytest.approx(730.0)

        dbu_hr, warnings = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(5.0)
        assert len(warnings) == 0

        sku = _get_sku_type(item, "aws")
        assert sku == "DLT_CORE_COMPUTE"

        price, found = _get_dbu_price("aws", "us-east-1", "PREMIUM", sku)
        assert price > 0

        monthly_dbus = dbu_hr * hours
        assert monthly_dbus == pytest.approx(3650.0)

        dbu_cost = monthly_dbus * price
        assert dbu_cost > 0

        is_sl = _is_serverless_workload(item)
        assert is_sl is False

    def test_serverless_performance_full_pipeline(self):
        """DLT Serverless Performance: full pipeline."""
        item = make_line_item(
            dlt_edition="ADVANCED",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            serverless_enabled=True,
            serverless_mode="performance",
            hours_per_month=730,
        )

        hours = _calculate_hours_per_month(item)
        assert hours == pytest.approx(730.0)

        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(29.0)

        sku = _get_sku_type(item, "aws")
        assert sku == "JOBS_SERVERLESS_COMPUTE"

        price, _ = _get_dbu_price("aws", "us-east-1", "PREMIUM", sku)
        assert price > 0

        monthly_dbus = dbu_hr * hours
        assert monthly_dbus == pytest.approx(21170.0)

        is_sl = _is_serverless_workload(item)
        assert is_sl is True

    def test_run_based_dlt_pipeline(self):
        """DLT with run-based hours: 24 runs x 60 min x 30 days = 720 hrs."""
        item = make_line_item(
            dlt_edition="PRO",
            driver_node_type="m5.xlarge",
            worker_node_type="r5.xlarge",
            num_workers=4,
            photon_enabled=True,
            serverless_enabled=False,
            runs_per_day=24,
            avg_runtime_minutes=60,
            days_per_month=30,
        )

        hours = _calculate_hours_per_month(item)
        assert hours == pytest.approx(720.0)

        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        # m5.xlarge=0.69, r5.xlarge=0.9: (0.69 + 0.9*4) * 2.9 = 12.441
        expected_dbu_hr = (0.69 + 0.9 * 4) * 2.9
        assert dbu_hr == pytest.approx(expected_dbu_hr)

        monthly_dbus = dbu_hr * hours
        assert monthly_dbus == pytest.approx(expected_dbu_hr * 720)


class TestDLTEditionModeMatrix:
    """Comprehensive matrix: 3 editions x 4 modes (classic, photon, sl-std, sl-perf)."""

    @pytest.mark.parametrize("edition,photon,serverless,mode,expected_mult", [
        # Classic Standard
        ("CORE", False, False, "standard", 1.0),
        ("PRO", False, False, "standard", 1.0),
        ("ADVANCED", False, False, "standard", 1.0),
        # Classic Photon (2.9x for AWS)
        ("CORE", True, False, "standard", 2.9),
        ("PRO", True, False, "standard", 2.9),
        ("ADVANCED", True, False, "standard", 2.9),
        # Serverless Standard (photon built-in 2.9x, mode 1x)
        ("CORE", False, True, "standard", 2.9),
        ("PRO", False, True, "standard", 2.9),
        ("ADVANCED", False, True, "standard", 2.9),
        # Serverless Performance (photon built-in 2.9x, mode 2x = 5.8x total)
        ("CORE", False, True, "performance", 5.8),
        ("PRO", False, True, "performance", 5.8),
        ("ADVANCED", False, True, "performance", 5.8),
    ])
    def test_dbu_multiplier(self, edition, photon, serverless, mode, expected_mult):
        """Verify total DBU multiplier for each edition/mode combination."""
        item = make_line_item(
            dlt_edition=edition,
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            photon_enabled=photon,
            serverless_enabled=serverless,
            serverless_mode=mode,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        base_dbu = 5.0  # driver(1.0) + 4*worker(1.0)
        assert dbu_hr == pytest.approx(base_dbu * expected_mult), \
            f"{edition} photon={photon} sl={serverless} mode={mode}: " \
            f"expected {base_dbu * expected_mult}, got {dbu_hr}"
