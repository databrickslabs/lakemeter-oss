"""Build the clean, deterministic Databricks App runtime payload."""

from __future__ import annotations

import re
import shutil
from collections import deque
from pathlib import Path


MAX_WORKSPACE_FILE_SIZE = 9 * 1024 * 1024
EXCLUDED_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".git",
    "node_modules",
}
EXCLUDED_SUFFIXES = {".pyc", ".csv", ".md"}
ASSET_REFERENCE = re.compile(
    r"(?:/assets/|\./)([A-Za-z0-9_.-]+\.(?:js|css|svg|png|jpg|jpeg|gif|webp|woff2?))"
)


def should_exclude(relative: Path) -> bool:
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return True
    if relative.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    if relative.name == "manifest.json" and "pricing" in relative.parts:
        return True
    return False


def referenced_assets(static_root: Path) -> set[str]:
    """Resolve the current Vite entrypoint and its lazy-loaded chunks."""
    index_path = static_root / "index.html"
    if not index_path.is_file():
        raise FileNotFoundError(f"Missing frontend entrypoint: {index_path}")

    discovered: set[str] = set()
    queue = deque(match.group(1) for match in ASSET_REFERENCE.finditer(
        index_path.read_text()
    ))
    while queue:
        name = queue.popleft()
        if name in discovered:
            continue
        path = static_root / "assets" / name
        if not path.is_file():
            raise FileNotFoundError(
                f"Frontend entrypoint references missing asset: assets/{name}"
            )
        discovered.add(name)
        if path.suffix in {".js", ".css"}:
            text = path.read_text(errors="ignore")
            for match in ASSET_REFERENCE.finditer(text):
                if match.group(1) not in discovered:
                    queue.append(match.group(1))
    if not discovered:
        raise RuntimeError("No frontend assets were referenced by index.html.")
    return discovered


def _copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def build_runtime_payload(repository_root: Path, destination: Path) -> None:
    """Assemble only runtime code, current frontend assets, and JSON pricing."""
    backend_app = repository_root / "backend/app"
    static_root = repository_root / "backend/static"
    selected_assets = referenced_assets(static_root)

    for path in sorted(backend_app.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(backend_app)
        if should_exclude(relative):
            continue
        _copy_file(path, destination / "backend/app" / relative)

    for path in sorted(static_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(static_root)
        if should_exclude(relative):
            continue
        if relative.parts and relative.parts[0] == "assets":
            if relative.name not in selected_assets:
                continue
        _copy_file(path, destination / "backend/static" / relative)

    _copy_file(repository_root / "app.yaml", destination / "app.yaml")
    _copy_file(repository_root / "requirements.txt", destination / "requirements.txt")

