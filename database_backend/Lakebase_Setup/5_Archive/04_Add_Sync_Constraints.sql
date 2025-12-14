-- =============================================================================
-- ADD SYNC-DEPENDENT VALIDATION CONSTRAINTS
-- =============================================================================
-- FILE: 04_Add_Sync_Constraints.sql
-- PURPOSE: Adds validation constraints that depend on sync_* tables
-- 
-- PREREQUISITE: sync_* tables must exist (created by Pricing_Sync notebooks)
-- 
-- RUN THIS AFTER:
--   1. 01_Create_Tables.sql (creates application tables with triggers)
--   2. Pricing_Sync notebooks (creates all sync_* tables)
--   3. BEFORE 02_Create_Views.sql (views reference these tables)
--
-- WHAT THIS DOES:
--   1. Region Validation: Prevents invalid cloud/region combinations
--      Example: ❌ AWS + eastus (Azure region)
--   
--   2. Instance Type Validation: Prevents using AWS instances on Azure, etc.
--      Example: ❌ Azure estimate with i3.xlarge (AWS instance)
-- 
-- NOTE: These constraints are also available (commented out) in 01_Create_Tables.sql
--       This is a convenience script to run them all at once.
-- =============================================================================

\echo ''
\echo '╔════════════════════════════════════════════════════════════════╗'
\echo '║          ADDING SYNC-DEPENDENT VALIDATION CONSTRAINTS         ║'
\echo '╚════════════════════════════════════════════════════════════════╝'
\echo ''

-- =============================================================================
-- SECTION 1: REGION VALIDATION
-- =============================================================================
\echo '1️⃣  REGION VALIDATION'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

-- Step 1.1: Add UNIQUE constraint on sync_ref_sku_region_map
\echo '   Adding UNIQUE constraint: sync_ref_sku_region_map(cloud, region_code)...'

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'uq_cloud_region_code'
    ) THEN
        ALTER TABLE lakemeter.sync_ref_sku_region_map 
        ADD CONSTRAINT uq_cloud_region_code 
        UNIQUE (cloud, region_code);
        
        RAISE NOTICE '   ✅ Added UNIQUE constraint: uq_cloud_region_code';
    ELSE
        RAISE NOTICE '   ⚠️  UNIQUE constraint already exists: uq_cloud_region_code';
    END IF;
END $$;

\echo ''

-- Step 1.2: Add FK constraint from estimates to sync_ref_sku_region_map
\echo '   Adding FK constraint: estimates(cloud, region) → sync_ref_sku_region_map...'

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'fk_estimates_cloud_region'
    ) THEN
        ALTER TABLE lakemeter.estimates 
        ADD CONSTRAINT fk_estimates_cloud_region 
        FOREIGN KEY (cloud, region) 
        REFERENCES lakemeter.sync_ref_sku_region_map(cloud, region_code);
        
        RAISE NOTICE '   ✅ Added FK constraint: fk_estimates_cloud_region';
    ELSE
        RAISE NOTICE '   ⚠️  FK constraint already exists: fk_estimates_cloud_region';
    END IF;
END $$;

\echo ''
\echo '   ✅ Region validation active!'
\echo '   → Prevents: AWS + eastus, AZURE + us-east-1, GCP + westeurope'
\echo ''

-- =============================================================================
-- SECTION 2: INSTANCE TYPE VALIDATION
-- =============================================================================
\echo '2️⃣  INSTANCE TYPE VALIDATION'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

-- Step 2.1: Add UNIQUE constraint on sync_ref_instance_dbu_rates
\echo '   Adding UNIQUE constraint: sync_ref_instance_dbu_rates(cloud, instance_type)...'

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'uq_cloud_instance_type'
    ) THEN
        ALTER TABLE lakemeter.sync_ref_instance_dbu_rates 
        ADD CONSTRAINT uq_cloud_instance_type 
        UNIQUE (cloud, instance_type);
        
        RAISE NOTICE '   ✅ Added UNIQUE constraint: uq_cloud_instance_type';
    ELSE
        RAISE NOTICE '   ⚠️  UNIQUE constraint already exists: uq_cloud_instance_type';
    END IF;
END $$;

\echo ''

-- Step 2.2: Add FK constraint for driver_node_type
\echo '   Adding FK constraint: line_items(cloud, driver_node_type) → sync_ref_instance_dbu_rates...'

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'fk_line_items_driver_instance'
    ) THEN
        -- Only add FK for non-NULL driver_node_type (some workloads don't use VMs)
        ALTER TABLE lakemeter.line_items 
        ADD CONSTRAINT fk_line_items_driver_instance 
        FOREIGN KEY (cloud, driver_node_type) 
        REFERENCES lakemeter.sync_ref_instance_dbu_rates(cloud, instance_type)
        DEFERRABLE INITIALLY DEFERRED;  -- Allow NULL values
        
        RAISE NOTICE '   ✅ Added FK constraint: fk_line_items_driver_instance';
    ELSE
        RAISE NOTICE '   ⚠️  FK constraint already exists: fk_line_items_driver_instance';
    END IF;
END $$;

\echo ''

-- Step 2.3: Add FK constraint for worker_node_type
\echo '   Adding FK constraint: line_items(cloud, worker_node_type) → sync_ref_instance_dbu_rates...'

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'fk_line_items_worker_instance'
    ) THEN
        -- Only add FK for non-NULL worker_node_type (some workloads don't use VMs)
        ALTER TABLE lakemeter.line_items 
        ADD CONSTRAINT fk_line_items_worker_instance 
        FOREIGN KEY (cloud, worker_node_type) 
        REFERENCES lakemeter.sync_ref_instance_dbu_rates(cloud, instance_type)
        DEFERRABLE INITIALLY DEFERRED;  -- Allow NULL values
        
        RAISE NOTICE '   ✅ Added FK constraint: fk_line_items_worker_instance';
    ELSE
        RAISE NOTICE '   ⚠️  FK constraint already exists: fk_line_items_worker_instance';
    END IF;
END $$;

\echo ''
\echo '   ✅ Instance type validation active!'
\echo '   → Prevents: AWS using Azure instances, Azure using GCP instances, etc.'
\echo ''

-- =============================================================================
-- VERIFICATION
-- =============================================================================
\echo '📊 VERIFICATION: Checking all constraints...'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

SELECT 
    CASE 
        WHEN contype = 'f' THEN '🔗 FK'
        WHEN contype = 'u' THEN '🔑 UNIQUE'
        ELSE '  ' || contype
    END as type,
    conname as constraint_name,
    '✅ EXISTS' as status
FROM pg_constraint
WHERE conname IN (
    'uq_cloud_region_code',
    'fk_estimates_cloud_region',
    'uq_cloud_instance_type',
    'fk_line_items_driver_instance',
    'fk_line_items_worker_instance'
)
ORDER BY 
    CASE conname
        WHEN 'uq_cloud_region_code' THEN 1
        WHEN 'fk_estimates_cloud_region' THEN 2
        WHEN 'uq_cloud_instance_type' THEN 3
        WHEN 'fk_line_items_driver_instance' THEN 4
        WHEN 'fk_line_items_worker_instance' THEN 5
    END;

\echo ''
\echo '╔════════════════════════════════════════════════════════════════╗'
\echo '║                   ✅ ALL CONSTRAINTS ADDED                    ║'
\echo '╚════════════════════════════════════════════════════════════════╝'
\echo ''

-- =============================================================================
-- EXAMPLE VALIDATION TESTS (Optional - uncomment to test)
-- =============================================================================

\echo '🧪 TEST EXAMPLES (these will show validation in action):'
\echo ''
\echo '   Valid operations:'
\echo '   ✅ INSERT INTO estimates (cloud=''AWS'', region=''us-east-1'', tier=''STANDARD'', ...)'
\echo '   ✅ INSERT INTO line_items (estimate_id=..., driver_node_type=''i3.xlarge'', ...)'
\echo '      → SUCCESS (i3.xlarge exists for AWS)'
\echo ''
\echo '   Invalid operations that will be BLOCKED:'
\echo '   ❌ INSERT INTO estimates (cloud=''AWS'', region=''eastus'', ...)'
\echo '      → ERROR: FK constraint fk_estimates_cloud_region violated'
\echo '      → Reason: eastus is an Azure region, not valid for AWS'
\echo ''
\echo '   ❌ INSERT INTO line_items (cloud=''AWS'', driver_node_type=''Standard_D4s_v3'', ...)'
\echo '      → ERROR: FK constraint fk_line_items_driver_instance violated'
\echo '      → Reason: Standard_D4s_v3 is an Azure instance, not valid for AWS'
\echo ''

-- Uncomment to run actual tests:
/*
-- Test 1: ❌ Invalid region (should fail)
INSERT INTO lakemeter.estimates (estimate_id, cloud, region, tier, owner_user_id, status, estimate_name)
VALUES (
    gen_random_uuid(), 
    'AWS', 
    'eastus',  -- Azure region
    'STANDARD',
    (SELECT user_id FROM lakemeter.users LIMIT 1),
    'draft',
    'TEST - Invalid Region'
);
-- Expected: ERROR: FK constraint "fk_estimates_cloud_region" violated

-- Test 2: ✅ Valid region (should succeed)
INSERT INTO lakemeter.estimates (estimate_id, cloud, region, tier, owner_user_id, status, estimate_name)
VALUES (
    gen_random_uuid(), 
    'AWS', 
    'us-east-1',  -- Valid AWS region
    'STANDARD',
    (SELECT user_id FROM lakemeter.users LIMIT 1),
    'draft',
    'TEST - Valid Region'
);
-- Expected: SUCCESS

-- Clean up test data:
DELETE FROM lakemeter.estimates WHERE estimate_name LIKE 'TEST -%';
*/

-- =============================================================================
-- SCRIPT COMPLETE
-- =============================================================================
\echo '✅ Script complete! All sync-dependent constraints are now active.'
\echo ''
\echo '📋 NEXT STEPS:'
\echo '   1. Run 02_Create_Views.sql to create cost calculation views'
\echo '   2. Test your application with these validations active'
\echo '   3. Frontend should query sync_ref_sku_region_map for valid regions'
\echo '   4. Frontend should query sync_ref_instance_dbu_rates for valid instances'
\echo ''

