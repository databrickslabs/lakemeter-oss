# Comparison: line_items Table vs calculate_line_item_costs() Function

## Line Items Table Columns (cost calculation relevant)

From `01_Create_Tables.py`:

1. `workload_type` VARCHAR(50) NOT NULL
2. `cloud` VARCHAR(20) - Auto-synced from estimates
3. `serverless_enabled` BOOLEAN DEFAULT false
4. `serverless_mode` VARCHAR(20)
5. `photon_enabled` BOOLEAN DEFAULT false
6. `driver_node_type` VARCHAR(100)
7. `worker_node_type` VARCHAR(100)
8. `num_workers` INT
9. `dlt_edition` VARCHAR(20)
10. `dbsql_warehouse_type` VARCHAR(20)
11. `dbsql_warehouse_size` VARCHAR(20)
12. `dbsql_num_clusters` INT DEFAULT 1
13. `vector_search_mode` VARCHAR(50)
14. `vector_capacity_millions` DECIMAL(10,2)
15. `model_serving_gpu_type` VARCHAR(50) ⚠️
16. `fmapi_provider` VARCHAR(50)
17. `fmapi_model` VARCHAR(100)
18. `fmapi_endpoint_type` VARCHAR(20)
19. `fmapi_context_length` VARCHAR(20)
20. `fmapi_pricing_type` VARCHAR(50) ⚠️ (NOT USED)
21. `fmapi_rate_type` VARCHAR(20)
22. `fmapi_quantity` BIGINT
23. `fmapi_provisioned_units` INT DEFAULT 1 ⚠️ (NOT USED)
24. `lakebase_cu` INT
25. `lakebase_storage_gb` INT ⚠️ (NOT USED)
26. `lakebase_ha_nodes` INT DEFAULT 1
27. `lakebase_backup_retention_days` INT DEFAULT 7 ⚠️ (NOT USED)
28. `runs_per_day` INT
29. `avg_runtime_minutes` INT
30. `days_per_month` INT DEFAULT 30
31. `hours_per_month` DECIMAL(10,2)
32. `driver_pricing_tier` VARCHAR(20)
33. `worker_pricing_tier` VARCHAR(20)
34. `driver_payment_option` VARCHAR(20) DEFAULT 'NA'
35. `worker_payment_option` VARCHAR(20) DEFAULT 'NA'

**MISSING IN TABLE:**
- `dbsql_vm_pricing_tier` ❌
- `dbsql_vm_payment_option` ❌

## Function Parameters

From `09_Main_Orchestrator.py`:

1. `p_workload_type` VARCHAR
2. `p_cloud` VARCHAR
3. `p_region` VARCHAR (from estimate, not stored in line_items)
4. `p_tier` VARCHAR (from estimate, not stored in line_items)
5. `p_serverless_enabled` BOOLEAN DEFAULT FALSE
6. `p_photon_enabled` BOOLEAN DEFAULT FALSE
7. `p_dlt_edition` VARCHAR DEFAULT NULL
8. `p_driver_node_type` VARCHAR DEFAULT NULL
9. `p_worker_node_type` VARCHAR DEFAULT NULL
10. `p_num_workers` INT DEFAULT 0
11. `p_driver_pricing_tier` VARCHAR DEFAULT 'on_demand'
12. `p_worker_pricing_tier` VARCHAR DEFAULT 'on_demand'
13. `p_runs_per_day` INT DEFAULT 0
14. `p_avg_runtime_minutes` INT DEFAULT 0
15. `p_days_per_month` INT DEFAULT 30
16. `p_hours_per_month` INT DEFAULT NULL
17. `p_serverless_mode` VARCHAR DEFAULT 'standard'
18. `p_dbsql_warehouse_type` VARCHAR DEFAULT NULL
19. `p_dbsql_warehouse_size` VARCHAR DEFAULT NULL
20. `p_dbsql_num_clusters` INT DEFAULT 1
21. `p_dbsql_vm_pricing_tier` VARCHAR DEFAULT 'on_demand' ⚠️
22. `p_vector_search_mode` VARCHAR DEFAULT NULL
23. `p_vector_search_capacity_millions` DECIMAL DEFAULT 0
24. `p_serverless_size` VARCHAR DEFAULT NULL ⚠️
25. `p_fmapi_model` VARCHAR DEFAULT NULL
26. `p_fmapi_provider` VARCHAR DEFAULT NULL
27. `p_fmapi_endpoint_type` VARCHAR DEFAULT 'global'
28. `p_fmapi_context_length` VARCHAR DEFAULT 'all'
29. `p_fmapi_rate_type` VARCHAR DEFAULT 'input_token'
30. `p_fmapi_quantity` BIGINT DEFAULT 0
31. `p_lakebase_cu` INT DEFAULT 0
32. `p_lakebase_ha_nodes` INT DEFAULT 1
33. `p_driver_payment_option` VARCHAR DEFAULT 'NA'
34. `p_worker_payment_option` VARCHAR DEFAULT 'NA'
35. `p_dbsql_vm_payment_option` VARCHAR DEFAULT 'NA' ⚠️

**NOT IN FUNCTION:**
- `fmapi_pricing_type` (deprecated in new design)
- `fmapi_provisioned_units` (deprecated in new design)
- `lakebase_storage_gb` (not used for pricing)
- `lakebase_backup_retention_days` (not used for pricing)

## ❌ MISMATCHES FOUND

### 1. Model Serving Column Name Mismatch
- **Table:** `model_serving_gpu_type` VARCHAR(50)
- **Function:** `p_serverless_size` VARCHAR
- **Impact:** Cannot map Model Serving line items to function
- **Fix:** Rename table column OR function parameter

### 2. DBSQL VM Pricing Tier Missing from Table
- **Table:** ❌ NOT PRESENT
- **Function:** `p_dbsql_vm_pricing_tier` VARCHAR DEFAULT 'on_demand'
- **Impact:** Cannot store DBSQL VM pricing tier in line_items
- **Fix:** Add `dbsql_vm_pricing_tier` column to table

### 3. DBSQL VM Payment Option Missing from Table
- **Table:** ❌ NOT PRESENT
- **Function:** `p_dbsql_vm_payment_option` VARCHAR DEFAULT 'NA'
- **Impact:** Cannot store DBSQL VM payment option (AWS reserved tiers)
- **Fix:** Add `dbsql_vm_payment_option` column to table

### 4. Unused Columns in Table
- `fmapi_pricing_type` - Replaced by `fmapi_rate_type` in new design
- `fmapi_provisioned_units` - Not used in new design
- `lakebase_storage_gb` - Not used for pricing calculation
- `lakebase_backup_retention_days` - Not used for pricing calculation
- **Fix:** Consider removing to simplify schema

## ✅ RECOMMENDED FIXES

### Option 1: Update Table to Match Function (Recommended)

```sql
ALTER TABLE lakemeter.line_items 
  ADD COLUMN dbsql_vm_pricing_tier VARCHAR(20) DEFAULT 'on_demand',
  ADD COLUMN dbsql_vm_payment_option VARCHAR(20) DEFAULT 'NA',
  RENAME COLUMN model_serving_gpu_type TO serverless_size;

-- Optionally remove deprecated columns
ALTER TABLE lakemeter.line_items
  DROP COLUMN fmapi_pricing_type,
  DROP COLUMN fmapi_provisioned_units,
  DROP COLUMN lakebase_storage_gb,
  DROP COLUMN lakebase_backup_retention_days;
```

### Option 2: Update Function to Match Table

```sql
-- Change p_serverless_size to p_model_serving_gpu_type
-- Remove p_dbsql_vm_pricing_tier (default to 'on_demand')
-- Remove p_dbsql_vm_payment_option (default to 'NA')
```

## 🎯 CONCLUSION

**Status:** ❌ **NOT ALIGNED**

**Critical Issues:**
1. Model Serving column name mismatch prevents mapping
2. Missing DBSQL VM pricing columns prevents full feature support
3. Deprecated FMAPI columns clutter the schema

**Recommendation:** Update table to match function (Option 1)


