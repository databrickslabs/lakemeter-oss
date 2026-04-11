---
sidebar_position: 3
---

# Deployment Inventory

This page lists everything the Lakemeter installer creates in your Databricks workspace. Use this as a reference for auditing or manual cleanup.

## Resource Summary

| Resource | Name | Type |
|----------|------|------|
| Lakebase instance | `lakemeter-customer` | Managed PostgreSQL |
| Database | `lakemeter_pricing` | PostgreSQL database |
| Schema | `lakemeter` | PostgreSQL schema |
| Application tables | `users`, `estimates`, `line_items`, `templates`, `sharing`, `conversation_messages`, `decision_records`, `ref_cloud_tiers`, `ref_workload_types` | PostgreSQL tables |
| Stored functions | 19 cost calculation functions | PostgreSQL functions |
| Pricing sync tables | 10 tables with DBU rates, VM costs, model pricing | PostgreSQL tables |
| Derived reference tables | `ref_fmapi_databricks_models`, `ref_fmapi_proprietary_models`, `ref_model_serving_gpu_types` | PostgreSQL tables |
| SKU mapping | `ref_sku_discount_mapping` | PostgreSQL table |
| Secret scope | `lakemeter-secrets` | Databricks secret scope |
| Secrets | 5 key-value pairs | Databricks secrets |
| Databricks App | `lakemeter` | Databricks App |
| App resources | 5 environment variable bindings | App config |
| Lakebase role | App Service Principal | Database role |
| PostgreSQL role | `lakemeter_sync_role` | Password-auth role |

---

## Lakebase Instance

| Property | Value |
|----------|-------|
| **Name** | `lakemeter-customer` (configurable via `--instance-name`) |
| **Type** | Managed PostgreSQL (Lakebase) |
| **Autoscaling** | 1 CU – 16 CU |
| **Scale-to-zero** | Enabled |
| **pg_native_login** | Enabled (password auth fallback) |

---

## Secret Scope: `lakemeter-secrets`

| Secret Key | Description |
|------------|-------------|
| `lakebase-instance-name` | Lakebase instance name (e.g., `lakemeter-customer`) |
| `lakebase-host` | Lakebase read-write DNS endpoint |
| `lakebase-user` | PostgreSQL role name (`lakemeter_sync_role`) |
| `lakebase-database` | Database name (`lakemeter_pricing`) |
| `lakebase-password` | Auto-generated password for `lakemeter_sync_role` |

---

## Databricks App: `lakemeter`

| Property | Value |
|----------|-------|
| **Name** | `lakemeter` (configurable via `--app-name`) |
| **Compute size** | MEDIUM (2 vCPU, 6 GB RAM) |
| **Runtime** | Ubuntu 22.04, Python 3.11, Node.js 22.16 |
| **Source path** | `/Workspace/Users/{user}/apps/lakemeter` |
| **URL** | `https://lakemeter-<workspace-id>.<cloud>.databricksapps.com` |

### App Resources

These environment variables are injected into the app container at runtime:

| Resource Name | Environment Variable | Type | Source |
|---------------|---------------------|------|--------|
| `lm-lakebase-instance` | `LAKEBASE_INSTANCE_NAME` | Secret | `lakemeter-secrets:lakebase-instance-name` |
| `lm-db-host` | `DB_HOST` | Secret | `lakemeter-secrets:lakebase-host` |
| `lm-db-user` | `DB_USER` | Secret | `lakemeter-secrets:lakebase-user` |
| `lm-db-name` | `DB_NAME` | Secret | `lakemeter-secrets:lakebase-database` |
| `lm-claude-endpoint` | `CLAUDE_MODEL_ENDPOINT` | Serving Endpoint | `databricks-claude-opus-4-6` |

### Service Principal

The app gets an auto-created Service Principal with:

| Permission | Target | Purpose |
|-----------|--------|---------|
| Lakebase role | `lakemeter-customer` instance | `DATABRICKS_SUPERUSER` — full database access |
| SQL grants | `lakemeter` schema | CONNECT, USAGE, ALL PRIVILEGES on tables/sequences/functions |
| Secret READ | `lakemeter-secrets` scope | Read database credentials |
| CAN_QUERY | `databricks-claude-opus-4-6` | Query the Claude model endpoint |

---

## Cleanup

To completely remove Lakemeter from your workspace:

```bash
# 1. Delete the Databricks App
databricks apps delete lakemeter --profile <profile>

# 2. Delete the Lakebase instance (destroys all data)
databricks api delete /api/2.0/database/instances/lakemeter-customer --profile <profile>

# 3. Delete the secrets scope
databricks secrets delete-scope lakemeter-secrets --profile <profile>

# 4. Remove bundle files (optional)
databricks workspace delete -r /Workspace/Users/{user}/.bundle/lakemeter-installer --profile <profile>

# 5. Remove app source (optional)
databricks workspace delete -r /Workspace/Users/{user}/apps/lakemeter --profile <profile>
```

**Warning:** Deleting the Lakebase instance permanently destroys all databases, tables, and data within it. This cannot be undone.
