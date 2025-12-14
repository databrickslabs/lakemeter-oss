-- =============================================================================
-- FIX: Transfer Ownership of sync_* Tables to lakemeter_sync_role
-- =============================================================================
-- Run this in Lakebase SQL Editor BEFORE running 04_Add_Sync_Constraints.py
-- This transfers ownership of pricing sync tables created by Pricing_Sync notebooks
-- =============================================================================

-- Step 1: Check current ownership
SELECT 
    '🔍 Current ownership of sync_* tables:' as info;

SELECT 
    tablename,
    tableowner,
    CASE 
        WHEN tableowner = current_user THEN '✅ YOU OWN THIS'
        WHEN tableowner = 'lakemeter_sync_role' THEN '✅ Already correct!'
        ELSE '❌ OWNED BY: ' || tableowner || ' (needs transfer)'
    END as status
FROM pg_tables
WHERE schemaname = 'lakemeter'
AND tablename LIKE 'sync_%'
ORDER BY tablename;

-- =============================================================================
-- Step 2: Transfer ownership to lakemeter_sync_role
-- =============================================================================
-- Run these if you see "❌ OWNED BY" above

-- Region mapping table
ALTER TABLE lakemeter.sync_ref_sku_region_map OWNER TO lakemeter_sync_role;

-- Instance DBU rates table
ALTER TABLE lakemeter.sync_ref_instance_dbu_rates OWNER TO lakemeter_sync_role;

-- DBU multipliers table
ALTER TABLE lakemeter.sync_ref_dbu_multipliers OWNER TO lakemeter_sync_role;

-- Pricing tables
ALTER TABLE lakemeter.sync_pricing_dbu_rates OWNER TO lakemeter_sync_role;
ALTER TABLE lakemeter.sync_pricing_vm_costs OWNER TO lakemeter_sync_role;

-- Product pricing tables
ALTER TABLE lakemeter.sync_product_dbsql_rates OWNER TO lakemeter_sync_role;
ALTER TABLE lakemeter.sync_product_serverless_rates OWNER TO lakemeter_sync_role;
ALTER TABLE lakemeter.sync_product_fmapi_databricks OWNER TO lakemeter_sync_role;
ALTER TABLE lakemeter.sync_product_fmapi_proprietary OWNER TO lakemeter_sync_role;

-- =============================================================================
-- Step 3: Verify ownership transfer
-- =============================================================================
SELECT 
    '✅ Verification: All sync_* tables' as info;

SELECT 
    tablename,
    tableowner,
    CASE 
        WHEN tableowner = 'lakemeter_sync_role' THEN '✅'
        ELSE '❌ Still wrong!'
    END as status
FROM pg_tables
WHERE schemaname = 'lakemeter'
AND tablename LIKE 'sync_%'
ORDER BY tablename;

-- Expected: All rows show ✅

-- =============================================================================
-- Step 4: Go back to Databricks and re-run 04_Add_Sync_Constraints.py
-- =============================================================================

-- =============================================================================
-- IF TRANSFER FAILS:
-- =============================================================================
-- Error: "must be able to SET ROLE lakemeter_sync_role"
-- 
-- This means you don't have permission to transfer to lakemeter_sync_role.
-- 
-- OPTIONS:
--   1. Log in as a superuser and run the ALTER TABLE commands
--   2. Log in as the current owner and run the ALTER TABLE commands
--   3. Ask Databricks admin to grant you permissions
--
-- To check who has superuser:
-- SELECT rolname FROM pg_roles WHERE rolsuper = true;
-- =============================================================================

