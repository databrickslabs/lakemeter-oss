-- ============================================================================
-- BASELINE CONSUMPTION HIERARCHY ANALYSIS
-- Purpose: Understand cardinality and relationships before restructuring MV
-- ============================================================================

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 1. Check sfdc_account_id vs sfdc_account_name (1:1?)

-- COMMAND ----------

-- Check if sfdc_account_id and sfdc_account_name are 1:1
SELECT 
  COUNT(DISTINCT sfdc_account_id) as unique_account_ids,
  COUNT(DISTINCT sfdc_account_name) as unique_account_names,
  COUNT(DISTINCT CONCAT(sfdc_account_id, '|', sfdc_account_name)) as unique_combinations,
  CASE 
    WHEN COUNT(DISTINCT sfdc_account_id) = COUNT(DISTINCT CONCAT(sfdc_account_id, '|', sfdc_account_name))
    THEN '✅ 1:1 Relationship'
    ELSE '❌ NOT 1:1 - Need to investigate'
  END as relationship_status
FROM main.fin_live_gold.paid_usage_metering
WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
  AND date < CURRENT_DATE();

-- COMMAND ----------

-- If NOT 1:1, show duplicates
SELECT 
  sfdc_account_id,
  COUNT(DISTINCT sfdc_account_name) as name_count,
  STRING_AGG(DISTINCT sfdc_account_name, ' | ') as all_names
FROM main.fin_live_gold.paid_usage_metering
WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
  AND date < CURRENT_DATE()
GROUP BY sfdc_account_id
HAVING COUNT(DISTINCT sfdc_account_name) > 1
ORDER BY name_count DESC
LIMIT 20;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 2. Check product_account_id availability and cardinality

-- COMMAND ----------

-- Check if product_account_id exists and has data
SELECT 
  COUNT(*) as total_rows,
  COUNT(DISTINCT product_account_id) as unique_product_accounts,
  COUNT(CASE WHEN product_account_id IS NULL THEN 1 END) as null_count,
  COUNT(CASE WHEN product_account_id IS NOT NULL THEN 1 END) as non_null_count,
  ROUND(100.0 * COUNT(CASE WHEN product_account_id IS NOT NULL THEN 1 END) / COUNT(*), 2) as pct_populated
FROM main.fin_live_gold.paid_usage_metering
WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
  AND date < CURRENT_DATE();

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 3. Hierarchy Level Analysis

-- COMMAND ----------

-- Level 1: sfdc_account_id only (top level)
SELECT 
  'Level 1: Account Only' as hierarchy_level,
  COUNT(DISTINCT sfdc_account_id) as row_count,
  'Highest level aggregation' as description
FROM main.fin_live_gold.paid_usage_metering
WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
  AND date < CURRENT_DATE()

UNION ALL

-- Level 2: sfdc_account_id + product_account_id + cloud
SELECT 
  'Level 2: Account + Product + Cloud' as hierarchy_level,
  COUNT(DISTINCT CONCAT(
    COALESCE(sfdc_account_id, 'NULL'), '|',
    COALESCE(product_account_id, 'NULL'), '|',
    COALESCE(cloud, 'NULL')
  )) as row_count,
  'Account broken down by E2 account and cloud' as description
FROM main.fin_live_gold.paid_usage_metering
WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
  AND date < CURRENT_DATE()

UNION ALL

-- Level 3: Level 2 + workspace + tier + region
SELECT 
  'Level 3: + Workspace + Tier + Region' as hierarchy_level,
  COUNT(DISTINCT CONCAT(
    COALESCE(sfdc_account_id, 'NULL'), '|',
    COALESCE(product_account_id, 'NULL'), '|',
    COALESCE(cloud, 'NULL'), '|',
    COALESCE(sfdc_workspace_object_id, 'NULL'), '|',
    COALESCE(sfdc_workspace_name, 'NULL')
  )) as row_count,
  'Workspace level aggregation' as description
FROM main.fin_live_gold.paid_usage_metering p
WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
  AND date < CURRENT_DATE()

UNION ALL

-- Level 4: Current (most granular) - add product_type + shield_sku + usage_unit
SELECT 
  'Level 4: Current (Most Granular)' as hierarchy_level,
  COUNT(DISTINCT CONCAT(
    COALESCE(sfdc_account_id, 'NULL'), '|',
    COALESCE(product_account_id, 'NULL'), '|',
    COALESCE(cloud, 'NULL'), '|',
    COALESCE(sfdc_workspace_object_id, 'NULL'), '|',
    COALESCE(sku, 'NULL'), '|',
    COALESCE(usage_unit, 'NULL')
  )) as row_count,
  'SKU-level detail (current MV granularity after sku_parser)' as description
FROM main.fin_live_gold.paid_usage_metering p
WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
  AND date < CURRENT_DATE()

ORDER BY hierarchy_level;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 4. Sample Data at Each Level

-- COMMAND ----------

-- Level 1 Sample: Top 5 accounts by usage
SELECT 
  sfdc_account_id,
  sfdc_account_name,
  COUNT(DISTINCT product_account_id) as num_product_accounts,
  COUNT(DISTINCT sfdc_workspace_object_id) as num_workspaces,
  COUNT(DISTINCT cloud) as num_clouds,
  SUM(usage_dollars) as total_dollars_3m
FROM main.fin_live_gold.paid_usage_metering
WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
  AND date < CURRENT_DATE()
GROUP BY sfdc_account_id, sfdc_account_name
ORDER BY total_dollars_3m DESC
LIMIT 5;

-- COMMAND ----------

-- Level 2 Sample: For one large account, show product_account_id breakdown
WITH top_account AS (
  SELECT sfdc_account_id
  FROM main.fin_live_gold.paid_usage_metering
  WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
    AND date < CURRENT_DATE()
  GROUP BY sfdc_account_id
  ORDER BY SUM(usage_dollars) DESC
  LIMIT 1
)
SELECT 
  p.sfdc_account_id,
  p.sfdc_account_name,
  p.product_account_id,
  p.cloud,
  COUNT(DISTINCT p.sfdc_workspace_object_id) as num_workspaces,
  SUM(p.usage_dollars) as total_dollars_3m
FROM main.fin_live_gold.paid_usage_metering p
INNER JOIN top_account t ON p.sfdc_account_id = t.sfdc_account_id
WHERE p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
  AND p.date < CURRENT_DATE()
GROUP BY 
  p.sfdc_account_id,
  p.sfdc_account_name,
  p.product_account_id,
  p.cloud
ORDER BY total_dollars_3m DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 5. Check Tier and Region Availability in Source

-- COMMAND ----------

-- Check if tier exists in source table or only in sku_parser_lookup
SELECT 
  'Source Table Fields' as check_type,
  COUNT(DISTINCT sku) as unique_skus,
  COUNT(DISTINCT cloud) as unique_clouds,
  COUNT(*) as total_rows
FROM main.fin_live_gold.paid_usage_metering
WHERE date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
  AND date < CURRENT_DATE();

-- COMMAND ----------

-- Show sample SKUs and how they map to tier/product_type
SELECT 
  p.sku,
  p.cloud,
  s.tier,
  s.product_type,
  s.region,
  COUNT(*) as occurrence_count,
  SUM(p.usage_dollars) as total_dollars
FROM main.fin_live_gold.paid_usage_metering p
LEFT JOIN users.steven_tan.sku_parser_lookup s
  ON p.sku = s.sku_name AND p.cloud = s.cloud
WHERE p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
  AND p.date < CURRENT_DATE()
GROUP BY p.sku, p.cloud, s.tier, s.product_type, s.region
ORDER BY total_dollars DESC
LIMIT 20;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Summary & Next Steps
-- MAGIC
-- MAGIC Based on the results above:
-- MAGIC 1. Confirm if sfdc_account_id:sfdc_account_name is 1:1
-- MAGIC 2. Check product_account_id population rate
-- MAGIC 3. Understand cardinality at each hierarchy level
-- MAGIC 4. Decide on final MV structure with multiple aggregation levels
