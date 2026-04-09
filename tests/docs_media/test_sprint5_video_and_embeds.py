"""Sprint 5: Validate tutorial video + GIF/video embeds in doc pages."""

import re
from pathlib import Path

import pytest

from tests.docs_media.conftest import DOCS_DIR, VIDEO_DIR, GIFS_DIR

# --- Tutorial video ---

VIDEO_FILE = "getting-started-tutorial.mp4"
MP4_FTYP_MARKER = b"ftyp"
MIN_VIDEO_SIZE_BYTES = 1024  # At least 1KB
MAX_VIDEO_SIZE_MB = 50

# --- GIF embed expectations per doc page ---

GIF_EMBEDS = {
    "user-guide/getting-started.md": ["creating-estimate.gif"],
    "user-guide/workloads.md": ["adding-workload.gif"],
    "user-guide/creating-estimates.md": ["creating-estimate.gif", "drag-and-drop.gif"],
    "user-guide/ai-assistant.md": ["ai-assistant.gif"],
    "user-guide/exporting.md": ["export-excel.gif"],
    "user-guide/overview.md": ["cost-summary.gif"],
}

# Pages that must embed the tutorial video
VIDEO_EMBED_PAGES = [
    "user-guide/getting-started.md",
    "user-guide/end-to-end-workflow.md",
]

# Forbidden customer names (avoid overly broad patterns like "commerci"
# which matches legitimate words like "commercial")
FORBIDDEN_NAMES = ["maya", "merchant"]


class TestTutorialVideoFile:
    """Tutorial video must exist as a valid MP4."""

    def test_video_directory_exists(self):
        assert VIDEO_DIR.exists(), f"Video directory missing: {VIDEO_DIR}"

    def test_video_file_exists(self):
        path = VIDEO_DIR / VIDEO_FILE
        assert path.exists(), f"Tutorial video missing: {path}"

    def test_video_is_mp4_format(self):
        path = VIDEO_DIR / VIDEO_FILE
        if not path.exists():
            pytest.skip("Video file not yet created")
        with open(path, "rb") as f:
            header = f.read(12)
        # MP4 files have 'ftyp' at offset 4
        assert MP4_FTYP_MARKER in header[:12], (
            f"Video is not a valid MP4 (header: {header[:12].hex()}). "
            f"Expected 'ftyp' marker in first 12 bytes."
        )

    def test_video_not_too_small(self):
        path = VIDEO_DIR / VIDEO_FILE
        if not path.exists():
            pytest.skip("Video file not yet created")
        size = path.stat().st_size
        assert size >= MIN_VIDEO_SIZE_BYTES, (
            f"Video is only {size} bytes — minimum is {MIN_VIDEO_SIZE_BYTES}"
        )

    def test_video_not_too_large(self):
        path = VIDEO_DIR / VIDEO_FILE
        if not path.exists():
            pytest.skip("Video file not yet created")
        size_mb = path.stat().st_size / (1024 * 1024)
        assert size_mb <= MAX_VIDEO_SIZE_MB, (
            f"Video is {size_mb:.1f}MB — maximum is {MAX_VIDEO_SIZE_MB}MB"
        )

    def test_no_gitkeep_only(self):
        """Video directory should contain the actual video, not just .gitkeep."""
        real_files = [
            f for f in VIDEO_DIR.iterdir()
            if f.is_file() and not f.name.startswith(".")
        ]
        assert len(real_files) >= 1, (
            "Video directory contains no real files (only dotfiles)"
        )


class TestGifEmbedsInDocPages:
    """Each of the 7 doc pages must embed the expected GIFs."""

    @pytest.mark.parametrize(
        "page,expected_gifs",
        GIF_EMBEDS.items(),
        ids=list(GIF_EMBEDS.keys()),
    )
    def test_page_contains_gif_references(self, page, expected_gifs):
        doc_path = DOCS_DIR / page
        assert doc_path.exists(), f"Doc page missing: {page}"
        content = doc_path.read_text(encoding="utf-8")
        for gif in expected_gifs:
            expected_ref = f"/img/gifs/{gif}"
            assert expected_ref in content, (
                f"{page} is missing GIF embed for {gif} "
                f"(expected '{expected_ref}' in page content)"
            )

    @pytest.mark.parametrize(
        "page,expected_gifs",
        GIF_EMBEDS.items(),
        ids=[f"{k}:markdown" for k in GIF_EMBEDS.keys()],
    )
    def test_gif_embeds_use_markdown_image_syntax(self, page, expected_gifs):
        """GIF embeds should use ![alt](/img/gifs/...) markdown syntax."""
        doc_path = DOCS_DIR / page
        if not doc_path.exists():
            pytest.skip(f"{page} does not exist")
        content = doc_path.read_text(encoding="utf-8")
        for gif in expected_gifs:
            pattern = rf'!\[[^\]]+\]\(/img/gifs/{re.escape(gif)}\)'
            assert re.search(pattern, content), (
                f"{page}: GIF {gif} not embedded with markdown image syntax "
                f"![alt text](/img/gifs/{gif})"
            )

    @pytest.mark.parametrize(
        "page,expected_gifs",
        GIF_EMBEDS.items(),
        ids=[f"{k}:alt" for k in GIF_EMBEDS.keys()],
    )
    def test_gif_embeds_have_alt_text(self, page, expected_gifs):
        """GIF embeds must have non-empty alt text."""
        doc_path = DOCS_DIR / page
        if not doc_path.exists():
            pytest.skip(f"{page} does not exist")
        content = doc_path.read_text(encoding="utf-8")
        for gif in expected_gifs:
            pattern = rf'!\[([^\]]*)\]\(/img/gifs/{re.escape(gif)}\)'
            match = re.search(pattern, content)
            assert match, f"{page}: no embed found for {gif}"
            alt_text = match.group(1)
            assert len(alt_text.strip()) > 5, (
                f"{page}: GIF {gif} has empty or too-short alt text: '{alt_text}'"
            )

    @pytest.mark.parametrize(
        "page,expected_gifs",
        GIF_EMBEDS.items(),
        ids=[f"{k}:file" for k in GIF_EMBEDS.keys()],
    )
    def test_referenced_gif_files_exist(self, page, expected_gifs):
        """GIF files referenced in doc pages must exist on disk."""
        for gif in expected_gifs:
            gif_path = GIFS_DIR / gif
            assert gif_path.exists(), (
                f"{page} references {gif} but file not found at {gif_path}"
            )


class TestVideoEmbedsInDocPages:
    """Doc pages that should embed the tutorial video."""

    @pytest.mark.parametrize("page", VIDEO_EMBED_PAGES)
    def test_page_contains_video_tag(self, page):
        doc_path = DOCS_DIR / page
        assert doc_path.exists(), f"Doc page missing: {page}"
        content = doc_path.read_text(encoding="utf-8")
        assert "<video" in content, (
            f"{page} is missing <video> tag for tutorial video embed"
        )

    @pytest.mark.parametrize("page", VIDEO_EMBED_PAGES)
    def test_video_tag_has_controls(self, page):
        doc_path = DOCS_DIR / page
        if not doc_path.exists():
            pytest.skip(f"{page} does not exist")
        content = doc_path.read_text(encoding="utf-8")
        assert "controls" in content, (
            f"{page}: <video> tag is missing 'controls' attribute"
        )

    @pytest.mark.parametrize("page", VIDEO_EMBED_PAGES)
    def test_video_tag_has_source(self, page):
        doc_path = DOCS_DIR / page
        if not doc_path.exists():
            pytest.skip(f"{page} does not exist")
        content = doc_path.read_text(encoding="utf-8")
        assert "/video/getting-started-tutorial.mp4" in content, (
            f"{page}: <video> source does not reference getting-started-tutorial.mp4"
        )

    @pytest.mark.parametrize("page", VIDEO_EMBED_PAGES)
    def test_video_tag_has_aria_label(self, page):
        """Video embeds should have aria-label for accessibility."""
        doc_path = DOCS_DIR / page
        if not doc_path.exists():
            pytest.skip(f"{page} does not exist")
        content = doc_path.read_text(encoding="utf-8")
        assert "aria-label" in content, (
            f"{page}: <video> tag is missing 'aria-label' for accessibility"
        )

    @pytest.mark.parametrize("page", VIDEO_EMBED_PAGES)
    def test_video_tag_has_fallback(self, page):
        """Video embed should have fallback text for unsupported browsers."""
        doc_path = DOCS_DIR / page
        if not doc_path.exists():
            pytest.skip(f"{page} does not exist")
        content = doc_path.read_text(encoding="utf-8")
        assert "does not support" in content.lower() or "download" in content.lower(), (
            f"{page}: <video> tag is missing fallback text"
        )


class TestNoForbiddenNamesInNewContent:
    """No real customer names in GIF/video embed sections."""

    ALL_UPDATED_PAGES = list(GIF_EMBEDS.keys()) + VIDEO_EMBED_PAGES

    @pytest.mark.parametrize("page", list(set(ALL_UPDATED_PAGES)))
    def test_no_forbidden_names(self, page):
        doc_path = DOCS_DIR / page
        if not doc_path.exists():
            pytest.skip(f"{page} does not exist")
        content = doc_path.read_text(encoding="utf-8").lower()
        for name in FORBIDDEN_NAMES:
            assert name not in content, (
                f"{page} contains forbidden customer name '{name}'"
            )


class TestEmbedCounts:
    """Verify the expected total number of new embeds."""

    def test_total_gif_embeds(self):
        """At least 7 GIF embeds across the 6 pages (creating-estimates has 2)."""
        total = 0
        for page, gifs in GIF_EMBEDS.items():
            doc_path = DOCS_DIR / page
            if not doc_path.exists():
                continue
            content = doc_path.read_text(encoding="utf-8")
            for gif in gifs:
                if f"/img/gifs/{gif}" in content:
                    total += 1
        assert total >= 7, (
            f"Expected at least 7 GIF embeds across doc pages, found {total}"
        )

    def test_total_video_embeds(self):
        """2 pages should have video embeds."""
        total = 0
        for page in VIDEO_EMBED_PAGES:
            doc_path = DOCS_DIR / page
            if not doc_path.exists():
                continue
            content = doc_path.read_text(encoding="utf-8")
            if "<video" in content:
                total += 1
        assert total == 2, (
            f"Expected 2 video embeds, found {total}"
        )
