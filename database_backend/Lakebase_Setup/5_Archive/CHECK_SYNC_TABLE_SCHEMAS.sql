-- =============================================================================
-- CHECK SYNC TABLE SCHEMAS
-- =============================================================================
-- Run this in Lakebase SQL Editor to see actual column names
-- Use this to write correct queries for frontend validation
-- =============================================================================

-- Check sync_ref_sku_region_map columns
SELECT 
    '📋 sync_ref_sku_region_map columns:' as info;

SELECT 
    column_name,
    data_type,
    character_maximum_length
FROM information_schema.columns
WHERE table_schema = 'lakemeter'
AND table_name = 'sync_ref_sku_region_map'
ORDER BY ordinal_position;

-- Sample data from sync_ref_sku_region_map
SELECT 
    '📊 Sample data (first 10 rows):' as info;

SELECT * FROM lakemeter.sync_ref_sku_region_map LIMIT 10;

-- =============================================================================

-- Check sync_ref_instance_dbu_rates columns
SELECT 
    '📋 sync_ref_instance_dbu_rates columns:' as info;

SELECT 
    column_name,
    data_type,
    character_maximum_length
FROM information_schema.columns
WHERE table_schema = 'lakemeter'
AND table_name = 'sync_ref_instance_dbu_rates'
ORDER BY ordinal_position;

-- Sample data from sync_ref_instance_dbu_rates
SELECT 
    '📊 Sample data (first 10 rows):' as info;

SELECT * FROM lakemeter.sync_ref_instance_dbu_rates LIMIT 10;

-- =============================================================================
-- CORRECTED QUERIES FOR FRONTEND
-- =============================================================================
-- Use the output above to write your frontend queries with correct column names
-- =============================================================================

