"""Sprint 2: Validate workload type guide screenshots and doc page references."""

import re
from pathlib import Path

import pytest

from tests.docs_media.conftest import DOCS_DIR, GUIDES_IMG_DIR

# The 15 screenshots Sprint 2 is responsible for
SPRINT_2_SCREENSHOTS = [
    "getting-started-page.png",
    "overview-page.png",
    "workloads-overview-page.png",
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
]

# Map each screenshot to the doc page that should reference it
SCREENSHOT_TO_DOC_PAGE = {
    "getting-started-page.png": "user-guide/getting-started.md",
    "overview-page.png": "user-guide/overview.md",
    "workloads-overview-page.png": "user-guide/overview.md",
    "dbsql-warehouses-guide.png": "user-guide/dbsql-warehouses.md",
    "dbsql-worked-example.png": "user-guide/dbsql-warehouses.md",
    "model-serving-guide.png": "user-guide/model-serving.md",
    "model-serving-worked-example.png": "user-guide/model-serving.md",
    "vector-search-guide.png": "user-guide/vector-search.md",
    "vector-search-worked-example.png": "user-guide/vector-search.md",
    "fmapi-databricks-guide.png": "user-guide/fmapi-databricks.md",
    "fmapi-databricks-worked-example.png": "user-guide/fmapi-databricks.md",
    "fmapi-proprietary-guide.png": "user-guide/fmapi-proprietary.md",
    "fmapi-proprietary-worked-example.png": "user-guide/fmapi-proprietary.md",
    "lakebase-guide.png": "user-guide/lakebase.md",
    "lakebase-worked-example.png": "user-guide/lakebase.md",
}

# Customer names that must never appear in alt text or captions
FORBIDDEN_NAMES = ["Maya", "Merchant", "Commerci"]


class TestSprint2ScreenshotFiles:
    """All 15 Sprint 2 screenshots must exist and be valid."""

    @pytest.mark.parametrize("filename", SPRINT_2_SCREENSHOTS)
    def test_screenshot_exists(self, filename):
        path = GUIDES_IMG_DIR / filename
        assert path.exists(), f"Sprint 2 screenshot missing: {filename}"

    @pytest.mark.parametrize("filename", SPRINT_2_SCREENSHOTS)
    def test_screenshot_not_empty(self, filename):
        path = GUIDES_IMG_DIR / filename
        assert path.stat().st_size > 0, (
            f"Sprint 2 screenshot is empty (0 bytes): {filename}"
        )

    @pytest.mark.parametrize("filename", SPRINT_2_SCREENSHOTS)
    def test_screenshot_reasonable_size(self, filename):
        path = GUIDES_IMG_DIR / filename
        size = path.stat().st_size
        assert size >= 10_000, (
            f"Sprint 2 screenshot suspiciously small ({size} bytes): {filename}"
        )
        assert size <= 2_000_000, (
            f"Sprint 2 screenshot too large ({size} bytes, >2MB): {filename}"
        )

    def test_sprint2_screenshot_count(self):
        """Exactly 15 screenshots in Sprint 2 scope."""
        assert len(SPRINT_2_SCREENSHOTS) == 15


class TestSprint2DocPageReferences:
    """Each Sprint 2 screenshot must be referenced in its doc page."""

    @pytest.mark.parametrize(
        "screenshot,doc_page",
        list(SCREENSHOT_TO_DOC_PAGE.items()),
        ids=list(SCREENSHOT_TO_DOC_PAGE.keys()),
    )
    def test_screenshot_referenced_in_doc(self, screenshot, doc_page):
        doc_path = DOCS_DIR / doc_page
        assert doc_path.exists(), f"Doc page not found: {doc_page}"
        content = doc_path.read_text(encoding="utf-8")
        assert screenshot in content, (
            f"Screenshot {screenshot} not referenced in {doc_page}"
        )

    @pytest.mark.parametrize(
        "screenshot,doc_page",
        list(SCREENSHOT_TO_DOC_PAGE.items()),
        ids=[f"alt:{k}" for k in SCREENSHOT_TO_DOC_PAGE.keys()],
    )
    def test_screenshot_has_descriptive_alt_text(self, screenshot, doc_page):
        doc_path = DOCS_DIR / doc_page
        content = doc_path.read_text(encoding="utf-8")
        pattern = rf'!\[([^\]]*)\]\(/img/guides/{re.escape(screenshot)}\)'
        match = re.search(pattern, content)
        assert match is not None, (
            f"No markdown image reference found for {screenshot} in {doc_page}"
        )
        alt_text = match.group(1)
        assert len(alt_text.strip()) >= 10, (
            f"Alt text too short for {screenshot}: '{alt_text}' "
            f"(expected at least 10 chars)"
        )

    @pytest.mark.parametrize(
        "screenshot,doc_page",
        list(SCREENSHOT_TO_DOC_PAGE.items()),
        ids=[f"caption:{k}" for k in SCREENSHOT_TO_DOC_PAGE.keys()],
    )
    def test_screenshot_has_caption(self, screenshot, doc_page):
        """Each screenshot should have an italic caption line below it."""
        doc_path = DOCS_DIR / doc_page
        content = doc_path.read_text(encoding="utf-8")
        img_pattern = rf'!\[[^\]]*\]\(/img/guides/{re.escape(screenshot)}\)'
        match = re.search(img_pattern, content)
        assert match is not None, (
            f"Image reference for {screenshot} not found in {doc_page}"
        )
        # Check the line after the image reference starts with *
        after_img = content[match.end():]
        lines_after = after_img.lstrip("\n").split("\n", 1)
        assert len(lines_after) > 0 and lines_after[0].startswith("*"), (
            f"No italic caption found after {screenshot} in {doc_page}. "
            f"Expected a line starting with '*' after the image reference."
        )


class TestSprint2NoCustomerNames:
    """No customer names in alt text or captions for Sprint 2 screenshots."""

    @pytest.mark.parametrize(
        "screenshot,doc_page",
        list(SCREENSHOT_TO_DOC_PAGE.items()),
        ids=[f"sanitized:{k}" for k in SCREENSHOT_TO_DOC_PAGE.keys()],
    )
    def test_no_customer_names_in_alt_or_caption(self, screenshot, doc_page):
        doc_path = DOCS_DIR / doc_page
        content = doc_path.read_text(encoding="utf-8")
        img_pattern = rf'!\[([^\]]*)\]\(/img/guides/{re.escape(screenshot)}\)'
        match = re.search(img_pattern, content)
        if match is None:
            return  # Handled by reference test
        alt_text = match.group(1)
        after_img = content[match.end():]
        caption_line = after_img.lstrip("\n").split("\n", 1)[0]
        combined = alt_text + " " + caption_line
        for name in FORBIDDEN_NAMES:
            assert name.lower() not in combined.lower(), (
                f"Customer name '{name}' found in alt text or caption "
                f"for {screenshot} in {doc_page}: '{combined}'"
            )
