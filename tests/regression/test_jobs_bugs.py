"""
Regression tests for bugs found during Sprint 1 evaluation.

BUG-S1-1: make_line_item duplicated in 3 files → FIXED (extracted to conftest.py)
BUG-S1-2: No Visual QA report → N/A for Build Agent (Visual QA Agent responsibility)
BUG-S1-3: No integration test → FIXED (test_jobs_export_integration.py)
BUG-S1-4: No coverage report → FIXED (run with --cov)
BUG-S1-5: Serverless photon 2x mismatch → FIXED (serverless always applies photon)
BUG-S1-6: Lakebase DBU formula discrepancy → FIXED (removed erroneous *2)
BUG-S1-12: num_workers default discrepancy → FIXED (or 1 → or 0 in calculations.py:70 + excel_row_writer.py defaults)
BUG-S1-13: Hours fallback discrepancy → FIXED (11 hrs → 0 in calculations.py:22)
BUG-S1-15: Deprecation warnings → FIXED (Pydantic V2 ConfigDict + SQLAlchemy orm import)
BUG-S1-12b: excel_row_writer.py num_workers defaults → FIXED (default=1 → default=0 in _write_vm_costs and _write_total_costs)
"""
import os
import sys
import pytest

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, BACKEND_DIR)

from tests.export.jobs.conftest import make_line_item


class TestBugS1_1_SharedFixtureNotDuplicated:
    """BUG-S1-1: make_line_item was duplicated in 3 test files.
    Fix: extracted to tests/sprint_1/conftest.py.
    Regression: verify all test files import from conftest, not define locally.
    """

    def test_conftest_make_line_item_exists(self):
        """conftest.py exports make_line_item."""
        item = make_line_item(workload_type="JOBS", num_workers=3)
        assert item.workload_type == "JOBS"
        assert item.num_workers == 3

    def test_conftest_defaults_are_complete(self):
        """make_line_item defaults include all LineItem model fields."""
        item = make_line_item()
        required_attrs = [
            "workload_type", "workload_name", "serverless_enabled",
            "photon_enabled", "driver_node_type", "worker_node_type",
            "num_workers", "dlt_edition", "dbsql_warehouse_type",
            "vector_search_mode", "model_serving_gpu_type",
            "fmapi_provider", "fmapi_model", "lakebase_cu",
            "runs_per_day", "hours_per_month", "notes",
        ]
        for attr in required_attrs:
            assert hasattr(item, attr), f"make_line_item missing attribute: {attr}"

    def test_no_duplicate_make_line_item_in_test_files(self):
        """Verify test files import make_line_item instead of defining it."""
        test_dir = os.path.join(os.path.dirname(__file__), '..', 'sprint_1')
        files_to_check = [
            'test_jobs_export.py',
            'test_jobs_vm_and_notes.py',
            'test_jobs_excel_export.py',
        ]
        for filename in files_to_check:
            filepath = os.path.join(test_dir, filename)
            if os.path.exists(filepath):
                with open(filepath) as f:
                    content = f.read()
                assert "def make_line_item(" not in content, \
                    f"{filename} still defines make_line_item locally — should import from conftest"


class TestBugS1_3_IntegrationTestExists:
    """BUG-S1-3: Tests didn't exercise the real export endpoint.
    Fix: test_jobs_export_integration.py added.
    Regression: verify the integration test file exists and has test classes.
    """

    def test_integration_test_file_exists(self):
        integration_path = os.path.join(
            os.path.dirname(__file__), '..', 'export', 'jobs', 'test_jobs_export_integration.py'
        )
        assert os.path.exists(integration_path), \
            "Integration test file test_jobs_export_integration.py must exist"

    def test_integration_test_has_endpoint_tests(self):
        integration_path = os.path.join(
            os.path.dirname(__file__), '..', 'export', 'jobs', 'test_jobs_export_integration.py'
        )
        with open(integration_path) as f:
            content = f.read()
        assert "TestExportEndpoint" in content, \
            "Integration test must have TestExportEndpoint test class"
        assert "/api/v1/export/estimate/" in content, \
            "Integration test must call the real export endpoint"


class TestBugS1_5_ServerlessPhotonFixed:
    """BUG-S1-5: Frontend always applies photon for serverless.
    Backend previously only applied photon when photon_enabled=True.
    FIXED: Backend now always applies photon for serverless (built-in).
    Photon multiplier is read from dbu-multipliers.json (2.9x for AWS).
    Regression: verify serverless always gets photon regardless of flag.
    """

    def test_serverless_always_applies_photon(self):
        """Backend serverless applies photon regardless of photon_enabled flag."""
        from app.routes.export import _calculate_dbu_per_hour

        without_flag = make_line_item(
            workload_type="JOBS", driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge", num_workers=2,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard",
        )
        with_flag = make_line_item(
            workload_type="JOBS", driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge", num_workers=2,
            photon_enabled=True, serverless_enabled=True,
            serverless_mode="standard",
        )
        dbu_without, _ = _calculate_dbu_per_hour(without_flag, "aws")
        dbu_with, _ = _calculate_dbu_per_hour(with_flag, "aws")
        # Serverless always has photon built-in — both should produce the same result
        assert dbu_with == pytest.approx(dbu_without), \
            f"Serverless photon should be identical regardless of flag: {dbu_with} vs {dbu_without}"

    def test_serverless_dbu_includes_photon_2x(self):
        """Verify serverless DBU/hr includes 2x photon multiplier."""
        from app.routes.export import _calculate_dbu_per_hour

        # Classic without photon as baseline
        classic_item = make_line_item(
            workload_type="JOBS", driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge", num_workers=2,
            photon_enabled=False, serverless_enabled=False,
        )
        serverless_item = make_line_item(
            workload_type="JOBS", driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge", num_workers=2,
            photon_enabled=False, serverless_enabled=True,
            serverless_mode="standard",
        )
        classic_dbu, _ = _calculate_dbu_per_hour(classic_item, "aws")
        serverless_dbu, _ = _calculate_dbu_per_hour(serverless_item, "aws")
        # Serverless standard = base × 2.9 (photon from dbu-multipliers.json) × 1 (standard mode)
        assert serverless_dbu == pytest.approx(classic_dbu * 2.9), \
            f"Serverless should be 2.9x classic (photon built-in): {serverless_dbu} vs {classic_dbu}"

    def test_classic_without_photon_no_multiplier(self):
        """Classic without photon_enabled should NOT get 2x multiplier."""
        from app.routes.export import _calculate_dbu_per_hour

        classic_no_photon = make_line_item(
            workload_type="JOBS", driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge", num_workers=2,
            photon_enabled=False, serverless_enabled=False,
        )
        classic_with_photon = make_line_item(
            workload_type="JOBS", driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge", num_workers=2,
            photon_enabled=True, serverless_enabled=False,
        )
        dbu_no, _ = _calculate_dbu_per_hour(classic_no_photon, "aws")
        dbu_yes, _ = _calculate_dbu_per_hour(classic_with_photon, "aws")
        # Classic with photon should be exactly 2.9x classic without (from dbu-multipliers.json)
        assert dbu_yes == pytest.approx(dbu_no * 2.9), \
            f"Classic photon should be 2.9x base: {dbu_yes} vs {dbu_no}"
        # And without photon should be less than with
        assert dbu_no < dbu_yes, "Classic without photon should have lower DBU/hr"


class TestBugS1_6_LakebaseDBUFormulaFixed:
    """BUG-S1-6: Backend previously used cu × nodes × 2, frontend uses cu × nodes.
    FIXED: Backend now uses cu × nodes (matching frontend and Databricks docs).
    Regression: verify formula is cu × nodes without the erroneous ×2.
    """

    def test_backend_lakebase_uses_cu_times_nodes(self):
        from app.routes.export import _calculate_dbu_per_hour

        item = make_line_item(
            workload_type="LAKEBASE", lakebase_cu=4, lakebase_ha_nodes=2,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        # Correct formula: cu × nodes = 4 × 2 = 8
        assert dbu_hr == pytest.approx(8.0), \
            f"Lakebase DBU/hr should be cu×nodes=8.0, got {dbu_hr}"

    def test_lakebase_single_node(self):
        from app.routes.export import _calculate_dbu_per_hour

        item = make_line_item(
            workload_type="LAKEBASE", lakebase_cu=0.5, lakebase_ha_nodes=1,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        # 0.5 × 1 = 0.5
        assert dbu_hr == pytest.approx(0.5), \
            f"Lakebase 0.5CU × 1 node should be 0.5, got {dbu_hr}"

    def test_lakebase_max_config(self):
        from app.routes.export import _calculate_dbu_per_hour

        item = make_line_item(
            workload_type="LAKEBASE", lakebase_cu=112, lakebase_ha_nodes=3,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        # 112 × 3 = 336
        assert dbu_hr == pytest.approx(336.0), \
            f"Lakebase 112CU × 3 nodes should be 336.0, got {dbu_hr}"


class TestBugS1_12_NumWorkersDefaultFixed:
    """BUG-S1-12: Backend defaulted num_workers to 1 via `int(item.num_workers or 1)`.
    Frontend uses 0. This caused Excel to overstate costs for zero-worker configs.
    FIXED: Backend now uses `int(item.num_workers or 0)` in calculations.py:70.
    Regression: verify backend returns driver-only DBU when num_workers is 0 or None.
    """

    def test_zero_workers_returns_driver_only(self):
        """num_workers=0 → DBU/hr = driver_dbu only (no worker contribution)."""
        from app.routes.export import _calculate_dbu_per_hour

        item = make_line_item(
            workload_type="JOBS", driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge", num_workers=0,
            photon_enabled=False, serverless_enabled=False,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        # i3.xlarge = 1.0 DBU/hr. With 0 workers: driver only = 1.0
        assert dbu_hr == pytest.approx(1.0), \
            f"0 workers should give driver-only DBU (1.0), got {dbu_hr}"

    def test_none_workers_returns_driver_only(self):
        """num_workers=None → same as 0, driver-only."""
        from app.routes.export import _calculate_dbu_per_hour

        item = make_line_item(
            workload_type="JOBS", driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge", num_workers=None,
            photon_enabled=False, serverless_enabled=False,
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        assert dbu_hr == pytest.approx(1.0), \
            f"None workers should give driver-only DBU (1.0), got {dbu_hr}"

    def test_frontend_backend_agree_on_zero_workers(self):
        """Frontend and backend both return driver-only for 0 workers."""
        from tests.export.jobs.test_jobs_calculations import (
            frontend_calc_jobs, backend_calc_jobs,
        )

        fe = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=100,
        )
        be = backend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=0,
            photon_enabled=False, serverless_enabled=False,
            hours_per_month=100,
        )
        assert fe["dbu_per_hour"] == pytest.approx(be["dbu_per_hour"]), \
            f"FE ({fe['dbu_per_hour']}) and BE ({be['dbu_per_hour']}) must agree on 0 workers"


class TestBugS1_13_HoursFallbackFixed:
    """BUG-S1-13: Backend returned 11 hours when no usage data was set.
    Frontend returned 0. This caused Excel to show non-zero costs for $0 browser items.
    FIXED: Backend now returns 0 in calculations.py:22.
    Regression: verify backend returns 0 when no usage data provided.
    """

    def test_no_usage_data_returns_zero_hours(self):
        """No runs_per_day, avg_runtime_minutes, or hours_per_month → 0 hours."""
        from app.routes.export import _calculate_hours_per_month

        item = make_line_item(
            workload_type="JOBS", runs_per_day=None,
            avg_runtime_minutes=None, hours_per_month=None,
        )
        hours = _calculate_hours_per_month(item)
        assert hours == pytest.approx(0.0), \
            f"No usage data should return 0 hours, got {hours}"

    def test_no_usage_data_returns_zero_cost(self):
        """No usage data → 0 hours → 0 monthly DBUs → $0 cost."""
        from app.routes.export import (
            _calculate_hours_per_month, _calculate_dbu_per_hour,
            _get_dbu_price, _get_sku_type,
        )

        item = make_line_item(
            workload_type="JOBS", driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge", num_workers=2,
            photon_enabled=False, serverless_enabled=False,
        )
        hours = _calculate_hours_per_month(item)
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        sku = _get_sku_type(item, "aws")
        dbu_rate, _ = _get_dbu_price("aws", "us-east-1", "PREMIUM", sku)

        monthly_dbus = dbu_hr * hours
        cost = monthly_dbus * dbu_rate

        assert hours == pytest.approx(0.0), "Hours should be 0"
        assert monthly_dbus == pytest.approx(0.0), "Monthly DBUs should be 0"
        assert cost == pytest.approx(0.0), "Cost should be $0"

    def test_frontend_backend_agree_on_zero_hours(self):
        """Frontend and backend both return 0 when no usage data set."""
        from tests.export.jobs.test_jobs_calculations import (
            frontend_calc_jobs, backend_calc_jobs,
        )

        fe = frontend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=False,
        )
        be = backend_calc_jobs(
            driver_dbu_rate=1.0, worker_dbu_rate=1.0, num_workers=2,
            photon_enabled=False, serverless_enabled=False,
        )
        assert fe["hours_per_month"] == pytest.approx(0.0), "Frontend: 0 hours"
        assert be["hours_per_month"] == pytest.approx(0.0), "Backend: 0 hours"
        assert fe["dbu_cost"] == pytest.approx(0.0), "Frontend: $0 cost"
        assert be["dbu_cost"] == pytest.approx(0.0), "Backend: $0 cost"


class TestBugS1_12b_ExcelRowWriterNumWorkersDefault:
    """BUG-S1-12b: excel_row_writer.py had `nw = row_data.get('num_workers', 1)`
    in both _write_vm_costs and _write_total_costs. The default fallback of 1
    would inflate VM costs if row_data lacked num_workers key.
    FIXED: Changed default to 0 to match frontend behavior.
    Regression: verify no `'num_workers', 1)` patterns remain in excel_row_writer.py.
    """

    def test_no_num_workers_default_one_in_row_writer(self):
        """excel_row_writer.py should not default num_workers to 1."""
        row_writer_path = os.path.join(
            BACKEND_DIR, 'app', 'routes', 'export', 'excel_row_writer.py'
        )
        with open(row_writer_path) as f:
            content = f.read()
        assert "'num_workers', 1)" not in content, \
            "excel_row_writer.py still has num_workers default=1 fallback"

    def test_no_num_workers_default_one_in_export_modules(self):
        """No export module should default num_workers to 1."""
        export_dir = os.path.join(BACKEND_DIR, 'app', 'routes', 'export')
        for filename in os.listdir(export_dir):
            if filename.endswith('.py'):
                filepath = os.path.join(export_dir, filename)
                with open(filepath) as f:
                    content = f.read()
                # Check for the specific pattern: or 1) with num_workers context
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'num_workers' in line and 'or 1)' in line:
                        pytest.fail(
                            f"{filename}:{i+1} has num_workers 'or 1)' fallback: {line.strip()}"
                        )
                    if 'num_workers' in line and ", 1)" in line and "get(" in line:
                        pytest.fail(
                            f"{filename}:{i+1} has num_workers default=1 in get(): {line.strip()}"
                        )


class TestBugS1_15_DeprecationWarningsFixed:
    """BUG-S1-15: 11 deprecation warnings emitted during test collection.
    - Pydantic V2: class Config → model_config = ConfigDict(...)
    - SQLAlchemy: sqlalchemy.ext.declarative → sqlalchemy.orm
    FIXED: All schemas use ConfigDict, database.py uses sqlalchemy.orm.
    Regression: verify no deprecated patterns remain.
    """

    def test_no_pydantic_class_config_in_schemas(self):
        """All schema files use model_config = ConfigDict, not class Config."""
        schema_dir = os.path.join(BACKEND_DIR, 'app', 'schemas')
        for filename in os.listdir(schema_dir):
            if filename.endswith('.py') and filename != '__init__.py':
                filepath = os.path.join(schema_dir, filename)
                with open(filepath) as f:
                    content = f.read()
                assert 'class Config:' not in content, \
                    f"{filename} still uses deprecated 'class Config:' — use model_config = ConfigDict(...)"

    def test_no_deprecated_declarative_base_import(self):
        """database.py uses sqlalchemy.orm.declarative_base, not sqlalchemy.ext.declarative."""
        db_path = os.path.join(BACKEND_DIR, 'app', 'database.py')
        with open(db_path) as f:
            content = f.read()
        assert 'sqlalchemy.ext.declarative' not in content, \
            "database.py still imports from deprecated sqlalchemy.ext.declarative"
        assert 'from sqlalchemy.orm import declarative_base' in content, \
            "database.py should import declarative_base from sqlalchemy.orm"

    def test_config_py_uses_configdict(self):
        """config.py Settings uses model_config = ConfigDict, not class Config."""
        config_path = os.path.join(BACKEND_DIR, 'app', 'config.py')
        with open(config_path) as f:
            content = f.read()
        assert 'class Config:' not in content, \
            "config.py still uses deprecated 'class Config:'"
        assert 'model_config' in content, \
            "config.py should use model_config = ConfigDict(...)"
