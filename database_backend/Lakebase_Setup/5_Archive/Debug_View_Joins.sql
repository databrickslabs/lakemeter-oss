-- ============================================================================
-- DEBUG: What is the view actually trying to look up for Azure/GCP?
-- ============================================================================
-- This checks what instance types are in line_items vs what exists in pricing
-- ============================================================================

-- 1. Show what's actually in the line_items for Azure/GCP
SELECT 
    line_item_id,
    workload_name,
    e.cloud,
    e.region,
    c.driver_node_type,
    c.worker_node_type,
    c.photon_enabled,
    c.serverless_enabled
FROM lakemeter.line_items c
JOIN lakemeter.estimates e ON e.estimate_id = c.estimate_id
WHERE e.cloud IN ('AZURE', 'GCP')
ORDER BY line_item_id;

-- ============================================================================

-- 2. For each Azure/GCP line item, check if driver instance type exists
SELECT 
    c.line_item_id,
    c.workload_name,
    e.cloud,
    c.driver_node_type,
    CASE 
        WHEN d.dbu_rate IS NOT NULL THEN '✅ FOUND: ' || d.dbu_rate::TEXT
        ELSE '❌ NOT FOUND'
    END as driver_lookup_result
FROM lakemeter.line_items c
JOIN lakemeter.estimates e ON e.estimate_id = c.estimate_id
LEFT JOIN lakemeter.sync_ref_instance_dbu_rates d 
    ON d.cloud = e.cloud 
    AND d.instance_type = c.driver_node_type
WHERE e.cloud IN ('AZURE', 'GCP')
ORDER BY c.line_item_id;

-- ============================================================================

-- 3. For each Azure/GCP line item, check if worker instance type exists
SELECT 
    c.line_item_id,
    c.workload_name,
    e.cloud,
    c.worker_node_type,
    CASE 
        WHEN w.dbu_rate IS NOT NULL THEN '✅ FOUND: ' || w.dbu_rate::TEXT
        ELSE '❌ NOT FOUND'
    END as worker_lookup_result
FROM lakemeter.line_items c
JOIN lakemeter.estimates e ON e.estimate_id = c.estimate_id
LEFT JOIN lakemeter.sync_ref_instance_dbu_rates w 
    ON w.cloud = e.cloud 
    AND w.instance_type = c.worker_node_type
WHERE e.cloud IN ('AZURE', 'GCP')
ORDER BY c.line_item_id;

-- ============================================================================

-- 4. For each Azure/GCP line item, check multiplier lookup
SELECT 
    c.line_item_id,
    c.workload_name,
    e.cloud,
    c.workload_type,
    c.photon_enabled,
    c.serverless_enabled,
    CASE WHEN c.photon_enabled THEN 'photon' ELSE 'standard' END as feature_lookup,
    'JOBS_COMPUTE' as sku_type_lookup,  -- Assuming JOBS workload
    CASE 
        WHEN m.multiplier IS NOT NULL THEN '✅ FOUND: ' || m.multiplier::TEXT
        ELSE '❌ NOT FOUND'
    END as multiplier_lookup_result
FROM lakemeter.line_items c
JOIN lakemeter.estimates e ON e.estimate_id = c.estimate_id
LEFT JOIN lakemeter.sync_ref_dbu_multipliers m 
    ON c.serverless_enabled = FALSE
    AND m.cloud = e.cloud
    AND m.feature = CASE WHEN c.photon_enabled THEN 'photon' ELSE 'standard' END
    AND m.sku_type = 'JOBS_COMPUTE'
WHERE e.cloud IN ('AZURE', 'GCP')
ORDER BY c.line_item_id;

-- ============================================================================

-- 5. Show what instance types are available for Azure in pricing tables
SELECT 
    'AZURE' as cloud,
    instance_type,
    dbu_rate
FROM lakemeter.sync_ref_instance_dbu_rates
WHERE cloud = 'AZURE'
ORDER BY instance_type
LIMIT 20;

-- ============================================================================

-- 6. Show what instance types are available for GCP in pricing tables
SELECT 
    'GCP' as cloud,
    instance_type,
    dbu_rate
FROM lakemeter.sync_ref_instance_dbu_rates
WHERE cloud = 'GCP'
ORDER BY instance_type
LIMIT 20;

-- ============================================================================

-- 7. Check if view was actually updated - look at the view definition
SELECT 
    definition
FROM pg_views
WHERE schemaname = 'lakemeter' 
  AND viewname = 'v_line_items_with_costs';

-- Search for 'AND m.cloud = h.cloud' in the definition
-- If this doesn't appear, the view wasn't updated!

-- ============================================================================

