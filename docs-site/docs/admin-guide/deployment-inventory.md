---
sidebar_position: 3
---

# Deployment Inventory

This page lists everything the Lakemeter installer creates in your Databricks workspace. Use this as a reference for auditing or manual cleanup.

## Resource Summary

| Resource | Name | Type |
|----------|------|------|
| Lakebase project | `lakemeter-customer` | Lakebase Autoscaling |
| Lakebase branch | `production` | Copy-on-write PostgreSQL branch |
| Lakebase endpoint | `primary` | Read-write autoscaling compute |
| Database | `lakemeter_pricing` | PostgreSQL database |
| Schema | `lakemeter` | PostgreSQL schema |
| Application tables | `users`, `estimates`, `line_items`, `templates`, `sharing`, `conversation_messages`, `decision_records`, `ref_cloud_tiers`, `ref_workload_types` | PostgreSQL tables |
| Stored functions | 15 cost calculation functions | PostgreSQL functions |
| Pricing sync tables | 10 tables with DBU rates, VM costs, model pricing | PostgreSQL tables |
| Derived reference tables | `ref_fmapi_databricks_models`, `ref_fmapi_proprietary_models`, `ref_model_serving_gpu_types` | PostgreSQL tables |
| SKU mapping | `ref_sku_discount_mapping` | PostgreSQL table |
| Secret scope | `lakemeter-secrets` | Databricks secret scope |
| Secrets | 7 key-value pairs | Databricks secrets |
| Databricks App | `lakemeter` | Databricks App |
| App resources | 7 environment variable bindings | App config |
| Lakebase role | App Service Principal | Database role |
| PostgreSQL role | `lakemeter_sync_role` | Password-auth role |

---

## Lakebase Autoscaling Project

| Property | Value |
|----------|-------|
| **Project ID** | `lakemeter-customer` (configurable via `--project-id`) |
| **Branch** | `production` |
| **Read-write endpoint** | `primary` |
| **Type** | Lakebase Autoscaling |
| **Autoscaling** | 1 CU – 16 CU |
| **Scale-to-zero** | After 5 minutes of inactivity |
| **Native login** | Enabled for password-auth fallback |

---

## Secret Scope: `lakemeter-secrets`

| Secret Key | Description |
|------------|-------------|
| `lakebase-project` | Full project resource name |
| `lakebase-branch` | Full production branch resource name |
| `lakebase-endpoint` | Full primary endpoint resource name |
| `lakebase-host` | Primary endpoint DNS host |
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
| `lm-lakebase-project` | `LAKEBASE_PROJECT` | Secret | `lakemeter-secrets:lakebase-project` |
| `lm-lakebase-branch` | `LAKEBASE_BRANCH` | Secret | `lakemeter-secrets:lakebase-branch` |
| `lm-lakebase-endpoint` | `LAKEBASE_ENDPOINT` | Secret | `lakemeter-secrets:lakebase-endpoint` |
| `lm-db-host` | `DB_HOST` | Secret | `lakemeter-secrets:lakebase-host` |
| `lm-db-user` | `DB_USER` | Secret | `lakemeter-secrets:lakebase-user` |
| `lm-db-name` | `DB_NAME` | Secret | `lakemeter-secrets:lakebase-database` |
| `lm-claude-endpoint` | `CLAUDE_MODEL_ENDPOINT` | Serving Endpoint | `databricks-claude-opus-4-6` |

### Service Principal

The app gets an auto-created Service Principal with:

| Permission | Target | Purpose |
|-----------|--------|---------|
| Lakebase OAuth role | `production` branch | Authenticates the app Service Principal |
| SQL grants | `lakemeter` schema | CONNECT, USAGE, ALL PRIVILEGES on tables/sequences/functions |
| Secret READ | `lakemeter-secrets` scope | Read database credentials |
| CAN_QUERY | `databricks-claude-opus-4-6` | Query the Claude model endpoint |

---

## Cleanup

To completely remove Lakemeter from your workspace:

```bash
# 1. Delete the Databricks App
databricks apps delete lakemeter --profile <profile>

# 2. Delete the Lakebase project (destroys all branches and data)
databricks postgres delete-project projects/lakemeter-customer --profile <profile>

# 3. Delete the secrets scope
databricks secrets delete-scope lakemeter-secrets --profile <profile>

# 4. Remove bundle files (optional)
databricks workspace delete -r /Workspace/Users/{user}/.bundle/lakemeter-installer --profile <profile>

# 5. Remove app source (optional)
databricks workspace delete -r /Workspace/Users/{user}/apps/lakemeter --profile <profile>
```

**Warning:** Deleting the Lakebase project permanently destroys all branches,
databases, tables, and data within it. This cannot be undone.
