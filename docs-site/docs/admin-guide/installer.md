---
sidebar_position: 6
---

# Installer Guide

Lakemeter includes a one-command installer (`scripts/install.sh`) that provisions a complete environment on Databricks — from Lakebase instance creation to app deployment and verification. All heavy lifting runs on Databricks serverless compute via a DABs (Databricks Asset Bundles) workflow. Total installation time is approximately **15-20 minutes**.

## Prerequisites

### Local machine

- **Databricks CLI** installed and configured with a workspace profile ([installation guide](https://docs.databricks.com/en/dev-tools/cli/install.html))
  - DABs support is included in the CLI (no additional installation needed)
  - Verify with: `databricks --version` (requires 0.200+)

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
- Database creation, schema setup, and stored functions
- Pricing data loading from pre-flattened CSV files included in the repository
- App Service Principal creation and Lakebase access grants
- App deployment and smoke test verification

## Usage

```bash
# Clone the repository
git clone https://github.com/steven-tan_data/lakemeter-opensource.git
cd lakemeter-opensource

# Interactive installation (prompts for names)
./scripts/install.sh --profile <cli-profile>

# Non-interactive (use all defaults)
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
| `-h`, `--help` | Show usage help |

## What You'll See

### Phase 1: Configuration (~5 seconds)

The installer checks connectivity and prompts for configuration (or uses defaults in `--non-interactive` mode):

```
Lakemeter Installer
================================

Checking workspace connectivity...
Connected as: admin@company.com

Configuration (press Enter to accept defaults)

  Lakebase instance name [lakemeter-customer]:
  Database name [lakemeter_pricing]:
  App name [lakemeter]:
  Secrets scope [lakemeter-secrets]:

Configuration:
  Instance name:  lakemeter-customer
  Database:       lakemeter_pricing
  App name:       lakemeter
  Secrets scope:  lakemeter-secrets
  Claude endpoint: databricks-claude-opus-4-6
```

### Phase 2: Bundle Deploy (~20 seconds)

Uploads notebooks, pricing data, and app source to the workspace:

```
Preparing bundle...
  Splitting vm-costs.csv (12MB)...
  Split into 2 parts
  Pricing data: 11 CSV files
  App source prepared

Deploying bundle to workspace...
Uploading bundle files to /Workspace/Users/admin@company.com/.bundle/lakemeter-installer/default/files...
Deploying resources...
Updating deployment state...
Deployment complete!
Bundle deployed
```

### Phase 3: Workflow Execution (~15 minutes)

The installer launches a DABs workflow with 9 tasks and shows live progress:

```
Running installer workflow on serverless compute...
  This will provision Lakebase, create tables, load pricing data,
  configure the app, and deploy it.

Note: The full installation typically takes 15-20 minutes.

  Run URL: https://your-workspace.cloud.databricks.com/#job/.../run/...

  Task Progress:
    [done] provision_lakebase     (30s)
    [done] create_app             (3m40s)
    [done] create_database        (16s)
    [done] create_functions       (15s)
    [done] load_pricing_data      (25s)
    [done] create_sku_mapping     (9s)
    [done] grant_app_access       (9s)
    [ .. ] deploy_app             running (8m22s)
    [    ] verify_installation    waiting
  Elapsed: 12m31s
```

The progress display refreshes every 10 seconds with live task status:
- `[done]` — completed with elapsed time
- `[ .. ]` — currently running
- `[    ]` — waiting for dependencies
- `[FAIL]` — task failed (installer exits with error details)

### Phase 4: Completion

```
Installation complete!

  App URL:      https://lakemeter-XXXXX.aws.databricksapps.com
  Verification: All smoke tests passed
  Details:      databricks runs get-output --run-id XXXXX --profile <profile>
```

## How It Works

The installer uses Databricks Asset Bundles (DABs) to package and run a workflow on serverless compute. The local shell script (`install.sh`) handles:

1. Prompting for configuration values
2. Preparing pricing data (splitting large CSV files)
3. Running `databricks bundle deploy` to upload notebooks and data files
4. Running `databricks bundle run` to execute the workflow
5. Polling and displaying live task progress

All database operations, app configuration, and deployment run as notebook tasks on Databricks serverless compute (environment v5, which has `psycopg2`, `requests`, and `databricks-sdk` pre-installed).

## The 9-Task Workflow

The DABs workflow executes 9 notebook tasks with parallelization where possible:

```
01_provision (30s)  ║  05a_create_app (3m40s)    ← parallel from start
      │             ║        │
02_create_db (16s)  ║        │
      │             ╠════════╝
  ┌───┴──────┐      │
02b_funcs  03_data  05b_grant_sp (9s)
  (15s)    (25s)         │
            │      06_deploy_app (10m39s)
       04_sku (9s)       │
                    07_verify (9s)
```

### Task 1: Provision Lakebase Instance (30s)

Creates a new Lakebase (managed PostgreSQL) instance via the Databricks SDK. If an instance with the same name already exists, reuses it.

- Configures autoscaling from 1 CU to 16 CU with scale-to-zero enabled
- Enables `pg_native_login` for password-based authentication fallback
- Passes instance host and UID to downstream tasks via task values

### Task 2: Create App (3m 40s, parallel with Task 1)

Creates/reuses the Databricks App and configures resources. Runs in parallel with database provisioning since it has no dependencies.

- Sets workspace secret for Lakebase instance name
- Creates the Databricks App (this is the slow step — `create_and_wait` takes ~3min)
- Configures 5 app resources with `valueFrom` secret references
- Generates `app.yaml` for the deployment step

### Task 3: Create Database, Schema, and Tables (16s)

Connects to Lakebase using owner OAuth credentials and executes DDL:

- Creates the database (e.g., `lakemeter_pricing`) if it doesn't exist
- Creates the `lakemeter` schema
- Creates 9 application tables: `users`, `templates`, `ref_cloud_tiers`, `estimates`, `ref_workload_types`, `line_items`, `conversation_messages`, `decision_records`, `sharing`
- Seeds reference data: 9 workload types and 8 cloud/tier combinations
- Creates case normalization triggers
- Creates a `lakemeter_sync_role` PostgreSQL role with a generated password
- Stores credentials in the secrets scope

### Task 4: Create Stored Functions (15s, parallel with Task 5)

Deploys 19 stored functions to the `lakemeter` schema — DBU calculators, VM cost calculators, line item cost orchestrator, and serverless compute calculators.

### Task 5: Load Pricing Reference Data (25s, parallel with Task 4)

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
| `vm-costs.csv` (split) | `sync_pricing_vm_costs` | ~111,000 |
| `sku-region-map.csv` | `sync_ref_sku_region_map` | 73 |

Also populates derived reference tables (`ref_fmapi_databricks_models`, `ref_fmapi_proprietary_models`, `ref_model_serving_gpu_types`) via SQL `INSERT...SELECT DISTINCT`.

### Task 6: Create SKU Discount Mapping (9s)

Populates the SKU discount mapping table from DBU rates and marks non-cross-service-eligible SKUs.

### Task 7: Grant App Service Principal Access (9s)

Grants the app's built-in Service Principal access to the Lakebase instance:

- Creates a Lakebase role with `identity_type=SERVICE_PRINCIPAL` and `membership_role=DATABRICKS_SUPERUSER`
- Grants SQL permissions: `CONNECT`, `USAGE`, `ALL PRIVILEGES` on tables, sequences, and functions

### Task 8: Deploy Application (10m 39s)

Copies app source from the DABs bundle to the app's workspace source path, then deploys:

- Uploads backend/ (FastAPI source + pre-built static assets), app.yaml, requirements.txt
- Excludes `__pycache__`, `.pyc`, `.csv`, `manifest.json`
- Triggers deployment via Databricks Apps API
- Waits for deployment to reach SUCCEEDED state (~10 minutes for snapshot + startup)

### Task 9: Verify Installation (9s)

Runs ~80 smoke tests against the live deployed app to confirm everything works:

| Category | Tests | What's Checked |
|----------|-------|----------------|
| Health | 2 | `/health`, `/api` endpoints respond correctly |
| Database | 1 | Database connectivity verified |
| Reference Data | ~50 | Regions, tiers, instances, VM costs, DBSQL warehouses, pricing, DBU rates, GPU types, vector search, photon multipliers — all tested for **AWS, Azure, and GCP** |
| Cost Calculations | ~20 | All workload types: Jobs, DBSQL, All-Purpose, DLT, Model Serving, Vector Search, FMAPI, Lakebase — with cross-cloud tests on Azure and GCP |
| AI Assistant | ~5 | Chat response, workload proposal, confirm-workload, conversation state |
| Estimate CRUD | 3 | Create estimate, add line item, Excel export |

If any test fails, the task reports which tests failed and the workflow marks as FAILED.

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

## What Gets Created

After a successful installation, your workspace will have:

| Resource | Details |
|----------|---------|
| **Lakebase instance** | `lakemeter-customer` — 1-16 CU, scale-to-zero |
| **Database** | `lakemeter_pricing` with `lakemeter` schema, 9 tables, 19 functions |
| **Secret scope** | `lakemeter-secrets` with 5 secrets (host, user, db, password, instance name) |
| **Databricks App** | `lakemeter` with 5 resources (4 secrets + 1 serving endpoint) |
| **App URL** | `https://lakemeter-XXXXX.aws.databricksapps.com` |

## Re-running the Installer

The installer is **idempotent** — running it again on the same workspace will:

- Reuse the existing Lakebase instance (no data loss)
- Reuse the existing app (no downtime during reconfiguration)
- Re-create tables with `IF NOT EXISTS` (existing data preserved)
- Reload pricing data via `TRUNCATE + INSERT` (refreshes to latest)
- Re-grant SP access (harmless if already granted)
- Redeploy the app (picks up code changes)

This means you can safely re-run the installer to:
- Update pricing data after a new release
- Fix a broken deployment
- Add newly created stored functions

## Troubleshooting

### Installer fails at provision_lakebase

- Check your profile has sufficient permissions to create database instances
- Ensure your workspace is in a Lakebase-supported region
- If the instance already exists in a FAILED state, delete it manually and re-run

### Installer fails at create_app

- The `apps.create_and_wait` call can timeout in rare cases — re-run the installer, it will reuse the partially created app
- Check workspace quota for Databricks Apps

### App can't connect to Lakebase after deploy

- The app's built-in SP needs a Lakebase role — Task 7 creates this automatically
- If the app was created before running the installer, re-run to re-grant permissions
- As a fallback, the app uses `lakemeter_sync_role` (password auth) created in Task 3

### verify_installation fails

- Check which specific tests failed in the Databricks UI (click the Run URL, then the verify_installation task)
- Common causes:
  - App still starting up (deploy_app completed but app not yet ready) — wait 2 minutes and check the app URL directly
  - Missing pricing data — re-run the installer to reload
  - AI assistant test fails — check that the `databricks-claude-opus-4-6` serving endpoint is available in your workspace

### Bundle deploy fails

- Ensure Databricks CLI is up to date: `databricks --version` (requires 0.200+)
- Check connectivity: `databricks current-user me --profile <profile>`
- Check for file permission issues: the installer needs write access to `scripts/pricing_data/` and `scripts/app_source/` for temporary files

### Progress display not updating

- The progress poller needs network access to poll `databricks jobs get-run` — check CLI connectivity
- You can always check progress in the Databricks UI via the Run URL printed at the start
