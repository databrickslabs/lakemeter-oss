"""Sprint 3: Validate user guide (Part 2) + admin guide screenshots and doc page references."""

import re
from pathlib import Path

import pytest

from tests.docs_media.conftest import DOCS_DIR, GUIDES_IMG_DIR

# The 16 screenshots Sprint 3 is responsible for
SPRINT_3_SCREENSHOTS = [
    # User guide Part 2 (8)
    "ai-assistant-guide.png",
    "ai-assistant-tools.png",
    "export-guide.png",
    "export-excel-structure.png",
    "calculation-reference-guide.png",
    "calculation-worked-example.png",
    "faq-guide.png",
    "faq-workload-table.png",
    # Admin guide (8)
    "admin-deployment-guide.png",
    "admin-configuration-guide.png",
    "admin-api-reference-guide.png",
    "admin-architecture-guide.png",
    "admin-database-guide.png",
    "admin-database-schema.png",
    "admin-permissions-guide.png",
    "admin-troubleshooting-guide.png",
]

# Map each screenshot to the doc page that should reference it
SCREENSHOT_TO_DOC_PAGE = {
    # User guide Part 2
    "ai-assistant-guide.png": "user-guide/ai-assistant.md",
    "ai-assistant-tools.png": "user-guide/ai-assistant.md",
    "export-guide.png": "user-guide/exporting.md",
    "export-excel-structure.png": "user-guide/exporting.md",
    "calculation-reference-guide.png": "user-guide/calculation-reference.md",
    "calculation-worked-example.png": "user-guide/calculation-reference.md",
    "faq-guide.png": "user-guide/faq.md",
    "faq-workload-table.png": "user-guide/faq.md",
    # Admin guide
    "admin-deployment-guide.png": "admin-guide/deployment.md",
    "admin-configuration-guide.png": "admin-guide/configuration.md",
    "admin-api-reference-guide.png": "admin-guide/api-reference.md",
    "admin-architecture-guide.png": "admin-guide/architecture.md",
    "admin-database-guide.png": "admin-guide/database.md",
    "admin-database-schema.png": "admin-guide/database.md",
    "admin-permissions-guide.png": "admin-guide/permissions.md",
    "admin-troubleshooting-guide.png": "admin-guide/troubleshooting.md",
}

# Customer names that must never appear in alt text or captions
FORBIDDEN_NAMES = ["Maya", "Merchant", "Commerci"]


class TestSprint3ScreenshotFiles:
    """All 16 Sprint 3 screenshots must exist and be valid."""

    @pytest.mark.parametrize("filename", SPRINT_3_SCREENSHOTS)
    def test_screenshot_exists(self, filename):
        path = GUIDES_IMG_DIR / filename
        assert path.exists(), f"Sprint 3 screenshot missing: {filename}"

    @pytest.mark.parametrize("filename", SPRINT_3_SCREENSHOTS)
    def test_screenshot_not_empty(self, filename):
        path = GUIDES_IMG_DIR / filename
        assert path.stat().st_size > 0, (
            f"Sprint 3 screenshot is empty (0 bytes): {filename}"
        )

    @pytest.mark.parametrize("filename", SPRINT_3_SCREENSHOTS)
    def test_screenshot_reasonable_size(self, filename):
        path = GUIDES_IMG_DIR / filename
        size = path.stat().st_size
        assert size >= 10_000, (
            f"Sprint 3 screenshot suspiciously small ({size} bytes): {filename}"
        )
        assert size <= 2_000_000, (
            f"Sprint 3 screenshot too large ({size} bytes, >2MB): {filename}"
        )

    def test_sprint3_screenshot_count(self):
        """Exactly 16 screenshots in Sprint 3 scope."""
        assert len(SPRINT_3_SCREENSHOTS) == 16


class TestSprint3DocPageReferences:
    """Each Sprint 3 screenshot must be referenced in its doc page."""

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


class TestSprint3NoCustomerNames:
    """No customer names in alt text or captions for Sprint 3 screenshots."""

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
