from pathlib import Path

import pytest

from upgrader.integrity import (
    resolve_payload_path,
    sha256_file,
    sha256_tree,
    verify_release_payload,
)
from upgrader.models import (
    ReleaseAction,
    ReleaseManifest,
    SemVer,
    UpgradePolicyError,
)


def test_tree_hash_is_deterministic(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    for root in (first, second):
        (root / "nested").mkdir(parents=True)
        (root / "b.txt").write_text("two")
        (root / "nested/a.txt").write_text("one")

    assert sha256_tree(first) == sha256_tree(second)


def test_payload_path_cannot_escape_root(tmp_path):
    with pytest.raises(UpgradePolicyError, match="escapes"):
        resolve_payload_path(tmp_path, "../outside.sql")


def test_release_action_checksum_is_verified(tmp_path):
    runtime = tmp_path / "app_source"
    runtime.mkdir()
    (runtime / "main.py").write_text("print('ok')")
    (tmp_path / "VERSION").write_text("1.0.0\n")
    action_path = tmp_path / "scripts/upgrades/migrations/001.sql"
    action_path.parent.mkdir(parents=True)
    action_path.write_text("SELECT 1;")

    manifest = ReleaseManifest(
        version=SemVer.parse("1.0.0"),
        operation="schema_migration",
        minimum_version=SemVer.parse("0.1.0"),
        migrations=(
            ReleaseAction(
                action_id="001",
                path="scripts/upgrades/migrations/001.sql",
                sha256=sha256_file(action_path),
            ),
        ),
        runtime_sha256=sha256_tree(runtime),
    )

    verify_release_payload(tmp_path, runtime, manifest)
    action_path.write_text("SELECT 2;")
    with pytest.raises(UpgradePolicyError, match="Checksum mismatch"):
        verify_release_payload(tmp_path, runtime, manifest)

