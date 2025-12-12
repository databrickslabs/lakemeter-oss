-- =============================================================================
-- DEBUG: VM Pricing Lookup Issues
-- =============================================================================
-- This query helps diagnose why Azure/GCP VM costs are returning 0
-- Run this in Lakebase to check what data exists
-- =============================================================================

-- 1. Check what clouds have VM pricing data
SELECT 
    cloud,
    COUNT(*) as row_count,
    COUNT(DISTINCT region) as region_count,
    COUNT(DISTINCT instance_type) as instance_type_count
FROM lakemeter.sync_pricing_vm_costs
GROUP BY cloud
ORDER BY cloud;

-- 2. Check Azure regions available
SELECT DISTINCT region 
FROM lakemeter.sync_pricing_vm_costs 
WHERE cloud = 'AZURE'
ORDER BY region;

-- 3. Check GCP regions available
SELECT DISTINCT region 
FROM lakemeter.sync_pricing_vm_costs 
WHERE cloud = 'GCP'
ORDER BY region;

-- 4. Check Azure instance types for eastus
SELECT DISTINCT instance_type, pricing_tier, cost_per_hour
FROM lakemeter.sync_pricing_vm_costs 
WHERE cloud = 'AZURE' 
  AND region = 'eastus'
ORDER BY instance_type, pricing_tier
LIMIT 20;

-- 5. Check GCP instance types for us-central1
SELECT DISTINCT instance_type, pricing_tier, cost_per_hour
FROM lakemeter.sync_pricing_vm_costs 
WHERE cloud = 'GCP' 
  AND region = 'us-central1'
ORDER BY instance_type, pricing_tier
LIMIT 20;

-- 6. Try case-insensitive match for Azure
SELECT cloud, region, instance_type, pricing_tier, cost_per_hour
FROM lakemeter.sync_pricing_vm_costs 
WHERE UPPER(cloud) = 'AZURE'
  AND LOWER(instance_type) LIKE '%d8s%'
LIMIT 10;

-- 7. Try case-insensitive match for GCP
SELECT cloud, region, instance_type, pricing_tier, cost_per_hour
FROM lakemeter.sync_pricing_vm_costs 
WHERE UPPER(cloud) = 'GCP'
  AND LOWER(instance_type) LIKE '%n1%'
LIMIT 10;

