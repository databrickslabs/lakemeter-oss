-- ============================================================================
-- QUICK FIX: Update ALL_PURPOSE product_type without dropping tables
-- ============================================================================
-- This fixes the $0 cost issue in Test_04_ALL_PURPOSE_Serverless
-- by updating the ref_workload_types table
-- ============================================================================

-- Check current value
SELECT 
    'BEFORE UPDATE' as status,
    workload_type,
    sku_product_type_serverless
FROM lakemeter.ref_workload_types
WHERE workload_type = 'ALL_PURPOSE';

-- Update to correct product_type
UPDATE lakemeter.ref_workload_types
SET sku_product_type_serverless = 'ALL_PURPOSE_SERVERLESS_COMPUTE'
WHERE workload_type = 'ALL_PURPOSE'
  AND sku_product_type_serverless = 'INTERACTIVE_SERVERLESS_COMPUTE';

-- Verify update
SELECT 
    'AFTER UPDATE' as status,
    workload_type,
    sku_product_type_serverless
FROM lakemeter.ref_workload_types
WHERE workload_type = 'ALL_PURPOSE';

-- ============================================================================
-- NEXT STEP: Run 02_Create_Views.py to recreate views with correct logic
-- ============================================================================
-- The views also need to be updated to use the correct product_type
-- Run 02_Create_Views.py notebook to apply the fix
-- ============================================================================

