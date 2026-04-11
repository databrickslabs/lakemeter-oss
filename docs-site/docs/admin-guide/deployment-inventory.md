---
sidebar_position: 7
---

# Deployment Inventory

This page lists everything the Lakemeter installer creates in your Databricks workspace, along with their configurations. Use this as a reference for auditing, troubleshooting, or manual cleanup.

## Resource Summary

| Resource | Name | Type | Created By |
|----------|------|------|------------|
| Lakebase instance | `lakemeter-customer` | Managed PostgreSQL | Task 1: provision_lakebase |
| Database | `lakemeter_pricing` | PostgreSQL database | Task 3: create_database |
| Schema | `lakemeter` | PostgreSQL schema | Task 3: create_database |
| Application tables | 9 tables | PostgreSQL tables | Task 3: create_database |
| Stored functions | 19 functions | PostgreSQL functions | Task 4: create_functions |
| Pricing data | 10 sync tables | PostgreSQL tables | Task 5: load_pricing_data |
| SKU mapping | 1 table | PostgreSQL table | Task 6: create_sku_mapping |
| Secret scope | `lakemeter-secrets` | Databricks secret scope | Task 3: create_database |
| Secrets | 5 key-value pairs | Databricks secrets | Tasks 2, 3 |
| Databricks App | `lakemeter` | Databricks App | Task 2: create_app |
| App resources | 5 resources | App environment config | Task 2: create_app |
| Lakebase role | App SP role | Database role | Task 7: grant_app_access |
| PostgreSQL role | `lakemeter_sync_role` | Password-auth role | Task 3: create_database |

---

## Lakebase Instance

| Property | Value |
|----------|-------|
| **Name** | `lakemeter-customer` (configurable via `--instance-name`) |
| **Type** | Managed PostgreSQL (Lakebase) |
| **Initial capacity** | CU_1 |
| **Autoscaling** | 1 CU – 16 CU |
| **Scale-to-zero** | Enabled |
| **Serverless compute** | Enabled |
| **pg_native_login** | Enabled (password auth fallback) |

### Scaling Behavior

The instance starts at CU_1 and autoscales based on load. When idle for a configurable period, it scales to zero — no cost when unused. On the next connection, it resumes in ~10-15 seconds.

| CU Size | vCPUs | Memory | Storage IOPS |
|---------|-------|--------|-------------|
| CU_1 | 2 | 8 GB | Baseline |
| CU_2 | 4 | 16 GB | 2x |
| CU_4 | 8 | 32 GB | 4x |
| CU_8 | 16 | 64 GB | 8x |
| CU_16 | 32 | 128 GB | 16x |

---

## Database: `lakemeter_pricing`

### Schema: `lakemeter`

#### Application Tables (9)

| Table | Description | Key Columns |
|-------|-------------|-------------|
| `users` | User profiles | `id`, `email`, `display_name`, `role` |
| `templates` | Estimate templates | `id`, `name`, `description`, `configuration` |
| `ref_cloud_tiers` | Cloud/tier reference | `cloud`, `tier` |
| `estimates` | Cost estimates | `id`, `name`, `cloud`, `region`, `tier`, `status` |
| `ref_workload_types` | Workload type reference | `key`, `display_name`, `category` |
| `line_items` | Estimate line items (workloads) | `id`, `estimate_id`, `workload_type`, `configuration`, `cost_per_month` |
| `conversation_messages` | AI assistant chat history | `id`, `conversation_id`, `role`, `content` |
| `decision_records` | Decision audit trail | `id`, `estimate_id`, `decision_type`, `details` |
| `sharing` | Estimate sharing | `id`, `estimate_id`, `shared_with`, `permission` |

#### Reference Data — Seeded Values

| Data | Count | Source |
|------|-------|--------|
| Workload types | 9 | `jobs_classic`, `jobs_serverless`, `all_purpose_classic`, `all_purpose_serverless`, `dbsql_classic`, `dbsql_pro`, `dbsql_serverless`, `dlt_classic`, `dlt_serverless` (+ model_serving, vector_search, fmapi, lakebase) |
| Cloud/tier combos | 8 | AWS/Azure/GCP × Standard/Premium/Enterprise (not all combos exist) |

#### Triggers

| Trigger | Table | Purpose |
|---------|-------|---------|
| `normalize_estimate_case` | `estimates` | Uppercases `cloud`, `region`, `tier` on INSERT/UPDATE |
| `normalize_line_item_case` | `line_items` | Uppercases cloud/region/tier in configuration JSON |

#### Indexes

Created during schema migrations for query performance on commonly filtered columns.

---

### Stored Functions (19)

| Function | Description |
|----------|-------------|
| `calculate_jobs_dbu` | DBU calculation for Jobs workloads |
| `calculate_all_purpose_dbu` | DBU calculation for All-Purpose workloads |
| `calculate_dbsql_dbu` | DBU calculation for DBSQL warehouses |
| `calculate_dlt_dbu` | DBU calculation for DLT pipelines |
| `calculate_serverless_compute_dbu` | DBU calculation for serverless workloads |
| `calculate_model_serving_dbu` | DBU calculation for Model Serving |
| `calculate_vector_search_dbu` | DBU calculation for Vector Search |
| `calculate_fmapi_dbu` | DBU calculation for Foundation Model APIs |
| `calculate_lakebase_dbu` | DBU calculation for Lakebase |
| `calculate_vm_costs` | VM cost lookup for classic compute |
| `calculate_dbsql_vm_costs` | VM cost calculation for DBSQL warehouses |
| `calculate_line_item_costs` | Main orchestrator — routes to correct calculator based on workload type |
| `get_dbu_price` | DBU price lookup by product type, cloud, region, tier |
| `get_product_type_for_pricing` | Maps workload config to SKU/product type |
| `calculate_hours_per_month` | Converts run-based usage to hours/month |
| `get_photon_multiplier` | Photon DBU multiplier lookup |
| `get_dbu_multiplier` | General DBU multiplier lookup |
| `get_serverless_multiplier` | Serverless mode multiplier (standard=1x, performance=2x) |
| `calculate_fmapi_token_costs` | Token-based cost calculation for FMAPI |

---

### Pricing Sync Tables (10)

These tables are populated by the installer and can be refreshed by re-running it.

| Table | Rows | Description |
|-------|------|-------------|
| `sync_pricing_vm_costs` | ~111,000 | VM hourly costs by cloud, region, instance type, pricing tier |
| `sync_pricing_dbu_rates` | ~2,400 | DBU prices by cloud, region, tier, product type |
| `sync_ref_instance_dbu_rates` | ~1,070 | DBU consumption rates per instance type |
| `sync_product_fmapi_proprietary` | ~500 | Proprietary model token pricing (OpenAI, Anthropic, Google) |
| `sync_product_fmapi_databricks` | ~100 | Databricks-hosted model token pricing |
| `sync_product_dbsql_rates` | ~80 | DBSQL DBU rates by warehouse type and size |
| `sync_ref_sku_region_map` | 73 | SKU-to-region availability mapping |
| `sync_ref_dbsql_warehouse_config` | ~55 | DBSQL warehouse hardware specs (instance types, worker counts) |
| `sync_ref_dbu_multipliers` | ~50 | DBU multipliers (Photon, edition, etc.) |
| `sync_product_serverless_rates` | ~20 | Serverless product rates (Model Serving, Vector Search) |

#### Derived Reference Tables (3)

Populated via `INSERT...SELECT DISTINCT` from the sync tables above:

| Table | Source | Description |
|-------|--------|-------------|
| `ref_fmapi_databricks_models` | `sync_product_fmapi_databricks` | Distinct Databricks model names and categories |
| `ref_fmapi_proprietary_models` | `sync_product_fmapi_proprietary` | Distinct proprietary model names by provider |
| `ref_model_serving_gpu_types` | `sync_product_serverless_rates` | GPU type options for Model Serving |

#### SKU Mapping Table (1)

| Table | Description |
|-------|-------------|
| `ref_sku_discount_mapping` | Maps SKU types to discount eligibility, populated from DBU rates |

---

## Secret Scope: `lakemeter-secrets`

| Secret Key | Set By | Description |
|------------|--------|-------------|
| `lakebase-instance-name` | Task 2 (create_app) | Lakebase instance name (e.g., `lakemeter-customer`) |
| `lakebase-host` | Task 3 (create_database) | Lakebase read-write DNS endpoint |
| `lakebase-user` | Task 3 (create_database) | PostgreSQL role name (`lakemeter_sync_role`) |
| `lakebase-database` | Task 3 (create_database) | Database name (`lakemeter_pricing`) |
| `lakebase-password` | Task 3 (create_database) | Auto-generated password for `lakemeter_sync_role` |

---

## Databricks App: `lakemeter`

| Property | Value |
|----------|-------|
| **Name** | `lakemeter` (configurable via `--app-name`) |
| **Description** | Lakemeter — Databricks cost estimation tool |
| **Compute size** | MEDIUM (2 vCPU, 6 GB RAM) |
| **Runtime** | Ubuntu 22.04, Python 3.11, Node.js 22.16 |
| **Source path** | `/Workspace/Users/{user}/apps/lakemeter` |
| **URL** | `https://lakemeter-{workspace_id}.aws.databricksapps.com` |

### App Resources (5)

These environment variables are injected into the app container at runtime via `valueFrom` references:

| Resource Name | Environment Variable | Type | Source |
|---------------|---------------------|------|--------|
| `lm-lakebase-instance` | `LAKEBASE_INSTANCE_NAME` | Secret | `lakemeter-secrets:lakebase-instance-name` |
| `lm-db-host` | `DB_HOST` | Secret | `lakemeter-secrets:lakebase-host` |
| `lm-db-user` | `DB_USER` | Secret | `lakemeter-secrets:lakebase-user` |
| `lm-db-name` | `DB_NAME` | Secret | `lakemeter-secrets:lakebase-database` |
| `lm-claude-endpoint` | `CLAUDE_MODEL_ENDPOINT` | Serving Endpoint | `databricks-claude-opus-4-6` |

### App Environment Variables (static)

These are set directly in `app.yaml`:

| Variable | Value | Description |
|----------|-------|-------------|
| `ENVIRONMENT` | `production` | App environment mode |
| `CORS_ORIGINS` | (empty) | CORS allowed origins |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_SSLMODE` | `require` | SSL mode for database connections |

### App Startup Command

```bash
cd backend && ../.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port ${DATABRICKS_APP_PORT:-8000}
```

### Service Principal

The app gets an auto-created Service Principal with:

| Permission | Target | Purpose |
|-----------|--------|---------|
| Lakebase role | `lakemeter-customer` instance | `DATABRICKS_SUPERUSER` — full database access |
| SQL grants | `lakemeter` schema | CONNECT, USAGE, ALL PRIVILEGES on tables/sequences/functions |
| Secret READ | `lakemeter-secrets` scope | Read database credentials |
| CAN_QUERY | `databricks-claude-opus-4-6` | Query the Claude model endpoint |

---

## PostgreSQL Role: `lakemeter_sync_role`

| Property | Value |
|----------|-------|
| **Name** | `lakemeter_sync_role` |
| **Auth** | Password (stored in `lakemeter-secrets:lakebase-password`) |
| **Purpose** | Fallback authentication when SP OAuth is unavailable |
| **Permissions** | Same as the App SP — full access to `lakemeter` schema |

---

## Workspace Files

### Bundle Files (temporary, under `.bundle/`)

```
/Workspace/Users/{user}/.bundle/lakemeter-installer/default/files/
├── notebooks/          # 9 installer notebook tasks
├── pricing_data/       # 11 CSV files
├── app_source/         # Backend source + static assets
└── functions/          # 19 SQL function files
```

These are uploaded by `databricks bundle deploy` and used by the workflow tasks. They persist between runs but are not part of the app runtime.

### App Source (runtime)

```
/Workspace/Users/{user}/apps/lakemeter/
├── backend/
│   ├── app/            # FastAPI Python source
│   │   ├── main.py
│   │   ├── routes/     # API endpoints
│   │   ├── services/   # Business logic
│   │   └── auth/       # Authentication
│   └── static/         # Pre-built frontend
│       ├── index.html
│       └── assets/     # JS/CSS bundles
├── app.yaml            # Databricks Apps config
└── requirements.txt    # Python dependencies
```

This is the app's runtime source — the Databricks Apps platform snapshots this directory when deploying.

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
