-- ============================================================================
-- Quick Check: What are the exact DLT product_type names in pricing?
-- ============================================================================
-- Run this in Lakebase SQL Editor to find the correct product_type for DLT Serverless
-- ============================================================================

-- 1. Check ALL product types that contain 'DLT' or 'DELTA'
SELECT DISTINCT
    cloud,
    product_type,
    COUNT(*) OVER (PARTITION BY cloud, product_type) as region_tier_combinations,
    MIN(price_per_dbu) OVER (PARTITION BY cloud, product_type) as min_price,
    MAX(price_per_dbu) OVER (PARTITION BY cloud, product_type) as max_price
FROM lakemeter_pricing.lakemeter.sync_pricing_dbu_rates
WHERE product_type LIKE '%DLT%' OR product_type LIKE '%DELTA%'
ORDER BY cloud, product_type;

-- 2. Sample data for DLT-related product types (AWS)
SELECT 
    cloud,
    region,
    tier,
    product_type,
    price_per_dbu
FROM lakemeter_pricing.lakemeter.sync_pricing_dbu_rates
WHERE cloud = 'AWS'
  AND (product_type LIKE '%DLT%' OR product_type LIKE '%DELTA%')
ORDER BY product_type, tier, region
LIMIT 20;

-- 3. Check what we're currently looking for in the view
-- The view logic uses: 'JOBS_SERVERLESS_COMPUTE'
-- Let's see if that exists:
SELECT 
    cloud,
    COUNT(DISTINCT region) as num_regions,
    COUNT(DISTINCT tier) as num_tiers,
    MIN(price_per_dbu) as min_price,
    MAX(price_per_dbu) as max_price
FROM lakemeter_pricing.lakemeter.sync_pricing_dbu_rates
WHERE product_type = 'JOBS_SERVERLESS_COMPUTE'
GROUP BY cloud;

-- If above returns 0 rows, try these variations:
SELECT DISTINCT product_type
FROM lakemeter_pricing.lakemeter.sync_pricing_dbu_rates
WHERE product_type IN (
    'JOBS_SERVERLESS_COMPUTE',
    'DLT_SERVERLESS_COMPUTE',
    'DLT_ADVANCED_SERVERLESS_COMPUTE',
    'DLT_PRO_SERVERLESS_COMPUTE',
    'DLT_CORE_SERVERLESS_COMPUTE'
);

-- ============================================================================
-- EXPECTED RESULTS:
-- ============================================================================
-- You should see the actual product_type name used in the pricing table.
-- This is what needs to be used in 02_Create_Views.py
--
-- Common possibilities:
--   - JOBS_SERVERLESS_COMPUTE (current assumption)
--   - DLT_SERVERLESS_COMPUTE
--   - DLT_ADVANCED_SERVERLESS_COMPUTE
--   - DLT_PRO_SERVERLESS_COMPUTE
--   - DLT_CORE_SERVERLESS_COMPUTE
-- ============================================================================

