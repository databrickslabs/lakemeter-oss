-- =============================================================================
-- TRANSFER OWNERSHIP TO lakemeter_sync_role
-- =============================================================================
-- Run this with an ADMIN user (not lakemeter_sync_role)
-- This transfers ownership of all objects to lakemeter_sync_role
-- =============================================================================

-- First, check who currently owns the objects
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables
WHERE schemaname = 'lakemeter'
ORDER BY tablename;

-- Views
SELECT 
    schemaname,
    viewname,
    viewowner
FROM pg_views
WHERE schemaname = 'lakemeter'
ORDER BY viewname;

-- =============================================================================
-- TRANSFER OWNERSHIP
-- =============================================================================

-- Transfer views first (they depend on tables)
ALTER VIEW IF EXISTS lakemeter.v_estimates_with_totals OWNER TO lakemeter_sync_role;
ALTER VIEW IF EXISTS lakemeter.v_line_items_with_costs OWNER TO lakemeter_sync_role;

-- Transfer tables
ALTER TABLE IF EXISTS lakemeter.users OWNER TO lakemeter_sync_role;
ALTER TABLE IF EXISTS lakemeter.templates OWNER TO lakemeter_sync_role;
ALTER TABLE IF EXISTS lakemeter.estimates OWNER TO lakemeter_sync_role;
ALTER TABLE IF EXISTS lakemeter.line_items OWNER TO lakemeter_sync_role;
ALTER TABLE IF EXISTS lakemeter.ref_workload_types OWNER TO lakemeter_sync_role;
ALTER TABLE IF EXISTS lakemeter.ref_cloud_tiers OWNER TO lakemeter_sync_role;
ALTER TABLE IF EXISTS lakemeter.conversation_messages OWNER TO lakemeter_sync_role;
ALTER TABLE IF EXISTS lakemeter.decision_records OWNER TO lakemeter_sync_role;
ALTER TABLE IF EXISTS lakemeter.sharing OWNER TO lakemeter_sync_role;

-- Transfer all sync_* tables (from Pricing_Sync)
ALTER TABLE IF EXISTS lakemeter.sync_ref_sku_region_map OWNER TO lakemeter_sync_role;
ALTER TABLE IF EXISTS lakemeter.sync_ref_instance_dbu_rates OWNER TO lakemeter_sync_role;
ALTER TABLE IF EXISTS lakemeter.sync_ref_dbu_multipliers OWNER TO lakemeter_sync_role;
ALTER TABLE IF EXISTS lakemeter.sync_pricing_dbu_rates OWNER TO lakemeter_sync_role;
ALTER TABLE IF EXISTS lakemeter.sync_pricing_vm_costs OWNER TO lakemeter_sync_role;
ALTER TABLE IF EXISTS lakemeter.sync_product_dbsql_rates OWNER TO lakemeter_sync_role;
ALTER TABLE IF EXISTS lakemeter.sync_product_serverless_rates OWNER TO lakemeter_sync_role;
ALTER TABLE IF EXISTS lakemeter.sync_product_fmapi_databricks OWNER TO lakemeter_sync_role;
ALTER TABLE IF EXISTS lakemeter.sync_product_fmapi_proprietary OWNER TO lakemeter_sync_role;

-- Transfer Salesforce sync tables
ALTER TABLE IF EXISTS lakemeter.dim_salesforce_account OWNER TO lakemeter_sync_role;
ALTER TABLE IF EXISTS lakemeter.fct_salesforce_use_case OWNER TO lakemeter_sync_role;
ALTER TABLE IF EXISTS lakemeter.hourly_opportunity OWNER TO lakemeter_sync_role;

-- Transfer schema ownership (optional, but recommended)
-- ALTER SCHEMA lakemeter OWNER TO lakemeter_sync_role;

-- =============================================================================
-- VERIFY OWNERSHIP
-- =============================================================================
SELECT 
    'Table' as object_type,
    tablename as object_name,
    tableowner as owner,
    CASE WHEN tableowner = 'lakemeter_sync_role' THEN '✅' ELSE '❌' END as status
FROM pg_tables
WHERE schemaname = 'lakemeter'
UNION ALL
SELECT 
    'View' as object_type,
    viewname as object_name,
    viewowner as owner,
    CASE WHEN viewowner = 'lakemeter_sync_role' THEN '✅' ELSE '❌' END as status
FROM pg_views
WHERE schemaname = 'lakemeter'
ORDER BY object_type, object_name;

-- =============================================================================
-- EXPECTED OUTPUT: All objects should show ✅ (owned by lakemeter_sync_role)
-- =============================================================================

