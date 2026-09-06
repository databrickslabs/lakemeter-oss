---
sidebar_position: 2
---

# Marketplace Installation and Security

Lakemeter can be installed directly from Databricks Marketplace as a managed
Databricks App. The Marketplace package is self-contained: installation does
not require a local CLI, an installer notebook, a personal access token, or a
separate pricing-data upload.

This page describes the resources, permissions, network access, bootstrap
behavior, and upgrade lifecycle of the Marketplace distribution. For the
open-source installer workflow, see the [Installer Guide](./installer).

## Installation flow

1. Open the Lakemeter listing in Databricks Marketplace and select **Install**.
2. Review and bind the resources declared by the app package.
3. Review the effective user API scopes and app settings.
4. Choose the app name, description, compute size, and usage policy.
5. Select **Install** and wait for the deployment to reach **Running**.
6. Open Lakemeter and create an estimate. No post-install bootstrap step is
   required.

Marketplace installs Lakemeter from an immutable Git release tag. The package
root is the repository's `backend` directory and includes `app.yaml`,
`manifest.yaml`, the backend application, pre-built frontend assets, schema
definitions, and pricing reference data.

## Declared app resources

The current package declares two resources in `manifest.yaml`.

| Resource | Type | Permission | Purpose |
| --- | --- | --- | --- |
| `postgres` | Lakebase Postgres database | `CAN_CONNECT_AND_CREATE` | Stores estimates, users, configuration, bootstrap state, and pricing reference data. |
| `claude-endpoint` | Databricks Model Serving endpoint | `CAN_QUERY` | Powers the optional AI sizing assistant. |

### Lakebase

The Lakebase binding is required for the application. Use a dedicated,
newly-created project or database for a new installation. The Databricks App
service principal creates and owns the `lakemeter` schema.

Do not reuse a schema created by a different Lakemeter app service principal
unless ownership and grants have been migrated deliberately. A new app
identity does not automatically inherit access to another identity's schema.

Lakemeter authenticates to Lakebase with a short-lived OAuth database
credential generated for the app service principal. The package does not use a
stored database password.

### Model Serving

Bind a Databricks-hosted Claude endpoint with `CAN_QUERY`. The endpoint is used
only when a user invokes the AI assistant. Estimate creation, manual workload
configuration, calculations, and Excel export do not send prompts to Model
Serving.

The current Marketplace package expects the resource binding during
installation even though the core calculator can operate without AI
assistance.

## User API scopes and identity

Databricks Apps provides workspace SSO for interactive users. The installed
app currently reports these effective user API scopes:

| Scope | Use |
| --- | --- |
| `iam.current-user:read` | Identifies the signed-in workspace user. |
| `iam.access-control:read` | Supports Databricks Apps access-control handling. |

Lakemeter does not request user access to Jobs, SQL warehouses, Unity Catalog
data, workspace files, or Databricks Secrets. It does not ask users to paste a
personal access token.

The app service principal, rather than the interactive user, authenticates to
the bound Lakebase database and Model Serving endpoint.

## Network access and egress

### App-compute connections

Lakemeter requires outbound connectivity only to Databricks-managed services:

| Destination | Protocol | Purpose |
| --- | --- | --- |
| The installation workspace host | HTTPS | Generates Lakebase OAuth credentials and invokes the bound Model Serving endpoint. |
| The bound Lakebase endpoint host | PostgreSQL over TLS, port 5432 | Reads and writes Lakemeter application data. |

No third-party server-side API or arbitrary internet egress is required for
the Marketplace runtime. Documentation and Databricks pricing links are
ordinary links opened by the user's browser.

### Browser-loaded assets

The current frontend downloads web fonts directly from:

- `https://fonts.googleapis.com`
- `https://fonts.gstatic.com`

These requests originate from the user's browser, not from the Databricks App
compute. No estimate contents are included in the font requests. Organizations
that block these hosts still receive fallback system fonts; calculator
functionality is unaffected.

## First-start bootstrap

On first start, Lakemeter:

1. Generates a short-lived Lakebase OAuth credential for its app service
   principal.
2. Connects to the bound database using TLS.
3. Creates the `lakemeter` schema and application tables.
4. Installs the packaged calculation functions and reference records.
5. Loads the packaged pricing CSV files, including split cloud VM pricing
   files.
6. Records the application version and pricing checksum.
7. Starts serving traffic only after database initialization and bootstrap
   succeed.

Bootstrap is idempotent. Later starts compare the recorded version and pricing
checksum and skip work that is already current.

Lakebase can be suspended by scale-to-zero. Startup retries transient wake-up
timeouts with bounded exponential backoff. Authentication and permission
errors are not retried as transient failures and cause startup to fail with an
actionable deployment log.

## Data handling

- Estimates, workload configuration, and application state remain in the
  customer's bound Lakebase database.
- Pricing reference data is packaged with the release and loaded locally into
  Lakebase.
- OAuth credentials are short-lived and are not persisted as application
  secrets.
- AI prompts are sent only to the bound Databricks Model Serving endpoint when
  a user invokes the assistant.
- Lakemeter does not send estimate data to a third-party analytics or
  telemetry service.

## Marketplace upgrades

Marketplace installations do not silently follow a mutable branch. For each
release, the provider publishes a new immutable Git tag and updates the
Marketplace listing.

When a new version is available:

1. Databricks displays an update notice on the installed app's Databricks Apps
   page.
2. An app administrator reviews the update and explicitly applies it.
3. Existing app identity, resource bindings, and Lakebase data remain in
   place.
4. Lakemeter runs its idempotent bootstrap against the existing database and
   applies compatible packaged updates.

If a release adds or changes resources, permissions, scopes, or network
requirements, Databricks asks the administrator to review those changes as
part of the update.

The [`scripts/upgrade.sh`](./upgrading) workflow applies to installations
created through the open-source installer. Marketplace-managed apps must use
the Marketplace update flow.

## Verify an installation

Open:

```text
https://<app-url>/api/v1/system/health
```

A healthy installation returns:

```json
{
  "status": "healthy",
  "app_version": "<installed-version>",
  "database": "connected"
}
```

Also verify:

- The app status is **Running** and its active deployment is **Succeeded**.
- The `postgres` resource points to the intended dedicated Lakebase database.
- The `claude-endpoint` resource has `CAN_QUERY`.
- A user can create an estimate, add a workload, calculate a non-zero cost,
  and export Excel.
- The AI assistant responds when Model Serving is enabled.

## Troubleshooting

### Lakebase connection timeout during startup

Review the app logs for retry messages. A transient timeout can occur while a
scale-to-zero endpoint wakes. The app retries this condition before serving
traffic. Persistent failures require checking the endpoint state and network
connectivity.

### Permission denied for schema `lakemeter`

The schema is likely owned by another app identity. For a new Marketplace
installation, bind a fresh database so the new service principal creates and
owns the schema. Do not drop an existing schema without first deciding how its
data will be preserved.

### Password authentication failed

Confirm that the Lakebase binding grants `CAN_CONNECT_AND_CREATE` and points to
the intended project, branch, and database. Marketplace installations use
OAuth-only database authentication and do not fall back to a stored password.

### AI assistant unavailable

Confirm that `claude-endpoint` is bound to an available Databricks Model
Serving endpoint with `CAN_QUERY`. Model Serving rate limits can affect the AI
assistant without affecting the core estimate workflow.

### Restricted browser egress

If Google Fonts is blocked, Lakemeter uses fallback system fonts. No calculator
or export capability depends on those domains.
