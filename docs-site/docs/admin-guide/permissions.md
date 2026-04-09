---
sidebar_position: 7
---

# Permissions & SP Roles API

Lakemeter uses a **Service Principal (SP)** with OAuth M2M (machine-to-machine) authentication to connect to Lakebase from the Databricks App. This guide documents the critical configuration requirements and a common pitfall that causes authentication failures.

![Permissions guide documentation page](/img/guides/admin-permissions-guide.png)
*The Permissions guide — OAuth M2M flow, Service Principal setup, and token management.*

## Why OAuth M2M?

Databricks Apps run as managed services — there is no interactive user session to provide credentials. The app authenticates to Lakebase by:

1. Exchanging SP credentials (client ID + secret) for a short-lived OAuth token
2. Using that token as the PostgreSQL password when connecting to Lakebase
3. Automatically refreshing the token before it expires

This is the **only** supported authentication method for Databricks Apps connecting to Lakebase.

## The Critical Finding: `identity_type=SERVICE_PRINCIPAL`

When creating a Lakebase role for a Service Principal, you **must** use the Lakebase Roles API with `identity_type: "SERVICE_PRINCIPAL"`. Using `CREATE ROLE` in PostgreSQL SQL or `identity_type: "PG_ONLY"` will create a role that **cannot** exchange OAuth tokens.

### What Works

```bash
# Correct: Use the Lakebase Roles API
POST /api/2.0/database/instances/{instance-name}/roles
{
  "name": "<service-principal-client-id>",
  "identity_type": "SERVICE_PRINCIPAL",
  "membership_role": "DATABRICKS_SUPERUSER"
}
```

### What Does NOT Work

```sql
-- WRONG: PostgreSQL CREATE ROLE does not register the SP for OAuth
CREATE ROLE "service-principal-id" WITH LOGIN;
```

```bash
# WRONG: PG_ONLY identity type cannot exchange OAuth tokens
POST /api/2.0/database/instances/{instance-name}/roles
{
  "name": "<service-principal-client-id>",
  "identity_type": "PG_ONLY",
  "membership_role": "DATABRICKS_SUPERUSER"
}
```

### Symptoms of Incorrect Configuration

If the SP role was created with the wrong `identity_type`, you'll see:

- `generate_database_credential` API call fails with a 403 or 404
- Token exchange returns an empty or invalid token
- PostgreSQL connection fails with "password authentication failed"
- The app health endpoint reports an unhealthy database connection

### How to Fix

If a role already exists with `identity_type=PG_ONLY`, the installer automatically:

1. Deletes the incorrect role via `DELETE /api/2.0/database/instances/{name}/roles/{role-name}`
2. Recreates it with `identity_type=SERVICE_PRINCIPAL`
3. Re-grants schema permissions
4. Verifies connectivity

## Permission Layers

The SP requires permissions at three levels:

### 1. Workspace Level

The SP needs `CAN_MANAGE` permission on the Lakebase instance:

```bash
PATCH /api/2.0/permissions/database-instances/{instance-name}
{
  "access_control_list": [{
    "service_principal_name": "<client-id>",
    "all_permissions": [{"permission_level": "CAN_MANAGE"}]
  }]
}
```

### 2. Instance Level (Roles API)

The SP needs a role with `DATABRICKS_SUPERUSER` membership:

```bash
POST /api/2.0/database/instances/{instance-name}/roles
{
  "name": "<client-id>",
  "identity_type": "SERVICE_PRINCIPAL",
  "membership_role": "DATABRICKS_SUPERUSER"
}
```

### 3. Schema Level (SQL Grants)

Fine-grained table access within the `lakemeter` schema:

```sql
GRANT USAGE ON SCHEMA lakemeter TO "<client-id>";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA lakemeter TO "<client-id>";
ALTER DEFAULT PRIVILEGES IN SCHEMA lakemeter
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "<client-id>";
```

The `ALTER DEFAULT PRIVILEGES` ensures the SP can access tables created in the future.

## Token Lifecycle

The OAuth token lifecycle is managed by `backend/app/auth/token_manager.py` and `backend/app/database.py`:

1. **Generation**: Calls `database.generate_database_credential()` with the Lakebase instance name using a `WorkspaceClient` authenticated with the SP credentials
2. **Caching**: Tokens are cached in memory and reused across connections
3. **Expiry**: Tokens have a limited TTL (typically 1 hour)
4. **Pool recycle**: SQLAlchemy connection pool recycles every **900 seconds (15 minutes)** — connections are refreshed well before token expiry
5. **Engine refresh**: The database engine is proactively refreshed every **30 minutes** (`_ENGINE_REFRESH_INTERVAL = 30 * 60`)
6. **Auto-recovery**: If a query fails with an auth error ("invalid authorization", "authentication failed", "password"), the engine automatically refreshes the token and retries

## Permission Tests

The test suite includes dedicated permission tests in `tests/test_lakebase_permissions.py`:

| Test | What It Verifies |
|------|-----------------|
| SP token generation | `generate_database_credential` returns a valid token |
| Token expiry validation | Token has a future expiry timestamp |
| DB connectivity | SP can connect to Lakebase with the generated token |
| PG16 version check | Connected instance runs PostgreSQL 16+ |
| Workload type read | SP can read all 9 workload types from pricing tables |
| DBU rate read | SP can read DBU rates with values > 0 |
| VM cost read | SP can read VM cost data |
| CRUD on users table | SP can INSERT, SELECT, UPDATE, DELETE on the users table |
| Token refresh | Token is automatically refreshed after invalidation |
| App health endpoint | FastAPI health endpoint returns 200 with healthy DB status |

Run them with:

```bash
python -m pytest tests/test_lakebase_permissions.py -v
```

:::note
These tests require network access to the Databricks workspace and are skip-guarded when the host is unreachable.
:::

## Secrets Configuration

The SP credentials are stored in a Databricks secrets scope:

| Secret Key | Description |
|------------|-------------|
| `sp_clientid` | Service Principal application (client) ID |
| `sp_secret` | Service Principal client secret |

Referenced in `app.yaml`:

```yaml
- name: "SP_CLIENT_ID_KEY"
  value: "sp_clientid"
- name: "SP_SECRET_KEY"
  value: "sp_secret"
```

The app reads the key names from environment variables, then fetches the actual values from the secrets scope at runtime. See the [Configuration Guide](./configuration) for the full environment variable reference.
