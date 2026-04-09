"""Sprint 11: Model Serving validation in combined estimate context.

Verifies that Model Serving GPU items produce correct costs when
generated alongside all other 8 workload types in a single Excel export.
Also parametrizes all 14 GPU types across 3 clouds for rate verification.
"""
import json
import os

import pytest

from app.routes.export.calculations import _calculate_dbu_per_hour
from app.routes.export.pricing import _get_sku_type
from tests.export.cross_workload.conftest import make_line_item, make_model_serving_gpu
from tests.export.cross_workload.excel_helpers import (
    generate_xlsx, find_row_by_name,
    COL_SKU, COL_DBU_HR, COL_DBUS_MO, COL_DRIVER_VM_HR,
    COL_WORKER_VM_HR, COL_MODE,
)

# Load GPU rates from pricing JSON
_PRICING_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', 'backend', 'static', 'pricing'
)
_RATES_PATH = os.path.join(_PRICING_DIR, 'model-serving-rates.json')
with open(_RATES_PATH) as f:
    _MS_RATES = json.load(f)

# Build parametrize list: (cloud, gpu_type, expected_dbu_rate)
_GPU_PARAMS = []
for key, info in _MS_RATES.items():
    cloud, gpu_type = key.split(':', 1)
    _GPU_PARAMS.append((cloud, gpu_type, info['dbu_rate']))


@pytest.fixture(scope="module")
def combined_wb():
    return generate_xlsx()


@pytest.fixture(scope="module")
def ws(combined_wb):
    return combined_wb.active


class TestModelServingInCombinedExcel:
    """AC-7 through AC-11: Model Serving row in combined Excel export."""

    def test_model_serving_row_exists(self, ws):
        row = find_row_by_name(ws, 'Model Serving GPU')
        assert row is not None, "Model Serving row missing from combined Excel"

    def test_sku_is_serverless_real_time(self, ws):
        row = find_row_by_name(ws, 'Model Serving GPU')
        sku = ws.cell(row=row, column=COL_SKU).value
        assert sku == 'SERVERLESS_REAL_TIME_INFERENCE'

    def test_dbu_hr_is_20(self, ws):
        row = find_row_by_name(ws, 'Model Serving GPU')
        val = ws.cell(row=row, column=COL_DBU_HR).value
        assert val == pytest.approx(20.0, abs=0.01), \
            f"Expected 20.0 DBU/hr for A10G 1x, got {val}"

    def test_dbus_mo_is_formula(self, ws):
        row = find_row_by_name(ws, 'Model Serving GPU')
        cell = ws.cell(row=row, column=COL_DBUS_MO)
        val = cell.value
        assert isinstance(val, str) and val.startswith('='), \
            f"DBUs/Mo should be a formula, got {val}"

    def test_no_vm_costs(self, ws):
        row = find_row_by_name(ws, 'Model Serving GPU')
        driver = ws.cell(row=row, column=COL_DRIVER_VM_HR).value
        worker = ws.cell(row=row, column=COL_WORKER_VM_HR).value
        assert driver == 0 or driver == '-', \
            f"Driver VM should be 0, got {driver}"
        assert worker == 0 or worker == '-', \
            f"Worker VM should be 0, got {worker}"

    def test_mode_is_serverless(self, ws):
        row = find_row_by_name(ws, 'Model Serving GPU')
        assert ws.cell(row=row, column=COL_MODE).value == 'Serverless'


class TestAllGpuRates:
    """AC-12: All 14 GPU types across 3 clouds produce correct DBU/hr."""

    @pytest.mark.parametrize("cloud,gpu_type,expected_rate", _GPU_PARAMS,
                             ids=[f"{c}:{g}" for c, g, _ in _GPU_PARAMS])
    def test_gpu_dbu_rate(self, cloud, gpu_type, expected_rate):
        item = make_line_item(
            workload_type="MODEL_SERVING",
            model_serving_gpu_type=gpu_type,
            hours_per_month=100,
        )
        dbu, warnings = _calculate_dbu_per_hour(item, cloud)
        assert dbu == pytest.approx(expected_rate, abs=0.01), \
            f"{cloud}:{gpu_type} expected {expected_rate}, got {dbu}"
        assert len(warnings) == 0, \
            f"{cloud}:{gpu_type} had warnings: {warnings}"

    @pytest.mark.parametrize("cloud,gpu_type,expected_rate", _GPU_PARAMS,
                             ids=[f"{c}:{g}" for c, g, _ in _GPU_PARAMS])
    def test_gpu_sku_always_serverless_rti(self, cloud, gpu_type,
                                           expected_rate):
        item = make_line_item(
            workload_type="MODEL_SERVING",
            model_serving_gpu_type=gpu_type,
        )
        assert _get_sku_type(item, cloud) == 'SERVERLESS_REAL_TIME_INFERENCE'
