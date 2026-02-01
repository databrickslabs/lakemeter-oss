# Lakemeter Lakebase Setup - Execution Guide

## 📋 Overview

This guide explains how to set up the Lakemeter database (Lakebase) using Python notebooks that connect directly to PostgreSQL from Databricks.

## 🎯 What Changed

### Before (SQL Files)
- ❌ Required `psql` command-line tool
- ❌ Copy/paste into Lakebase SQL Editor
- ❌ Manual execution with limited progress tracking
- ❌ Syntax errors with `\echo` commands

### After (Python Notebooks)
- ✅ Run directly from Databricks UI
- ✅ Connect to PostgreSQL using `psycopg2`
- ✅ Real-time progress with ✅/❌ indicators
- ✅ Prerequisite checks before execution
- ✅ Automatic verification after each step
- ✅ Idempotent (safe to re-run)

## 📁 Files Created

| File | Purpose | Execution Time |
|------|---------|----------------|
| `01_Create_Tables.py` | Creates all application tables + constraints + triggers | ~2-3 min |
| `02_Create_Views.py` | Creates cost calculation views | ~30 sec |
| `04_Add_Sync_Constraints.py` | Adds region + instance type validation | ~15 sec |

## 🔄 Execution Order

```
1. 01_Create_Tables.py
   ├─ Creates: users, templates, estimates, line_items
   ├─ Creates: ref_workload_types, ref_cloud_tiers
   ├─ Adds: 32+ constraints (cloud/tier, business logic, enums)
   └─ Creates: Triggers for auto-syncing line_items.cloud

2. Pricing_Sync Notebooks (in Pricing_Sync folder)
   ├─ Creates: sync_ref_sku_region_map
   ├─ Creates: sync_ref_instance_dbu_rates
   ├─ Creates: sync_pricing_dbu_rates
   ├─ Creates: sync_pricing_vm_costs
   └─ Creates: sync_product_* tables

3. 04_Add_Sync_Constraints.py (OPTIONAL - see note below)
   ├─ Adds: Region validation (cloud + region FK)
   └─ Adds: Instance type validation (cloud + instance FK)
   ⚠️  NOTE: May fail if sync_* tables owned by Databricks connector

4. 02_Create_Views.py
   ├─ Creates: v_line_items_with_costs
   └─ Creates: v_estimates_with_totals
```

## 🚀 How to Run

### Step 1: Open Databricks Workspace
1. Go to: https://fe-vm-lakemeter.cloud.databricks.com
2. Navigate to: `/Workspace/Users/steven.tan@databricks.com/lakemeter/Lakebase_Setup/`

### Step 2: Run Notebooks in Order

#### A. 01_Create_Tables.py
```
1. Open the notebook
2. Click "Run All" or run cells sequentially
3. Wait for completion (~2-3 minutes)
4. Verify: Should show ✅ for all tables/constraints
```

Expected output:
```
✅ Connected to Lakebase!
✅ Created users table
✅ Created estimates table
✅ Created line_items table
✅ Created ref_workload_types table (9 workload types)
✅ Created ref_cloud_tiers table (8 cloud/tier combinations)
✅ Added 32+ constraints
✅ Created 2 triggers
🎉 APPLICATION TABLES CREATED SUCCESSFULLY!
```

#### B. Pricing_Sync Notebooks
```
Run all notebooks in the Pricing_Sync folder
(These create the sync_* tables needed for pricing)
```

#### C. 04_Add_Sync_Constraints.py
```
1. Open the notebook
2. Click "Run All"
3. Wait for completion (~15 seconds)
4. Verify: Should show ✅ for 5 constraints
```

Expected output:
```
✅ Added UNIQUE constraint: uq_cloud_region_code
✅ Added FK constraint: fk_estimates_cloud_region
✅ Added UNIQUE constraint: uq_cloud_instance_type
✅ Added FK constraint: fk_line_items_driver_instance
✅ Added FK constraint: fk_line_items_worker_instance
✅ ALL SYNC-DEPENDENT CONSTRAINTS ADDED SUCCESSFULLY!
```

#### D. 02_Create_Views.py
```
1. Open the notebook
2. Click "Run All"
3. Wait for completion (~30 seconds)
4. Verify: Should show ✅ for 2 views
```

Expected output:
```
✅ All prerequisites met!
✅ Created v_line_items_with_costs
✅ Created v_estimates_with_totals
🎉 VIEWS CREATED SUCCESSFULLY!
```

## 🔍 Verification

After running all notebooks, verify the setup:

### Check Tables
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'lakemeter' 
AND table_type = 'BASE TABLE'
ORDER BY table_name;
```

Expected: 12+ tables (users, estimates, line_items, sync_*, etc.)

### Check Views
```sql
SELECT table_name 
FROM information_schema.views 
WHERE table_schema = 'lakemeter'
ORDER BY table_name;
```

Expected: 2 views (v_line_items_with_costs, v_estimates_with_totals)

### Check Constraints
```sql
SELECT contype, COUNT(*) as count
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
JOIN pg_namespace n ON t.relnamespace = n.oid
WHERE n.nspname = 'lakemeter'
GROUP BY contype;
```

Expected:
- Primary Keys: 10+
- Foreign Keys: 15+
- Check Constraints: 20+
- Unique Constraints: 5+

## 🛡️ What Each Constraint Does

### Cloud/Tier Validation
```sql
-- Prevents: ❌ Azure + ENTERPRISE tier
FK: estimates(cloud, tier) → ref_cloud_tiers(cloud, tier)
```

### Region Validation
```sql
-- Prevents: ❌ AWS + eastus (Azure region)
FK: estimates(cloud, region) → sync_ref_sku_region_map(cloud, region_code)
```

### Instance Type Validation
```sql
-- Prevents: ❌ AWS + Standard_D4s_v3 (Azure instance)
FK: line_items(cloud, driver_node_type) → sync_ref_instance_dbu_rates(cloud, instance_type)
FK: line_items(cloud, worker_node_type) → sync_ref_instance_dbu_rates(cloud, instance_type)
```

### Business Logic Constraints
```sql
-- Serverless requires Photon
CHECK: serverless_enabled = FALSE OR photon_enabled = TRUE

-- Autoscale min <= max
CHECK: autoscale_min_workers <= autoscale_max_workers

-- Positive usage values
CHECK: runs_per_day > 0, avg_runtime_minutes > 0

-- Valid ranges
CHECK: num_workers >= 0 AND num_workers <= 1000
CHECK: days_per_month >= 1 AND days_per_month <= 31
```

### Enum Validation
```sql
-- Valid clouds
CHECK: cloud IN ('AWS', 'AZURE', 'GCP')

-- Valid serverless modes
CHECK: serverless_mode IN ('standard', 'performance')

-- Valid DLT editions
CHECK: dlt_edition IN ('CORE', 'PRO', 'ADVANCED')

-- Valid pricing tiers
CHECK: driver_pricing_tier IN ('on_demand', 'reserved_1y', 'reserved_3y')
CHECK: worker_pricing_tier IN ('on_demand', 'spot', 'reserved_1y', 'reserved_3y')
```

## 🐛 Troubleshooting

### Issue: "Connection failed"
**Solution:**
- Check Lakebase is running
- Verify credentials in notebook (lakemeter_sync_role / [STORED_IN_SECRET_SCOPE])
- Check network connectivity

### Issue: "Table already exists"
**Solution:**
- Notebooks are idempotent
- If you need to recreate, drop tables manually first
- Or just re-run (will skip existing objects)

### Issue: "FK constraint violated"
**Solution:**
- Check sync_* tables exist (run Pricing_Sync first)
- Verify data is valid (e.g., AWS + us-east-1, not AWS + eastus)

### Issue: "Prerequisites not met"
**Solution:**
- Read the error message
- Run missing prerequisites first
- Check table existence queries

## 📊 Database Schema Summary

### Application Tables (created by 01_Create_Tables.py)
- `users` - User accounts
- `templates` - Estimate templates
- `estimates` - Customer estimates (main entity)
- `line_items` - Individual workload line items
- `ref_workload_types` - Workload type configuration
- `ref_cloud_tiers` - Valid cloud/tier combinations
- `conversation_messages` - AI chat history
- `decision_records` - Decision tracking
- `sharing` - Estimate sharing

### Sync Tables (created by Pricing_Sync notebooks)
- `sync_ref_sku_region_map` - Valid regions per cloud
- `sync_ref_instance_dbu_rates` - Instance DBU rates
- `sync_pricing_dbu_rates` - DBU pricing by product
- `sync_pricing_vm_costs` - VM costs by instance/region/tier
- `sync_product_dbsql_rates` - DBSQL warehouse pricing
- `sync_product_serverless_rates` - Serverless product pricing
- `sync_product_fmapi_databricks` - Databricks FMAPI rates
- `sync_product_fmapi_proprietary` - Proprietary FMAPI rates

### Views (created by 02_Create_Views.py)
- `v_line_items_with_costs` - Line items with calculated costs
- `v_estimates_with_totals` - Estimates with aggregated totals

---

## ⚠️ Known Issue: Databricks Managed Connector Ownership

### The Problem

If `sync_*` tables are created by **Databricks managed connectors**, they will be owned by a system account like `databricks_writer_XXXXX`.

```sql
-- Example ownership
tablename                    | tableowner
-----------------------------+------------------------
sync_ref_sku_region_map      | databricks_writer_16482
sync_pricing_dbu_rates       | databricks_writer_16482
...
```

**Impact:** You **cannot** add UNIQUE constraints to these tables without superuser privileges.

### Solution Options

#### **Option 1: Skip 04_Add_Sync_Constraints.py (Recommended)**

The constraints added by `04_Add_Sync_Constraints.py` are **nice-to-have, not required**.

**What you lose:**
- ❌ Database-level validation of cloud/region combinations
- ❌ Database-level validation of cloud/instance type combinations

**What still works:**
- ✅ All cost calculations (views work fine)
- ✅ All business logic constraints (in `line_items`)
- ✅ Frontend can query `sync_*` tables for valid options
- ✅ Frontend validates before INSERT (same result)

**Recommendation:** Just skip `04_Add_Sync_Constraints.py` and handle validation in the frontend.

#### **Option 2: Ask Databricks Admin**

If you **really** want database-level validation, ask your Databricks admin to either:

**A. Grant ALTER permission:**
```sql
GRANT ALL ON TABLE lakemeter.sync_ref_sku_region_map TO lakemeter_sync_role;
GRANT ALL ON TABLE lakemeter.sync_ref_instance_dbu_rates TO lakemeter_sync_role;
```

**B. Make you a temporary superuser:**
```sql
ALTER ROLE lakemeter_sync_role WITH SUPERUSER;
-- Run 04_Add_Sync_Constraints.py
ALTER ROLE lakemeter_sync_role WITH NOSUPERUSER;
```

#### **Option 3: Accept Partial Success**

Run `04_Add_Sync_Constraints.py` anyway - it will:
- ✅ Add constraints to application tables (you own these)
- ❌ Skip constraints on `sync_*` tables (owned by connector)
- ✅ Document what failed

### Updated Execution Order

```
1. 01_Create_Tables.py       ✅ Always run
2. Pricing_Sync notebooks     ✅ Always run  
3. 04_Add_Sync_Constraints.py ⚠️  OPTIONAL (skip if connector ownership)
4. 02_Create_Views.py         ✅ Always run
```

---

## 🎉 Success Criteria

After running all notebooks, you should have:

✅ 12+ tables created
✅ 2 views created
✅ 50+ constraints added
✅ 2 triggers created
✅ All verifications passed
✅ No errors in output

## 📝 Notes

- **Idempotent:** All notebooks can be re-run safely
- **Hardcoded credentials:** lakemeter_sync_role / [STORED_IN_SECRET_SCOPE]
- **Connection:** Direct to Lakebase PostgreSQL (instance-364041a4-0aae-44df-bbc6-37ac84169dfe)
- **SSL:** Required (sslmode='require')

## 🔗 Links

- Databricks Workspace: https://fe-vm-lakemeter.cloud.databricks.com
- GitHub Repo: https://github.com/muharandy/promptsizer (branch: database_backend)
- Lakebase Setup Folder: `/Workspace/Users/steven.tan@databricks.com/lakemeter/Lakebase_Setup/`

---

**Created:** 2025-12-13  
**Last Updated:** 2025-12-13  
**Version:** 1.0
