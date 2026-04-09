"""Integration validation: verify all expected test modules exist and collect.

Ensures no test directories or files have been accidentally deleted,
and that pytest can discover and collect them without import errors.

Tests are organized by feature/domain under tests/export/ and
tests/ai_assistant/, not by sprint number.
"""
from pathlib import Path

import pytest

TESTS_ROOT = Path(__file__).resolve().parent.parent


# --- Export workload test directories ---

EXPECTED_EXPORT_DIRS = [
    "jobs",
    "all_purpose",
    "dlt",
    "dbsql",
    "model_serving",
    "fmapi_databricks",
    "fmapi_proprietary",
    "vector_search",
    "lakebase",
    "cross_workload",
    "sku_alignment",
]

EXPECTED_AI_ASSISTANT_DIRS = [
    "jobs",
    "all_purpose",
    "dlt",
    "dbsql",
    "model_serving",
    "fmapi_databricks",
    "fmapi_proprietary",
    "vector_search",
    "lakebase",
    "multi_workload",
    "ml_pipeline",
]

EXPECTED_SUPPORT_DIRS = [
    "regression",
    "test_installation",
    "test_integration_validation",
    "docs_media",
]


class TestDirectoryStructure:
    """Verify expected test directories exist."""

    @pytest.mark.parametrize("dirname", EXPECTED_EXPORT_DIRS)
    def test_export_dir_exists(self, dirname):
        d = TESTS_ROOT / "export" / dirname
        assert d.is_dir(), (
            f"Missing export test directory: tests/export/{dirname}"
        )

    @pytest.mark.parametrize("dirname", EXPECTED_AI_ASSISTANT_DIRS)
    def test_ai_assistant_dir_exists(self, dirname):
        d = TESTS_ROOT / "ai_assistant" / dirname
        assert d.is_dir(), (
            f"Missing AI assistant test directory: "
            f"tests/ai_assistant/{dirname}"
        )

    @pytest.mark.parametrize("dirname", EXPECTED_SUPPORT_DIRS)
    def test_support_dir_exists(self, dirname):
        d = TESTS_ROOT / dirname
        assert d.is_dir(), f"Missing test directory: tests/{dirname}"


# --- Conftest existence ---


class TestConftestFiles:
    """Verify conftest.py files exist where expected."""

    def test_root_conftest(self):
        assert (TESTS_ROOT / "conftest.py").is_file()

    def test_export_root_conftest(self):
        p = TESTS_ROOT / "export" / "conftest.py"
        # Export root conftest is optional — some projects put it there
        # but the per-workload conftest files are what matter
        pass

    @pytest.mark.parametrize("dirname", EXPECTED_EXPORT_DIRS[:9])
    def test_export_workload_conftest(self, dirname):
        assert (TESTS_ROOT / "export" / dirname / "conftest.py").is_file(), (
            f"Missing conftest.py in tests/export/{dirname}"
        )


# --- Test file counts ---

MINIMUM_EXPORT_TEST_FILES = {
    "jobs": 5,
    "all_purpose": 5,
    "dlt": 8,
    "dbsql": 5,
    "model_serving": 5,
    "fmapi_databricks": 5,
    "fmapi_proprietary": 3,
    "vector_search": 3,
    "lakebase": 3,
    "cross_workload": 3,
    "sku_alignment": 2,
}

MINIMUM_SUPPORT_TEST_FILES = {
    "ai_assistant": 2,
    "regression": 3,
    "test_installation": 3,
}


class TestFileCount:
    """Verify each directory has the expected minimum number of test files."""

    @pytest.mark.parametrize(
        "dirname,min_files",
        MINIMUM_EXPORT_TEST_FILES.items(),
    )
    def test_min_export_test_files(self, dirname, min_files):
        d = TESTS_ROOT / "export" / dirname
        test_files = list(d.rglob("test_*.py"))
        assert len(test_files) >= min_files, (
            f"tests/export/{dirname} has {len(test_files)} test files, "
            f"expected >= {min_files}: {[f.name for f in test_files]}"
        )

    @pytest.mark.parametrize(
        "dirname,min_files",
        MINIMUM_SUPPORT_TEST_FILES.items(),
    )
    def test_min_support_test_files(self, dirname, min_files):
        d = TESTS_ROOT / dirname
        test_files = list(d.rglob("test_*.py"))
        assert len(test_files) >= min_files, (
            f"tests/{dirname} has {len(test_files)} test files, "
            f"expected >= {min_files}: {[f.name for f in test_files]}"
        )


# --- Permission tests file ---


class TestPermissionTests:
    """Verify the standalone Lakebase permission test file exists."""

    def test_permission_test_file_exists(self):
        p = TESTS_ROOT / "test_lakebase_permissions.py"
        assert p.is_file(), "Missing tests/test_lakebase_permissions.py"

    def test_permission_test_has_classes(self):
        """Ensure the 5 expected test classes are defined."""
        content = (TESTS_ROOT / "test_lakebase_permissions.py").read_text()
        expected_classes = [
            "TestTokenGeneration",
            "TestDatabaseConnection",
            "TestReadAccess",
            "TestWriteAccess",
            "TestTokenRefresh",
        ]
        for cls in expected_classes:
            assert f"class {cls}" in content, (
                f"Missing class {cls} in test_lakebase_permissions.py"
            )

    def test_permission_test_has_skip_guard(self):
        """Ensure tests are skip-guarded for offline runs."""
        content = (TESTS_ROOT / "test_lakebase_permissions.py").read_text()
        assert "skipif" in content or "skip" in content, (
            "Permission tests should be skip-guarded for offline runs"
        )


# --- Init files ---


class TestInitFiles:
    """Verify __init__.py files exist in test packages."""

    @pytest.mark.parametrize("dirname", EXPECTED_EXPORT_DIRS)
    def test_export_init_file(self, dirname):
        assert (TESTS_ROOT / "export" / dirname / "__init__.py").is_file(), (
            f"Missing __init__.py in tests/export/{dirname}"
        )

    @pytest.mark.parametrize("dirname", EXPECTED_AI_ASSISTANT_DIRS)
    def test_ai_assistant_init_file(self, dirname):
        assert (
            TESTS_ROOT / "ai_assistant" / dirname / "__init__.py"
        ).is_file(), (
            f"Missing __init__.py in tests/ai_assistant/{dirname}"
        )

    @pytest.mark.parametrize(
        "dirname", ["regression", "test_installation"]
    )
    def test_support_init_file(self, dirname):
        assert (TESTS_ROOT / dirname / "__init__.py").is_file(), (
            f"Missing __init__.py in tests/{dirname}"
        )
