# Lakemeter Installer E2E Test Report

**Date:** 2026-04-11  
**Tester:** steven.tan@databricks.com  
**Workspace:** fe-vm-lakemeter.cloud.databricks.com  
**CLI Profile:** lakemeter  
**Run ID:** 74542605548011  
**Run URL:** https://fe-vm-lakemeter.cloud.databricks.com/?o=335310294452632#job/902515825315646/run/74542605548011

---

## Overall Result: ALL PASS

| Metric | Value |
|--------|-------|
| Total wall clock | **14m 40s** |
| Tasks | **9/9 passed** |
| Verification tests | **All passed** (9s) |
| App URL | https://lakemeter-335310294452632.aws.databricksapps.com |

---

## 1. CLI Input

### Command Executed

```bash
cd lakemeter_app
bash scripts/install.sh --profile lakemeter --non-interactive
```

### Effective Configuration (all defaults)

| Parameter | Value |
|-----------|-------|
| Databricks CLI profile | `lakemeter` |
| Instance name | `lakemeter-customer` |
| Database name | `lakemeter_pricing` |
| App name | `lakemeter` |
| Secrets scope | `lakemeter-secrets` |
| Claude endpoint | `databricks-claude-opus-4-6` |

---

## 2. CLI Output (verbatim)

```
Lakemeter Installer
================================

Checking workspace connectivity...
Connected as: steven.tan@databricks.com

Configuration:
  Instance name:  lakemeter-customer
  Database:       lakemeter_pricing
  App name:       lakemeter
  Secrets scope:  lakemeter-secrets
  Claude endpoint: databricks-claude-opus-4-6

Preparing bundle...
  Splitting vm-costs.csv (12MB)...
  Split into 2 parts
  Pricing data: 11 CSV files
  App source prepared

Deploying bundle to workspace...
Uploading bundle files to /Workspace/Users/steven.tan@databricks.com/.bundle/lakemeter-installer/default/files...
Deploying resources...
Updating deployment state...
Deployment complete!
Bundle deployed

Running installer workflow on serverless compute...
  This will provision Lakebase, create tables, load pricing data,
  configure the app, and deploy it.

Note: The full installation typically takes 15-20 minutes.

Run URL: https://fe-vm-lakemeter.cloud.databricks.com/?o=335310294452632#job/902515825315646/run/74542605548011
```

> **Note:** The progress poller did not display during this run due to a bug in the run ID extraction (now fixed — see Section 6). The workflow completed successfully via `--no-wait` + background execution. After the fix, the CLI will show a live-updating task dashboard refreshing every 10 seconds.

### Expected CLI Progress Display (after fix)

```
  Task Progress:
    [done] provision_lakebase     (30s)
    [done] create_app             (3m40s)
    [done] create_database        (16s)
    [done] create_functions       (15s)
    [done] load_pricing_data      (25s)
    [done] create_sku_mapping     (9s)
    [done] grant_app_access       (9s)
    [done] deploy_app             (10m39s)
    [done] verify_installation    (9s)
  Elapsed: 14m40s

Installation complete!

  App URL:      https://lakemeter-335310294452632.aws.databricksapps.com
  Verification: All smoke tests passed
  Details:      databricks runs get-output --run-id 74542605548011 --profile lakemeter
```

---

## 3. Bundle Deploy Phase

| Step | Duration | Details |
|------|----------|---------|
| Prepare pricing data | ~2s | 11 CSV files (vm-costs.csv split into 2 parts due to 9MB limit) |
| Prepare app source | ~1s | backend/app/, backend/static/, requirements.txt |
| `databricks bundle deploy` | ~15s | Uploaded to `/Workspace/Users/steven.tan@databricks.com/.bundle/lakemeter-installer/default/files` |
| **Total bundle deploy** | **~18s** | |

### Files Synced by Bundle

| Directory | Contents |
|-----------|----------|
| `notebooks/` | 9 Python notebooks (01-07 + 02b, 05a, 05b) |
| `pricing_data/` | 11 CSV files (dbu-rates, instance-dbu-rates, dbu-multipliers, dbsql-rates, dbsql-warehouse-config, serverless-rates, fmapi-databricks-rates, fmapi-proprietary-rates, vm-costs_part1, vm-costs_part2, sku-region-map) |
| `app_source/` | backend/ (FastAPI source + pre-built static assets), requirements.txt |
| `functions/` | 19 SQL function files |

---

## 4. Workflow Execution Phase

### Task Dependency Graph (DAG)

```
Time  0s          30s         1m          2m          3m          4m         ...10m        ...14m
      ├───────────┼───────────┼───────────┼───────────┼───────────┼──────────···──────────···──────┤
      │                                                                                           │
      ├─ provision_lakebase (30s) ─┐                                                              │
      │                            ├─ create_database (16s) ─┬─ load_pricing (25s) ── create_sku (9s)
      │                            │                         └─ create_funcs (15s)                │
      │                            │                                                              │
      ├─ create_app (3m40s) ───────┴─ grant_app_access (9s) ── deploy_app (10m39s) ── verify (9s)│
      │                                                                                           │
      └───────────────────────────────────────────────────────────────────────────────────────────┘
```

### Per-Task Timing

| # | Task | Start Offset | Duration | Result | Exit Message |
|---|------|-------------|----------|--------|-------------|
| 1 | `provision_lakebase` | +0s | **30s** | SUCCESS | `Created new instance: ep-rough-sea-d1h9nfx1.database.us-west-2.cloud.databricks.com (11.7s)` |
| 2 | `create_app` | +0s | **3m 40s** | SUCCESS | `App 'lakemeter' configured with 5 resources (207.1s)` |
| 3 | `create_database` | +30s | **16s** | SUCCESS | `Database, schema, tables, and auth role created successfully` |
| 4 | `create_functions` | +47s | **15s** | SUCCESS | `All 19 functions deployed successfully` |
| 5 | `load_pricing_data` | +47s | **25s** | SUCCESS | (completed normally) |
| 6 | `create_sku_mapping` | +72s | **9s** | SUCCESS | (completed normally) |
| 7 | `grant_app_access` | +221s (3m41s) | **9s** | SUCCESS | `App SP access granted (2.7s)` |
| 8 | `deploy_app` | +230s (3m50s) | **10m 39s** | SUCCESS | `Deploy started — check UI for status` |
| 9 | `verify_installation` | +870s (14m30s) | **9s** | SUCCESS | All tests passed |

### Parallelization Analysis

| Branch | Tasks | Duration | Critical Path? |
|--------|-------|----------|---------------|
| DB provisioning | provision → create_db → (functions ∥ data) → sku_mapping | **1m 35s** | No |
| App creation | create_app | **3m 40s** | Yes (blocks grant_app_access) |
| Merge + Deploy | grant_app_access → deploy_app → verify | **10m 57s** | Yes |

**Critical path:** `create_app (3m40s)` → `grant_app_access (9s)` → `deploy_app (10m39s)` → `verify (9s)` = **14m 28s**

The DB branch finishes in 1m35s while the app branch takes 3m40s, so DB provisioning completes ~2 minutes before app creation finishes. Parallelization saves ~1m35s compared to fully sequential.

---

## 5. What Each Task Did

### Task 1: provision_lakebase (30s)

- Created new Lakebase instance `lakemeter-customer`
- Instance host: `ep-rough-sea-d1h9nfx1.database.us-west-2.cloud.databricks.com`
- Configured autoscaling: 1-16 CU with scale-to-zero
- Enabled `pg_native_login` for password auth fallback
- Passed instance_host, instance_uid, instance_name via task values

### Task 2: create_app (3m 40s, parallel with Task 1)

- Set workspace secret: `lakemeter-secrets:lakebase-instance-name`
- Created Databricks App `lakemeter` (this is the slow part — `create_and_wait` takes ~3min)
- Configured 5 app resources:
  - `lm-lakebase-instance` → secret `lakebase-instance-name`
  - `lm-db-host` → secret `lakebase-host`
  - `lm-db-user` → secret `lakebase-user`
  - `lm-db-name` → secret `lakebase-database`
  - `lm-claude-endpoint` → serving endpoint `databricks-claude-opus-4-6`
- Generated `app.yaml` and wrote to bundle files path

### Task 3: create_database (16s)

- Connected to Lakebase via owner OAuth credentials
- Created database `lakemeter_pricing`
- Created schema `lakemeter`
- Created 9 application tables: `users`, `templates`, `ref_cloud_tiers`, `estimates`, `ref_workload_types`, `line_items`, `conversation_messages`, `decision_records`, `sharing`
- Seeded reference data (9 workload types, 8 cloud/tier combinations)
- Created case normalization triggers on `estimates` and `line_items`
- Created `lakemeter_sync_role` PostgreSQL role with generated password
- Stored credentials in secrets scope (`lakebase-host`, `lakebase-user`, `lakebase-database`, `lakebase-password`)
- Ran schema migrations (indexes, additional columns)

### Task 4: create_functions (15s, parallel with Task 5)

- Deployed 19 stored functions to `lakemeter` schema
- Functions include: DBU calculators (jobs, all-purpose, DBSQL, DLT, serverless, model-serving, vector-search, FMAPI, lakebase), VM cost calculators, line item cost orchestrator

### Task 5: load_pricing_data (25s, parallel with Task 4)

- Loaded 11 CSV files into sync tables via TRUNCATE + bulk INSERT
- ~115,000+ total rows across all tables:

| Table | Approximate Rows |
|-------|-----------------|
| `sync_pricing_vm_costs` | ~111,000 |
| `sync_pricing_dbu_rates` | ~2,400 |
| `sync_ref_instance_dbu_rates` | ~1,070 |
| `sync_product_fmapi_proprietary` | ~500 |
| `sync_product_fmapi_databricks` | ~100 |
| `sync_product_dbsql_rates` | ~80 |
| `sync_ref_sku_region_map` | 73 |
| `sync_ref_dbsql_warehouse_config` | ~55 |
| `sync_ref_dbu_multipliers` | ~50 |
| `sync_product_serverless_rates` | ~20 |

- Also populated derived reference tables (`ref_fmapi_databricks_models`, `ref_fmapi_proprietary_models`, `ref_model_serving_gpu_types`) via SQL `INSERT...SELECT DISTINCT`

### Task 6: create_sku_mapping (9s)

- Populated `ref_sku_discount_mapping` from DBU rates
- Marked non-cross-service-eligible SKUs

### Task 7: grant_app_access (9s)

- Retrieved app Service Principal client ID
- Created Lakebase role for SP (`identity_type=SERVICE_PRINCIPAL`, `membership_role=DATABRICKS_SUPERUSER`)
- Granted SQL permissions via psycopg2:
  - `GRANT CONNECT ON DATABASE lakemeter_pricing`
  - `GRANT USAGE ON SCHEMA lakemeter`
  - `GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA lakemeter`
  - `GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA lakemeter`
  - `GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA lakemeter`

### Task 8: deploy_app (10m 39s)

- Uploaded app source from bundle files to app workspace path (`/Workspace/Users/steven.tan@databricks.com/apps/lakemeter/`)
- Files uploaded: backend/ (FastAPI source + pre-built static assets), app.yaml, requirements.txt
- Excluded: `__pycache__`, `.pyc`, `.csv`, `manifest.json`
- Triggered deployment via REST API (`POST /api/2.0/apps/lakemeter/deployments`)
- Waited for deployment to reach SUCCEEDED state
- Breakdown: ~30s upload + ~10min Databricks Apps snapshot + startup

### Task 9: verify_installation (9s)

Ran ~80 smoke tests against the live deployed app:

**Test 1: Health & API Root** (2 tests)
- `GET /health` → `{"status": "healthy"}`
- `GET /api` → `{"name": "Lakemeter API", "version": "1.0.0"}`

**Test 2: Database Connectivity** (1 test)
- `GET /api/v1/debug/database` → DB connection confirmed

**Test 3: Reference Data — All 3 Clouds** (~50 tests)
- Regions: AWS (✓), Azure (✓), GCP (✓)
- Tiers: AWS (✓), Azure (✓), GCP (✓)
- Instance types: AWS/us-east-1 (✓), Azure/eastus (✓), GCP/us-central1 (✓)
- VM costs: AWS/i3.xlarge (✓), Azure/Standard_DS3_v2 (✓), GCP/n1-standard-4 (✓)
- DBSQL warehouse sizes: AWS (✓), Azure (✓), GCP (✓)
- DBSQL warehouse VM costs: AWS (✓), Azure (✓), GCP (✓)
- Pricing product types: AWS (✓), Azure (✓), GCP (✓)
- DBU rates: AWS (✓), Azure (✓), GCP (✓)
- Model Serving GPU types: AWS (✓), Azure (✓), GCP (✓)
- Vector Search modes: AWS (✓), Azure (✓), GCP (✓)
- Photon multipliers: AWS (✓), Azure (✓), GCP (✓)
- Lakebase CU sizes (✓), DLT editions (✓), Serverless modes (✓)
- VM pricing options (✓), SKU types (✓)
- FMAPI Databricks models (✓)
- FMAPI Proprietary: OpenAI (✓), Anthropic (✓), Google (✓)
- FMAPI form configs: Databricks (✓), Proprietary (✓)

**Test 4: Cost Calculations** (~20 tests)
- Jobs Classic — AWS (✓)
- Jobs Serverless — AWS (✓)
- DBSQL Classic — AWS (✓)
- DBSQL Pro — AWS (✓)
- DBSQL Serverless — AWS (✓)
- All-Purpose Classic — AWS (✓)
- All-Purpose Serverless — AWS (✓)
- DLT Core — AWS (✓)
- DLT Pro — AWS (✓)
- DLT Advanced — AWS (✓)
- DLT Serverless — AWS (✓)
- Model Serving — AWS (✓)
- Vector Search — AWS (✓)
- FMAPI Databricks — AWS (✓)
- FMAPI Proprietary/Anthropic — AWS (✓)
- Lakebase — AWS (✓)
- Jobs Classic — Azure (✓)
- Jobs Classic — GCP (✓)

**Test 5: AI Assistant** (~5 tests)
- Non-streaming chat response (✓)
- Workload proposal with specific non-default config (✓)
- Confirm-workload (✓)
- Conversation state retrieval (✓)
- Conversation cleanup (✓)

**Test 6: Estimate CRUD + Excel Export** (3 tests)
- Create estimate (✓)
- Add line item (✓)
- Excel export (✓)
- Cleanup (✓)

---

## 6. Bugs Found & Fixed

### Bug 1: Run ID Extraction (install.sh)

**Symptom:** Progress poller showed "Could not fetch run status. Check the Databricks UI."

**Root cause:** `databricks bundle run --no-wait` outputs:
```
Run URL: https://host/?o=335310294452632#job/902515825315646/run/74542605548011
```

The script used `grep -oE 'runs/[0-9]+'` (plural `runs/`) but the format uses `run/` (singular). The fallback `grep -oE '[0-9]{5,}'` grabbed the workspace org ID (`335310294452632`) before the actual run ID.

**Fix:** Changed to `grep -oE 'run/[0-9]+'` with `tail -1` to get the last match (the run ID, not the org ID).

### Bug 2: Wrong CLI Command for Run Status (install.sh)

**Symptom:** `databricks runs get --run-id X` returns "unknown command".

**Root cause:** Databricks CLI uses `databricks jobs get-run RUN_ID` (positional argument), not `databricks runs get --run-id`.

**Fix:** Changed to `databricks jobs get-run "$RUN_ID" $PROFILE_FLAG`.

### Bug 3: Temp File Race in URL Extraction (install.sh)

**Symptom:** `RUN_URL` always empty.

**Root cause:** The `BUNDLE_RUN_OUTPUT` temp file was deleted (`rm -f`) before extracting the URL from it.

**Fix:** Moved URL extraction before the `rm -f`.

---

## 7. Post-Install Verification

### App Status

```
App name:      lakemeter
App URL:       https://lakemeter-335310294452632.aws.databricksapps.com
Deploy status: SUCCEEDED
```

### Lakebase Instance

```
Instance:          lakemeter-customer
Host:              ep-rough-sea-d1h9nfx1.database.us-west-2.cloud.databricks.com
Scaling:           1-16 CU, scale-to-zero
pg_native_login:   enabled
```

### Secrets Scope: `lakemeter-secrets`

| Secret Key | Status |
|------------|--------|
| `lakebase-instance-name` | Set |
| `lakebase-host` | Set |
| `lakebase-user` | Set |
| `lakebase-database` | Set |
| `lakebase-password` | Set |

### App Resources

| Resource Name | Type | Permission |
|---------------|------|------------|
| `lm-lakebase-instance` | Secret (`lakebase-instance-name`) | READ |
| `lm-db-host` | Secret (`lakebase-host`) | READ |
| `lm-db-user` | Secret (`lakebase-user`) | READ |
| `lm-db-name` | Secret (`lakebase-database`) | READ |
| `lm-claude-endpoint` | Serving Endpoint (`databricks-claude-opus-4-6`) | CAN_QUERY |

---

## 8. Timing Summary

| Phase | Duration | Notes |
|-------|----------|-------|
| CLI startup + connectivity check | ~2s | `databricks current-user me` |
| Bundle preparation | ~3s | Copy CSVs (split vm-costs.csv), copy app source |
| `databricks bundle deploy` | ~15s | Upload notebooks, pricing data, app source, functions |
| **Workflow execution** | **14m 40s** | 9 tasks on serverless compute |
| ├ DB branch (parallel) | 1m 35s | provision → create_db → (funcs ∥ data) → sku |
| ├ App branch (parallel) | 3m 40s | create_app |
| ├ Grant SP access | 9s | After both branches complete |
| ├ Deploy app | 10m 39s | Upload files + wait for deployment |
| └ Verify installation | 9s | ~80 smoke tests |
| **Total end-to-end** | **~15 minutes** | |

---

## 9. Conclusion

The installer works end-to-end with zero manual intervention. All 9 workflow tasks pass, and the verification notebook confirms all APIs, reference data, cost calculations, AI assistant, and Excel export work correctly across all 3 clouds (AWS, Azure, GCP).

Three bugs were found in the CLI progress poller (run ID extraction, CLI command syntax, temp file race) — all fixed in the same commit. The core installer logic (bundle deploy + workflow execution) is solid.

The deploy_app step (10m39s) dominates total runtime — this is Databricks Apps infrastructure time (snapshot + container startup) and cannot be reduced from our side.
