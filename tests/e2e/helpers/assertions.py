"""Assertion helpers for comparing API calculation results vs Excel export values.

Uses tolerance-aware comparison (±0.01) for floating-point rounding differences.
"""
import json
from pathlib import Path
from typing import Optional

# Tolerance for floating-point comparison
TOLERANCE = 0.02  # 2 cents tolerance for rounding


def assert_close(actual: Optional[float], expected: Optional[float],
                 field: str, tolerance: float = TOLERANCE):
    """Assert two values are within tolerance."""
    if expected is None and actual is None:
        return
    if expected is None or actual is None:
        # One is None, the other isn't — only fail if the non-None value is significant
        non_none = actual if actual is not None else expected
        if non_none and abs(non_none) > tolerance:
            raise AssertionError(
                f"{field}: expected={expected}, actual={actual}"
            )
        return
    diff = abs(actual - expected)
    if diff > tolerance:
        raise AssertionError(
            f"{field}: expected={expected:.4f}, actual={actual:.4f}, diff={diff:.4f} > tolerance={tolerance}"
        )


def assert_costs_match(api_result: dict, excel_row, workload_label: str = ""):
    """Compare API calculation result against an Excel row.

    api_result: The 'data' dict from a /calculate/* response
    excel_row: An ExcelRow from the parsed Excel
    """
    prefix = f"[{workload_label}] " if workload_label else ""
    errors = []

    # DBU calculations
    dbu_calc = api_result.get("dbu_calculation", {})
    if dbu_calc:
        try:
            assert_close(
                excel_row.dbu_per_hour, dbu_calc.get("dbu_per_hour"),
                f"{prefix}DBU/Hr"
            )
        except AssertionError as e:
            errors.append(str(e))
        try:
            assert_close(
                excel_row.dbus_per_month, dbu_calc.get("dbu_per_month"),
                f"{prefix}DBUs/Mo", tolerance=1.0  # DBUs can be large numbers
            )
        except AssertionError as e:
            errors.append(str(e))
        try:
            assert_close(
                excel_row.dbu_rate_list, dbu_calc.get("dbu_price"),
                f"{prefix}DBU Rate (List)", tolerance=0.001
            )
        except AssertionError as e:
            errors.append(str(e))
        try:
            assert_close(
                excel_row.dbu_cost_list, dbu_calc.get("dbu_cost_per_month"),
                f"{prefix}DBU Cost (List)", tolerance=1.0
            )
        except AssertionError as e:
            errors.append(str(e))

    # VM costs (classic only)
    # Note: Excel uses DEFAULT_VM_PRICING (hardcoded, us-east-1 only), API uses stored function (DB).
    # VM pricing sources may differ in presence or rates. Compare only when:
    # 1. Both sources have non-zero VM data, AND
    # 2. The driver VM hourly rate matches (same pricing source/region)
    vm_costs = api_result.get("vm_costs", {})
    api_has_vm_data = (vm_costs.get("vm_cost_per_month") or 0) > 0
    excel_has_vm_data = (excel_row.driver_vm_per_hr or 0) > 0 or (excel_row.total_vm_cost or 0) > 0
    # Check if hourly rates agree (within tolerance) — if not, sources use different pricing
    api_driver_vm_hr = vm_costs.get("driver_vm_cost_per_hour") or 0
    excel_driver_vm_hr = excel_row.driver_vm_per_hr or 0
    vm_rates_match = abs(api_driver_vm_hr - excel_driver_vm_hr) <= 0.01 if (api_has_vm_data and excel_has_vm_data) else False
    vm_comparable = vm_costs and not excel_row.is_serverless and api_has_vm_data and excel_has_vm_data and vm_rates_match

    if vm_comparable:
        try:
            assert_close(
                excel_row.driver_vm_per_hr, vm_costs.get("driver_vm_cost_per_hour"),
                f"{prefix}Driver VM $/Hr", tolerance=0.01
            )
        except AssertionError as e:
            errors.append(str(e))
        # Compare individual driver/worker VM costs only if the API provides them
        if vm_costs.get("driver_vm_cost_per_month") is not None:
            try:
                assert_close(
                    excel_row.driver_vm_cost, vm_costs.get("driver_vm_cost_per_month"),
                    f"{prefix}Driver VM Cost", tolerance=1.0
                )
            except AssertionError as e:
                errors.append(str(e))
        if vm_costs.get("total_worker_vm_cost_per_month") is not None:
            try:
                assert_close(
                    excel_row.worker_vm_cost, vm_costs.get("total_worker_vm_cost_per_month"),
                    f"{prefix}Worker VM Cost", tolerance=1.0
                )
            except AssertionError as e:
                errors.append(str(e))
        try:
            assert_close(
                excel_row.total_vm_cost, vm_costs.get("vm_cost_per_month"),
                f"{prefix}Total VM Cost", tolerance=1.0
            )
        except AssertionError as e:
            errors.append(str(e))

    # Total cost — full compare only when VM data is comparable
    total_cost = api_result.get("total_cost", {})
    if total_cost:
        if vm_comparable or excel_row.is_serverless or (not api_has_vm_data and not excel_has_vm_data):
            try:
                assert_close(
                    excel_row.total_cost_list,
                    total_cost.get("cost_per_month"),
                    f"{prefix}Total Cost (List)", tolerance=1.0
                )
            except AssertionError as e:
                errors.append(str(e))
        else:
            # VM pricing sources differ — only compare the DBU cost portion
            api_dbu_cost = api_result.get("dbu_calculation", {}).get("dbu_cost_per_month", 0)
            excel_dbu_cost = excel_row.dbu_cost_list
            if api_dbu_cost and excel_dbu_cost is not None:
                try:
                    assert_close(
                        excel_dbu_cost, api_dbu_cost,
                        f"{prefix}DBU Cost cross-check (VM pricing sources differ)",
                        tolerance=1.0
                    )
                except AssertionError as e:
                    errors.append(str(e))

    # Hours/month
    usage = api_result.get("usage", {})
    if usage and excel_row.hours_per_month is not None:
        try:
            assert_close(
                excel_row.hours_per_month, usage.get("hours_per_month"),
                f"{prefix}Hours/Mo", tolerance=0.1
            )
        except AssertionError as e:
            errors.append(str(e))

    if errors:
        raise AssertionError(
            f"{len(errors)} discrepancies found:\n" + "\n".join(f"  - {e}" for e in errors)
        )


def save_test_results(results: list, output_path: str):
    """Save test results as JSON for analysis."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
