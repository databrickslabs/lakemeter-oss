---
sidebar_position: 6
---

# Installer Guide

Lakemeter includes a zero-click installer (`scripts/install_lakemeter.py`) that provisions a complete environment on Databricks — from Lakebase instance creation to app deployment.

## Prerequisites

Before running the installer, ensure you have:

- **Python 3.10+** with `databricks-sdk`, `psycopg2-binary`, and `requests` (these are used by the installer script itself to provision Lakebase and create tables)
- **Databricks CLI** installed and configured with a workspace profile

That's it. The installer handles everything else automatically:
- Lakebase is available on all Databricks workspaces — the installer provisions the instance
- The Databricks App gets its own Service Principal automatically — no need to register one
- Node.js 22 and npm are included in the Databricks Apps runtime — the frontend builds from source at app startup
- Pricing data files ship with the repository

## Usage

```bash
# Full installation with static pricing (default — uses bundled JSON files)
python scripts/install_lakemeter.py --profile <cli-profile>

# Full installation with live API pricing (fetches from cloud APIs + scheduled sync)
python scripts/install_lakemeter.py --profile <cli-profile> --pricing-source api

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
| `--pricing-source` | Pricing data source: `static` (bundled JSON, default) or `api` (live cloud APIs + scheduled sync) |
| `--skip-provision` | Skip Lakebase instance creation — use an existing instance |
| `--skip-deploy` | Skip frontend build and app deployment |
| `--dry-run` | Validate prerequisites and show config plan without executing |
| `--non-interactive` | Use all defaults with no prompts (for CI/CD pipelines) |

## The 12-Step Flow

The installer executes 12 sequential steps. Each step prints a progress indicator and a green checkmark on success.

### Step 1: Validate Prerequisites

Checks Python version (3.10+), required Python packages (`databricks-sdk`, `psycopg2-binary`, `requests`), Databricks CLI installation, pricing data files, and workspace connectivity.

```
[1/12] Validating prerequisites
  ✓ Python 3.11
  ✓ Required Python packages installed
  ✓ Databricks CLI found
  ✓ Pricing data: 9 JSON files
  ✓ Authenticated as user@company.com
```

### Step 2: Gather Configuration

Interactive prompts collect deployment parameters. All parameters have sensible defaults. Use `--non-interactive` to skip prompts and accept all defaults.

#### Pricing Source

The installer asks whether to use **static** (bundled JSON files) or **live API** pricing:

- **Static (default):** Uses pre-bundled pricing data in `backend/static/pricing/`. No cloud credentials needed. Steps 5, 9, and 10 are skipped.
- **Live API:** Fetches pricing from cloud APIs (AWS Pricing API, Azure Retail Prices API, GCP Cloud Billing API) and Databricks `system.billing.list_prices`. Creates a UC catalog, uploads ETL notebooks, and schedules a weekly sync workflow.

When **Live API** is selected, the installer prompts for cloud credentials:

| Credential | Purpose | Required for |
|------------|---------|--------------|
| AWS Access Key ID | AWS Pricing API (boto3) | `03_Fetch_AWS_VM` notebook |
| AWS Secret Access Key | AWS Pricing API (boto3) | `03_Fetch_AWS_VM` notebook |
| GCP Service Account JSON | GCP Cloud Billing Catalog API | `05_Fetch_GCP_VM` notebook |
| AWS workspace config | Databricks REST API for DBU prices | `01_Fetch_DBU_Prices` notebook |
| Azure workspace config | Databricks REST API for DBU prices | `01_Fetch_DBU_Prices` notebook |
| GCP workspace config | Databricks REST API for DBU prices | `01_Fetch_DBU_Prices` notebook |

Workspace configs are JSON objects: `{"host": "https://...", "token": "dapi...", "warehouse_id": "..."}`. Azure VM pricing requires no credentials (public API). All credentials are stored in the secrets scope automatically.

| Parameter | Default | Description |
|-----------|---------|-------------|
| Instance name | `lakemeter-customer` | Lakebase instance identifier |
| Database name | `lakemeter_pricing` | PostgreSQL database name |
| App name | `lakemeter` | Databricks App name |
| Secrets scope | `lakemeter-secrets` | Databricks secret scope name |
| Pricing source | `static` | `static` (bundled JSON files) or `api` (live cloud APIs) |
| UC catalog name | `lakemeter_catalog` | Unity Catalog for ETL pricing tables (only when pricing source is `api`) |

The following are fixed (not user-configurable):

| Setting | Value | Reason |
|---------|-------|--------|
| Lakebase scaling | 0.5–16 CU, scale-to-zero | Optimal for cost and performance — starts minimal, scales up under load |
| Claude endpoint | `databricks-claude-opus-4-6` | Same endpoint on every Databricks workspace |

### Step 3: Provision Lakebase Instance

Creates a new Lakebase (managed PostgreSQL) instance via the Databricks SDK (`database.create_database_instance`). If an instance with the same name already exists, this step reuses it.

- Instance creation takes 2–5 minutes
- The installer polls every 5 seconds until the instance reaches `AVAILABLE` state (timeout: 10 minutes)
- Configures autoscaling from 0.5 CU to 16 CU with scale-to-zero enabled
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

### Step 5: Create Unity Catalog and Schema

:::note
Only runs when pricing source is `api`. Skipped for `static` (default).
:::

Creates a Unity Catalog and schema for ETL pricing tables. If the catalog or schema already exists, the installer reuses it.

- Creates the catalog (e.g., `lakemeter_catalog`) via `w.catalogs.create()` if it doesn't exist
- Creates the `lakemeter` schema within the catalog via `w.schemas.create()` if it doesn't exist

### Step 6: Load Pricing Reference Data

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

### Step 7: Create SKU Discount Mapping

Populates the SKU discount mapping table that maps workload configurations to Databricks SKU names and discount tiers. This enables accurate pricing lookups for Excel export.

### Step 8: Create Cost Calculation Views

Creates PostgreSQL views that aggregate pricing data for common query patterns used by the API layer.

### Step 9: Upload ETL Notebooks

:::note
Only runs when pricing source is `api`. Skipped for `static` (default).
:::

Stores cloud API credentials in the secrets scope and uploads 12 ETL pricing sync notebooks from `etl/pricing_sync/` to the workspace at `/Workspace/Users/{user}/lakemeter/etl/pricing_sync/`.

- Stores all collected API credentials (AWS keys, GCP SA JSON, workspace configs) in the secrets scope
- Patches `CATALOG` and `SECRET_SCOPE` variables in each notebook to match user's configuration
- Uploads `Instance Type Pricing.xlsx` alongside notebooks (used by `02_Load_DBU_Rates`)
- Debug/utility notebooks (98/99 prefix) are excluded

Notebooks uploaded:
- `01_Fetch_DBU_Prices` through `12_Load_FMAPI_Proprietary_Rates`

### Step 10: Create Pricing Sync Workflow

:::note
Only runs when pricing source is `api`. Skipped for `static` (default).
:::

Creates a Databricks Workflow (`lakemeter-pricing-sync`) that runs all 12 ETL notebooks as a sequential task chain. If a workflow with the same name already exists, the installer updates it.

- Tasks run sequentially (each depends on the previous)
- Schedule: Weekly on Sundays at 2:00 AM UTC
- Uses serverless compute (no cluster management)

### Step 11: Configure Application

Generates the `app.yaml` file with `valueFrom` resource references and configures the corresponding Databricks App resources so those references resolve at runtime.

```yaml
env:
  - name: "LAKEBASE_INSTANCE_NAME"
    valueFrom: "lakemeter-lakebase-instance"
  - name: "DB_HOST"
    valueFrom: "lakemeter-db-host"
  - name: "DB_USER"
    valueFrom: "lakemeter-db-user"
  - name: "DB_NAME"
    valueFrom: "lakemeter-db-name"
  - name: "CLAUDE_MODEL_ENDPOINT"
    valueFrom: "lakemeter-claude-endpoint"
```

`DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID`, and `DATABRICKS_CLIENT_SECRET` are auto-injected by the Databricks Apps platform — no manual configuration needed.

The installer also:

- Creates workspace secrets for each configuration value and maps them to app-level resources via the Apps API
- Configures a Claude model serving endpoint resource (`CAN_QUERY`) for the AI Assistant
- Grants the Databricks App's own built-in service principal access to the Lakebase instance (role creation with `identity_type=SERVICE_PRINCIPAL` + SQL permissions)

### Step 12: Deploy Application

Runs `deploy.sh --workspace-deploy` to sync the application files to the Databricks workspace and deploy the app. Only essential files are synced (backend, frontend source, scripts, app.yaml). Skipped with `--skip-deploy`.

## After Installation

Once all steps complete:

1. **If you chose Live API pricing:** Run the pricing sync workflow manually for the first time (the weekly schedule starts automatically, but you need initial data):
   ```bash
   databricks jobs run-now lakemeter-pricing-sync -p your-profile
   ```
   If you chose Static pricing, this step is not needed — pricing data was loaded from bundled JSON files.
2. If you used `--skip-deploy`, deploy manually:
   ```bash
   cd backend && databricks apps deploy lakemeter --source-code-path . -p your-profile
   ```
3. Verify the app is running:
   ```bash
   databricks apps get lakemeter -p your-profile
   ```

## Troubleshooting

### Installer fails at Step 3 (provisioning)

- Check your profile has sufficient permissions to create database instances
- Use `--skip-provision` if an instance already exists

### App can't connect to Lakebase after deploy

- The app's built-in SP needs a Lakebase role with `identity_type=SERVICE_PRINCIPAL` — Step 11 creates this automatically
- If the app was created before running the installer, re-run the installer with `--skip-provision` to re-grant permissions
- As a fallback, the app uses `lakemeter_sync_role` (password auth) created in Step 4

### Pricing data counts don't match

- Pricing data files are updated periodically from Databricks pricing APIs
- The installer uses `TRUNCATE + INSERT` for idempotent reloads
- Small variations between environments are normal
