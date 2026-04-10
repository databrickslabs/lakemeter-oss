---
sidebar_position: 6
---

# Installer Guide

Lakemeter includes a one-command installer (`scripts/install.sh`) that provisions a complete environment on Databricks — from Lakebase instance creation to app deployment. All heavy lifting runs on Databricks serverless compute via a DABs (Databricks Asset Bundles) workflow.

## Prerequisites

### Local machine

- **Databricks CLI** installed and configured with a workspace profile ([installation guide](https://docs.databricks.com/en/dev-tools/cli/install.html))
  - DABs support is included in the CLI (no additional installation needed)

That's it — no Python packages, no Node.js, no other dependencies needed locally.

### Databricks workspace

- **AWS workspace** in a [Lakebase-supported region](https://docs.databricks.com/en/oltp/projects/manage-projects.html): `us-east-1`, `us-east-2`, `us-west-2`, `ca-central-1`, `sa-east-1`, `eu-central-1`, `eu-west-1`, `eu-west-2`, `ap-south-1`, `ap-southeast-1`, `ap-southeast-2`
- **Permissions** — the user running the installer needs:
  - **Lakebase**: `CAN CREATE` on database projects (granted to all workspace users by default)
  - **Secret scopes**: ability to create a scope or `WRITE` access to an existing one (all workspace users can create scopes by default)
  - **Databricks Apps**: ability to create apps (granted to all workspace users by default)
  - **Serverless compute**: access to run serverless jobs (the installer workflow runs on serverless environment v5)

The installer handles everything else automatically:
- Lakebase instance provisioning (reuses existing if same name)
- App Service Principal creation and Lakebase access grants
- Pricing data loading from pre-flattened CSV files included in the repository

## Usage

```bash
# Full installation (interactive — prompts for names)
./scripts/install.sh --profile <cli-profile>

# CI/CD mode (use all defaults, no interactive prompts)
./scripts/install.sh --profile <cli-profile> --non-interactive
```

### CLI Flags

| Flag | Description |
|------|-------------|
| `--profile` | Databricks CLI profile name (required if not using DEFAULT) |
| `--non-interactive` | Use all defaults with no prompts (for CI/CD pipelines) |
| `--instance-name` | Lakebase instance name (default: `lakemeter-customer`) |
| `--db-name` | Database name (default: `lakemeter_pricing`) |
| `--app-name` | App name (default: `lakemeter`) |
| `--secrets-scope` | Secret scope name (default: `lakemeter-secrets`) |

## How It Works

The installer uses Databricks Asset Bundles (DABs) to package and run a workflow on serverless compute. The local shell script (`install.sh`) only handles:

1. Prompting for configuration values
2. Running `databricks bundle deploy` to upload notebooks and data files
3. Running `databricks bundle run` to execute the workflow

All database operations, app configuration, and deployment run as notebook tasks on Databricks serverless compute (environment v5, which has `psycopg2`, `requests`, and `databricks-sdk` pre-installed).

## The 6-Step Workflow

The DABs workflow executes 6 sequential notebook tasks. Each task depends on the previous one completing successfully.

### Task 1: Provision Lakebase Instance

Creates a new Lakebase (managed PostgreSQL) instance via the Databricks SDK. If an instance with the same name already exists, this task reuses it.

- Instance creation takes 2–5 minutes
- Configures autoscaling from 1 CU to 16 CU with scale-to-zero enabled
- Enables `pg_native_login` for password-based authentication fallback
- Passes instance host and UID to downstream tasks via task values

### Task 2: Create Database, Schema, and Tables

Connects to the Lakebase instance using owner OAuth credentials and executes DDL:

- Creates the database (e.g., `lakemeter_pricing`) if it doesn't exist
- Creates the `lakemeter` schema
- Creates 9 application tables: `users`, `templates`, `ref_cloud_tiers`, `estimates`, `ref_workload_types`, `line_items`, `conversation_messages`, `decision_records`, `sharing`
- Seeds reference data: 9 workload types and 8 cloud/tier combinations
- Creates case normalization triggers on `estimates` and `line_items` tables
- Creates a `lakemeter_sync_role` PostgreSQL role with a generated password
- Stores the role credentials in the secrets scope
- Runs schema migrations (indexes, additional columns)

### Task 3: Load Pricing Reference Data

Reads pre-flattened CSV pricing files from the DABs bundle path and bulk-loads into Lakebase sync tables.

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

Also populates derived reference tables (`ref_fmapi_databricks_models`, `ref_fmapi_proprietary_models`, `ref_model_serving_gpu_types`) via SQL `INSERT...SELECT DISTINCT`.

### Task 4: Create SKU Discount Mapping

Populates the SKU discount mapping table from DBU rates and marks non-cross-service-eligible SKUs.

### Task 5: Configure Application

Creates/reuses the Databricks App, configures app resources with `valueFrom` secret references, generates `app.yaml`, and grants the app's built-in Service Principal access to the Lakebase instance.

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

### Task 6: Deploy Application

Copies application files from the DABs bundle path to the app's workspace source path and deploys via the Databricks SDK. Pre-built frontend assets are included in the bundle.

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| Instance name | `lakemeter-customer` | Lakebase instance identifier |
| Database name | `lakemeter_pricing` | PostgreSQL database name |
| App name | `lakemeter` | Databricks App name |
| Secrets scope | `lakemeter-secrets` | Databricks secret scope name |

The following are fixed (not user-configurable):

| Setting | Value | Reason |
|---------|-------|--------|
| Lakebase scaling | 1–16 CU, scale-to-zero | Optimal for cost and performance |
| Claude endpoint | `databricks-claude-opus-4-6` | Same endpoint on every Databricks workspace |
| Serverless environment | v5 | Pre-installed psycopg2, requests, databricks-sdk |

## Troubleshooting

### Installer fails at Task 1 (provisioning)

- Check your profile has sufficient permissions to create database instances
- Ensure your workspace is in a Lakebase-supported region

### App can't connect to Lakebase after deploy

- The app's built-in SP needs a Lakebase role with `identity_type=SERVICE_PRINCIPAL` — Task 5 creates this automatically
- If the app was created before running the installer, re-run the installer to re-grant permissions
- As a fallback, the app uses `lakemeter_sync_role` (password auth) created in Task 2

### Pricing data counts don't match

- Pricing data files are updated periodically from Databricks pricing APIs
- The installer uses `TRUNCATE + INSERT` for idempotent reloads
- Small variations between environments are normal

### Bundle deploy fails

- Ensure Databricks CLI is up to date: `databricks --version` (requires 0.200+)
- Check connectivity: `databricks current-user me --profile <profile>`
