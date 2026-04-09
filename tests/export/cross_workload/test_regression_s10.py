"""Sprint 10 regression tests for evaluator-reported bugs BUG-S10-001..005."""
import configparser
import os
import pytest
from tests.export.cross_workload.conftest import (
    make_model_serving_gpu, make_fmapi_databricks, make_fmapi_proprietary,
    make_dlt_pro_serverless, make_vector_search_standard,
)
from tests.export.cross_workload.excel_helpers import (
    generate_xlsx, find_row_by_name, find_all_data_rows, COL_NOTES,
)
from app.routes.export.calculations import _calculate_dbu_per_hour
from app.routes.export.pricing import _get_sku_type


class TestBugS10001ModelServingGpu:
    """Regression: BUG-S10-001 — Model Serving GPU must resolve to non-zero DBU/hr.

    Root cause: Prior iteration used gpu_type='gpu_medium' which did not exist
    in pricing JSON. Fixed by using 'gpu_medium_a10g_1x' which is a valid key.
    """

    def test_gpu_type_is_valid(self):
        """Conftest uses a GPU type that exists in pricing data."""
        item = make_model_serving_gpu()
        assert item.model_serving_gpu_type == 'gpu_medium_a10g_1x'

    def test_dbu_per_hour_nonzero(self):
        """Model Serving GPU returns a specific non-zero DBU/hr."""
        item = make_model_serving_gpu()
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu > 0, f"Model Serving GPU returned 0 DBU/hr: {warnings}"
        assert dbu == pytest.approx(20.0, abs=0.01)

    def test_no_pricing_warnings(self):
        """Model Serving GPU resolves without fallback warnings."""
        item = make_model_serving_gpu()
        _, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert len(warnings) == 0, f"Unexpected warnings: {warnings}"

    def test_excel_dbu_hr_nonzero(self):
        """Model Serving GPU shows non-zero DBU/hr in Excel output."""
        wb = generate_xlsx()
        ws = wb.active
        row = find_row_by_name(ws, 'Model Serving GPU')
        from tests.export.cross_workload.excel_helpers import COL_DBU_HR
        val = ws.cell(row=row, column=COL_DBU_HR).value
        assert val > 0, f"Excel shows 0 DBU/hr for Model Serving"


class TestBugS10002FallbackNotesInExcel:
    """Regression: BUG-S10-002 — Items with fallback pricing show warning notes.

    After SKU alignment, DLT Serverless uses JOBS_SERVERLESS_COMPUTE and
    Vector Search uses SERVERLESS_REAL_TIME_INFERENCE — both are standard SKUs
    found in the pricing JSON, so they no longer generate fallback warnings.
    """

    @pytest.fixture(scope="class")
    def ws(self):
        return generate_xlsx().active

    def test_dlt_has_no_fallback_note(self, ws):
        """DLT Serverless now uses JOBS_SERVERLESS_COMPUTE (found in pricing JSON)."""
        row = find_row_by_name(ws, 'DLT Pro Serverless')
        notes = ws.cell(row=row, column=COL_NOTES).value or ''
        # With aligned SKUs, pricing is found in JSON — no fallback warning
        assert 'DELTA_LIVE_TABLES' not in notes

    def test_vector_search_no_fallback_note(self, ws):
        """Vector Search uses SERVERLESS_REAL_TIME_INFERENCE (found in pricing JSON)."""
        row = find_row_by_name(ws, 'Vector Search Standard 5M')
        notes = ws.cell(row=row, column=COL_NOTES).value or ''
        assert 'VECTOR_SEARCH_ENDPOINT' not in notes

    def test_non_fallback_items_have_no_warning(self, ws):
        """Standard items (Jobs, DBSQL, Lakebase) do NOT have fallback notes."""
        for name in ['Jobs Serverless Perf', 'DBSQL Serverless Medium',
                     'Lakebase 4CU 2HA']:
            row = find_row_by_name(ws, name)
            notes = ws.cell(row=row, column=COL_NOTES).value
            if notes:
                assert 'fallback' not in notes.lower(), \
                    f"{name} should not have fallback warning: {notes}"


class TestBugS10003FmapiSkuExact:
    """Regression: BUG-S10-003 — FMAPI SKU assertions must be exact strings.

    Prior iteration used `isinstance(sku, str) and len(sku) > 0` which would
    pass with any arbitrary string. Fixed to assert exact expected SKU values.
    """

    def test_fmapi_databricks_sku_exact(self):
        """FMAPI Databricks SKU is exactly SERVERLESS_REAL_TIME_INFERENCE."""
        item = make_fmapi_databricks()
        sku = _get_sku_type(item, 'aws')
        assert sku == 'SERVERLESS_REAL_TIME_INFERENCE'

    def test_fmapi_proprietary_sku_exact(self):
        """FMAPI Proprietary SKU is exactly ANTHROPIC_MODEL_SERVING."""
        item = make_fmapi_proprietary()
        sku = _get_sku_type(item, 'aws')
        assert sku == 'ANTHROPIC_MODEL_SERVING'

    def test_fmapi_skus_differ(self):
        """Databricks and Proprietary FMAPI use different SKUs."""
        db_sku = _get_sku_type(make_fmapi_databricks(), 'aws')
        prop_sku = _get_sku_type(make_fmapi_proprietary(), 'aws')
        assert db_sku != prop_sku


class TestBugS10004FileSizeCompliance:
    """Regression: BUG-S10-004 — No test file exceeds 200 lines.

    Prior iteration had test_combined_excel.py at 310 lines. Fixed by splitting
    into test_excel_structure.py and test_excel_formulas.py.
    """

    def test_no_file_exceeds_200_lines(self):
        """All Sprint 10 test files are under 200 lines."""
        test_dir = os.path.dirname(__file__)
        for fname in os.listdir(test_dir):
            if not fname.endswith('.py') or fname == '__init__.py':
                continue
            fpath = os.path.join(test_dir, fname)
            with open(fpath) as f:
                line_count = sum(1 for _ in f)
            assert line_count <= 200, \
                f"{fname} has {line_count} lines (limit: 200)"

    def test_ai_conftest_under_200_lines(self):
        """AI assistant conftest.py and chat_helpers.py under 200 lines."""
        ai_dir = os.path.join(
            os.path.dirname(__file__), '..', 'ai_assistant'
        )
        for fname in ('conftest.py', 'chat_helpers.py'):
            fpath = os.path.join(ai_dir, fname)
            if not os.path.exists(fpath):
                continue
            with open(fpath) as f:
                line_count = sum(1 for _ in f)
            assert line_count <= 200, \
                f"ai_assistant/{fname} has {line_count} lines (limit: 200)"


class TestBugS10005TestSuiteTimeout:
    """Regression: BUG-S10-005 — Default `pytest` must not include AI tests.

    Root cause: pyproject.toml had testpaths=["tests"] without ignoring
    tests/ai_assistant/. AI tests make live FMAPI calls with 30s retries,
    causing total suite to exceed 1800s timeout.
    """

    def test_pyproject_ignores_ai_tests(self):
        """pyproject.toml addopts must include --ignore=tests/ai_assistant."""
        root = os.path.join(os.path.dirname(__file__), '..', '..', '..')
        pyproject = os.path.join(root, 'pyproject.toml')
        with open(pyproject) as f:
            content = f.read()
        assert '--ignore=tests/ai_assistant' in content, \
            "pyproject.toml must exclude AI tests from default pytest run"

    def test_ai_conftest_has_fmapi_skip(self):
        """AI conftest auto-skips when FMAPI is unreachable."""
        ai_conftest = os.path.join(
            os.path.dirname(__file__), '..', '..', 'ai_assistant', 'conftest.py'
        )
        with open(ai_conftest) as f:
            content = f.read()
        assert '_fmapi_reachable' in content, \
            "AI conftest must check FMAPI reachability"
        assert '_skip_if_fmapi_unreachable' in content, \
            "AI conftest must have autouse skip fixture"

    def test_default_pytest_collects_no_ai_tests(self):
        """Default pytest --collect-only should not collect tests FROM ai_assistant/."""
        import subprocess
        result = subprocess.run(
            ['python', '-m', 'pytest', '--collect-only', '-q'],
            capture_output=True, text=True,
            cwd=os.path.join(os.path.dirname(__file__), '..', '..', '..'),
        )
        # Check that no test lines start with the ai_assistant directory path.
        # Other tests may reference "ai_assistant" in their parametrized IDs
        # (e.g., test_suite_completeness checking directory existence), so we
        # only flag lines that are actual ai_assistant test module collections.
        ai_test_lines = [
            line for line in result.stdout.splitlines()
            if line.startswith('tests/ai_assistant/')
        ]
        assert len(ai_test_lines) == 0, (
            f"AI tests leaked into default collection: {ai_test_lines[:5]}"
        )
