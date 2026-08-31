import pytest

from validate_release import (
    validate_changed_paths,
    validate_version_alignment,
)
from upgrader.models import (
    ReleaseAction,
    ReleaseManifest,
    SemVer,
    UpgradePolicyError,
)


def release(version, operation):
    action = ReleaseAction(
        action_id="test-action",
        path="scripts/upgrades/test-action.sql",
        sha256="a" * 64,
    )
    return ReleaseManifest(
        version=SemVer.parse(version),
        operation=operation,
        minimum_version=SemVer.parse("0.1.0"),
        data_updates=(action,) if operation == "data_update" else (),
        migrations=(action,) if operation == "schema_migration" else (),
    )


def test_repository_version_sources_are_aligned():
    assert validate_version_alignment() == "0.2.0"


def test_patch_rejects_database_data_file():
    with pytest.raises(UpgradePolicyError, match="Patch releases"):
        validate_changed_paths(
            SemVer.parse("0.1.0"),
            release("0.1.1", "code_only"),
            ["backend/static/pricing/dbu-rates.json"],
        )


def test_minor_rejects_schema_definition_change():
    with pytest.raises(UpgradePolicyError, match="Minor releases"):
        validate_changed_paths(
            SemVer.parse("0.1.0"),
            release("0.2.0", "data_update"),
            ["scripts/upgrades/migrations/001-add-column.sql"],
        )


@pytest.mark.parametrize(
    "path",
    [
        "backend/app/models/estimate.py",
        "etl/lakebase_setup/setup/01_Create_Tables.py",
        "etl/lakebase_setup/release_2/00_Add_Missing_API_Columns.sql",
    ],
)
def test_minor_allows_install_schema_alignment(path):
    validate_changed_paths(
        SemVer.parse("0.1.0"),
        release("0.2.0", "data_update"),
        [path],
    )


def test_patch_still_rejects_install_schema_alignment():
    with pytest.raises(UpgradePolicyError, match="Patch releases"):
        validate_changed_paths(
            SemVer.parse("0.1.0"),
            release("0.1.1", "code_only"),
            ["backend/app/models/estimate.py"],
        )


def test_minor_allows_data_update_module():
    manifest = release("0.2.0", "data_update")
    validate_changed_paths(
        SemVer.parse("0.1.0"),
        manifest,
        ["scripts/upgrades/data_updates/020-refresh.sql"],
    )

