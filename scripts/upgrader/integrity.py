"""Release payload integrity checks."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .models import ReleaseManifest, UpgradePolicyError


HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_tree(root: Path) -> str:
    """Hash a runtime tree deterministically by relative path and contents."""
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def resolve_payload_path(root: Path, relative: str) -> Path:
    root = root.resolve()
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        raise UpgradePolicyError(
            f"Release action path escapes the payload root: {relative}"
        )
    return candidate


def verify_release_payload(
    repository_root: Path,
    payload_root: Path,
    manifest: ReleaseManifest,
) -> None:
    version = (repository_root / "VERSION").read_text().strip()
    if version != str(manifest.version):
        raise UpgradePolicyError(
            f"VERSION is {version}, but the release manifest targets "
            f"{manifest.version}."
        )

    for action in (*manifest.data_updates, *manifest.migrations):
        path = resolve_payload_path(repository_root, action.path)
        if not path.is_file():
            raise UpgradePolicyError(
                f"Release action {action.action_id} is missing: {action.path}"
            )
        if not HEX_SHA256.fullmatch(action.sha256):
            raise UpgradePolicyError(
                f"Release action {action.action_id} has an invalid SHA-256."
            )
        actual = sha256_file(path)
        if actual != action.sha256:
            raise UpgradePolicyError(
                f"Checksum mismatch for {action.action_id}: "
                f"expected {action.sha256}, got {actual}."
            )

    if manifest.runtime_sha256:
        if not HEX_SHA256.fullmatch(manifest.runtime_sha256):
            raise UpgradePolicyError("runtime_sha256 is not a valid SHA-256.")
        actual_runtime = sha256_tree(payload_root)
        if actual_runtime != manifest.runtime_sha256:
            raise UpgradePolicyError(
                "Runtime payload checksum mismatch: "
                f"expected {manifest.runtime_sha256}, got {actual_runtime}."
            )

