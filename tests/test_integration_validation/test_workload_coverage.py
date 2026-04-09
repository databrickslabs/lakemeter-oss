"""Integration validation: verify all 9 workload types have test coverage.

Maps each workload type to its corresponding test directory under tests/export/
and tests/ai_assistant/, and validates that each has calculation, export, and
edge-case tests. Tests are organized by feature/domain, not by sprint number.
"""
import json
from pathlib import Path

import pytest

TESTS_ROOT = Path(__file__).resolve().parent.parent
PRICING_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "backend"
    / "static"
    / "pricing"
)

# Canonical mapping: workload type → export test directory name
WORKLOAD_EXPORT_DIR_MAP = {
    "JOBS": "jobs",
    "ALL_PURPOSE": "all_purpose",
    "DLT": "dlt",
    "DBSQL": "dbsql",
    "MODEL_SERVING": "model_serving",
    "FMAPI_DATABRICKS": "fmapi_databricks",
    "FMAPI_PROPRIETARY": "fmapi_proprietary",
    "VECTOR_SEARCH": "vector_search",
    "LAKEBASE": "lakebase",
}

# Canonical mapping: workload type → AI assistant test directory name
WORKLOAD_AI_DIR_MAP = {
    "JOBS": "jobs",
    "ALL_PURPOSE": "all_purpose",
    "DLT": "dlt",
    "DBSQL": "dbsql",
    "MODEL_SERVING": "model_serving",
    "FMAPI_DATABRICKS": "fmapi_databricks",
    "FMAPI_PROPRIETARY": "fmapi_proprietary",
    "VECTOR_SEARCH": "vector_search",
    "LAKEBASE": "lakebase",
}

# Multi-workload / cross-workload test directories
MULTI_WORKLOAD_DIRS = {
    "cross_workload": "Cross-workload combined scenarios",
    "sku_alignment": "SKU alignment across workloads",
}


class TestWorkloadCoverage:
    """Verify every workload type has dedicated export test coverage."""

    @pytest.mark.parametrize(
        "workload,export_dir", WORKLOAD_EXPORT_DIR_MAP.items()
    )
    def test_workload_has_export_test_directory(self, workload, export_dir):
        d = TESTS_ROOT / "export" / export_dir
        assert d.is_dir(), (
            f"No export test directory for {workload}: tests/export/{export_dir}"
        )

    @pytest.mark.parametrize(
        "workload,export_dir", WORKLOAD_EXPORT_DIR_MAP.items()
    )
    def test_workload_has_calculation_tests(self, workload, export_dir):
        d = TESTS_ROOT / "export" / export_dir
        calc_keywords = ("calc", "rate", "sku", "pricing", "dbu")
        calc_files = [
            f
            for f in d.glob("test_*.py")
            if any(kw in f.name.lower() for kw in calc_keywords)
        ]
        assert len(calc_files) >= 1, (
            f"No calculation/pricing test files for {workload} in "
            f"tests/export/{export_dir}. "
            f"Files: {[f.name for f in d.glob('test_*.py')]}"
        )

    @pytest.mark.parametrize(
        "workload,export_dir", WORKLOAD_EXPORT_DIR_MAP.items()
    )
    def test_workload_has_export_tests(self, workload, export_dir):
        d = TESTS_ROOT / "export" / export_dir
        export_keywords = ("export", "excel")
        export_files = [
            f
            for f in d.glob("test_*.py")
            if any(kw in f.name.lower() for kw in export_keywords)
        ]
        assert len(export_files) >= 1, (
            f"No export/excel test files for {workload} in "
            f"tests/export/{export_dir}. "
            f"Files: {[f.name for f in d.glob('test_*.py')]}"
        )


class TestMultiWorkloadCoverage:
    """Verify cross-workload and multi-workload scenario tests exist."""

    @pytest.mark.parametrize(
        "dir_name,desc", MULTI_WORKLOAD_DIRS.items()
    )
    def test_multi_workload_dir_exists(self, dir_name, desc):
        d = TESTS_ROOT / "export" / dir_name
        assert d.is_dir(), (
            f"Missing multi-workload test dir: tests/export/{dir_name} ({desc})"
        )

    def test_cross_workload_has_combined_tests(self):
        d = TESTS_ROOT / "export" / "cross_workload"
        combined = [
            f
            for f in d.glob("test_*.py")
            if "combined" in f.name.lower() or "cross" in f.name.lower()
        ]
        assert len(combined) >= 1, (
            "tests/export/cross_workload/ should have combined/cross tests"
        )

    def test_ai_multi_workload_tests(self):
        d = TESTS_ROOT / "ai_assistant" / "multi_workload"
        assert d.is_dir(), (
            "Missing AI assistant multi-workload test dir"
        )
        test_files = list(d.glob("test_*.py"))
        assert len(test_files) >= 1, (
            "AI assistant multi_workload dir should have test files"
        )

    def test_ai_ml_pipeline_tests(self):
        d = TESTS_ROOT / "ai_assistant" / "ml_pipeline"
        assert d.is_dir(), (
            "Missing AI assistant ML pipeline test dir"
        )
        test_files = list(d.glob("test_*.py"))
        assert len(test_files) >= 1, (
            "AI assistant ml_pipeline dir should have test files"
        )


class TestPricingDataCoverage:
    """Verify pricing data files exist for all workloads."""

    EXPECTED_PRICING_FILES = [
        "dbu-rates.json",
        "instance-dbu-rates.json",
        "dbu-multipliers.json",
        "dbsql-rates.json",
        "dbsql-warehouse-config.json",
        "fmapi-databricks-rates.json",
        "fmapi-proprietary-rates.json",
        "model-serving-rates.json",
        "vector-search-rates.json",
    ]

    @pytest.mark.parametrize("filename", EXPECTED_PRICING_FILES)
    def test_pricing_file_exists(self, filename):
        p = PRICING_DIR / filename
        assert p.is_file(), f"Missing pricing file: {filename}"

    @pytest.mark.parametrize("filename", EXPECTED_PRICING_FILES)
    def test_pricing_file_valid_json(self, filename):
        p = PRICING_DIR / filename
        data = json.loads(p.read_text())
        assert data, f"Pricing file {filename} is empty"

    def test_manifest_exists(self):
        assert (PRICING_DIR / "manifest.json").is_file()

    def test_manifest_lists_all_files(self):
        manifest = json.loads((PRICING_DIR / "manifest.json").read_text())
        files_listed = manifest.get("files", [])
        for expected in self.EXPECTED_PRICING_FILES:
            assert expected in files_listed, (
                f"manifest.json does not list {expected}"
            )

    def test_manifest_total_entries_positive(self):
        manifest = json.loads((PRICING_DIR / "manifest.json").read_text())
        total = manifest.get("total_entries", 0)
        assert total > 1000, (
            f"Expected 1000+ total pricing entries, got {total}"
        )


class TestAIAssistantCoverage:
    """Verify AI assistant tests cover workload types."""

    @pytest.mark.parametrize(
        "workload,ai_dir", WORKLOAD_AI_DIR_MAP.items()
    )
    def test_ai_workload_has_test_directory(self, workload, ai_dir):
        d = TESTS_ROOT / "ai_assistant" / ai_dir
        assert d.is_dir(), (
            f"Missing AI assistant test dir for {workload}: "
            f"tests/ai_assistant/{ai_dir}"
        )

    @pytest.mark.parametrize(
        "workload,ai_dir", WORKLOAD_AI_DIR_MAP.items()
    )
    def test_ai_workload_has_tests(self, workload, ai_dir):
        d = TESTS_ROOT / "ai_assistant" / ai_dir
        test_files = list(d.glob("test_*.py"))
        assert len(test_files) >= 1, (
            f"No test files for {workload} in tests/ai_assistant/{ai_dir}"
        )


class TestRegressionCoverage:
    """Verify regression tests exist covering key workload areas."""

    def test_regression_dir_has_tests(self):
        d = TESTS_ROOT / "regression"
        test_files = list(d.glob("test_*.py"))
        assert len(test_files) >= 3, (
            f"Expected >= 3 regression test files, got {len(test_files)}"
        )

    def test_regression_covers_jobs(self):
        d = TESTS_ROOT / "regression"
        jobs_files = [
            f for f in d.glob("test_*.py") if "jobs" in f.name.lower()
        ]
        assert len(jobs_files) >= 1, (
            "Missing regression tests covering jobs workload"
        )

    def test_regression_covers_dlt_or_dbsql(self):
        d = TESTS_ROOT / "regression"
        dlt_dbsql_files = [
            f
            for f in d.glob("test_*.py")
            if "dlt" in f.name.lower() or "dbsql" in f.name.lower()
        ]
        assert len(dlt_dbsql_files) >= 1, (
            "Missing regression tests covering DLT/DBSQL workloads"
        )

    def test_regression_covers_fmapi(self):
        d = TESTS_ROOT / "regression"
        fmapi_files = [
            f for f in d.glob("test_*.py") if "fmapi" in f.name.lower()
        ]
        assert len(fmapi_files) >= 1, (
            "Missing regression tests covering FMAPI workloads"
        )

    def test_regression_covers_vector_model_lakebase(self):
        d = TESTS_ROOT / "regression"
        vml_files = [
            f
            for f in d.glob("test_*.py")
            if any(
                kw in f.name.lower()
                for kw in ("vector", "model", "lakebase")
            )
        ]
        assert len(vml_files) >= 1, (
            "Missing regression tests covering vector search/model serving/"
            "lakebase workloads"
        )
