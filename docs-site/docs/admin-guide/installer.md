---
sidebar_position: 6
---

# Installer Guide

Lakemeter includes a zero-click installer (`scripts/install_lakemeter.py`) that provisions a complete environment on Databricks — from Lakebase instance creation to app deployment.

## Prerequisites

### Local machine

- **Python 3.10+** with three packages:
  ```bash
  pip install databricks-sdk psycopg2-binary requests
  ```
- **Databricks CLI** installed and configured with a workspace profile ([installation guide](https://docs.databricks.com/en/dev-tools/cli/install.html))
- **Node.js + npm** (optional) — only needed if you want to rebuild the frontend from source. If not installed, the installer uses the pre-built frontend assets included in the repository.

### Databricks workspace

- **AWS workspace** in a [Lakebase-supported region](https://docs.databricks.com/en/oltp/projects/manage-projects.html): `us-east-1`, `us-east-2`, `us-west-2`, `ca-central-1`, `sa-east-1`, `eu-central-1`, `eu-west-1`, `eu-west-2`, `ap-south-1`, `ap-southeast-1`, `ap-southeast-2`
- **Permissions** — the user running the installer needs:
  - **Lakebase**: `CAN CREATE` on database projects (granted to all workspace users by default)
  - **Secret scopes**: ability to create a scope or `WRITE` access to an existing one (all workspace users can create scopes by default)
  - **Databricks Apps**: ability to create apps (granted to all workspace users by default)
  - **Serverless compute**: access to run a one-shot serverless job (Step 5 loads pricing data)

The installer handles everything else automatically:
- Lakebase instance provisioning (reuses existing if same name)
- App Service Principal creation and Lakebase access grants
- Pricing data loading from pre-flattened CSV files included in the repository

## Usage

```bash
# Full installation (interactive — prompts for names)
python scripts/install_lakemeter.py --profile <cli-profile>

# CI/CD mode (use all defaults, no interactive prompts)
python scripts/install_lakemeter.py --profile <cli-profile> --non-interactive
```

### CLI Flags

| Flag | Description |
|------|-------------|
| `--profile` | **(Required)** Databricks CLI profile name |
| `--non-interactive` | Use all defaults with no prompts (for CI/CD pipelines) |

## The 8-Step Flow

The installer executes 8 sequential steps. Each step prints a progress indicator and a green checkmark on success. If a Lakebase instance or Databricks App with the same name already exists, the installer reuses it.

### Step 1: Validate Prerequisites

Checks Python version (3.10+), required Python packages (`databricks-sdk`, `psycopg2-binary`, `requests`), Databricks CLI installation, pricing CSV files, and workspace connectivity.

```
[1/8] Validating prerequisites
  ✓ Python 3.11
  ✓ Required Python packages installed
  ✓ Databricks CLI found
  ✓ Pricing data: 10 CSV files
  ✓ Authenticated as user@company.com
```

### Step 2: Gather Configuration

Interactive prompts collect deployment parameters. All parameters have sensible defaults. Use `--non-interactive` to skip prompts and accept all defaults.

| Parameter | Default | Description |
|-----------|---------|-------------|
| Instance name | `lakemeter-customer` | Lakebase instance identifier |
| Database name | `lakemeter_pricing` | PostgreSQL database name |
| App name | `lakemeter` | Databricks App name |
| Secrets scope | `lakemeter-secrets` | Databricks secret scope name |

The following are fixed (not user-configurable):

| Setting | Value | Reason |
|---------|-------|--------|
| Lakebase scaling | 0.5–16 CU, scale-to-zero | Optimal for cost and performance — starts minimal, scales up under load |
| Claude endpoint | `databricks-claude-opus-4-6` | Same endpoint on every Databricks workspace |

### Step 3: Provision Lakebase Instance

Creates a new Lakebase (managed PostgreSQL) instance via the Databricks SDK. If an instance with the same name already exists, this step reuses it.

- Instance creation takes 2–5 minutes
- The installer polls every 5 seconds until the instance reaches `AVAILABLE` state (timeout: 10 minutes)
- Configures autoscaling from 0.5 CU to 16 CU with scale-to-zero enabled
- Enables `pg_native_login` for password-based authentication fallback

### Step 4: Create Database, Schema, and Tables

Connects to the Lakebase instance using owner credentials and executes DDL:

- Creates the database (e.g., `lakemeter_pricing`) if it doesn't exist
- Creates the `lakemeter` schema
- Creates 9 application tables: `users`, `templates`, `ref_cloud_tiers`, `estimates`, `ref_workload_types`, `line_items`, `conversation_messages`, `decision_records`, `sharing`
- Seeds reference data: 14 workload types and 8 cloud/tier combinations
- Creates case normalization triggers on `estimates` and `line_items` tables
- Creates a `lakemeter_sync_role` PostgreSQL role with a generated password
- Stores the role credentials in the secrets scope
- Adds indexes and the `discount_config` JSONB column

### Step 5: Load Pricing Reference Data

Uploads 10 pre-flattened CSV pricing files and a loader notebook to the workspace, then runs the notebook on serverless compute. The notebook bulk-loads all data into Lakebase sync tables.

| CSV File | Sync Table | Rows |
|----------|-----------|------|
| `dbu-rates.csv` | `sync_pricing_dbu_rates` | ~2,400 |
| `instance-dbu-rates.csv` | `sync_ref_instance_dbu_rates` | ~1,070 |
| `dbu-multipliers.csv` | `sync_ref_dbu_multipliers` | ~50 |
| `dbsql-rates.csv` | `sync_product_dbsql_rates` | ~80 |
| `dbsql-warehouse-config.csv` | `sync_ref_dbsql_warehouse_config` | ~55 |
| `serverless-rates.csv` | `sync_product_serverless_rates` | ~20 |
| `fmapi-databricks-rates.csv` | `sync_product_fmapi_databricks` | ~100 |
| `fmapi-proprietary-rates.csv` | `sync_product_fmapi_proprietary` | ~500 |
| `vm-costs.csv` | `sync_pricing_vm_costs` | ~111,000 |
| `sku-region-map.csv` | `sync_ref_sku_region_map` | 73 |

The notebook also populates derived reference tables (`ref_fmapi_databricks_models`, `ref_fmapi_proprietary_models`, `ref_model_serving_gpu_types`) via SQL `INSERT...SELECT DISTINCT` from the main rate tables.

### Step 6: Create SKU Discount Mapping and Views

Populates the SKU discount mapping table and creates PostgreSQL views that aggregate pricing data for the API layer.

### Step 7: Configure Application

Generates the `app.yaml` file with `valueFrom` resource references and configures the corresponding Databricks App resources:

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

Also grants the app's built-in service principal access to the Lakebase instance.

### Step 8: Deploy Application

Syncs application files to the Databricks workspace and deploys the app.

## Troubleshooting

### Installer fails at Step 3 (provisioning)

- Check your profile has sufficient permissions to create database instances

### App can't connect to Lakebase after deploy

- The app's built-in SP needs a Lakebase role with `identity_type=SERVICE_PRINCIPAL` — Step 7 creates this automatically
- If the app was created before running the installer, re-run the installer to re-grant permissions
- As a fallback, the app uses `lakemeter_sync_role` (password auth) created in Step 4

### Pricing data counts don't match

- Pricing data files are updated periodically from Databricks pricing APIs
- The installer uses `TRUNCATE + INSERT` for idempotent reloads
- Small variations between environments are normal
