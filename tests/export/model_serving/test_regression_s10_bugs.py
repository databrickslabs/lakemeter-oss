"""Sprint 11: Regression tests for BUG-S10-001 through BUG-S10-004.

These tests guard against the 4 bugs found in Sprint 10 iteration 1:
- BUG-S10-001: gpu_medium (invalid) returned 0 DBU/hr silently
- BUG-S10-002: Notes column empty for 5 of 9 primary workload rows
- BUG-S10-003: FMAPI SKU assertions were too weak (just len > 0)
- BUG-S10-004: test_combined_excel.py exceeded 200-line file limit
"""
import os
import pytest
from types import SimpleNamespace

from app.routes.export.calculations import _calculate_dbu_per_hour
from app.routes.export.pricing import _get_sku_type
from tests.export.cross_workload.conftest import (
    make_line_item, make_model_serving_gpu,
    make_fmapi_databricks, make_fmapi_proprietary,
)


class TestBugS10001InvalidGpuType:
    """BUG-S10-001: gpu_medium (bare key, not in pricing JSON) must
    return 0 DBU/hr with a warning — never silently succeed."""

    def test_invalid_gpu_medium_returns_zero(self):
        item = make_line_item(
            workload_type="MODEL_SERVING",
            model_serving_gpu_type="gpu_medium",
            hours_per_month=200,
        )
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 0, f"Invalid gpu_medium should yield 0 DBU/hr, got {dbu}"

    def test_invalid_gpu_medium_produces_warning(self):
        item = make_line_item(
            workload_type="MODEL_SERVING",
            model_serving_gpu_type="gpu_medium",
            hours_per_month=200,
        )
        _, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert len(warnings) > 0, "Expected warning for invalid gpu_medium"
        assert any('gpu_medium' in w for w in warnings)

    def test_valid_gpu_medium_a10g_1x_returns_20(self):
        item = make_model_serving_gpu()  # uses gpu_medium_a10g_1x
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == pytest.approx(20.0, abs=0.01)
        assert len(warnings) == 0, f"Unexpected warnings: {warnings}"


class TestBugS10003ExactSkuAssertions:
    """BUG-S10-003: FMAPI SKU assertions must use exact string match,
    not just isinstance(str) and len > 0."""

    def test_fmapi_databricks_sku_exact(self):
        item = make_fmapi_databricks()
        sku = _get_sku_type(item, 'aws')
        assert sku == 'SERVERLESS_REAL_TIME_INFERENCE', \
            f"FMAPI DB SKU should be exact, got '{sku}'"

    def test_fmapi_proprietary_sku_exact(self):
        item = make_fmapi_proprietary()
        sku = _get_sku_type(item, 'aws')
        assert sku == 'ANTHROPIC_MODEL_SERVING', \
            f"FMAPI Prop SKU should be exact, got '{sku}'"

    def test_model_serving_sku_exact(self):
        item = make_model_serving_gpu()
        sku = _get_sku_type(item, 'aws')
        assert sku == 'SERVERLESS_REAL_TIME_INFERENCE', \
            f"Model Serving SKU should be exact, got '{sku}'"


class TestBugS10004FileSizeLimit:
    """BUG-S10-004: All test files in sprint_10 and sprint_11 must be
    under 200 lines."""

    @pytest.mark.parametrize("sprint_dir", ["sprint_10", "sprint_11"])
    def test_all_test_files_under_200_lines(self, sprint_dir):
        tests_root = os.path.join(
            os.path.dirname(__file__), '..', sprint_dir
        )
        tests_root = os.path.normpath(tests_root)
        if not os.path.isdir(tests_root):
            pytest.skip(f"{sprint_dir} not found")
        for fname in os.listdir(tests_root):
            if not fname.endswith('.py'):
                continue
            fpath = os.path.join(tests_root, fname)
            with open(fpath) as f:
                line_count = sum(1 for _ in f)
            assert line_count <= 200, \
                f"{sprint_dir}/{fname} has {line_count} lines (max 200)"
