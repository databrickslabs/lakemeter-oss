---
sidebar_position: 2
---

# Configuration

Lakemeter is configured through environment variables in `app.yaml` and Service Principal credentials stored in a Databricks secret scope.

![Configuration guide documentation page](/img/guides/admin-configuration-guide.png)
*The Configuration guide — environment variables, secret scopes, and runtime settings.*

## Environment Variables

Set these in `app.yaml` under the `env` section. Variables marked `valueFrom` are resolved at runtime by Databricks Apps from app resource references.

### Required Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `ENVIRONMENT` | `value` | `production`, `development`, or `local` (default: `local`). In production, logging is limited to warnings/errors and the Swagger API docs (`/docs` and `/redoc`) are disabled. In `development` or `local`, verbose logging is enabled. |
| `DATABRICKS_HOST` | `value` | Full workspace URL (e.g., `https://workspace.cloud.databricks.com`) |
| `DATABRICKS_SECRETS_SCOPE` | `valueFrom` | App resource reference for the secret scope name |
| `LAKEBASE_INSTANCE_NAME` | `valueFrom` | App resource reference for the Lakebase instance identifier |
| `DB_HOST` | `valueFrom` | App resource reference for the Lakebase connection hostname |
| `DB_USER` | `valueFrom` | App resource reference for the database username |
| `DB_NAME` | `valueFrom` | App resource reference for the database name (default: `lakemeter_pricing`) |

### Optional Variables

| Variable | Source | Default | Description |
|----------|--------|---------|-------------|
| `DB_PORT` | `value` | `5432` | PostgreSQL port |
| `DB_SSLMODE` | `value` | `require` | SSL mode for database connections |
| `SP_CLIENT_ID_KEY` | `value` | `sp_clientid` | Key name within the secret scope for the SP client ID |
| `SP_SECRET_KEY` | `value` | `sp_secret` | Key name within the secret scope for the SP client secret |
| `CORS_ORIGINS` | `value` | `""` (empty) | Comma-separated allowed origins. Empty = same-origin only. |
| `LOG_LEVEL` | `value` | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR |

### Local Development Variables

When running locally (without Databricks Apps), these additional variables apply:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABRICKS_CONFIG_PROFILE` | (none) | CLI profile name for local Databricks SDK auth |
| `DATABASE_URL` | (none) | Full database URL override (bypasses token manager) |

## `valueFrom` vs `value`

Databricks Apps resolves `valueFrom` references at runtime from app resources. This keeps sensitive values like database hostnames and credentials out of the YAML file:

```yaml
# Resolved at runtime from an app resource — never appears in the YAML
- name: DB_HOST
  valueFrom: "lakemeter-db-host"

# Hardcoded, non-sensitive default
- name: DB_PORT
  value: "5432"
```

The installer (`install_lakemeter.py`) generates these resource references automatically. See the [Installer Guide](./installer) for details.

## Service Principal Credentials

The app reads SP credentials from the Databricks secret scope at runtime. Two keys are required:

| Secret Key | Description |
|------------|-------------|
| `sp_clientid` | Service Principal application (client) ID |
| `sp_secret` | Service Principal client secret |

The key names are configured via `SP_CLIENT_ID_KEY` and `SP_SECRET_KEY` environment variables. The app fetches the actual credential values from the secret scope using these key names.

### How Credentials Are Used

1. The app reads `SP_CLIENT_ID_KEY` and `SP_SECRET_KEY` from environment variables (default: `sp_clientid`, `sp_secret`)
2. It fetches the actual SP credentials from the `DATABRICKS_SECRETS_SCOPE` using those key names
3. It exchanges the SP credentials for a short-lived OAuth token via `generate_database_credential()`
4. The token is used as the PostgreSQL password to connect to Lakebase
5. Tokens are cached in memory and proactively refreshed every 30 minutes (well before the 1-hour expiry)

## Database Connection

Lakemeter connects to Lakebase using SQLAlchemy with OAuth token-based authentication:

```
postgresql://{DB_USER}:{oauth-token}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode={DB_SSLMODE}
```

The OAuth token is generated from SP credentials and automatically refreshed. The connection pool is configured with:

- **Pool size**: 5 connections
- **Max overflow**: 10 additional connections
- **Pool recycle**: 900 seconds (15 minutes) — ensures connections are refreshed before token expiry
- **Pre-ping**: Enabled — validates connections before use

See the [Permissions Guide](./permissions) for full details on SP role setup and the `identity_type=SERVICE_PRINCIPAL` requirement.

## CORS Configuration

By default, CORS allows same-origin requests only (the React frontend is served from the same FastAPI backend). In local development, the default origins include `http://localhost:5173`, `http://localhost:3000`, and `http://localhost:5175`.

To allow cross-origin access in production:

```yaml
env:
  - name: CORS_ORIGINS
    value: "https://other-app.databricksapps.com"
```

Leave empty for same-origin only (recommended for production).
