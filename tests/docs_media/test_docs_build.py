"""Validate the docs site can build without errors."""

import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import pytest

from tests.docs_media.conftest import DOCS_SITE_DIR


class _LinkCollector(HTMLParser):
    """Collect links, assets, and anchors from generated HTML."""

    def __init__(self):
        super().__init__()
        self.links = []
        self.anchors = set()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.anchors.add(attributes["id"])
        if tag == "a" and "name" in attributes:
            self.anchors.add(attributes["name"])
        for attribute in ("href", "src"):
            if attribute in attributes:
                self.links.append(attributes[attribute])


def _parse_html(path):
    parser = _LinkCollector()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    return parser


def _assert_generated_links_resolve(build_dir):
    """Validate links as GitHub Pages resolves direct trailing-slash URLs."""
    origin = "https://databrickslabs.github.io"
    base_path = "/lakemeter-oss/"
    parsed_files = {}
    failures = []

    for source in build_dir.rglob("*.html"):
        relative = source.relative_to(build_dir).as_posix()
        if relative == "index.html":
            route = base_path
        elif relative.endswith("/index.html"):
            route = f"{base_path}{relative[:-10]}/"
        else:
            route = f"{base_path}{relative}"

        for raw_link in _parse_html(source).links:
            if not raw_link or raw_link.startswith(
                ("#", "data:", "javascript:", "mailto:", "tel:")
            ):
                continue

            target_url = urlparse(urljoin(f"{origin}{route}", raw_link))
            if (
                target_url.netloc != "databrickslabs.github.io"
                or not target_url.path.startswith(base_path)
            ):
                continue

            target_path = unquote(target_url.path[len(base_path) :])
            if not target_path or target_path.endswith("/"):
                candidates = [build_dir / target_path / "index.html"]
            elif Path(target_path).suffix:
                candidates = [build_dir / target_path]
            else:
                candidates = [
                    build_dir / target_path / "index.html",
                    build_dir / f"{target_path}.html",
                    build_dir / target_path,
                ]

            target = next(
                (candidate for candidate in candidates if candidate.exists()),
                None,
            )
            if target is None:
                failures.append(
                    f"{relative}: {raw_link} -> {target_url.path}"
                )
                continue

            if target_url.fragment and target.suffix == ".html":
                parser = parsed_files.setdefault(target, _parse_html(target))
                if target_url.fragment not in parser.anchors:
                    failures.append(
                        f"{relative}: {raw_link} -> missing anchor "
                        f"#{target_url.fragment}"
                    )

    assert not failures, (
        "Generated documentation contains broken internal links:\n"
        + "\n".join(failures)
    )


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
        _assert_generated_links_resolve(DOCS_SITE_DIR / "build")

    def test_package_json_has_build_script(self):
        """package.json must have a build script."""
        import json

        pkg = DOCS_SITE_DIR / "package.json"
        assert pkg.exists(), "package.json not found"
        data = json.loads(pkg.read_text(encoding="utf-8"))
        assert "build" in data.get("scripts", {}), (
            "package.json missing 'build' script"
        )
