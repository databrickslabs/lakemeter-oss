import pytest

from upgrader.models import (
    ReleaseAction,
    ReleaseManifest,
    SemVer,
    UpgradePolicyError,
    transition_kind,
    validate_release_policy,
)


def manifest(version, operation="code_only", **overrides):
    values = {
        "version": SemVer.parse(version),
        "operation": operation,
        "minimum_version": SemVer.parse("0.1.0"),
    }
    values.update(overrides)
    return ReleaseManifest(**values)


def action(action_id="change"):
    return ReleaseAction(
        action_id=action_id,
        path=f"scripts/upgrades/{action_id}.sql",
        sha256="a" * 64,
    )


@pytest.mark.parametrize(
    ("installed", "target", "expected"),
    [
        ("0.1.0", "0.1.1", "patch"),
        ("0.1.9", "0.2.0", "minor"),
        ("1.9.9", "2.0.0", "major"),
        ("0.1.0", "0.1.0", "same"),
    ],
)
def test_transition_kind(installed, target, expected):
    assert transition_kind(SemVer.parse(installed), SemVer.parse(target)) == expected


def test_patch_must_be_code_only():
    release = manifest("0.1.1", operation="data_update", pricing_refresh=True)
    with pytest.raises(UpgradePolicyError, match="Patch releases"):
        validate_release_policy(SemVer.parse("0.1.0"), release)


def test_minor_allows_data_update():
    release = manifest(
        "0.2.0",
        operation="data_update",
        pricing_refresh=True,
        data_updates=(action("refresh-pricing"),),
    )
    assert validate_release_policy(SemVer.parse("0.1.3"), release) == "minor"


def test_minor_rejects_schema_migration():
    release = manifest("0.2.0", operation="schema_migration")
    with pytest.raises(UpgradePolicyError, match="Minor releases"):
        validate_release_policy(SemVer.parse("0.1.0"), release)


def test_major_allows_schema_migration():
    release = manifest(
        "2.0.0",
        operation="schema_migration",
        migrations=(action("schema-v2"),),
    )
    assert validate_release_policy(SemVer.parse("1.8.4"), release) == "major"


@pytest.mark.parametrize("target", ["0.2.1", "2.1.0"])
def test_release_boundary_must_reset_lower_components(target):
    with pytest.raises(UpgradePolicyError):
        transition_kind(SemVer.parse("0.1.0"), SemVer.parse(target))


def test_downgrade_requires_rollback():
    with pytest.raises(UpgradePolicyError, match="use rollback"):
        transition_kind(SemVer.parse("1.2.0"), SemVer.parse("1.1.0"))


@pytest.mark.parametrize(
    ("installed", "target"),
    [("0.1.0", "0.3.0"), ("1.5.0", "3.0.0")],
)
def test_database_release_lines_cannot_be_skipped(installed, target):
    with pytest.raises(UpgradePolicyError, match="cannot skip"):
        transition_kind(SemVer.parse(installed), SemVer.parse(target))

