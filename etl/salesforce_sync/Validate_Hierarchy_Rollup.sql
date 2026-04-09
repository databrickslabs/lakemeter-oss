-- ============================================================================
-- HIERARCHY ROLLUP VALIDATION
-- Purpose: Ensure each level can properly roll up to parent levels
-- Excludes: Test/generic accounts (0018Y00002scnyoQAA - Generic Business Subscription)
-- ============================================================================

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Hierarchy Rollup Validation
-- MAGIC
-- MAGIC Check if aggregation at each level produces consistent results
-- MAGIC
-- MAGIC **Excluded Accounts:**
-- MAGIC - `0018Y00002scnyoQAA` (Generic Business Subscription)

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### Test 1: Level 4 → Level 3 Rollup (Most Granular to Workspace)

-- COMMAND ----------

-- Count at Level 4 (most granular - current MV structure)
WITH level_4 AS (
  SELECT 
    sfdc_account_id,
    product_account_id,
    cloud,
    sfdc_workspace_object_id,
    sfdc_workspace_name,
    sku,
    usage_unit,
    COUNT(*) as row_count,
    SUM(usage_dollars) as total_dollars
  FROM main.fin_live_gold.paid_usage_metering
  WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
    AND date < CURRENT_DATE()
    AND sfdc_account_id != '0018Y00002scnyoQAA'  -- Exclude Generic Business Subscription
  GROUP BY 
    sfdc_account_id,
    product_account_id,
    cloud,
    sfdc_workspace_object_id,
    sfdc_workspace_name,
    sku,
    usage_unit
),
-- Roll up to Level 3 (workspace level)
level_3_from_4 AS (
  SELECT 
    sfdc_account_id,
    product_account_id,
    cloud,
    sfdc_workspace_object_id,
    sfdc_workspace_name,
    COUNT(*) as num_skus,
    SUM(total_dollars) as total_dollars
  FROM level_4
  GROUP BY 
    sfdc_account_id,
    product_account_id,
    cloud,
    sfdc_workspace_object_id,
    sfdc_workspace_name
),
-- Count at Level 3 directly (without tier/region/product_type yet)
level_3_direct AS (
  SELECT 
    sfdc_account_id,
    product_account_id,
    cloud,
    sfdc_workspace_object_id,
    sfdc_workspace_name,
    SUM(usage_dollars) as total_dollars
  FROM main.fin_live_gold.paid_usage_metering
  WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
    AND date < CURRENT_DATE()
    AND sfdc_account_id != '0018Y00002scnyoQAA'  -- Exclude Generic Business Subscription
  GROUP BY 
    sfdc_account_id,
    product_account_id,
    cloud,
    sfdc_workspace_object_id,
    sfdc_workspace_name
)
SELECT 
  'Level 4 to Level 3 Rollup Check' as test_name,
  (SELECT COUNT(*) FROM level_3_from_4) as rolled_up_count,
  (SELECT COUNT(*) FROM level_3_direct) as direct_count,
  (SELECT SUM(total_dollars) FROM level_3_from_4) as rolled_up_dollars,
  (SELECT SUM(total_dollars) FROM level_3_direct) as direct_dollars,
  CASE 
    WHEN (SELECT COUNT(*) FROM level_3_from_4) = (SELECT COUNT(*) FROM level_3_direct)
     AND ABS((SELECT SUM(total_dollars) FROM level_3_from_4) - (SELECT SUM(total_dollars) FROM level_3_direct)) < 0.01
    THEN '✅ Rollup Valid'
    ELSE '❌ Rollup MISMATCH'
  END as validation_status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### Test 2: Level 3 → Level 2 Rollup (Workspace to Product Account + Cloud)

-- COMMAND ----------

WITH level_3 AS (
  SELECT 
    sfdc_account_id,
    product_account_id,
    cloud,
    sfdc_workspace_object_id,
    SUM(usage_dollars) as total_dollars
  FROM main.fin_live_gold.paid_usage_metering
  WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
    AND date < CURRENT_DATE()
    AND sfdc_account_id != '0018Y00002scnyoQAA'  -- Exclude Generic Business Subscription
  GROUP BY 
    sfdc_account_id,
    product_account_id,
    cloud,
    sfdc_workspace_object_id
),
level_2_from_3 AS (
  SELECT 
    sfdc_account_id,
    product_account_id,
    cloud,
    COUNT(*) as num_workspaces,
    SUM(total_dollars) as total_dollars
  FROM level_3
  GROUP BY 
    sfdc_account_id,
    product_account_id,
    cloud
),
level_2_direct AS (
  SELECT 
    sfdc_account_id,
    product_account_id,
    cloud,
    SUM(usage_dollars) as total_dollars
  FROM main.fin_live_gold.paid_usage_metering
  WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
    AND date < CURRENT_DATE()
    AND sfdc_account_id != '0018Y00002scnyoQAA'  -- Exclude Generic Business Subscription
  GROUP BY 
    sfdc_account_id,
    product_account_id,
    cloud
)
SELECT 
  'Level 3 to Level 2 Rollup Check' as test_name,
  (SELECT COUNT(*) FROM level_2_from_3) as rolled_up_count,
  (SELECT COUNT(*) FROM level_2_direct) as direct_count,
  (SELECT SUM(total_dollars) FROM level_2_from_3) as rolled_up_dollars,
  (SELECT SUM(total_dollars) FROM level_2_direct) as direct_dollars,
  CASE 
    WHEN (SELECT COUNT(*) FROM level_2_from_3) = (SELECT COUNT(*) FROM level_2_direct)
     AND ABS((SELECT SUM(total_dollars) FROM level_2_from_3) - (SELECT SUM(total_dollars) FROM level_2_direct)) < 0.01
    THEN '✅ Rollup Valid'
    ELSE '❌ Rollup MISMATCH'
  END as validation_status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### Test 3: Level 2 → Level 1 Rollup (Product Account to Salesforce Account)

-- COMMAND ----------

WITH level_2 AS (
  SELECT 
    sfdc_account_id,
    product_account_id,
    cloud,
    SUM(usage_dollars) as total_dollars
  FROM main.fin_live_gold.paid_usage_metering
  WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
    AND date < CURRENT_DATE()
    AND sfdc_account_id != '0018Y00002scnyoQAA'  -- Exclude Generic Business Subscription
  GROUP BY 
    sfdc_account_id,
    product_account_id,
    cloud
),
level_1_from_2 AS (
  SELECT 
    sfdc_account_id,
    COUNT(*) as num_product_account_cloud_combos,
    SUM(total_dollars) as total_dollars
  FROM level_2
  GROUP BY sfdc_account_id
),
level_1_direct AS (
  SELECT 
    sfdc_account_id,
    SUM(usage_dollars) as total_dollars
  FROM main.fin_live_gold.paid_usage_metering
  WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
    AND date < CURRENT_DATE()
    AND sfdc_account_id != '0018Y00002scnyoQAA'  -- Exclude Generic Business Subscription
  GROUP BY sfdc_account_id
)
SELECT 
  'Level 2 to Level 1 Rollup Check' as test_name,
  (SELECT COUNT(*) FROM level_1_from_2) as rolled_up_count,
  (SELECT COUNT(*) FROM level_1_direct) as direct_count,
  (SELECT SUM(total_dollars) FROM level_1_from_2) as rolled_up_dollars,
  (SELECT SUM(total_dollars) FROM level_1_direct) as direct_dollars,
  CASE 
    WHEN (SELECT COUNT(*) FROM level_1_from_2) = (SELECT COUNT(*) FROM level_1_direct)
     AND ABS((SELECT SUM(total_dollars) FROM level_1_from_2) - (SELECT SUM(total_dollars) FROM level_1_direct)) < 0.01
    THEN '✅ Rollup Valid'
    ELSE '❌ Rollup MISMATCH'
  END as validation_status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### Test 4: Check for NULL product_account_id Impact

-- COMMAND ----------

-- How do NULLs affect the hierarchy?
SELECT 
  CASE 
    WHEN product_account_id IS NULL THEN 'NULL product_account_id'
    ELSE 'Valid product_account_id'
  END as product_account_status,
  COUNT(*) as row_count,
  COUNT(DISTINCT sfdc_account_id) as unique_accounts,
  COUNT(DISTINCT sfdc_workspace_object_id) as unique_workspaces,
  SUM(usage_dollars) as total_dollars,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as pct_of_total
FROM main.fin_live_gold.paid_usage_metering
WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
  AND date < CURRENT_DATE()
  AND sfdc_account_id != '0018Y00002scnyoQAA'  -- Exclude Generic Business Subscription
GROUP BY CASE WHEN product_account_id IS NULL THEN 'NULL product_account_id' ELSE 'Valid product_account_id' END;

-- COMMAND ----------

-- Sample accounts with NULL product_account_id
SELECT 
  sfdc_account_id,
  sfdc_account_name,
  COUNT(*) as rows_with_null_product_account,
  COUNT(DISTINCT sfdc_workspace_object_id) as num_workspaces,
  SUM(usage_dollars) as total_dollars
FROM main.fin_live_gold.paid_usage_metering
WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
  AND date < CURRENT_DATE()
  AND product_account_id IS NULL
  AND sfdc_account_id != '0018Y00002scnyoQAA'  -- Exclude Generic Business Subscription
GROUP BY sfdc_account_id, sfdc_account_name
ORDER BY total_dollars DESC
LIMIT 20;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### Investigation: Product Types with NULL product_account_id

-- COMMAND ----------

-- Which product types have NULL product_account_id?
SELECT 
  product_type,
  COUNT(*) as row_count,
  COUNT(DISTINCT sfdc_account_id) as unique_accounts,
  COUNT(DISTINCT sfdc_workspace_object_id) as unique_workspaces,
  SUM(usage_dollars) as total_dollars,
  ROUND(100.0 * SUM(usage_dollars) / SUM(SUM(usage_dollars)) OVER(), 2) as pct_of_null_dollars
FROM main.fin_live_gold.paid_usage_metering
WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
  AND date < CURRENT_DATE()
  AND product_account_id IS NULL
  AND sfdc_account_id != '0018Y00002scnyoQAA'  -- Exclude Generic Business Subscription
GROUP BY product_type
ORDER BY total_dollars DESC;

-- COMMAND ----------

-- SKU breakdown for NULL product_account_id records
SELECT 
  product_type,
  sku,
  COUNT(*) as row_count,
  COUNT(DISTINCT sfdc_account_id) as unique_accounts,
  SUM(usage_dollars) as total_dollars
FROM main.fin_live_gold.paid_usage_metering
WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
  AND date < CURRENT_DATE()
  AND product_account_id IS NULL
  AND sfdc_account_id != '0018Y00002scnyoQAA'  -- Exclude Generic Business Subscription
GROUP BY product_type, sku
ORDER BY total_dollars DESC
LIMIT 30;

-- COMMAND ----------

-- Are these product types ALWAYS NULL, or only sometimes?
WITH product_type_null_stats AS (
  SELECT 
    product_type,
    COUNT(*) as total_rows,
    SUM(CASE WHEN product_account_id IS NULL THEN 1 ELSE 0 END) as null_rows,
    SUM(CASE WHEN product_account_id IS NOT NULL THEN 1 ELSE 0 END) as non_null_rows,
    SUM(usage_dollars) as total_dollars,
    SUM(CASE WHEN product_account_id IS NULL THEN usage_dollars ELSE 0 END) as null_dollars,
    SUM(CASE WHEN product_account_id IS NOT NULL THEN usage_dollars ELSE 0 END) as non_null_dollars
  FROM main.fin_live_gold.paid_usage_metering
  WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
    AND date < CURRENT_DATE()
    AND sfdc_account_id != '0018Y00002scnyoQAA'  -- Exclude Generic Business Subscription
  GROUP BY product_type
)
SELECT 
  product_type,
  total_rows,
  null_rows,
  non_null_rows,
  ROUND(100.0 * null_rows / total_rows, 2) as pct_null_rows,
  total_dollars,
  null_dollars,
  non_null_dollars,
  ROUND(100.0 * null_dollars / total_dollars, 2) as pct_null_dollars,
  CASE 
    WHEN null_rows = total_rows THEN '🔴 ALWAYS NULL'
    WHEN null_rows = 0 THEN '✅ NEVER NULL'
    ELSE '🟡 SOMETIMES NULL'
  END as null_pattern
FROM product_type_null_stats
WHERE null_rows > 0  -- Only show product types with at least some NULLs
ORDER BY null_dollars DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### Test 5: Check Workspace ID Uniqueness Across Product Accounts

-- COMMAND ----------

-- Are workspace IDs unique within a salesforce account, or can same workspace appear under multiple product_accounts?
WITH workspace_product_mapping AS (
  SELECT 
    sfdc_account_id,
    sfdc_workspace_object_id,
    sfdc_workspace_name,
    COUNT(DISTINCT product_account_id) as num_product_accounts,
    STRING_AGG(DISTINCT product_account_id, ', ') as product_account_list
  FROM main.fin_live_gold.paid_usage_metering
  WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
    AND date < CURRENT_DATE()
    AND product_account_id IS NOT NULL
    AND sfdc_account_id != '0018Y00002scnyoQAA'  -- Exclude Generic Business Subscription
  GROUP BY 
    sfdc_account_id,
    sfdc_workspace_object_id,
    sfdc_workspace_name
)
SELECT 
  CASE 
    WHEN num_product_accounts = 1 THEN '1 product_account'
    WHEN num_product_accounts = 2 THEN '2 product_accounts'
    WHEN num_product_accounts >= 3 THEN '3+ product_accounts'
  END as workspace_mapping,
  COUNT(*) as num_workspaces,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as pct_of_workspaces
FROM workspace_product_mapping
GROUP BY 
  CASE 
    WHEN num_product_accounts = 1 THEN '1 product_account'
    WHEN num_product_accounts = 2 THEN '2 product_accounts'
    WHEN num_product_accounts >= 3 THEN '3+ product_accounts'
  END
ORDER BY workspace_mapping;

-- COMMAND ----------

-- Show examples of workspaces appearing under multiple product_accounts
SELECT *
FROM (
  SELECT 
    sfdc_account_id,
    sfdc_workspace_object_id,
    sfdc_workspace_name,
    COUNT(DISTINCT product_account_id) as num_product_accounts,
    STRING_AGG(DISTINCT product_account_id, ', ') as product_account_list,
    SUM(usage_dollars) as total_dollars
  FROM main.fin_live_gold.paid_usage_metering
  WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
    AND date < CURRENT_DATE()
    AND product_account_id IS NOT NULL
    AND sfdc_account_id != '0018Y00002scnyoQAA'  -- Exclude Generic Business Subscription
  GROUP BY 
    sfdc_account_id,
    sfdc_workspace_object_id,
    sfdc_workspace_name
)
WHERE num_product_accounts > 1
ORDER BY num_product_accounts DESC, total_dollars DESC
LIMIT 20;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Summary
-- MAGIC
-- MAGIC Based on rollup validation results:
-- MAGIC 1. ✅ or ❌ Level 4 → Level 3 rollup
-- MAGIC 2. ✅ or ❌ Level 3 → Level 2 rollup  
-- MAGIC 3. ✅ or ❌ Level 2 → Level 1 rollup
-- MAGIC 4. Impact of NULL product_account_id on hierarchy
-- MAGIC 5. Whether workspaces can belong to multiple product_accounts
