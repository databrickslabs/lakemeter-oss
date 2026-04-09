"""Validate all image references in doc pages point to existing files."""

import re
from pathlib import Path

import pytest

from tests.docs_media.conftest import DOCS_DIR, DOCS_SITE_DIR, STATIC_IMG_DIR


def _collect_image_refs():
    """Collect all markdown image references from doc files."""
    refs = []
    for md_file in DOCS_DIR.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        # Match ![alt text](/img/path.ext)
        for match in re.finditer(
            r'!\[([^\]]*)\]\((/img/[^)]+)\)', content
        ):
            alt_text = match.group(1)
            img_path = match.group(2)
            refs.append((md_file, alt_text, img_path))
    return refs


IMAGE_REFS = _collect_image_refs()


class TestImageReferencesExist:
    """Every image reference in docs must point to an existing file."""

    @pytest.mark.parametrize(
        "md_file,alt_text,img_path",
        IMAGE_REFS,
        ids=[
            f"{r[0].relative_to(DOCS_DIR)}:{r[2]}"
            for r in IMAGE_REFS
        ],
    )
    def test_image_file_exists(self, md_file, alt_text, img_path):
        """Image reference must resolve to a real file in static/."""
        # /img/foo.png -> docs-site/static/img/foo.png
        relative = img_path.lstrip("/")
        full_path = DOCS_SITE_DIR / "static" / relative
        assert full_path.exists(), (
            f"{md_file.relative_to(DOCS_DIR)}: "
            f"references {img_path} but file not found at {full_path}"
        )

    @pytest.mark.parametrize(
        "md_file,alt_text,img_path",
        IMAGE_REFS,
        ids=[
            f"{r[0].relative_to(DOCS_DIR)}:alt:{r[2]}"
            for r in IMAGE_REFS
        ],
    )
    def test_image_has_alt_text(self, md_file, alt_text, img_path):
        """Every image reference should have descriptive alt text."""
        assert len(alt_text.strip()) > 0, (
            f"{md_file.relative_to(DOCS_DIR)}: "
            f"image {img_path} has empty alt text"
        )


class TestImageFilesNotEmpty:
    """All image files must be non-zero size."""

    @pytest.fixture
    def all_image_files(self):
        pngs = list(STATIC_IMG_DIR.rglob("*.png"))
        gifs = list(STATIC_IMG_DIR.rglob("*.gif"))
        return [f for f in pngs + gifs if f.name != "docusaurus.png"]

    def test_no_zero_byte_images(self, all_image_files):
        """No image file should be zero bytes."""
        zero_byte = [f for f in all_image_files if f.stat().st_size == 0]
        assert len(zero_byte) == 0, (
            f"Found zero-byte image files: "
            f"{[str(f.relative_to(STATIC_IMG_DIR)) for f in zero_byte]}"
        )

    def test_png_files_reasonable_size(self, all_image_files):
        """PNG files should be under 2MB (reasonable for doc screenshots)."""
        oversized = [
            (f, f.stat().st_size)
            for f in all_image_files
            if f.suffix == ".png" and f.stat().st_size > 2 * 1024 * 1024
        ]
        assert len(oversized) == 0, (
            f"Oversized PNG files (>2MB): "
            f"{[(str(f.relative_to(STATIC_IMG_DIR)), s) for f, s in oversized]}"
        )


class TestImageReferenceCount:
    """Sanity checks on the total number of image references."""

    def test_minimum_image_refs(self):
        """Docs should have at least 50 image references."""
        assert len(IMAGE_REFS) >= 50, (
            f"Expected at least 50 image references, found {len(IMAGE_REFS)}"
        )

    def test_core_screenshots_referenced(self):
        """Core screenshots should be referenced in at least one doc page."""
        core_files = [
            "home-page.png",
            "calculator-overview.png",
            "estimates-list.png",
            "all-workloads-overview.png",
            "workload-expanded-config.png",
            "estimate-with-workloads.png",
            "workload-calculation-detail.png",
        ]
        referenced_images = {ref[2].split("/")[-1] for ref in IMAGE_REFS}
        for core_file in core_files:
            assert core_file in referenced_images, (
                f"Core screenshot {core_file} is not referenced in any doc page"
            )
