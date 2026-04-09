"""Validate the docs site can build without errors."""

import subprocess
from pathlib import Path

import pytest

from tests.docs_media.conftest import DOCS_SITE_DIR


@pytest.mark.slow
class TestDocsSiteBuild:
    """Docs site must build without broken link or image errors."""

    def test_node_modules_exist(self):
        """Node modules must be installed before build can run."""
        node_modules = DOCS_SITE_DIR / "node_modules"
        if not node_modules.exists():
            pytest.skip(
                "node_modules not installed — run 'cd docs-site && npm install'"
            )

    def test_docs_build_succeeds(self):
        """npm run build must exit 0 with no broken link errors."""
        node_modules = DOCS_SITE_DIR / "node_modules"
        if not node_modules.exists():
            pytest.skip("node_modules not installed")

        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(DOCS_SITE_DIR),
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, (
            f"Docs build failed with exit code {result.returncode}.\n"
            f"STDERR:\n{result.stderr[-2000:]}"
        )

    def test_package_json_has_build_script(self):
        """package.json must have a build script."""
        import json

        pkg = DOCS_SITE_DIR / "package.json"
        assert pkg.exists(), "package.json not found"
        data = json.loads(pkg.read_text(encoding="utf-8"))
        assert "build" in data.get("scripts", {}), (
            "package.json missing 'build' script"
        )
