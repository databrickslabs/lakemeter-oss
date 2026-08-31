#!/usr/bin/env python3
"""Validate version alignment and Lakemeter release-policy compliance."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from upgrader.models import (  # noqa: E402
    ReleaseManifest,
    SemVer,
    UpgradePolicyError,
    transition_kind,
    validate_release_policy,
)


UPGRADE_SCHEMA_PATH_PREFIXES = (
    "scripts/upgrades/migrations/",
)
INSTALL_SCHEMA_PATH_PREFIXES = (
    "backend/app/models/",
    "etl/lakebase_setup/setup/",
    "etl/lakebase_setup/release_",
)
DATA_PATH_PREFIXES = (
    "scripts/upgrades/data_updates/",
    "backend/static/pricing/",
    "pricing_data/",
)


def _json_version(path: Path) -> str:
    return str(json.loads(path.read_text())["version"])


def version_sources() -> dict[str, str]:
    frontend_version = re.search(
        r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]",
        (ROOT / "frontend/src/version.ts").read_text(),
    )
    backend_version = re.search(
        r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]",
        (ROOT / "backend/app/version.py").read_text(),
    )
    if not frontend_version or not backend_version:
        raise UpgradePolicyError("Unable to parse generated version modules.")
    manifest = ReleaseManifest.load(ROOT / "scripts/upgrades/release.json")
    return {
        "VERSION": (ROOT / "VERSION").read_text().strip(),
        "frontend/package.json": _json_version(ROOT / "frontend/package.json"),
        "frontend/package-lock.json": _json_version(
            ROOT / "frontend/package-lock.json"
        ),
        "docs-site/package.json": _json_version(ROOT / "docs-site/package.json"),
        "docs-site/package-lock.json": _json_version(
            ROOT / "docs-site/package-lock.json"
        ),
        "frontend/src/version.ts": frontend_version.group(1),
        "backend/app/version.py": backend_version.group(1),
        "scripts/upgrades/release.json": str(manifest.version),
    }


def validate_version_alignment() -> str:
    sources = version_sources()
    versions = set(sources.values())
    if len(versions) != 1:
        details = ", ".join(f"{path}={value}" for path, value in sources.items())
        raise UpgradePolicyError(f"Version sources are inconsistent: {details}")
    return versions.pop()


def changed_files(base_ref: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def validate_changed_paths(
    previous_version: SemVer,
    manifest: ReleaseManifest,
    paths: list[str],
) -> None:
    kind = validate_release_policy(previous_version, manifest)
    upgrade_schema_changes = [
        path
        for path in paths
        if path.startswith(UPGRADE_SCHEMA_PATH_PREFIXES)
    ]
    install_schema_changes = [
        path
        for path in paths
        if path.startswith(INSTALL_SCHEMA_PATH_PREFIXES)
        or (
            path.endswith(".sql")
            and not path.startswith("scripts/upgrades/data_updates/")
            and not path.startswith(UPGRADE_SCHEMA_PATH_PREFIXES)
        )
    ]
    schema_changes = upgrade_schema_changes + install_schema_changes
    data_changes = [
        path for path in paths if path.startswith(DATA_PATH_PREFIXES)
    ]

    if kind == "patch" and (schema_changes or data_changes):
        raise UpgradePolicyError(
            "Patch releases cannot change database schema or data files: "
            + ", ".join(schema_changes + data_changes)
        )
    if kind == "minor" and upgrade_schema_changes:
        raise UpgradePolicyError(
            "Minor releases cannot change database schema files: "
            + ", ".join(upgrade_schema_changes)
        )
    if manifest.operation == "code_only" and (
        manifest.changes_database or data_changes
    ):
        raise UpgradePolicyError(
            "A code_only release contains database actions or data changes."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous-version")
    parser.add_argument("--base-ref")
    parser.add_argument(
        "--initial",
        action="store_true",
        help="Validate version alignment only for the first public release.",
    )
    args = parser.parse_args()

    current = validate_version_alignment()
    if args.initial:
        print(f"Release {current}: version sources aligned (initial release)")
        return
    if not args.previous_version or not args.base_ref:
        parser.error("--previous-version and --base-ref are required")

    manifest = ReleaseManifest.load(ROOT / "scripts/upgrades/release.json")
    previous = SemVer.parse(args.previous_version)
    paths = changed_files(args.base_ref)
    validate_changed_paths(previous, manifest, paths)
    kind = transition_kind(previous, manifest.version)
    print(
        f"Release {manifest.version}: {kind} / {manifest.operation}; "
        f"{len(paths)} changed files validated"
    )


if __name__ == "__main__":
    main()

