#!/usr/bin/env python3
"""Synchronize Lakemeter version metadata."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-.][0-9A-Za-z]+)?$")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


def _update_package(path: Path, version: str) -> None:
    data = _load_json(path)
    data["version"] = version
    _write_json(path, data)


def _update_lockfile(path: Path, version: str) -> None:
    data = _load_json(path)
    data["version"] = version
    if "" in data.get("packages", {}):
        data["packages"][""]["version"] = version
    _write_json(path, data)


def update_version(version: str) -> None:
    if not VERSION_PATTERN.match(version):
        raise SystemExit(f"Invalid version '{version}'. Expected format like 0.1.0.")

    (ROOT / "VERSION").write_text(f"{version}\n")
    (ROOT / "frontend/src/version.ts").write_text(f"export const APP_VERSION = '{version}'\n")

    _update_package(ROOT / "frontend/package.json", version)
    _update_lockfile(ROOT / "frontend/package-lock.json", version)
    _update_package(ROOT / "docs-site/package.json", version)
    _update_lockfile(ROOT / "docs-site/package-lock.json", version)

    print(f"Updated Lakemeter version metadata to {version}")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/update_version.py <version>")
    update_version(sys.argv[1])


if __name__ == "__main__":
    main()

