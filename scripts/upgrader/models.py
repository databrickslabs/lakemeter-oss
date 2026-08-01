"""Core data models and release-policy enforcement for upgrades."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SEMVER_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"$"
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
OPERATIONS = {"code_only", "data_update", "schema_migration"}


class UpgradePolicyError(ValueError):
    """Raised when a release violates Lakemeter's upgrade contract."""


@dataclass(frozen=True)
class SemVer:
    """Minimal SemVer value used for deterministic upgrade policy checks."""

    major: int
    minor: int
    patch: int
    suffix: str = ""

    @classmethod
    def parse(cls, value: str) -> "SemVer":
        match = SEMVER_PATTERN.fullmatch(value.strip().removeprefix("v"))
        if not match:
            raise UpgradePolicyError(
                f"Invalid version '{value}'. Expected MAJOR.MINOR.PATCH."
            )
        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
        )

    @property
    def core(self) -> tuple[int, int, int]:
        return self.major, self.minor, self.patch

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}{self.suffix}"


def transition_kind(installed: SemVer, target: SemVer) -> str:
    """Classify an upgrade according to the Lakemeter release contract."""
    if target.core <= installed.core:
        if target.core == installed.core:
            return "same"
        raise UpgradePolicyError(
            f"Target {target} is older than installed version {installed}; use rollback."
        )
    if target.major > installed.major:
        if target.major != installed.major + 1:
            raise UpgradePolicyError(
                f"Major upgrades cannot skip a release line: {installed} to {target}."
            )
        if target.minor != 0 or target.patch != 0:
            raise UpgradePolicyError(
                f"Major upgrades must target X.0.0, not {target}."
            )
        return "major"
    if target.minor > installed.minor:
        if target.minor != installed.minor + 1:
            raise UpgradePolicyError(
                f"Minor upgrades cannot skip a data release: {installed} to {target}."
            )
        if target.patch != 0:
            raise UpgradePolicyError(
                f"Minor upgrades must target X.Y.0, not {target}."
            )
        return "minor"
    return "patch"


@dataclass(frozen=True)
class ReleaseAction:
    """A checksummed migration or data-update module."""

    action_id: str
    path: str
    sha256: str
    transactional: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReleaseAction":
        required = {"id", "path", "sha256"}
        missing = required - data.keys()
        if missing:
            raise UpgradePolicyError(
                f"Release action is missing fields: {', '.join(sorted(missing))}"
            )
        action_id = str(data["id"])
        action_path = Path(str(data["path"]))
        checksum = str(data["sha256"]).lower()
        if action_path.is_absolute() or ".." in action_path.parts:
            raise UpgradePolicyError(
                f"Release action {action_id} must use a repository-relative path."
            )
        if not SHA256_PATTERN.fullmatch(checksum):
            raise UpgradePolicyError(
                f"Release action {action_id} has an invalid SHA-256 checksum."
            )
        return cls(
            action_id=action_id,
            path=action_path.as_posix(),
            sha256=checksum,
            transactional=bool(data.get("transactional", True)),
        )


@dataclass(frozen=True)
class ReleaseManifest:
    """Machine-readable release behavior consumed by the upgrader."""

    version: SemVer
    operation: str
    minimum_version: SemVer
    data_updates: tuple[ReleaseAction, ...] = ()
    migrations: tuple[ReleaseAction, ...] = ()
    pricing_refresh: bool = False
    runtime_sha256: str = ""

    @classmethod
    def load(cls, path: Path) -> "ReleaseManifest":
        data = json.loads(path.read_text())
        operation = str(data.get("operation", ""))
        if operation not in OPERATIONS:
            raise UpgradePolicyError(
                f"Invalid release operation '{operation}'. "
                f"Expected one of {sorted(OPERATIONS)}."
            )
        manifest = cls(
            version=SemVer.parse(str(data["version"])),
            operation=operation,
            minimum_version=SemVer.parse(str(data.get("minimum_version", "0.1.0"))),
            data_updates=tuple(
                ReleaseAction.from_dict(item)
                for item in data.get("data_updates", [])
            ),
            migrations=tuple(
                ReleaseAction.from_dict(item)
                for item in data.get("migrations", [])
            ),
            pricing_refresh=bool(data.get("pricing_refresh", False)),
            runtime_sha256=str(data.get("runtime_sha256", "")).lower(),
        )
        action_ids = [
            action.action_id
            for action in (*manifest.migrations, *manifest.data_updates)
        ]
        duplicates = sorted(
            action_id
            for action_id in set(action_ids)
            if action_ids.count(action_id) > 1
        )
        if duplicates:
            raise UpgradePolicyError(
                "Duplicate database action IDs: " + ", ".join(duplicates)
            )
        if manifest.pricing_refresh and not manifest.data_updates:
            raise UpgradePolicyError(
                "pricing_refresh requires an explicit checksummed data update."
            )
        return manifest

    @property
    def changes_database(self) -> bool:
        return bool(self.data_updates or self.migrations or self.pricing_refresh)


def validate_release_policy(
    installed: SemVer,
    manifest: ReleaseManifest,
) -> str:
    """Validate release contents against patch/minor/major guarantees."""
    kind = transition_kind(installed, manifest.version)
    if kind == "same":
        return kind
    if installed.core < manifest.minimum_version.core:
        raise UpgradePolicyError(
            f"Installed version {installed} is below this release's minimum "
            f"supported version {manifest.minimum_version}."
        )
    if kind == "patch":
        if manifest.operation != "code_only" or manifest.changes_database:
            raise UpgradePolicyError(
                "Patch releases must be code_only and cannot change database data "
                "or schema."
            )
    elif kind == "minor":
        if (
            manifest.operation != "data_update"
            or not manifest.data_updates
            or manifest.migrations
        ):
            raise UpgradePolicyError(
                "Minor releases must declare data_update, include at least one data "
                "update, and cannot contain schema migrations."
            )
    elif kind == "major":
        if manifest.operation != "schema_migration" or not manifest.migrations:
            raise UpgradePolicyError(
                "Major releases must declare schema_migration and include at "
                "least one schema migration."
            )
    return kind


@dataclass
class Installation:
    """Discovered live installation details."""

    app_name: str
    app_url: str
    source_path: str
    active_source_path: str | None
    installed_version: SemVer
    workspace_user: str
    secret_scope: str | None = None
    database_name: str | None = None
    database_host: str | None = None
    database_user: str | None = None
    database_host_secret_scope: str | None = None
    database_host_secret_key: str | None = None
    lakebase_project: str | None = None
    lakebase_branch: str | None = None
    lakebase_branch_secret_scope: str | None = None
    lakebase_branch_secret_key: str | None = None
    lakebase_endpoint: str | None = None
    lakebase_endpoint_secret_scope: str | None = None
    lakebase_endpoint_secret_key: str | None = None
    lakebase_instance: str | None = None
    legacy_baseline: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def management_path(self) -> str:
        return f"{self.source_path.rstrip('/')}/.lakemeter"


@dataclass
class UpgradePlan:
    """Resolved upgrade plan displayed before any mutation."""

    installation: Installation
    manifest: ReleaseManifest
    transition: str
    run_id: str

    @property
    def requires_database_backup(self) -> bool:
        return self.manifest.changes_database

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "app_name": self.installation.app_name,
            "app_url": self.installation.app_url,
            "installed_version": str(self.installation.installed_version),
            "target_version": str(self.manifest.version),
            "transition": self.transition,
            "operation": self.manifest.operation,
            "database_backup_required": self.requires_database_backup,
            "data_updates": [item.action_id for item in self.manifest.data_updates],
            "migrations": [item.action_id for item in self.manifest.migrations],
            "pricing_refresh": self.manifest.pricing_refresh,
            "legacy_baseline": self.installation.legacy_baseline,
            "warnings": self.installation.warnings,
        }

