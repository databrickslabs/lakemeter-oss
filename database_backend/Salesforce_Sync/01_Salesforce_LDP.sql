-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Salesforce Sync - Lakeflow Declarative Pipeline
-- MAGIC 
-- MAGIC **Workspace:** `adb-2548836972759138.18.azuredatabricks.net` (Logfood)
-- MAGIC 
-- MAGIC **Pipeline Location:** `/Workspace/Users/steven.tan@databricks.com/lakemeter/Salesforce_Sync`
-- MAGIC 
-- MAGIC This DLT pipeline creates materialized views for Salesforce tables with the same transformations:
-- MAGIC - `dim_salesforce_account` - Deduplicated by account name, keeping latest ds
-- MAGIC - `fct_salesforce_use_case` - Distinct use cases
-- MAGIC - `hourly_opportunity` - Distinct opportunities

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 1. Salesforce Accounts (Deduplicated, with Use Cases)

-- COMMAND ----------

CREATE OR REFRESH MATERIALIZED VIEW mv_dim_salesforce_account
COMMENT "Salesforce accounts - deduplicated by account name, keeping latest ds, only accounts with use cases"
AS
WITH accounts_with_use_cases AS (
  SELECT DISTINCT
    a.salesforce_account_id,
    a.salesforce_account_name,
    a.ds
  FROM main.metric_store.dim_salesforce_account a
  INNER JOIN main.metric_store.fct_salesforce_use_case__core uc
    ON a.salesforce_account_id = uc.salesforce_account_id
),
ranked_accounts AS (
  SELECT 
    salesforce_account_id,
    salesforce_account_name,
    ROW_NUMBER() OVER (
      PARTITION BY salesforce_account_name 
      ORDER BY ds DESC
    ) AS rn
  FROM accounts_with_use_cases
)
SELECT 
  salesforce_account_id,
  salesforce_account_name
FROM ranked_accounts
WHERE rn = 1;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 2. Salesforce Use Cases (Distinct)

-- COMMAND ----------

CREATE OR REFRESH MATERIALIZED VIEW mv_fct_salesforce_use_case
COMMENT "Salesforce use cases - distinct records"
AS
SELECT DISTINCT
  customer_id,
  salesforce_use_case_id,
  dim_canonical_customer_name,
  dim_salesforce_use_case_id,
  salesforce_use_case_name
FROM main.metric_store.fct_salesforce_use_case__core;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 3. Hourly Opportunities (Distinct)

-- COMMAND ----------

CREATE OR REFRESH MATERIALIZED VIEW mv_hourly_opportunity
COMMENT "Hourly opportunities - distinct records"
AS
SELECT DISTINCT
  id,
  name,
  accountid
FROM main.sfdc_bronze.hourly_opportunity;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 4. Baseline Consumption (All Hierarchy Levels + All Time Periods)
-- MAGIC 
-- MAGIC **Strategy:** ONE materialized view with ALL hierarchy levels:
-- MAGIC - Level 1: Salesforce Account (most aggregated)
-- MAGIC - Level 2: Product Account + Cloud
-- MAGIC - Level 3: Workspace
-- MAGIC - Level 4: SKU Detail (most granular)
-- MAGIC 
-- MAGIC **Each level includes:**
-- MAGIC - `hierarchy_level` (1-4): Numeric level identifier
-- MAGIC - `hierarchy_level_name`: Human-readable level name
-- MAGIC - `dimension_keys`: Comma-separated list of dimension columns included at this level
-- MAGIC - Time period summaries: 3m, 30d, 90d, 1m (24 columns)
-- MAGIC - Monthly breakdown: 12 months pivoted (72 columns)
-- MAGIC - Total: 99 metadata columns + 96 measure columns
-- MAGIC 
-- MAGIC **Hierarchy Levels:**
-- MAGIC 
-- MAGIC | Level | Name | dimension_keys | Dimensions NULL/Aggregated |
-- MAGIC |-------|------|----------------|----------------------------|
-- MAGIC | 1 | ACCOUNT_LEVEL | `sfdc_account_id, sfdc_account_name` | product_account_id, cloud, workspace, tier, product_type, region, shield_sku, usage_unit |
-- MAGIC | 2 | PRODUCT_ACCOUNT_CLOUD | `sfdc_account_id, sfdc_account_name, product_account_id, cloud` | workspace, tier, product_type, region, shield_sku, usage_unit |
-- MAGIC | 3 | WORKSPACE_LEVEL | `sfdc_account_id, sfdc_account_name, product_account_id, cloud, sfdc_workspace_object_id, sfdc_workspace_name` | tier, product_type, region, shield_sku, usage_unit |
-- MAGIC | 4 | SKU_LEVEL | `ALL dimensions (11 total)` | None - most granular |
-- MAGIC 
-- MAGIC **Measures (6 × 16 time periods = 96 columns):**
-- MAGIC - usage_amount, usage_dollars, usage_dollars_at_list
-- MAGIC - shield_usage_amount, shield_dollars, shield_dollars_at_list
-- MAGIC 
-- MAGIC **Example Queries:**
-- MAGIC ```sql
-- MAGIC -- See what dimensions are at each level
-- MAGIC SELECT DISTINCT hierarchy_level, hierarchy_level_name, dimension_keys 
-- MAGIC FROM mv_baseline_consumption 
-- MAGIC ORDER BY hierarchy_level;
-- MAGIC 
-- MAGIC -- Get account-level summary (Level 1)
-- MAGIC SELECT * FROM mv_baseline_consumption WHERE hierarchy_level = 1;
-- MAGIC 
-- MAGIC -- Get workspace-level detail for a specific account (Level 3)
-- MAGIC SELECT * FROM mv_baseline_consumption 
-- MAGIC WHERE hierarchy_level = 3 
-- MAGIC   AND sfdc_account_id = '001XXXXXX';
-- MAGIC 
-- MAGIC -- Get full SKU breakdown (Level 4)
-- MAGIC SELECT * FROM mv_baseline_consumption 
-- MAGIC WHERE hierarchy_level = 4
-- MAGIC   AND product_type = 'JOBS';
-- MAGIC ```

-- COMMAND ----------

CREATE OR REFRESH MATERIALIZED VIEW mv_baseline_consumption
COMMENT "Baseline consumption at ALL hierarchy levels (1=Account, 2=Product+Cloud, 3=Workspace, 4=SKU) with all time periods"
AS

-- ===========================================================================
-- LEVEL 1: ACCOUNT_LEVEL (Most Aggregated)
-- Dimensions: sfdc_account_id, sfdc_account_name
-- Aggregated: Everything else
-- ===========================================================================
SELECT 
  1 AS hierarchy_level,
  'ACCOUNT_LEVEL' AS hierarchy_level_name,
  'sfdc_account_id, sfdc_account_name' AS dimension_keys,
  
  -- Account dimensions (ONLY dimensions at this level)
  p.sfdc_account_id,
  p.sfdc_account_name,
  
  -- All other dimensions are NULL at this level
  CAST(NULL AS STRING) AS product_account_id,
  CAST(NULL AS STRING) AS sfdc_workspace_object_id,
  CAST(NULL AS STRING) AS sfdc_workspace_name,
  CAST(NULL AS STRING) AS cloud,
  CAST(NULL AS STRING) AS tier,
  CAST(NULL AS STRING) AS product_type,
  CAST(NULL AS STRING) AS region,
  CAST(NULL AS STRING) AS shield_sku,
  CAST(NULL AS STRING) AS usage_unit,
  
  -- ===================================================================
  -- PAST 3 COMPLETE MONTHS - NORMALIZED
  -- ===================================================================
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_amount ELSE 0 
  END) / 3 as usage_amount_3m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_dollars ELSE 0 
  END) / 3 as usage_dollars_3m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_dollars_at_list ELSE 0 
  END) / 3 as usage_dollars_at_list_3m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_usage_amount ELSE 0 
  END) / 3 as shield_usage_amount_3m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_price ELSE 0 
  END) / 3 as shield_dollars_3m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_list_price ELSE 0 
  END) / 3 as shield_dollars_at_list_3m,
  
  -- ===================================================================
  -- PAST 30 DAYS (rolling)
  -- ===================================================================
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.usage_amount ELSE 0 
  END) as usage_amount_30d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.usage_dollars ELSE 0 
  END) as usage_dollars_30d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.usage_dollars_at_list ELSE 0 
  END) as usage_dollars_at_list_30d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_usage_amount ELSE 0 
  END) as shield_usage_amount_30d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_price ELSE 0 
  END) as shield_dollars_30d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_list_price ELSE 0 
  END) as shield_dollars_at_list_30d,
  
  -- ===================================================================
  -- PAST 90 DAYS - NORMALIZED
  -- ===================================================================
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.usage_amount ELSE 0 
  END) / 3 as usage_amount_90d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.usage_dollars ELSE 0 
  END) / 3 as usage_dollars_90d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.usage_dollars_at_list ELSE 0 
  END) / 3 as usage_dollars_at_list_90d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_usage_amount ELSE 0 
  END) / 3 as shield_usage_amount_90d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_price ELSE 0 
  END) / 3 as shield_dollars_90d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_list_price ELSE 0 
  END) / 3 as shield_dollars_at_list_90d,
  
  -- ===================================================================
  -- PAST 1 COMPLETE MONTH
  -- ===================================================================
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_amount ELSE 0 
  END) as usage_amount_1m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_dollars ELSE 0 
  END) as usage_dollars_1m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_dollars_at_list ELSE 0 
  END) as usage_dollars_at_list_1m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_usage_amount ELSE 0 
  END) as shield_usage_amount_1m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_price ELSE 0 
  END) as shield_dollars_1m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_list_price ELSE 0 
  END) as shield_dollars_at_list_1m,
  
  -- ===================================================================
  -- MONTHLY BREAKDOWN (12 MONTHS)
  -- ===================================================================
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m1,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m1,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m1,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m1,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m1,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m1,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m2,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m2,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m2,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m2,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m2,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m2,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m3,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m3,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m3,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m3,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m3,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m3,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m4,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m4,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m4,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m4,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m4,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m4,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m5,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m5,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m5,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m5,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m5,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m5,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m6,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m6,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m6,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m6,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m6,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m6,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m7,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m7,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m7,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m7,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m7,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m7,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m8,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m8,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m8,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m8,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m8,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m8,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m9,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m9,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m9,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m9,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m9,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m9,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m10,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m10,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m10,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m10,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m10,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m10,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m11,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m11,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m11,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m11,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m11,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m11,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m12,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m12,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m12,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m12,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m12,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m12
  
FROM main.fin_live_gold.paid_usage_metering p
WHERE p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -12))
  AND p.date < CURRENT_DATE()
GROUP BY 
  p.sfdc_account_id,
  p.sfdc_account_name

UNION ALL

-- ===========================================================================
-- LEVEL 2: PRODUCT_ACCOUNT_CLOUD
-- Dimensions: sfdc_account_id, sfdc_account_name, product_account_id, cloud
-- Aggregated: workspace, tier, product_type, region, shield_sku, usage_unit
-- ===========================================================================
SELECT 
  2 AS hierarchy_level,
  'PRODUCT_ACCOUNT_CLOUD' AS hierarchy_level_name,
  'sfdc_account_id, sfdc_account_name, product_account_id, cloud' AS dimension_keys,
  
  -- Account dimensions
  p.sfdc_account_id,
  p.sfdc_account_name,
  
  -- Product account dimension (ADDED at this level)
  p.product_account_id,
  
  -- Workspace dimensions (NULL at this level)
  CAST(NULL AS STRING) AS sfdc_workspace_object_id,
  CAST(NULL AS STRING) AS sfdc_workspace_name,
  
  -- Cloud dimension (INCLUDED at this level)
  p.cloud,
  
  -- SKU dimensions (NULL at this level)
  CAST(NULL AS STRING) AS tier,
  CAST(NULL AS STRING) AS product_type,
  CAST(NULL AS STRING) AS region,
  CAST(NULL AS STRING) AS shield_sku,
  CAST(NULL AS STRING) AS usage_unit,
  
  -- ===================================================================
  -- PAST 3 COMPLETE MONTHS (e.g., Oct, Nov, Dec if running in Jan)
  -- NORMALIZED TO AVERAGE MONTHLY SPEND (divided by 3)
  -- ===================================================================
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_amount ELSE 0 
  END) / 3 as usage_amount_3m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_dollars ELSE 0 
  END) / 3 as usage_dollars_3m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_dollars_at_list ELSE 0 
  END) / 3 as usage_dollars_at_list_3m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_usage_amount ELSE 0 
  END) / 3 as shield_usage_amount_3m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_price ELSE 0 
  END) / 3 as shield_dollars_3m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_list_price ELSE 0 
  END) / 3 as shield_dollars_at_list_3m,
  
  -- ===================================================================
  -- PAST 30 DAYS (rolling)
  -- ===================================================================
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.usage_amount ELSE 0 
  END) as usage_amount_30d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.usage_dollars ELSE 0 
  END) as usage_dollars_30d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.usage_dollars_at_list ELSE 0 
  END) as usage_dollars_at_list_30d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_usage_amount ELSE 0 
  END) as shield_usage_amount_30d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_price ELSE 0 
  END) as shield_dollars_30d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_list_price ELSE 0 
  END) as shield_dollars_at_list_30d,
  
  -- ===================================================================
  -- PAST 90 DAYS (rolling)
  -- NORMALIZED TO AVERAGE MONTHLY SPEND (divided by 3)
  -- ===================================================================
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.usage_amount ELSE 0 
  END) / 3 as usage_amount_90d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.usage_dollars ELSE 0 
  END) / 3 as usage_dollars_90d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.usage_dollars_at_list ELSE 0 
  END) / 3 as usage_dollars_at_list_90d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_usage_amount ELSE 0 
  END) / 3 as shield_usage_amount_90d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_price ELSE 0 
  END) / 3 as shield_dollars_90d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_list_price ELSE 0 
  END) / 3 as shield_dollars_at_list_90d,
  
  -- ===================================================================
  -- PAST 1 COMPLETE MONTH (last complete month)
  -- ===================================================================
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_amount ELSE 0 
  END) as usage_amount_1m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_dollars ELSE 0 
  END) as usage_dollars_1m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_dollars_at_list ELSE 0 
  END) as usage_dollars_at_list_1m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_usage_amount ELSE 0 
  END) as shield_usage_amount_1m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_price ELSE 0 
  END) as shield_dollars_1m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_list_price ELSE 0 
  END) as shield_dollars_at_list_1m,
  
  -- ===================================================================
  -- MONTHLY BREAKDOWN (12 MONTHS PIVOTED)
  -- ===================================================================
  -- MONTH 1 (12 months ago)
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m1,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m1,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m1,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m1,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m1,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m1,
  
  -- MONTH 2 (11 months ago)
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m2,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m2,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m2,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m2,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m2,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m2,
  
  -- MONTH 3 (10 months ago)
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m3,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m3,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m3,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m3,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m3,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m3,
  
  -- MONTH 4 (9 months ago)
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m4,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m4,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m4,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m4,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m4,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m4,
  
  -- MONTH 5 (8 months ago)
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m5,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m5,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m5,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m5,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m5,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m5,
  
  -- MONTH 6 (7 months ago)
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m6,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m6,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m6,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m6,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m6,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m6,
  
  -- MONTH 7 (6 months ago)
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m7,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m7,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m7,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m7,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m7,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m7,
  
  -- MONTH 8 (5 months ago)
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m8,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m8,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m8,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m8,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m8,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m8,
  
  -- MONTH 9 (4 months ago)
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m9,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m9,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m9,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m9,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m9,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m9,
  
  -- MONTH 10 (3 months ago)
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m10,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m10,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m10,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m10,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m10,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m10,
  
  -- MONTH 11 (2 months ago)
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m11,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m11,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m11,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m11,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m11,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m11,
  
  -- MONTH 12 (1 month ago - last complete month)
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m12,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m12,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m12,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m12,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m12,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m12
  
FROM main.fin_live_gold.paid_usage_metering p
WHERE p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -12))
  AND p.date < CURRENT_DATE()
GROUP BY 
  p.sfdc_account_id,
  p.sfdc_account_name,
  p.product_account_id,
  p.cloud

UNION ALL

-- ===========================================================================
-- LEVEL 3: WORKSPACE_LEVEL
-- Dimensions: sfdc_account_id, sfdc_account_name, product_account_id, cloud, 
--             sfdc_workspace_object_id, sfdc_workspace_name
-- Aggregated: tier, product_type, region, shield_sku, usage_unit
-- ===========================================================================
SELECT 
  3 AS hierarchy_level,
  'WORKSPACE_LEVEL' AS hierarchy_level_name,
  'sfdc_account_id, sfdc_account_name, product_account_id, cloud, sfdc_workspace_object_id, sfdc_workspace_name' AS dimension_keys,
  
  -- Account dimensions
  p.sfdc_account_id,
  p.sfdc_account_name,
  
  -- Product account dimension
  p.product_account_id,
  
  -- Workspace dimensions (ADDED at this level)
  p.sfdc_workspace_object_id,
  p.sfdc_workspace_name,
  
  -- Cloud dimension
  p.cloud,
  
  -- SKU dimensions (NULL at this level)
  CAST(NULL AS STRING) AS tier,
  CAST(NULL AS STRING) AS product_type,
  CAST(NULL AS STRING) AS region,
  CAST(NULL AS STRING) AS shield_sku,
  CAST(NULL AS STRING) AS usage_unit,
  
  -- ===================================================================
  -- PAST 3 COMPLETE MONTHS - NORMALIZED
  -- ===================================================================
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_amount ELSE 0 
  END) / 3 as usage_amount_3m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_dollars ELSE 0 
  END) / 3 as usage_dollars_3m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_dollars_at_list ELSE 0 
  END) / 3 as usage_dollars_at_list_3m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_usage_amount ELSE 0 
  END) / 3 as shield_usage_amount_3m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_price ELSE 0 
  END) / 3 as shield_dollars_3m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_list_price ELSE 0 
  END) / 3 as shield_dollars_at_list_3m,
  
  -- ===================================================================
  -- PAST 30 DAYS
  -- ===================================================================
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.usage_amount ELSE 0 
  END) as usage_amount_30d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.usage_dollars ELSE 0 
  END) as usage_dollars_30d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.usage_dollars_at_list ELSE 0 
  END) as usage_dollars_at_list_30d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_usage_amount ELSE 0 
  END) as shield_usage_amount_30d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_price ELSE 0 
  END) as shield_dollars_30d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_list_price ELSE 0 
  END) as shield_dollars_at_list_30d,
  
  -- ===================================================================
  -- PAST 90 DAYS - NORMALIZED
  -- ===================================================================
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.usage_amount ELSE 0 
  END) / 3 as usage_amount_90d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.usage_dollars ELSE 0 
  END) / 3 as usage_dollars_90d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.usage_dollars_at_list ELSE 0 
  END) / 3 as usage_dollars_at_list_90d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_usage_amount ELSE 0 
  END) / 3 as shield_usage_amount_90d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_price ELSE 0 
  END) / 3 as shield_dollars_90d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_list_price ELSE 0 
  END) / 3 as shield_dollars_at_list_90d,
  
  -- ===================================================================
  -- PAST 1 COMPLETE MONTH
  -- ===================================================================
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_amount ELSE 0 
  END) as usage_amount_1m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_dollars ELSE 0 
  END) as usage_dollars_1m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_dollars_at_list ELSE 0 
  END) as usage_dollars_at_list_1m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_usage_amount ELSE 0 
  END) as shield_usage_amount_1m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_price ELSE 0 
  END) as shield_dollars_1m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_list_price ELSE 0 
  END) as shield_dollars_at_list_1m,
  
  -- ===================================================================
  -- MONTHLY BREAKDOWN (12 MONTHS)
  -- ===================================================================
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m1,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m1,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m1,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m1,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m1,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m1,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m2,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m2,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m2,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m2,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m2,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m2,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m3,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m3,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m3,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m3,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m3,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m3,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m4,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m4,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m4,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m4,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m4,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m4,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m5,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m5,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m5,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m5,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m5,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m5,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m6,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m6,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m6,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m6,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m6,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m6,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m7,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m7,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m7,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m7,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m7,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m7,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m8,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m8,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m8,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m8,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m8,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m8,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m9,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m9,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m9,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m9,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m9,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m9,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m10,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m10,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m10,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m10,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m10,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m10,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m11,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m11,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m11,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m11,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m11,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m11,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m12,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m12,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m12,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m12,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m12,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m12
  
FROM main.fin_live_gold.paid_usage_metering p
WHERE p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -12))
  AND p.date < CURRENT_DATE()
GROUP BY 
  p.sfdc_account_id,
  p.sfdc_account_name,
  p.product_account_id,
  p.cloud,
  p.sfdc_workspace_object_id,
  p.sfdc_workspace_name

UNION ALL

-- ===========================================================================
-- LEVEL 4: SKU_LEVEL (Most Granular)
-- Dimensions: ALL - sfdc_account_id, sfdc_account_name, product_account_id, cloud, 
--             sfdc_workspace_object_id, sfdc_workspace_name, tier, product_type, 
--             region, shield_sku, usage_unit
-- Aggregated: None - this is the most detailed level
-- ===========================================================================
SELECT 
  4 AS hierarchy_level,
  'SKU_LEVEL' AS hierarchy_level_name,
  'sfdc_account_id, sfdc_account_name, product_account_id, cloud, sfdc_workspace_object_id, sfdc_workspace_name, tier, product_type, region, shield_sku, usage_unit' AS dimension_keys,
  
  -- Account dimensions
  p.sfdc_account_id,
  p.sfdc_account_name,
  
  -- Product account dimension
  p.product_account_id,
  
  -- Workspace dimensions
  p.sfdc_workspace_object_id,
  p.sfdc_workspace_name,
  
  -- Cloud dimension
  p.cloud,
  
  -- SKU dimensions (ALL included at this most granular level)
  s.tier,
  s.product_type,
  s.region,
  COALESCE(p.add_on.shield_sku, 'NO_SHIELD') as shield_sku,
  p.usage_unit,
  
  -- ===================================================================
  -- PAST 3 COMPLETE MONTHS - NORMALIZED
  -- ===================================================================
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_amount ELSE 0 
  END) / 3 as usage_amount_3m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_dollars ELSE 0 
  END) / 3 as usage_dollars_3m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_dollars_at_list ELSE 0 
  END) / 3 as usage_dollars_at_list_3m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_usage_amount ELSE 0 
  END) / 3 as shield_usage_amount_3m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_price ELSE 0 
  END) / 3 as shield_dollars_3m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_list_price ELSE 0 
  END) / 3 as shield_dollars_at_list_3m,
  
  -- ===================================================================
  -- PAST 30 DAYS
  -- ===================================================================
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.usage_amount ELSE 0 
  END) as usage_amount_30d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.usage_dollars ELSE 0 
  END) as usage_dollars_30d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.usage_dollars_at_list ELSE 0 
  END) as usage_dollars_at_list_30d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_usage_amount ELSE 0 
  END) as shield_usage_amount_30d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_price ELSE 0 
  END) as shield_dollars_30d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 30)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_list_price ELSE 0 
  END) as shield_dollars_at_list_30d,
  
  -- ===================================================================
  -- PAST 90 DAYS - NORMALIZED
  -- ===================================================================
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.usage_amount ELSE 0 
  END) / 3 as usage_amount_90d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.usage_dollars ELSE 0 
  END) / 3 as usage_dollars_90d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.usage_dollars_at_list ELSE 0 
  END) / 3 as usage_dollars_at_list_90d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_usage_amount ELSE 0 
  END) / 3 as shield_usage_amount_90d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_price ELSE 0 
  END) / 3 as shield_dollars_90d,
  
  SUM(CASE 
    WHEN p.date >= DATE_SUB(CURRENT_DATE(), 90)
     AND p.date < CURRENT_DATE()
    THEN p.add_on.shield_list_price ELSE 0 
  END) / 3 as shield_dollars_at_list_90d,
  
  -- ===================================================================
  -- PAST 1 COMPLETE MONTH
  -- ===================================================================
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_amount ELSE 0 
  END) as usage_amount_1m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_dollars ELSE 0 
  END) as usage_dollars_1m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.usage_dollars_at_list ELSE 0 
  END) as usage_dollars_at_list_1m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_usage_amount ELSE 0 
  END) as shield_usage_amount_1m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_price ELSE 0 
  END) as shield_dollars_1m,
  
  SUM(CASE 
    WHEN p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -1))
     AND p.date < DATE_TRUNC('month', CURRENT_DATE())
    THEN p.add_on.shield_list_price ELSE 0 
  END) as shield_dollars_at_list_1m,
  
  -- ===================================================================
  -- MONTHLY BREAKDOWN (12 MONTHS)
  -- ===================================================================
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m1,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m1,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m1,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m1,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m1,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m1,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m2,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m2,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m2,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m2,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m2,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -11), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m2,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m3,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m3,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m3,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m3,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m3,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -10), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m3,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m4,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m4,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m4,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m4,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m4,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -9), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m4,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m5,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m5,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m5,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m5,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m5,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -8), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m5,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m6,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m6,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m6,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m6,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m6,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -7), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m6,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m7,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m7,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m7,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m7,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m7,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m7,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m8,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m8,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m8,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m8,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m8,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -5), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m8,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m9,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m9,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m9,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m9,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m9,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -4), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m9,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m10,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m10,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m10,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m10,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m10,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -3), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m10,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m11,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m11,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m11,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m11,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m11,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -2), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m11,
  
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.usage_amount ELSE 0 END) as usage_amount_m12,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.usage_dollars ELSE 0 END) as usage_dollars_m12,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.usage_dollars_at_list ELSE 0 END) as usage_dollars_at_list_m12,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.add_on.shield_usage_amount ELSE 0 END) as shield_usage_amount_m12,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.add_on.shield_price ELSE 0 END) as shield_dollars_m12,
  SUM(CASE WHEN DATE_FORMAT(p.date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN p.add_on.shield_list_price ELSE 0 END) as shield_dollars_at_list_m12
  
FROM main.fin_live_gold.paid_usage_metering p
LEFT JOIN users.steven_tan.sku_parser_lookup s
  ON p.sku = s.sku_name AND p.cloud = s.cloud
WHERE p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -12))
  AND p.date < CURRENT_DATE()
GROUP BY 
  p.sfdc_account_id,
  p.sfdc_account_name,
  p.product_account_id,
  p.cloud,
  p.sfdc_workspace_object_id,
  p.sfdc_workspace_name,
  s.tier,
  s.product_type,
  s.region,
  shield_sku,
  p.usage_unit;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Verification Queries

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### Check Hierarchy Level Distribution

-- COMMAND ----------

-- Verify all 4 hierarchy levels exist and count rows per level
SELECT 
  hierarchy_level,
  hierarchy_level_name,
  dimension_keys,
  COUNT(*) as row_count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as pct_of_total,
  -- Show sample dimension cardinality
  COUNT(DISTINCT sfdc_account_id) as unique_accounts,
  COUNT(DISTINCT product_account_id) as unique_product_accounts,
  COUNT(DISTINCT sfdc_workspace_object_id) as unique_workspaces,
  COUNT(DISTINCT tier) as unique_tiers,
  COUNT(DISTINCT product_type) as unique_product_types
FROM mv_baseline_consumption
GROUP BY hierarchy_level, hierarchy_level_name, dimension_keys
ORDER BY hierarchy_level;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### Validate Hierarchy Rollup
-- MAGIC
-- MAGIC Ensure that aggregating Level 4 produces the same totals as Level 1

-- COMMAND ----------

WITH level_4_totals AS (
  SELECT 
    SUM(usage_dollars_3m) as total_dollars_3m
  FROM mv_baseline_consumption
  WHERE hierarchy_level = 4
),
level_1_totals AS (
  SELECT 
    SUM(usage_dollars_3m) as total_dollars_3m
  FROM mv_baseline_consumption
  WHERE hierarchy_level = 1
)
SELECT 
  'Hierarchy Rollup Validation' as test_name,
  l4.total_dollars_3m as level_4_total,
  l1.total_dollars_3m as level_1_total,
  ABS(l4.total_dollars_3m - l1.total_dollars_3m) as difference,
  CASE 
    WHEN ABS(l4.total_dollars_3m - l1.total_dollars_3m) < 0.01 THEN '✅ VALID'
    ELSE '❌ MISMATCH'
  END as validation_status
FROM level_4_totals l4, level_1_totals l1;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### Sample Data by Hierarchy Level

-- COMMAND ----------

-- Level 1: Account Level (most aggregated)
SELECT 'Level 1: ACCOUNT_LEVEL' as level_name, * 
FROM mv_baseline_consumption 
WHERE hierarchy_level = 1 
ORDER BY usage_dollars_3m DESC
LIMIT 5;

-- COMMAND ----------

-- Level 2: Product Account + Cloud
SELECT 'Level 2: PRODUCT_ACCOUNT_CLOUD' as level_name, * 
FROM mv_baseline_consumption 
WHERE hierarchy_level = 2 
ORDER BY usage_dollars_3m DESC
LIMIT 5;

-- COMMAND ----------

-- Level 3: Workspace Level
SELECT 'Level 3: WORKSPACE_LEVEL' as level_name, * 
FROM mv_baseline_consumption 
WHERE hierarchy_level = 3 
ORDER BY usage_dollars_3m DESC
LIMIT 5;

-- COMMAND ----------

-- Level 4: SKU Level (most granular)
SELECT 'Level 4: SKU_LEVEL' as level_name, * 
FROM mv_baseline_consumption 
WHERE hierarchy_level = 4 
ORDER BY usage_dollars_3m DESC
LIMIT 5;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### Check Row Counts (All MVs)

-- COMMAND ----------

SELECT 'mv_dim_salesforce_account' AS table_name, COUNT(*) AS row_count FROM mv_dim_salesforce_account
UNION ALL
SELECT 'mv_fct_salesforce_use_case' AS table_name, COUNT(*) AS row_count FROM mv_fct_salesforce_use_case
UNION ALL
SELECT 'mv_hourly_opportunity' AS table_name, COUNT(*) AS row_count FROM mv_hourly_opportunity
UNION ALL
SELECT 'mv_baseline_consumption' AS table_name, COUNT(*) AS row_count FROM mv_baseline_consumption
UNION ALL
SELECT 'mv_baseline_consumption - Level 1' AS table_name, COUNT(*) AS row_count FROM mv_baseline_consumption WHERE hierarchy_level = 1
UNION ALL
SELECT 'mv_baseline_consumption - Level 2' AS table_name, COUNT(*) AS row_count FROM mv_baseline_consumption WHERE hierarchy_level = 2
UNION ALL
SELECT 'mv_baseline_consumption - Level 3' AS table_name, COUNT(*) AS row_count FROM mv_baseline_consumption WHERE hierarchy_level = 3
UNION ALL
SELECT 'mv_baseline_consumption - Level 4' AS table_name, COUNT(*) AS row_count FROM mv_baseline_consumption WHERE hierarchy_level = 4;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ### Legacy Sample Queries (Other MVs)

-- COMMAND ----------

SELECT 'Accounts' AS source, * FROM mv_dim_salesforce_account LIMIT 5;

-- COMMAND ----------

SELECT 'Use Cases' AS source, * FROM mv_fct_salesforce_use_case LIMIT 5;

-- COMMAND ----------

SELECT 'Opportunities' AS source, * FROM mv_hourly_opportunity LIMIT 5;
