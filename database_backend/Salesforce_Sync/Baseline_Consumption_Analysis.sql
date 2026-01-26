-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Baseline Consumption Analysis
-- MAGIC 
-- MAGIC **Source Table:** `main.fin_live_gold.paid_usage_metering`
-- MAGIC 
-- MAGIC **Goal:** Establish baseline consumption metrics by various dimensions

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 1. Get Table Definition

-- COMMAND ----------

-- Show table schema
DESCRIBE EXTENDED main.fin_live_gold.paid_usage_metering;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 2. Understand the Numeric Columns
-- MAGIC 
-- MAGIC Let's check sample data to understand the different numeric fields:

-- COMMAND ----------

-- Sample data with all numeric columns
SELECT 
  sfdc_account_name,
  sku,
  cloud,
  date,
  -- Usage metrics
  usage_amount,
  raw_usage_amount,
  net_usage_amount,
  credits_usage_amount,
  -- Price metrics
  list_price,
  rev_share_price,
  discount_price,
  -- Dollar metrics (RAW)
  usage_dollars_raw,
  usage_dollars_at_list_raw,
  -- Dollar metrics (ADJUSTED)
  usage_dollars,
  usage_dollars_at_list,
  -- Shield add-on
  add_on.shield_usage_amount,
  add_on.shield_price,
  add_on.shield_list_price
FROM main.fin_live_gold.paid_usage_metering
WHERE date >= DATE_SUB(CURRENT_DATE(), 7)  -- Last 7 days sample
LIMIT 100;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 3. Column Definitions (Based on Common Usage Metering Patterns)
-- MAGIC 
-- MAGIC | Column | Description | Use For Baseline |
-- MAGIC |--------|-------------|------------------|
-- MAGIC | `usage_amount` | Raw usage quantity | ✅ Primary usage metric |
-- MAGIC | `raw_usage_amount` | Original usage before adjustments | ⚠️ Use if different from usage_amount |
-- MAGIC | `net_usage_amount` | Usage after credits/discounts | ❌ Not for baseline (has discounts) |
-- MAGIC | `credits_usage_amount` | Usage covered by credits | ℹ️ Track separately |
-- MAGIC | `usage_dollars` | **RECOMMENDED for $** | ✅ Actual dollars (with discounts) |
-- MAGIC | `usage_dollars_at_list` | Dollars at list price | ✅ For list price baseline |
-- MAGIC | `usage_dollars_raw` | Raw dollars before adjustments | ⚠️ Check if needed |
-- MAGIC | `usage_dollars_at_list_raw` | Raw list price dollars | ⚠️ Check if needed |

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 4. Date Range Helpers

-- COMMAND ----------

-- Current date and key date ranges
SELECT 
  CURRENT_DATE() AS today,
  DATE_TRUNC('month', CURRENT_DATE()) AS current_month_start,
  DATE_SUB(DATE_TRUNC('month', CURRENT_DATE()), 1) AS last_month_end,
  DATE_TRUNC('month', DATE_SUB(CURRENT_DATE(), 31)) AS last_month_start,
  DATE_TRUNC('month', DATE_SUB(CURRENT_DATE(), 62)) AS two_months_ago_start,
  DATE_TRUNC('month', DATE_SUB(CURRENT_DATE(), 93)) AS three_months_ago_start,
  DATE_SUB(CURRENT_DATE(), 30) AS last_30_days,
  DATE_SUB(CURRENT_DATE(), 90) AS last_90_days;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 5. Baseline Consumption - Last 3 Complete Months
-- MAGIC 
-- MAGIC **Recommended for baseline:** Use last 3 complete months (Dec, Nov, Oct for January 2026)

-- COMMAND ----------

-- Last 3 complete months by account, cloud, SKU
WITH date_ranges AS (
  SELECT 
    DATE_TRUNC('month', DATE_SUB(CURRENT_DATE(), 31)) AS last_month_start,
    DATE_SUB(DATE_TRUNC('month', CURRENT_DATE()), 1) AS last_month_end,
    DATE_TRUNC('month', DATE_SUB(CURRENT_DATE(), 31)) AS month_1_start,
    LAST_DAY(DATE_TRUNC('month', DATE_SUB(CURRENT_DATE(), 31))) AS month_1_end,
    DATE_TRUNC('month', DATE_SUB(CURRENT_DATE(), 62)) AS month_2_start,
    LAST_DAY(DATE_TRUNC('month', DATE_SUB(CURRENT_DATE(), 62))) AS month_2_end,
    DATE_TRUNC('month', DATE_SUB(CURRENT_DATE(), 93)) AS month_3_start,
    LAST_DAY(DATE_TRUNC('month', DATE_SUB(CURRENT_DATE(), 93))) AS month_3_end
)
SELECT 
  sfdc_account_id,
  sfdc_account_name,
  cloud,
  sku,
  product_type,
  compute_workload_type,
  usage_type,
  usage_unit,
  -- Aggregate usage
  SUM(usage_amount) AS total_usage_amount,
  AVG(usage_amount) AS avg_daily_usage_amount,
  -- Aggregate dollars
  SUM(usage_dollars) AS total_usage_dollars,
  SUM(usage_dollars_at_list) AS total_usage_dollars_at_list,
  AVG(usage_dollars) AS avg_daily_usage_dollars,
  -- Count days with usage
  COUNT(DISTINCT date) AS days_with_usage,
  MIN(date) AS first_usage_date,
  MAX(date) AS last_usage_date
FROM main.fin_live_gold.paid_usage_metering, date_ranges
WHERE date >= date_ranges.month_3_start
  AND date <= date_ranges.month_1_end
GROUP BY 
  sfdc_account_id,
  sfdc_account_name,
  cloud,
  sku,
  product_type,
  compute_workload_type,
  usage_type,
  usage_unit
ORDER BY total_usage_dollars DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 6. Baseline Consumption - Last 90 Days (Rolling)

-- COMMAND ----------

SELECT 
  sfdc_account_id,
  sfdc_account_name,
  cloud,
  sku,
  product_type,
  -- Aggregate usage
  SUM(usage_amount) AS total_usage_amount_90d,
  AVG(usage_amount) AS avg_daily_usage_amount_90d,
  -- Aggregate dollars
  SUM(usage_dollars) AS total_usage_dollars_90d,
  SUM(usage_dollars_at_list) AS total_usage_dollars_at_list_90d,
  -- Daily average
  SUM(usage_dollars) / 90 AS avg_daily_dollars_90d,
  -- Monthly projection (90 days / 3 months)
  SUM(usage_dollars) / 3 AS projected_monthly_dollars,
  -- Count
  COUNT(DISTINCT date) AS days_with_usage_90d
FROM main.fin_live_gold.paid_usage_metering
WHERE date >= DATE_SUB(CURRENT_DATE(), 90)
  AND date < CURRENT_DATE()
GROUP BY 
  sfdc_account_id,
  sfdc_account_name,
  cloud,
  sku,
  product_type
ORDER BY total_usage_dollars_90d DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 7. Baseline Consumption - Last 30 Days (Rolling)

-- COMMAND ----------

SELECT 
  sfdc_account_id,
  sfdc_account_name,
  cloud,
  sku,
  product_type,
  -- Aggregate usage
  SUM(usage_amount) AS total_usage_amount_30d,
  AVG(usage_amount) AS avg_daily_usage_amount_30d,
  -- Aggregate dollars
  SUM(usage_dollars) AS total_usage_dollars_30d,
  SUM(usage_dollars_at_list) AS total_usage_dollars_at_list_30d,
  -- Daily average
  SUM(usage_dollars) / 30 AS avg_daily_dollars_30d,
  -- Count
  COUNT(DISTINCT date) AS days_with_usage_30d
FROM main.fin_live_gold.paid_usage_metering
WHERE date >= DATE_SUB(CURRENT_DATE(), 30)
  AND date < CURRENT_DATE()
GROUP BY 
  sfdc_account_id,
  sfdc_account_name,
  cloud,
  sku,
  product_type
ORDER BY total_usage_dollars_30d DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 8. Baseline by Cloud and Region
-- MAGIC 
-- MAGIC Region is typically encoded in the SKU

-- COMMAND ----------

SELECT 
  sfdc_account_id,
  sfdc_account_name,
  cloud,
  -- Extract region from SKU (adjust pattern based on actual SKU format)
  CASE 
    WHEN sku LIKE '%us-east%' THEN 'us-east'
    WHEN sku LIKE '%us-west%' THEN 'us-west'
    WHEN sku LIKE '%eu-west%' THEN 'eu-west'
    WHEN sku LIKE '%ap-south%' THEN 'ap-south'
    ELSE 'other'
  END AS region,
  sku,
  -- Last 90 days
  SUM(usage_dollars) AS total_usage_dollars_90d,
  AVG(usage_dollars) AS avg_daily_usage_dollars_90d,
  SUM(usage_amount) AS total_usage_amount_90d
FROM main.fin_live_gold.paid_usage_metering
WHERE date >= DATE_SUB(CURRENT_DATE(), 90)
  AND date < CURRENT_DATE()
GROUP BY 
  sfdc_account_id,
  sfdc_account_name,
  cloud,
  region,
  sku
ORDER BY total_usage_dollars_90d DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 9. Baseline Summary by Account (All Dimensions)

-- COMMAND ----------

WITH last_90_days AS (
  SELECT 
    sfdc_account_id,
    sfdc_account_name,
    cloud,
    SUM(usage_dollars) AS usage_dollars_90d,
    SUM(usage_amount) AS usage_amount_90d,
    COUNT(DISTINCT date) AS active_days_90d
  FROM main.fin_live_gold.paid_usage_metering
  WHERE date >= DATE_SUB(CURRENT_DATE(), 90)
    AND date < CURRENT_DATE()
  GROUP BY sfdc_account_id, sfdc_account_name, cloud
),
last_30_days AS (
  SELECT 
    sfdc_account_id,
    SUM(usage_dollars) AS usage_dollars_30d,
    SUM(usage_amount) AS usage_amount_30d,
    COUNT(DISTINCT date) AS active_days_30d
  FROM main.fin_live_gold.paid_usage_metering
  WHERE date >= DATE_SUB(CURRENT_DATE(), 30)
    AND date < CURRENT_DATE()
  GROUP BY sfdc_account_id
),
last_complete_month AS (
  SELECT 
    sfdc_account_id,
    SUM(usage_dollars) AS usage_dollars_last_month,
    SUM(usage_amount) AS usage_amount_last_month,
    COUNT(DISTINCT date) AS active_days_last_month
  FROM main.fin_live_gold.paid_usage_metering
  WHERE date >= DATE_TRUNC('month', DATE_SUB(CURRENT_DATE(), 31))
    AND date < DATE_TRUNC('month', CURRENT_DATE())
  GROUP BY sfdc_account_id
)
SELECT 
  d90.sfdc_account_id,
  d90.sfdc_account_name,
  d90.cloud,
  -- 90 days
  d90.usage_dollars_90d,
  d90.usage_amount_90d,
  d90.active_days_90d,
  d90.usage_dollars_90d / 90 AS avg_daily_dollars_90d,
  -- 30 days
  d30.usage_dollars_30d,
  d30.usage_amount_30d,
  d30.active_days_30d,
  d30.usage_dollars_30d / 30 AS avg_daily_dollars_30d,
  -- Last complete month
  lm.usage_dollars_last_month,
  lm.usage_amount_last_month,
  lm.active_days_last_month,
  -- Trend (30d vs 90d)
  ROUND((d30.usage_dollars_30d / 30) / (d90.usage_dollars_90d / 90) * 100 - 100, 2) AS trend_pct_change
FROM last_90_days d90
LEFT JOIN last_30_days d30 ON d90.sfdc_account_id = d30.sfdc_account_id
LEFT JOIN last_complete_month lm ON d90.sfdc_account_id = lm.sfdc_account_id
ORDER BY d90.usage_dollars_90d DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 10. SKU-Level Breakdown (Top SKUs by Account)

-- COMMAND ----------

SELECT 
  sfdc_account_id,
  sfdc_account_name,
  cloud,
  sku,
  product_type,
  compute_workload_type,
  usage_unit,
  -- Last 90 days metrics
  SUM(usage_dollars) AS usage_dollars_90d,
  SUM(usage_amount) AS usage_amount_90d,
  SUM(usage_dollars) / 90 AS avg_daily_dollars_90d,
  -- Percentage of total account spend
  SUM(usage_dollars) / SUM(SUM(usage_dollars)) OVER (PARTITION BY sfdc_account_id) * 100 AS pct_of_account_spend,
  -- Rank within account
  ROW_NUMBER() OVER (PARTITION BY sfdc_account_id ORDER BY SUM(usage_dollars) DESC) AS sku_rank
FROM main.fin_live_gold.paid_usage_metering
WHERE date >= DATE_SUB(CURRENT_DATE(), 90)
  AND date < CURRENT_DATE()
GROUP BY 
  sfdc_account_id,
  sfdc_account_name,
  cloud,
  sku,
  product_type,
  compute_workload_type,
  usage_unit
HAVING SUM(usage_dollars) > 0
ORDER BY sfdc_account_id, usage_dollars_90d DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 11. Month-over-Month Comparison (Last 3 Complete Months)

-- COMMAND ----------

WITH monthly_usage AS (
  SELECT 
    sfdc_account_id,
    sfdc_account_name,
    cloud,
    DATE_TRUNC('month', date) AS month,
    SUM(usage_dollars) AS monthly_usage_dollars,
    SUM(usage_amount) AS monthly_usage_amount,
    COUNT(DISTINCT date) AS active_days
  FROM main.fin_live_gold.paid_usage_metering
  WHERE date >= DATE_TRUNC('month', DATE_SUB(CURRENT_DATE(), 93))
    AND date < DATE_TRUNC('month', CURRENT_DATE())
  GROUP BY 
    sfdc_account_id,
    sfdc_account_name,
    cloud,
    DATE_TRUNC('month', date)
)
SELECT 
  sfdc_account_id,
  sfdc_account_name,
  cloud,
  MAX(CASE WHEN month = DATE_TRUNC('month', DATE_SUB(CURRENT_DATE(), 31)) THEN monthly_usage_dollars END) AS month_1_dollars,
  MAX(CASE WHEN month = DATE_TRUNC('month', DATE_SUB(CURRENT_DATE(), 62)) THEN monthly_usage_dollars END) AS month_2_dollars,
  MAX(CASE WHEN month = DATE_TRUNC('month', DATE_SUB(CURRENT_DATE(), 93)) THEN monthly_usage_dollars END) AS month_3_dollars,
  AVG(monthly_usage_dollars) AS avg_monthly_dollars_3m,
  STDDEV(monthly_usage_dollars) AS stddev_monthly_dollars_3m
FROM monthly_usage
GROUP BY 
  sfdc_account_id,
  sfdc_account_name,
  cloud
ORDER BY avg_monthly_dollars_3m DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 12. Recommended Baseline Metric
-- MAGIC 
-- MAGIC **For baseline consumption, use:**
-- MAGIC - **Time Period:** Last 90 days (rolling) or Last 3 complete months
-- MAGIC - **Metric:** `usage_dollars` (actual cost) or `usage_dollars_at_list` (list price)
-- MAGIC - **Dimensions:** Account, Cloud, SKU, Product Type
-- MAGIC - **Aggregation:** Average daily spend or Monthly average

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## 13. Quick Check - Verify Which Column to Use

-- COMMAND ----------

-- Compare the different dollar columns to understand the differences
SELECT 
  sfdc_account_name,
  date,
  sku,
  usage_amount,
  usage_dollars_raw,
  usage_dollars_at_list_raw,
  usage_dollars,
  usage_dollars_at_list,
  net_usage_amount,
  credits_usage_amount,
  discount_price,
  -- Show differences
  usage_dollars_at_list - usage_dollars AS discount_amount,
  ROUND((usage_dollars / NULLIF(usage_dollars_at_list, 0)) * 100, 2) AS effective_discount_pct
FROM main.fin_live_gold.paid_usage_metering
WHERE date >= DATE_SUB(CURRENT_DATE(), 7)
  AND usage_dollars > 0
LIMIT 100;
