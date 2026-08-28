"""Regression tests for DBSQL VM pricing in Excel exports."""
import pytest

from app.routes.export.excel_builder import _lookup_dbsql_vm_costs
from tests.export.cross_workload.test_vm_pricing_export import (
    _PricingDB,
    _find_row,
    _load_workbook,
)
from tests.export.dbsql.conftest import make_line_item as make_dbsql_item


def test_dbsql_lookup_returns_rates_for_selected_payment_option():
    db = _PricingDB({
        ("i3.4xlarge", "reserved_3y", "no_upfront"): 0.31,
        ("i3.2xlarge", "reserved_3y", "no_upfront"): 0.16,
    })
    item = make_dbsql_item(
        dbsql_warehouse_type="CLASSIC",
        dbsql_warehouse_size="Small",
        dbsql_vm_pricing_tier="reserved_3y",
        dbsql_vm_payment_option="no_upfront",
    )
    notes = []

    driver_rate, worker_rate, worker_count = _lookup_dbsql_vm_costs(
        item, "aws", "us-east-1", {}, db, notes
    )

    assert driver_rate == pytest.approx(0.31)
    assert worker_rate == pytest.approx(0.16)
    assert worker_count == 4
    assert {call["payment_option"] for call in db.calls} == {"no_upfront"}
    assert notes == []


def test_dbsql_export_prefers_current_driver_worker_tiers_over_legacy_tier():
    db = _PricingDB({
        ("i3.4xlarge", "on_demand", "na"): 1.248,
        ("i3.2xlarge", "spot", "na"): 0.3072,
        ("i3.4xlarge", "reserved_1y", "all_upfront"): 0.75,
        ("i3.2xlarge", "reserved_1y", "all_upfront"): 0.20,
    })
    item = make_dbsql_item(
        workload_name="DBSQL UI Parity",
        dbsql_warehouse_type="CLASSIC",
        dbsql_warehouse_size="Small",
        hours_per_month=11,
        driver_pricing_tier="on_demand",
        driver_payment_option="no_upfront",
        worker_pricing_tier="spot",
        worker_payment_option="NA",
        # Simulate an estimate created before separate driver/worker controls.
        dbsql_vm_pricing_tier="reserved_1y",
        dbsql_vm_payment_option="all_upfront",
    )

    workbook = _load_workbook(item, "aws", "us-east-1", db)
    sheet = workbook.active
    row = _find_row(sheet, "DBSQL UI Parity")

    assert sheet.cell(row=row, column=10).value == "On-Demand"
    assert sheet.cell(row=row, column=11).value == "Spot"
    assert sheet.cell(row=row, column=27).value == pytest.approx(1.248)
    assert sheet.cell(row=row, column=28).value == pytest.approx(0.3072)
    assert sheet.cell(row=row, column=31).value == pytest.approx(27.2448)
    assert {call["pricing_tier"] for call in db.calls} == {"on_demand", "spot"}
    workbook.close()


def test_dbsql_export_defaults_reserved_worker_na_to_aws_no_upfront():
    db = _PricingDB({
        ("i3.4xlarge", "reserved_1y", "no_upfront"): 0.794977,
        ("i3.2xlarge", "reserved_1y", "no_upfront"): 0.405854,
    })
    item = make_dbsql_item(
        workload_name="DBSQL Reserved UI Parity",
        dbsql_warehouse_type="CLASSIC",
        dbsql_warehouse_size="Small",
        hours_per_month=11,
        driver_pricing_tier="reserved_1y",
        driver_payment_option="no_upfront",
        worker_pricing_tier="reserved_1y",
        # Reproduces the stale value saved while the UI displayed No Upfront.
        worker_payment_option="NA",
    )

    workbook = _load_workbook(item, "aws", "us-east-1", db)
    sheet = workbook.active
    row = _find_row(sheet, "DBSQL Reserved UI Parity")

    assert sheet.cell(row=row, column=10).value == "1-Year Reserved"
    assert sheet.cell(row=row, column=11).value == "1-Year Reserved"
    assert sheet.cell(row=row, column=27).value == pytest.approx(0.794977)
    assert sheet.cell(row=row, column=28).value == pytest.approx(0.405854)
    assert sheet.cell(row=row, column=31).value == pytest.approx(26.602323)
    assert {call["payment_option"] for call in db.calls} == {"no_upfront"}
    workbook.close()
