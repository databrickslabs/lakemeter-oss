-- ============================================================================
-- Update pricing_vm_costs View to Handle NULL payment_option + Deduplication
-- ============================================================================
-- This script recreates the pricing_vm_costs view to:
-- 1. Replace NULL payment_option with 'NA'
-- 2. Deduplicate records by keeping the most recent one (based on updated_at)

USE CATALOG lakemeter_catalog;
USE SCHEMA lakemeter;

-- Drop and recreate the view with COALESCE for payment_option and deduplication
CREATE OR REPLACE VIEW pricing_vm_costs AS
WITH ranked_vm_costs AS (
    SELECT 
        cloud,
        region,
        instance_type,
        pricing_tier,
        COALESCE(payment_option, 'NA') as payment_option,  -- Convert NULL to 'NA'
        cost_per_hour,
        currency,
        source,
        fetched_at,
        updated_at,
        ROW_NUMBER() OVER (
            PARTITION BY cloud, region, instance_type, pricing_tier, COALESCE(payment_option, 'NA')
            ORDER BY COALESCE(updated_at, fetched_at) DESC
        ) as rn
    FROM vm_costs
)
SELECT 
    cloud,
    region,
    instance_type,
    pricing_tier,
    payment_option,
    cost_per_hour,
    currency,
    source,
    fetched_at,
    updated_at
FROM ranked_vm_costs
WHERE rn = 1;

-- Verify no duplicates
SELECT 
    cloud,
    region,
    instance_type,
    pricing_tier,
    payment_option,
    COUNT(*) as count
FROM pricing_vm_costs
GROUP BY cloud, region, instance_type, pricing_tier, payment_option
HAVING COUNT(*) > 1;

-- Should return 0 rows if deduplication worked

-- Verify the change - count by cloud and payment_option
SELECT 
    cloud,
    payment_option,
    COUNT(*) as count
FROM pricing_vm_costs
GROUP BY cloud, payment_option
ORDER BY cloud, payment_option;

-- Show sample records
SELECT * FROM pricing_vm_costs
WHERE cloud = 'AWS'
ORDER BY region, instance_type, pricing_tier
LIMIT 20;

