---
sidebar_position: 3
---

# Upgrade Guide

Lakemeter includes a version-aware upgrade utility at `scripts/upgrade.sh`. It
discovers the existing installation, validates the checked-out release, applies
the release's Semantic Versioning policy, and verifies the deployed app and its
database connection.

:::important Update the repository first
The upgrader applies the release that is present in your local checkout. It
does not download a release automatically. Update the repository, check out the
desired release tag, or download a fresh release archive before upgrading.
:::

## Upgrade policy

Lakemeter uses the following release policy:

- **Patch release** (`0.1.0` to `0.1.1`): application code only. The upgrader
  does not stop, back up, or modify Lakebase.
- **Minor release** (`0.1.1` to `0.2.0`): data-only database updates. The
  upgrader creates a Lakebase backup branch before applying them.
- **Major release** (`0.x.x` to `1.0.0`, or `1.x.x` to `2.0.0`): schema
  migrations, optionally followed by data updates. The upgrader creates a
  Lakebase backup branch first.

Database release lines cannot be skipped. For example, upgrade through a
required `0.2.x` data release before moving to `0.3.0`.

## Prerequisites

Before starting:

1. Install the Databricks CLI and authenticate a workspace profile.
2. Use a clean checkout of the release you want to install.
3. Confirm the existing Databricks App is running.
4. For minor or major releases, ensure the installation uses Lakebase
   Autoscaling project, branch, and endpoint bindings.

Verify CLI access:

```bash
databricks current-user me --profile <profile>
```

Prepare a release checkout:

```bash
git fetch --tags
git checkout <release-tag>
git status --short
```

`git status --short` should return no output. Production upgrades reject a
dirty checkout.

## Check the installation

Run these read-only commands before applying a release:

```bash
./scripts/upgrade.sh status --profile <profile>
./scripts/upgrade.sh plan --profile <profile>
./scripts/upgrade.sh doctor --profile <profile>
```

Use `--app-name <name>` when the app is not named `lakemeter`.

### `status`

Shows the discovered installation version, app source, Lakebase resources, and
the latest recorded upgrade run.

### `plan`

Validates the release manifest and runtime checksum, then reports:

- Installed and target versions
- Patch, minor, major, or same-version transition
- Declared migrations and data updates
- Whether a database backup is required
- Discovery warnings that should be reviewed before applying

### `doctor`

Checks workspace access, app discovery, release policy, payload integrity, and
the backup prerequisites required by the current release.

Do not apply a release while `doctor` reports `blocked`.

:::note Older installations
Installations created by the current installer already expose the Lakebase
Autoscaling project, `production` branch, `primary` endpoint, and their secret
bindings. If a future database-changing release reports missing branch or
endpoint bindings for an older installation, update to the latest patch and
run the current installer once. The installer reuses the existing project and
app and adds the required bindings without deleting estimates.
:::

## Apply an upgrade

Run the plan and doctor checks first, then apply:

```bash
./scripts/upgrade.sh apply --profile <profile>
```

The command asks for confirmation. For unattended automation:

```bash
./scripts/upgrade.sh apply --profile <profile> --yes
```

Use `--allow-dirty` only when developing the upgrade utility. It should not be
used for production upgrades.

## What happens during an upgrade

Every release follows these common steps:

1. Discover the deployed app, installed version, active source path, Lakebase
   resources, and secret bindings.
2. Validate the release manifest, Semantic Versioning transition, action
   checksums, and complete runtime checksum.
3. Acquire a workspace run lock so two upgrades cannot run concurrently.
4. Stage an immutable runtime at:

   ```text
   <app-source>/releases/v<version>
   ```

5. Preserve the installation's existing `app.yaml` and resource bindings.
6. Deploy the versioned runtime.
7. Call the authenticated health and version endpoints.
8. Require the expected app version and a successful database connection.
9. Record the completed release and deployment in workspace state.

### Patch releases

Patch upgrades stage and deploy application code only. Lakebase remains online
and is not modified.

### Minor and major releases

Before changing the database, the upgrader:

1. Connects with a short-lived Lakebase OAuth credential.
2. Acquires a PostgreSQL advisory lock.
3. Stops the app to prevent writes during the backup and database update.
4. Creates a copy-on-write branch from the production branch.
5. Ensures the backup branch has a queryable endpoint.
6. Executes each declared database action in manifest order.
7. Restarts the app, deploys the new runtime, and verifies it.

Minor releases can execute only declared data updates. Major releases can
execute schema migrations and data updates.

## Idempotency and interrupted runs

The upgrader is safe to run repeatedly:

- Applying an already-installed version returns `no_change`.
- A successful versioned runtime cannot be overwritten with different content.
- Completed phases are recorded and reused when a run resumes.
- Completed data updates are not executed again.
- Schema migrations are recorded with their checksums.
- Workspace and PostgreSQL locks prevent concurrent upgrade runs.

The upgrader intentionally does not replay a database action marked `started`
when its commit result is unknown after an interruption. Replaying it could
duplicate a non-idempotent change. The upgrader fails safely and rolls back to
the recorded recovery point instead.

Release SQL should still be written defensively, using transactions and
idempotent statements where practical.

## Automatic recovery

If an upgrade fails, the upgrader attempts to:

1. Release the database advisory lock.
2. Repoint database secrets to the pre-upgrade backup branch, when one exists.
3. Redeploy the previous application source.
4. Restart the app.
5. Restore the previous installation metadata.
6. Record any rollback errors for operator review.

Patch failures restore only the previous application because patch releases do
not create database backups.

## Manual rollback

To roll back the latest recorded upgrade:

```bash
./scripts/upgrade.sh rollback --profile <profile>
```

For a database-changing release, rollback points the app to the backup branch
and deploys the previous application source. It does not overwrite the original
production branch.

After rollback:

```bash
./scripts/upgrade.sh status --profile <profile>
```

Then confirm the app's health endpoint:

```text
https://<app-url>/api/v1/system/health
```

Expected response:

```json
{
  "status": "healthy",
  "database": "connected"
}
```

## Troubleshooting

### Repository has uncommitted changes

Use a clean release checkout. Do not use `--allow-dirty` to bypass this check
for a production installation.

### Installed version cannot be discovered

Older installations without version metadata are treated as the legacy
baseline version. Review the warning in `plan` before applying.

### Database backup capability is blocked

Confirm the app has secret resources for:

- `lakebase-project`
- `lakebase-branch`
- `lakebase-endpoint`
- `lakebase-host`

The current installer configures these automatically.

### Another upgrade holds the lock

Check `status` for an active run. Do not manually remove a lock while an
upgrade job is still running.

### Deployment verification fails

Review the Databricks App deployment logs and the upgrade run output. The
upgrader will already have attempted automatic recovery.

