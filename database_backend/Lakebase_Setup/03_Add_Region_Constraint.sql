-- =============================================================================
-- ADD REGION VALIDATION CONSTRAINT
-- =============================================================================
-- FILE: 03_Add_Region_Constraint.sql
-- PURPOSE: Adds cloud/region validation constraint
-- 
-- PREREQUISITE: sync_ref_sku_region_map must exist (created by pricing sync)
-- 
-- RUN THIS AFTER:
--   1. 01_Create_Tables.sql (creates application tables)
--   2. Pricing_Sync notebooks (creates sync_ref_sku_region_map)
--   3. 02_Create_Views.sql (creates cost calculation views)
--
-- WHAT THIS DOES:
--   - Adds UNIQUE constraint on sync_ref_sku_region_map(cloud, region_code)
--   - Adds FK constraint from estimates(cloud, region) to sync_ref_sku_region_map
--   - Prevents invalid cloud/region combinations (e.g., AWS + eastus)
-- =============================================================================

-- =============================================================================
-- STEP 1: Add UNIQUE constraint on sync_ref_sku_region_map
-- =============================================================================
-- This allows us to create a foreign key reference to (cloud, region_code)

DO $$ 
BEGIN
    -- Check if constraint already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'uq_cloud_region_code'
    ) THEN
        ALTER TABLE lakemeter.sync_ref_sku_region_map 
        ADD CONSTRAINT uq_cloud_region_code 
        UNIQUE (cloud, region_code);
        
        RAISE NOTICE '✅ Added UNIQUE constraint: uq_cloud_region_code';
    ELSE
        RAISE NOTICE '⚠️  UNIQUE constraint uq_cloud_region_code already exists, skipping';
    END IF;
END $$;

-- =============================================================================
-- STEP 2: Add FK constraint from estimates to sync_ref_sku_region_map
-- =============================================================================
-- This validates that estimates.region is a valid region for estimates.cloud

DO $$ 
BEGIN
    -- Check if constraint already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'fk_estimates_cloud_region'
    ) THEN
        ALTER TABLE lakemeter.estimates 
        ADD CONSTRAINT fk_estimates_cloud_region 
        FOREIGN KEY (cloud, region) 
        REFERENCES lakemeter.sync_ref_sku_region_map(cloud, region_code);
        
        RAISE NOTICE '✅ Added FK constraint: fk_estimates_cloud_region';
    ELSE
        RAISE NOTICE '⚠️  FK constraint fk_estimates_cloud_region already exists, skipping';
    END IF;
END $$;

-- =============================================================================
-- VERIFICATION
-- =============================================================================
-- Check that constraints were added successfully

SELECT 
    'uq_cloud_region_code' as constraint_name,
    CASE WHEN COUNT(*) > 0 THEN '✅ EXISTS' ELSE '❌ MISSING' END as status
FROM pg_constraint 
WHERE conname = 'uq_cloud_region_code'
UNION ALL
SELECT 
    'fk_estimates_cloud_region' as constraint_name,
    CASE WHEN COUNT(*) > 0 THEN '✅ EXISTS' ELSE '❌ MISSING' END as status
FROM pg_constraint 
WHERE conname = 'fk_estimates_cloud_region';

-- =============================================================================
-- TEST QUERIES (Optional - validate data)
-- =============================================================================

-- Show all valid cloud/region combinations
SELECT 
    cloud, 
    region_code, 
    sku_region,
    COUNT(*) OVER (PARTITION BY cloud) as regions_per_cloud
FROM lakemeter.sync_ref_sku_region_map
ORDER BY cloud, region_code;

-- Example: Test invalid combinations (should fail after constraint is added)
-- Uncomment to test:

-- ❌ This should FAIL (AWS + Azure region):
-- INSERT INTO lakemeter.estimates (estimate_id, cloud, region, tier, owner_user_id, status)
-- VALUES (gen_random_uuid(), 'AWS', 'eastus', 'STANDARD', (SELECT user_id FROM lakemeter.users LIMIT 1), 'draft');
-- Expected error: violates foreign key constraint "fk_estimates_cloud_region"

-- ✅ This should SUCCEED (AWS + valid AWS region):
-- INSERT INTO lakemeter.estimates (estimate_id, cloud, region, tier, owner_user_id, status)
-- VALUES (gen_random_uuid(), 'AWS', 'us-east-1', 'STANDARD', (SELECT user_id FROM lakemeter.users LIMIT 1), 'draft');

-- =============================================================================
-- SCRIPT COMPLETE
-- =============================================================================
-- Region validation is now active!
-- 
-- Frontend Integration:
--   GET /api/v1/regions?cloud=AWS
--   → Query: SELECT region_code, sku_region FROM sync_ref_sku_region_map WHERE cloud = 'AWS'
--   → Returns only valid regions for selected cloud
-- =============================================================================

