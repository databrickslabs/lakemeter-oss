# Bidirectional Alignment: Function ↔ Table

## Part 1: In Function BUT NOT in line_items Table

These parameters exist in `calculate_line_item_costs()` but have NO corresponding column in `line_items`:

| Function Parameter | Type | Default | Why Not in Table? |
|-------------------|------|---------|-------------------|
| `p_region` | VARCHAR | - | ✅ Stored in `estimates` table, not line_items |
| `p_tier` | VARCHAR | - | ✅ Stored in `estimates` table, not line_items |
| `p_dbsql_vm_pricing_tier` | VARCHAR | 'on_demand' | ❌ **MISSING** - should be in table |
| `p_dbsql_vm_payment_option` | VARCHAR | 'NA' | ❌ **MISSING** - should be in table |
| `p_serverless_size` | VARCHAR | NULL | ❌ **COLUMN NAME MISMATCH** - table has `model_serving_gpu_type` |

**Summary:**
- ✅ 2 parameters correctly reference `estimates` table
- ❌ 2 parameters are missing from table (DBSQL VM pricing)
- ❌ 1 parameter has name mismatch (Model Serving)

---

## Part 2: In line_items Table BUT NOT in Function

These columns exist in `line_items` table but have NO corresponding parameter in function:

| Table Column | Type | Default | Why Not in Function? |
|-------------|------|---------|---------------------|
| `line_item_id` | UUID | - | ✅ Primary key, not needed for calculation |
| `estimate_id` | UUID | - | ✅ Foreign key, not needed for calculation |
| `display_order` | INT | - | ✅ UI ordering, not needed for calculation |
| `workload_name` | VARCHAR(255) | - | ✅ Display name, not needed for calculation |
| `model_serving_gpu_type` | VARCHAR(50) | - | ❌ **NAME MISMATCH** - function uses `p_serverless_size` |
| `fmapi_pricing_type` | VARCHAR(50) | - | ❌ **DEPRECATED** - replaced by `fmapi_rate_type` |
| `fmapi_provisioned_units` | INT | 1 | ❌ **DEPRECATED** - not used in new design |
| `lakebase_storage_gb` | INT | - | ⚠️  Not used for pricing calculation |
| `lakebase_backup_retention_days` | INT | 7 | ⚠️  Not used for pricing calculation |
| `workload_config` | JSON | - | ✅ Extensible field, not needed for standard calc |
| `notes` | TEXT | - | ✅ Metadata, not needed for calculation |
| `created_at` | TIMESTAMP | NOW | ✅ Metadata, not needed for calculation |
| `updated_at` | TIMESTAMP | NOW | ✅ Metadata, not needed for calculation |

**Summary:**
- ✅ 7 columns correctly excluded (metadata, IDs, display fields)
- ❌ 1 column has name mismatch (Model Serving)
- ❌ 2 columns are deprecated (FMAPI old design)
- ⚠️  2 columns not used for pricing (Lakebase storage/backup)

---

## Critical Mismatches Summary

### 🔴 CRITICAL: Cannot Map Data

1. **Model Serving Name Mismatch**
   - Table: `model_serving_gpu_type`
   - Function: `p_serverless_size`
   - **Impact:** Cannot pass Model Serving data from table to function
   - **Fix:** Rename table column to `serverless_size`

2. **DBSQL VM Pricing Tier Missing**
   - Table: ❌ NOT PRESENT
   - Function: ✅ `p_dbsql_vm_pricing_tier`
   - **Impact:** Cannot store DBSQL VM pricing tier in line_items
   - **Fix:** Add `dbsql_vm_pricing_tier VARCHAR(20) DEFAULT 'on_demand'`

3. **DBSQL VM Payment Option Missing**
   - Table: ❌ NOT PRESENT
   - Function: ✅ `p_dbsql_vm_payment_option`
   - **Impact:** Cannot store AWS reserved tier options for DBSQL VMs
   - **Fix:** Add `dbsql_vm_payment_option VARCHAR(20) DEFAULT 'NA'`

### 🟡 WARNING: Schema Cleanup Needed

4. **Deprecated FMAPI Columns**
   - `fmapi_pricing_type` - Replaced by `fmapi_rate_type`
   - `fmapi_provisioned_units` - Not used in new design
   - **Impact:** Clutters schema, may confuse developers
   - **Fix:** Drop these columns

5. **Unused Lakebase Columns**
   - `lakebase_storage_gb` - Not used for pricing
   - `lakebase_backup_retention_days` - Not used for pricing
   - **Impact:** Minor clutter
   - **Fix:** Consider dropping or documenting as "for future use"

---

## Recommended SQL to Fix Alignment

```sql
-- 1. Add missing columns
ALTER TABLE lakemeter.line_items 
  ADD COLUMN dbsql_vm_pricing_tier VARCHAR(20) DEFAULT 'on_demand',
  ADD COLUMN dbsql_vm_payment_option VARCHAR(20) DEFAULT 'NA';

-- 2. Fix column name mismatch
ALTER TABLE lakemeter.line_items 
  RENAME COLUMN model_serving_gpu_type TO serverless_size;

-- 3. Remove deprecated columns (OPTIONAL but recommended)
ALTER TABLE lakemeter.line_items
  DROP COLUMN fmapi_pricing_type,
  DROP COLUMN fmapi_provisioned_units;

-- 4. Remove unused columns (OPTIONAL)
ALTER TABLE lakemeter.line_items
  DROP COLUMN lakebase_storage_gb,
  DROP COLUMN lakebase_backup_retention_days;
```

---

## Complete Mapping Table

| line_items Column | Function Parameter | Status |
|------------------|-------------------|--------|
| workload_type | p_workload_type | ✅ Match |
| cloud | p_cloud | ✅ Match |
| - | p_region | ✅ From estimates |
| - | p_tier | ✅ From estimates |
| serverless_enabled | p_serverless_enabled | ✅ Match |
| photon_enabled | p_photon_enabled | ✅ Match |
| dlt_edition | p_dlt_edition | ✅ Match |
| driver_node_type | p_driver_node_type | ✅ Match |
| worker_node_type | p_worker_node_type | ✅ Match |
| num_workers | p_num_workers | ✅ Match |
| driver_pricing_tier | p_driver_pricing_tier | ✅ Match |
| worker_pricing_tier | p_worker_pricing_tier | ✅ Match |
| runs_per_day | p_runs_per_day | ✅ Match |
| avg_runtime_minutes | p_avg_runtime_minutes | ✅ Match |
| days_per_month | p_days_per_month | ✅ Match |
| hours_per_month | p_hours_per_month | ✅ Match |
| serverless_mode | p_serverless_mode | ✅ Match |
| dbsql_warehouse_type | p_dbsql_warehouse_type | ✅ Match |
| dbsql_warehouse_size | p_dbsql_warehouse_size | ✅ Match |
| dbsql_num_clusters | p_dbsql_num_clusters | ✅ Match |
| ❌ NOT IN TABLE | p_dbsql_vm_pricing_tier | ❌ MISSING |
| vector_search_mode | p_vector_search_mode | ✅ Match |
| vector_capacity_millions | p_vector_search_capacity_millions | ✅ Match |
| model_serving_gpu_type | p_serverless_size | ❌ NAME MISMATCH |
| fmapi_model | p_fmapi_model | ✅ Match |
| fmapi_provider | p_fmapi_provider | ✅ Match |
| fmapi_endpoint_type | p_fmapi_endpoint_type | ✅ Match |
| fmapi_context_length | p_fmapi_context_length | ✅ Match |
| fmapi_rate_type | p_fmapi_rate_type | ✅ Match |
| fmapi_quantity | p_fmapi_quantity | ✅ Match |
| lakebase_cu | p_lakebase_cu | ✅ Match |
| lakebase_ha_nodes | p_lakebase_ha_nodes | ✅ Match |
| driver_payment_option | p_driver_payment_option | ✅ Match |
| worker_payment_option | p_worker_payment_option | ✅ Match |
| ❌ NOT IN TABLE | p_dbsql_vm_payment_option | ❌ MISSING |
| fmapi_pricing_type | ❌ NOT IN FUNCTION | ❌ DEPRECATED |
| fmapi_provisioned_units | ❌ NOT IN FUNCTION | ❌ DEPRECATED |
| lakebase_storage_gb | ❌ NOT IN FUNCTION | ⚠️ UNUSED |
| lakebase_backup_retention_days | ❌ NOT IN FUNCTION | ⚠️ UNUSED |

**Total Columns in Table:** 42  
**Total Parameters in Function:** 35  
**Perfect Matches:** 30 ✅  
**Mismatches:** 3 ❌  
**Deprecated:** 2 ❌  
**Unused:** 2 ⚠️  
**Metadata (excluded):** 7 ✅


