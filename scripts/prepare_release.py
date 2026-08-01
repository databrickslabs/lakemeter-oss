#!/usr/bin/env python3
"""Generate or verify checksums in the Lakemeter release manifest."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from upgrader.integrity import sha256_file, sha256_tree  # noqa: E402
from upgrader.payload import build_runtime_payload  # noqa: E402


def generate_manifest() -> tuple[dict, str]:
    manifest_path = ROOT / "scripts/upgrades/release.json"
    manifest = json.loads(manifest_path.read_text())
    for group in ("data_updates", "migrations"):
        for action in manifest.get(group, []):
            action["sha256"] = sha256_file(ROOT / action["path"])

    with tempfile.TemporaryDirectory() as temp_dir:
        runtime = Path(temp_dir) / "runtime"
        runtime.mkdir()
        build_runtime_payload(ROOT, runtime)
        runtime_hash = sha256_tree(runtime)
    manifest["runtime_sha256"] = runtime_hash
    return manifest, runtime_hash


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail instead of updating when checksums differ.",
    )
    args = parser.parse_args()

    path = ROOT / "scripts/upgrades/release.json"
    current = json.loads(path.read_text())
    generated, runtime_hash = generate_manifest()
    if args.check:
        if current != generated:
            raise SystemExit(
                "Release checksums are stale. Run: "
                "python scripts/prepare_release.py"
            )
        print(f"Release checksums verified: {runtime_hash}")
        return

    path.write_text(json.dumps(generated, indent=2) + "\n")
    print(f"Updated release checksums: {runtime_hash}")


if __name__ == "__main__":
    main()

