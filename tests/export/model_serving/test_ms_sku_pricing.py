"""Test Model Serving SKU mapping and pricing lookups.

AC-13, AC-14: SKU = SERVERLESS_REAL_TIME_INFERENCE, $/DBU = $0.07.
AC-15, AC-16: Always serverless, no VM costs.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from app.routes.export.pricing import _get_sku_type, FALLBACK_DBU_PRICES
from app.routes.export.calculations import _is_serverless_workload
from .conftest import make_line_item


class TestModelServingSKU:
    """AC-13: SKU is SERVERLESS_REAL_TIME_INFERENCE for all GPU types."""

    @pytest.mark.parametrize("gpu_type", [
        "cpu", "gpu_small_t4", "gpu_medium_a10g_1x",
        "gpu_medium_a10g_4x", "gpu_xlarge_a100_80gb_8x",
    ])
    def test_sku_for_gpu_type(self, gpu_type):
        item = make_line_item(model_serving_gpu_type=gpu_type)
        sku = _get_sku_type(item)
        assert sku == 'SERVERLESS_REAL_TIME_INFERENCE'

    def test_sku_with_no_gpu_type(self):
        item = make_line_item(model_serving_gpu_type=None)
        sku = _get_sku_type(item)
        assert sku == 'SERVERLESS_REAL_TIME_INFERENCE'


class TestModelServingPricing:
    """AC-14: Fallback $/DBU for SERVERLESS_REAL_TIME_INFERENCE."""

    def test_fallback_price_exists(self):
        assert 'SERVERLESS_REAL_TIME_INFERENCE' in FALLBACK_DBU_PRICES

    def test_fallback_price_is_007(self):
        assert FALLBACK_DBU_PRICES['SERVERLESS_REAL_TIME_INFERENCE'] == 0.07


class TestModelServingServerless:
    """AC-15, AC-16: Model Serving is always serverless."""

    @pytest.mark.parametrize("gpu_type", [
        "cpu", "gpu_small_t4", "gpu_medium_a10g_1x",
        "gpu_xlarge_a100_80gb_8x", None,
    ])
    def test_is_serverless(self, gpu_type):
        item = make_line_item(model_serving_gpu_type=gpu_type)
        assert _is_serverless_workload(item) is True

    def test_serverless_regardless_of_serverless_enabled(self):
        """MODEL_SERVING is serverless even if serverless_enabled is False."""
        item = make_line_item(serverless_enabled=False)
        assert _is_serverless_workload(item) is True

    def test_not_confused_with_jobs(self):
        """Ensure JOBS is NOT serverless when serverless_enabled=False."""
        item = make_line_item(workload_type="JOBS", serverless_enabled=False)
        assert _is_serverless_workload(item) is False
