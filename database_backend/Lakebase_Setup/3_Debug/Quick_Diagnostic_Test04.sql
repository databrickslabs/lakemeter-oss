-- ============================================================================
-- QUICK DIAGNOSTIC: Why Test_04 ALL_PURPOSE Serverless Shows $0 Costs
-- ============================================================================
-- Run this in Lakebase SQL Editor to quickly identify the issue
-- ============================================================================

-- 1. Check what line items were created
SELECT 
    '1. Line Items Created' as check_name,
    COUNT(*) as count
FROM lakemeter.line_items
WHERE workload_type = 'ALL_PURPOSE' 
  AND serverless_enabled = TRUE;

-- 2. Sample line item with estimate details
SELECT 
    '2. Sample Line Item' as check_name,
    li.cloud,
    e.region,
    e.tier,
    li.driver_node_type,
    li.worker_node_type,
    li.num_workers,
    li.runs_per_day,
    li.avg_runtime_minutes,
    li.days_per_month
FROM lakemeter.line_items li
JOIN lakemeter.estimates e ON li.estimate_id = e.estimate_id
WHERE li.workload_type = 'ALL_PURPOSE' 
  AND li.serverless_enabled = TRUE
LIMIT 1;

-- 3. Check if instance DBU rates exist (CRITICAL!)
SELECT 
    '3. Instance DBU Rates' as check_name,
    r.cloud,
    r.instance_type,
    r.dbu_rate
FROM lakemeter.sync_ref_instance_dbu_rates r
WHERE EXISTS (
    SELECT 1 FROM lakemeter.line_items li
    WHERE li.workload_type = 'ALL_PURPOSE' 
      AND li.serverless_enabled = TRUE
      AND li.cloud = r.cloud
      AND (li.driver_node_type = r.instance_type OR li.worker_node_type = r.instance_type)
)
LIMIT 10;

-- 4. Check if DBU pricing exists (MOST CRITICAL!)
SELECT 
    '4. DBU Pricing Available?' as check_name,
    p.cloud,
    p.region,
    p.tier,
    p.product_type,
    p.price_per_dbu
FROM lakemeter.sync_pricing_dbu_rates p
WHERE p.product_type = 'ALL_PURPOSE_SERVERLESS_COMPUTE'
  AND EXISTS (
      SELECT 1 FROM lakemeter.line_items li
      JOIN lakemeter.estimates e ON li.estimate_id = e.estimate_id
      WHERE li.workload_type = 'ALL_PURPOSE' 
        AND li.serverless_enabled = TRUE
        AND e.cloud = p.cloud
        AND e.region = p.region
        AND e.tier = p.tier
  )
LIMIT 10;

-- 5. Check what's in the view
SELECT 
    '5. View Calculation' as check_name,
    cloud,
    region,
    tier,
    hours_per_month,
    driver_dbu_rate,
    worker_dbu_rate,
    dbu_per_hour,
    price_per_dbu,
    product_type_for_pricing,
    dbu_cost_per_month,
    cost_per_month
FROM lakemeter.v_line_items_with_costs
WHERE workload_type = 'ALL_PURPOSE' 
  AND serverless_enabled = TRUE
LIMIT 5;

-- ============================================================================
-- 6. ROOT CAUSE ANALYSIS - Check for missing pricing data
-- ============================================================================

-- Get all cloud/region/tier combinations from line items
WITH line_item_combos AS (
    SELECT DISTINCT
        e.cloud,
        e.region,
        e.tier
    FROM lakemeter.line_items li
    JOIN lakemeter.estimates e ON li.estimate_id = e.estimate_id
    WHERE li.workload_type = 'ALL_PURPOSE' 
      AND li.serverless_enabled = TRUE
),
-- Check which ones have pricing
pricing_check AS (
    SELECT 
        lic.cloud,
        lic.region,
        lic.tier,
        CASE 
            WHEN p.price_per_dbu IS NOT NULL THEN '✅ HAS PRICING'
            ELSE '❌ MISSING PRICING'
        END as status,
        p.price_per_dbu
    FROM line_item_combos lic
    LEFT JOIN lakemeter.sync_pricing_dbu_rates p
        ON lic.cloud = p.cloud
        AND lic.region = p.region
        AND lic.tier = p.tier
        AND p.product_type = 'ALL_PURPOSE_SERVERLESS_COMPUTE'
)
SELECT 
    '6. Pricing Coverage Analysis' as check_name,
    cloud,
    region,
    tier,
    status,
    COALESCE(price_per_dbu, 0) as price_per_dbu
FROM pricing_check
ORDER BY status DESC, cloud, region, tier;

-- ============================================================================
-- 7. If pricing is missing, what regions ARE available?
-- ============================================================================

SELECT 
    '7. Available Regions for ALL_PURPOSE_SERVERLESS_COMPUTE' as check_name,
    cloud,
    region,
    tier,
    price_per_dbu
FROM lakemeter.sync_pricing_dbu_rates
WHERE product_type = 'ALL_PURPOSE_SERVERLESS_COMPUTE'
  AND cloud IN (
      SELECT DISTINCT e.cloud
      FROM lakemeter.line_items li
      JOIN lakemeter.estimates e ON li.estimate_id = e.estimate_id
      WHERE li.workload_type = 'ALL_PURPOSE' AND li.serverless_enabled = TRUE
  )
ORDER BY cloud, region, tier;

-- ============================================================================
-- EXPECTED RESULTS:
-- ============================================================================
-- If you see "❌ MISSING PRICING" in check #6, that's your problem!
-- The region names in your test don't match the region names in pricing table.
--
-- Common mismatches:
--   Test uses: "us-east-1"  →  Pricing has: "us-east-1" or "USE1" or "US_EAST_1"
--   Test uses: "eastus"     →  Pricing has: "eastus" or "EASTUS" or "East US"
--
-- Solution: Update Test_04 to use the correct region names from check #7.
-- ============================================================================

