"""Sprint 4: Validate workflow GIF files — existence, format, size, naming."""

from pathlib import Path

import pytest

from tests.docs_media.conftest import GIFS_DIR

# The 6 workflow GIFs Sprint 4 must deliver
SPRINT_4_GIFS = [
    "creating-estimate.gif",
    "adding-workload.gif",
    "drag-and-drop.gif",
    "ai-assistant.gif",
    "export-excel.gif",
    "cost-summary.gif",
]

# GIF89a magic bytes
GIF89A_MAGIC = b"GIF89a"

# Size bounds
MIN_SIZE_KB = 50
MAX_SIZE_MB = 5

# Forbidden customer names in filenames
FORBIDDEN_NAMES = ["maya", "merchant", "commerci"]

# Doc pages that will embed each GIF (Sprint 5 handles embedding, but we validate readiness)
GIF_TO_DOC_PAGE = {
    "creating-estimate.gif": ["user-guide/creating-estimates.md", "user-guide/getting-started.md"],
    "adding-workload.gif": ["user-guide/workloads.md"],
    "drag-and-drop.gif": ["user-guide/creating-estimates.md"],
    "ai-assistant.gif": ["user-guide/ai-assistant.md"],
    "export-excel.gif": ["user-guide/exporting.md"],
    "cost-summary.gif": ["user-guide/overview.md"],
}


class TestGifFilesExist:
    """All 6 GIF files must exist in the gifs directory."""

    def test_gifs_directory_exists(self):
        assert GIFS_DIR.exists(), f"GIFs directory missing: {GIFS_DIR}"

    @pytest.mark.parametrize("filename", SPRINT_4_GIFS)
    def test_gif_exists(self, filename):
        path = GIFS_DIR / filename
        assert path.exists(), f"Workflow GIF missing: {filename}"

    def test_gif_count(self):
        """Exactly 6 GIF files in the directory."""
        gif_files = list(GIFS_DIR.glob("*.gif"))
        assert len(gif_files) == 6, (
            f"Expected 6 GIFs, found {len(gif_files)}: "
            f"{[f.name for f in gif_files]}"
        )

    def test_no_unexpected_files(self):
        """Only .gif files in the directory (no .tmp, .bak, etc.)."""
        non_gif = [
            f for f in GIFS_DIR.iterdir()
            if f.is_file() and f.suffix != ".gif" and not f.name.startswith(".")
        ]
        assert len(non_gif) == 0, (
            f"Unexpected files in gifs/: {[f.name for f in non_gif]}"
        )


class TestGifFormat:
    """Each GIF must be a valid GIF89a file."""

    @pytest.mark.parametrize("filename", SPRINT_4_GIFS)
    def test_gif89a_magic_bytes(self, filename):
        path = GIFS_DIR / filename
        if not path.exists():
            pytest.skip(f"{filename} does not exist yet")
        with open(path, "rb") as f:
            header = f.read(6)
        assert header == GIF89A_MAGIC, (
            f"{filename} is not a valid GIF89a file (header: {header!r})"
        )

    @pytest.mark.parametrize("filename", SPRINT_4_GIFS)
    def test_gif_has_multiple_frames(self, filename):
        """Each GIF must be animated (>1 frame)."""
        path = GIFS_DIR / filename
        if not path.exists():
            pytest.skip(f"{filename} does not exist yet")
        from PIL import Image
        img = Image.open(path)
        assert img.n_frames > 1, (
            f"{filename} has only {img.n_frames} frame — must be animated"
        )

    @pytest.mark.parametrize("filename", SPRINT_4_GIFS)
    def test_gif_width_800(self, filename):
        """Each GIF must be ~800px wide."""
        path = GIFS_DIR / filename
        if not path.exists():
            pytest.skip(f"{filename} does not exist yet")
        from PIL import Image
        img = Image.open(path)
        assert 750 <= img.size[0] <= 850, (
            f"{filename} width is {img.size[0]}px, expected ~800px"
        )


class TestGifSizeBounds:
    """Each GIF must be between 50KB and 5MB."""

    @pytest.mark.parametrize("filename", SPRINT_4_GIFS)
    def test_gif_not_too_small(self, filename):
        path = GIFS_DIR / filename
        if not path.exists():
            pytest.skip(f"{filename} does not exist yet")
        size_kb = path.stat().st_size / 1024
        assert size_kb >= MIN_SIZE_KB, (
            f"{filename} is only {size_kb:.0f}KB — minimum is {MIN_SIZE_KB}KB"
        )

    @pytest.mark.parametrize("filename", SPRINT_4_GIFS)
    def test_gif_not_too_large(self, filename):
        path = GIFS_DIR / filename
        if not path.exists():
            pytest.skip(f"{filename} does not exist yet")
        size_mb = path.stat().st_size / (1024 * 1024)
        assert size_mb <= MAX_SIZE_MB, (
            f"{filename} is {size_mb:.1f}MB — maximum is {MAX_SIZE_MB}MB"
        )


class TestGifNaming:
    """GIF filenames must follow conventions and not contain forbidden names."""

    @pytest.mark.parametrize("filename", SPRINT_4_GIFS)
    def test_no_forbidden_names_in_filename(self, filename):
        lower = filename.lower()
        for name in FORBIDDEN_NAMES:
            assert name not in lower, (
                f"Forbidden name '{name}' found in GIF filename: {filename}"
            )

    @pytest.mark.parametrize("filename", SPRINT_4_GIFS)
    def test_kebab_case_naming(self, filename):
        """GIF filenames should use kebab-case."""
        stem = Path(filename).stem
        assert stem == stem.lower(), f"Filename not lowercase: {filename}"
        assert "_" not in stem, f"Use kebab-case not snake_case: {filename}"


class TestGifDocPageReadiness:
    """Verify GIF paths will resolve correctly for Docusaurus embedding."""

    @pytest.mark.parametrize("gif,pages", GIF_TO_DOC_PAGE.items())
    def test_static_path_format(self, gif, pages):
        """GIF can be referenced as /img/gifs/{gif} in Docusaurus."""
        expected_path = f"/img/gifs/{gif}"
        # Just verify the static file exists where Docusaurus expects it
        actual_path = GIFS_DIR / gif
        if not actual_path.exists():
            pytest.skip(f"{gif} does not exist yet")
        assert actual_path.exists(), (
            f"GIF {gif} not found at expected Docusaurus static path"
        )

    @pytest.mark.parametrize("gif,pages", GIF_TO_DOC_PAGE.items())
    def test_target_doc_pages_exist(self, gif, pages):
        """Doc pages that will embed this GIF must exist."""
        from tests.docs_media.conftest import DOCS_DIR
        for page in pages:
            doc_path = DOCS_DIR / page
            assert doc_path.exists(), (
                f"Target doc page {page} for {gif} does not exist"
            )
