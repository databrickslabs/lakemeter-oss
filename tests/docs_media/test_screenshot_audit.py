"""Validate the screenshot audit report and media directory structure."""

from pathlib import Path

import pytest

from tests.docs_media.conftest import (
    DOCS_SITE_DIR,
    GIFS_DIR,
    GUIDES_IMG_DIR,
    STATIC_IMG_DIR,
    VIDEO_DIR,
    REPO_ROOT,
)

AUDIT_REPORT = REPO_ROOT / "harness" / "audit" / "screenshot-audit-report.md"

EXPECTED_CORE_SCREENSHOTS = [
    "home-page.png",
    "login-page.png",
    "estimates-list.png",
    "calculator-overview.png",
    "all-workloads-overview.png",
    "workload-expanded-config.png",
    "estimate-with-workloads.png",
    "workload-calculation-detail.png",
]

EXPECTED_GUIDE_SCREENSHOTS = [
    "dbsql-warehouses-guide.png",
    "dbsql-worked-example.png",
    "model-serving-guide.png",
    "model-serving-worked-example.png",
    "vector-search-guide.png",
    "vector-search-worked-example.png",
    "fmapi-databricks-guide.png",
    "fmapi-databricks-worked-example.png",
    "fmapi-proprietary-guide.png",
    "fmapi-proprietary-worked-example.png",
    "lakebase-guide.png",
    "lakebase-worked-example.png",
    "ai-assistant-guide.png",
    "ai-assistant-tools.png",
    "export-guide.png",
    "export-excel-structure.png",
    "calculation-reference-guide.png",
    "calculation-worked-example.png",
    "faq-guide.png",
    "faq-workload-table.png",
    "admin-deployment-guide.png",
    "admin-configuration-guide.png",
    "admin-api-reference-guide.png",
    "admin-architecture-guide.png",
    "admin-database-guide.png",
    "admin-database-schema.png",
    "admin-permissions-guide.png",
    "admin-troubleshooting-guide.png",
    "overview-page.png",
    "getting-started-page.png",
    "workloads-overview-page.png",
]


class TestAuditReportExists:
    """The screenshot audit report must exist and be complete."""

    def test_audit_report_exists(self):
        assert AUDIT_REPORT.exists(), (
            f"Audit report not found at {AUDIT_REPORT}"
        )

    def test_audit_report_not_empty(self):
        content = AUDIT_REPORT.read_text(encoding="utf-8")
        assert len(content) > 500, "Audit report is too short to be complete"

    def test_audit_report_covers_all_core_screenshots(self):
        content = AUDIT_REPORT.read_text(encoding="utf-8")
        for screenshot in EXPECTED_CORE_SCREENSHOTS:
            assert screenshot in content, (
                f"Audit report does not mention core screenshot: {screenshot}"
            )

    def test_audit_report_has_summary_table(self):
        content = AUDIT_REPORT.read_text(encoding="utf-8")
        assert "| Category" in content, "Audit report missing summary table"
        assert "Customer Name Violation" in content, (
            "Audit report missing customer name violation tracking"
        )


class TestCoreScreenshotsExist:
    """All 8 core screenshots must exist in static/img/."""

    @pytest.mark.parametrize("filename", EXPECTED_CORE_SCREENSHOTS)
    def test_core_screenshot_exists(self, filename):
        path = STATIC_IMG_DIR / filename
        assert path.exists(), f"Core screenshot missing: {filename}"

    @pytest.mark.parametrize("filename", EXPECTED_CORE_SCREENSHOTS)
    def test_core_screenshot_not_empty(self, filename):
        path = STATIC_IMG_DIR / filename
        if path.exists():
            assert path.stat().st_size > 0, (
                f"Core screenshot is empty: {filename}"
            )


class TestGuideScreenshotsExist:
    """All guide screenshots must exist in static/img/guides/."""

    @pytest.mark.parametrize("filename", EXPECTED_GUIDE_SCREENSHOTS)
    def test_guide_screenshot_exists(self, filename):
        path = GUIDES_IMG_DIR / filename
        assert path.exists(), f"Guide screenshot missing: {filename}"


class TestDirectoryStructure:
    """Media directories must exist for future sprints."""

    def test_gifs_directory_exists(self):
        assert GIFS_DIR.exists(), (
            "GIFs directory not found at docs-site/static/img/gifs/"
        )

    def test_video_directory_exists(self):
        assert VIDEO_DIR.exists(), (
            "Video directory not found at docs-site/static/video/"
        )

    def test_guides_directory_exists(self):
        assert GUIDES_IMG_DIR.exists(), (
            "Guides directory not found at docs-site/static/img/guides/"
        )
