---
sidebar_position: 6
---

# Installer Guide

Lakemeter includes a zero-click installer (`scripts/install_lakemeter.py`) that provisions a complete environment on Databricks — from Lakebase instance creation to app deployment.

## Prerequisites

Before running the installer, ensure you have:

- **Python 3.10+** with the following packages installed:
  - `databricks-sdk`
  - `psycopg2-binary`
  - `requests`
- **Databricks CLI** installed and configured with a workspace profile
- **Service Principal** registered in your workspace (the installer creates the secrets scope and prompts for credentials if needed)
- **Lakebase** feature enabled on your workspace (the installer provisions the instance automatically)
- **Node.js 22+ and npm** (optional — the Databricks Apps runtime includes Node.js 22.16, so this is only needed for local frontend builds)

## Usage

```bash
# Full installation (provisions everything from scratch)
python scripts/install_lakemeter.py --profile <cli-profile>

# Skip instance provisioning (use an existing Lakebase instance)
python scripts/install_lakemeter.py --profile <cli-profile> --skip-provision

# Skip app deployment (database setup only)
python scripts/install_lakemeter.py --profile <cli-profile> --skip-deploy

# Preview mode (validate config without making changes)
python scripts/install_lakemeter.py --profile <cli-profile> --dry-run

# CI/CD mode (use all defaults, no interactive prompts)
python scripts/install_lakemeter.py --profile <cli-profile> --non-interactive
```

### CLI Flags

| Flag | Description |
|------|-------------|
| `--profile` | **(Required)** Databricks CLI profile name |
| `--skip-provision` | Skip Lakebase instance creation — use an existing instance |
| `--skip-deploy` | Skip frontend build and app deployment |
| `--dry-run` | Validate prerequisites and show config plan without executing |
| `--non-interactive` | Use all defaults with no prompts (for CI/CD pipelines) |

## The 10-Step Flow

The installer executes 10 sequential steps. Each step prints a progress indicator and a green checkmark on success.

### Step 1: Validate Prerequisites

Checks Python version (3.10+), required Python packages (`databricks-sdk`, `psycopg2-binary`, `requests`), Node.js/npm availability, Databricks CLI installation, pricing data files in `backend/static/pricing/`, and workspace connectivity.

```
[1/10] Validating prerequisites
  ✓ Python 3.11
  ✓ Required Python packages installed
  ✓ Node.js v22.16.0
  ✓ Databricks CLI found
  ✓ Pricing data: 9 JSON files
  ✓ Authenticated as user@company.com
```

### Step 2: Gather Configuration

Interactive prompts collect deployment parameters. All parameters have sensible defaults. Use `--non-interactive` to skip prompts and accept all defaults.

| Parameter | Default | Description |
|-----------|---------|-------------|
| Instance name | `lakemeter-customer` | Lakebase instance identifier |
| Database name | `lakemeter_pricing` | PostgreSQL database name |
| App name | `lakemeter` | Databricks App name |
| CU size | `CU_1` | Lakebase compute unit size (CU_1, CU_2, CU_4, CU_8) |
| Secrets scope | `lakemeter-secrets` | Databricks secret scope name |
| SP client ID key | `sp_clientid` | Secret scope key for SP client ID |
| SP secret key | `sp_secret` | Secret scope key for SP client secret |
| Claude endpoint | `databricks-claude-opus-4-6` | Claude model serving endpoint name (for AI Assistant) |

### Step 3: Provision Lakebase Instance

Creates a new Lakebase (managed PostgreSQL) instance via the Databricks SDK (`database.create_database_instance`). If an instance with the same name already exists, this step reuses it.

- Instance creation takes 2–5 minutes
- The installer polls every 5 seconds until the instance reaches `AVAILABLE` state (timeout: 10 minutes)
- Enables auto-scaling (serverless compute) on the instance
- Enables `pg_native_login` for password-based authentication fallback
- Returns the instance DNS hostname, UID, and name
- Skipped with `--skip-provision`

### Step 4: Create Database, Schema, and Tables

Connects to the Lakebase instance using owner credentials (via `generate_database_credential`) and executes DDL:

- Creates the database (e.g., `lakemeter_pricing`) if it doesn't exist
- Creates the `lakemeter` schema
- Creates 9 application tables: `users`, `templates`, `ref_cloud_tiers`, `estimates`, `ref_workload_types`, `line_items`, `conversation_messages`, `decision_records`, `sharing`
- Seeds reference data: 14 workload types and 8 cloud/tier combinations
- Creates case normalization triggers on `estimates` and `line_items` tables (auto-normalizes cloud, tier, workload_type, etc.)
- Creates a `lakemeter_sync_role` PostgreSQL role with a generated password as a fallback authentication method
- Stores the role credentials (`lakebase-user`, `lakebase-password`, `lakebase-host`, `lakebase-database`) in the secrets scope
- Adds indexes on `line_items(estimate_id)` and `line_items(workload_type)`
- Adds the `discount_config` JSONB column to estimates
- Updates the Lakebase CU size constraint (supports 0.5 and 1–112)

### Step 5: Load Pricing Reference Data

Loads 9 pricing data files from `backend/static/pricing/` into sync tables. Tables are truncated before each load for idempotent refreshes.

| File | Sync Table | Content |
|------|-----------|---------|
| `dbu-rates.json` | `sync_pricing_dbu_rates` | DBU rates by cloud, region, tier |
| `instance-dbu-rates.json` | `sync_ref_instance_dbu_rates` | Instance-level DBU rates |
| `dbu-multipliers.json` | `sync_ref_dbu_multipliers` | Feature multipliers (Photon, serverless) |
| `dbsql-rates.json` | `sync_product_dbsql_rates` | DBSQL warehouse rates by type and size |
| `dbsql-warehouse-config.json` | `sync_ref_dbsql_warehouse_config` | Warehouse driver/worker configuration |
| `model-serving-rates.json` | `sync_product_serverless_rates` | Model Serving GPU/CPU rates |
| `vector-search-rates.json` | `sync_product_serverless_rates` | Vector Search endpoint rates |
| `fmapi-databricks-rates.json` | `sync_product_fmapi_databricks` | FMAPI Databricks-hosted model rates |
| `fmapi-proprietary-rates.json` | `sync_product_fmapi_proprietary` | FMAPI proprietary model rates |

Also creates reference tables: `ref_fmapi_databricks_models`, `ref_fmapi_proprietary_models`, `ref_model_serving_gpu_types`, and `sync_ref_sku_region_map`.

### Step 6: Create SKU Discount Mapping

Populates the SKU discount mapping table that maps workload configurations to Databricks SKU names and discount tiers. This enables accurate pricing lookups for Excel export.

### Step 7: Configure Service Principal Access

The most critical step — configures OAuth M2M access so the Databricks App can connect to Lakebase. See the [Permissions Guide](./permissions) for full details.

Sub-steps:

1. **Ensure secrets scope exists** — creates the scope if it doesn't exist
2. **Collect SP credentials** — reads SP client ID and secret from the secrets scope, or prompts the user to enter them (and stores them)
3. **Grant `CAN_MANAGE`** workspace-level permission on the Lakebase instance
4. **Create SP role** via the Lakebase Roles API with `identity_type=SERVICE_PRINCIPAL`
5. **Grant schema permissions** — `ALL PRIVILEGES` on tables, sequences, and functions in the `lakemeter` schema, plus `ALTER DEFAULT PRIVILEGES`
6. **Verify connectivity** — generate an OAuth token and execute a test query

:::caution
If a role already exists with `identity_type=PG_ONLY`, the installer deletes it and recreates it with `identity_type=SERVICE_PRINCIPAL`. The `PG_ONLY` type cannot exchange OAuth tokens — see the [Permissions Guide](./permissions).
:::

### Step 8: Create Cost Calculation Views

Creates PostgreSQL views that aggregate pricing data for common query patterns used by the API layer.

### Step 9: Generate App Configuration

Generates the `app.yaml` file with `valueFrom` resource references and then configures the corresponding Databricks App resources so those references resolve at runtime.

```yaml
env:
  - name: "DATABRICKS_SECRETS_SCOPE"
    valueFrom: "lakemeter-secrets-scope"
  - name: "LAKEBASE_INSTANCE_NAME"
    valueFrom: "lakemeter-lakebase-instance"
  - name: "DB_HOST"
    valueFrom: "lakemeter-db-host"
  - name: "DB_USER"
    valueFrom: "lakemeter-db-user"
  - name: "DB_NAME"
    valueFrom: "lakemeter-db-name"
```

The installer also configures Databricks App resources so that `valueFrom` references resolve at runtime. It creates workspace secrets for each configuration value and maps them to app-level resources via the Apps API. It also:

- Configures a Claude model serving endpoint resource for the AI Assistant
- Grants the Databricks App's own service principal access to the Lakebase instance (role creation + SQL permissions)

### Step 10: Deploy Application

Runs `deploy.sh --workspace-deploy` to sync the application files to the Databricks workspace and deploy the app. Only essential files are synced (backend, frontend source, scripts, app.yaml). Skipped with `--skip-deploy`.

## After Installation

Once all steps complete:

1. If you used `--skip-deploy`, deploy manually:
   ```bash
   cd backend && databricks apps deploy lakemeter --source-code-path . -p your-profile
   ```
2. Verify the app is running:
   ```bash
   databricks apps get lakemeter -p your-profile
   ```

## Troubleshooting

### Installer fails at Step 3 (provisioning)

- Ensure Lakebase is enabled on your workspace
- Check your profile has sufficient permissions to create database instances
- Use `--skip-provision` if an instance already exists

### Installer fails at Step 7 (SP access)

- The installer creates the secrets scope automatically, but the SP must exist in the workspace
- If prompted for SP credentials, ensure you enter the correct client ID and secret
- The SP must use `identity_type=SERVICE_PRINCIPAL` — see the [Permissions Guide](./permissions)
- Check that the SP has workspace-level access

### Pricing data counts don't match

- Pricing data files are updated periodically from Databricks pricing APIs
- The installer uses `TRUNCATE + INSERT` for idempotent reloads
- Small variations between environments are normal
