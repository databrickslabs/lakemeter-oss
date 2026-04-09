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
-- MAGIC ## 4. Baseline Consumption (All Time Periods + Monthly Breakdown)
-- MAGIC 
-- MAGIC **Strategy:** ONE materialized view with EVERYTHING:
-- MAGIC - Time period summaries: 3m, 30d, 90d, 1m (24 columns)
-- MAGIC - Monthly breakdown: 12 months pivoted (72 columns)
-- MAGIC - Total: 96 measure columns + 10 dimensions = 106 columns
-- MAGIC 
-- MAGIC **Result:** ONE row per dimension (~100k rows)
-- MAGIC - Smallest possible dataset
-- MAGIC - Zero aggregation needed in Lakebase - just SELECT!
-- MAGIC 
-- MAGIC **Column groups:**
-- MAGIC 1. Dimensions (10): account, workspace, cloud, tier, product_type, region, shield_sku, usage_unit
-- MAGIC 2. Summary metrics with suffixes: _3m, _30d, _90d, _1m (24 columns)
-- MAGIC    - _3m and _90d are NORMALIZED (divided by 3) for average monthly spend
-- MAGIC    - _30d and _1m are kept as-is (~1 month each)
-- MAGIC 3. Monthly metrics with suffixes: _m1 to _m12 (72 columns)
-- MAGIC    - Each represents one complete month (no normalization needed)
-- MAGIC 
-- MAGIC **Dimensions (10):**
-- MAGIC - sfdc_account_id, sfdc_account_name
-- MAGIC - sfdc_workspace_object_id, sfdc_workspace_name
-- MAGIC - cloud, tier, product_type, region
-- MAGIC - shield_sku, usage_unit
-- MAGIC 
-- MAGIC **Measures (6 × 16 time periods = 96 columns):**
-- MAGIC - usage_amount
-- MAGIC - usage_dollars
-- MAGIC - usage_dollars_at_list
-- MAGIC - shield_usage_amount
-- MAGIC - shield_dollars
-- MAGIC - shield_dollars_at_list

-- COMMAND ----------

CREATE OR REFRESH MATERIALIZED VIEW mv_baseline_consumption
COMMENT "Complete baseline consumption - all time periods (3m/30d/90d/1m) + 12 monthly breakdown in ONE view"
AS
SELECT 
  -- Account dimensions
  p.sfdc_account_id,
  p.sfdc_account_name,
  
  -- Workspace dimensions  
  p.sfdc_workspace_object_id,
  p.sfdc_workspace_name,
  
  -- Cloud & SKU dimensions (from SKU parser)
  p.cloud,
  s.tier,
  s.product_type,  -- refined sku (after removing tier and region)
  s.region,
  
  -- Shield SKU dimension
  COALESCE(p.add_on.shield_sku, 'NO_SHIELD') as shield_sku,
  
  -- Usage unit dimension
  p.usage_unit,
  
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
LEFT JOIN users.steven_tan.sku_parser_lookup s
  ON p.sku = s.sku_name AND p.cloud = s.cloud
WHERE p.date >= DATE_TRUNC('month', ADD_MONTHS(CURRENT_DATE(), -3))  -- Need at least 3 months of data
  AND p.date < CURRENT_DATE()
GROUP BY 
  p.sfdc_account_id,
  p.sfdc_account_name,
  p.sfdc_workspace_object_id,
  p.sfdc_workspace_name,
  p.cloud,
  s.tier,
  s.product_type,
  s.region,
  shield_sku,
  p.usage_unit;