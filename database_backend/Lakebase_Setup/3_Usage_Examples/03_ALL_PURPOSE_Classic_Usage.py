# Databricks notebook source
# MAGIC %md
# MAGIC # 📘 Usage Guide: ALL_PURPOSE Classic
# MAGIC
# MAGIC **Workload Type:** `ALL_PURPOSE`  
# MAGIC **Compute Mode:** Classic (interactive clusters)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 🧮 Cost Formula
# MAGIC
# MAGIC ```
# MAGIC Total Cost = DBU Cost + VM Cost
# MAGIC
# MAGIC WHERE:
# MAGIC   DBU Cost = (Driver DBU/hour + Worker DBU/hour × num_workers) 
# MAGIC              × Photon Multiplier (from sync_ref_dbu_multipliers)
# MAGIC              × hours_per_month 
# MAGIC              × DBU Price ($/DBU from sync_pricing_dbu_rates)
# MAGIC
# MAGIC   VM Cost = (Driver VM $/hour + Worker VM $/hour × num_workers) 
# MAGIC             × hours_per_month
# MAGIC
# MAGIC   hours_per_month = runs_per_day × (avg_runtime_minutes / 60) × days_per_month
# MAGIC                     OR use p_hours_per_month to override (e.g., 720 for 24/7)
# MAGIC ```
# MAGIC
# MAGIC **Key Components:**
# MAGIC - **DBU rates:** Higher than Jobs workload type
# MAGIC - **Product type:** `ALL_PURPOSE_COMPUTE` or `ALL_PURPOSE_COMPUTE_(PHOTON)`
# MAGIC - **Photon multiplier:** **OPTIONAL for Classic** - set `photon_enabled = TRUE` or `FALSE`
# MAGIC - **DBU calculation:** Same as Jobs (driver + worker × count) × multiplier
# MAGIC - **VM costs:** Same as Jobs
# MAGIC - **Runtime:** Use `runs_per_day`/`avg_runtime_minutes` OR override with `p_hours_per_month`
# MAGIC - **Driver and worker:** Can have different pricing tiers and payment options
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## ✅ How to Validate Your Inputs
# MAGIC
# MAGIC **Validation Tables:** `lakemeter.sync_ref_instance_dbu_rates` + `lakemeter.sync_pricing_vm_costs`
# MAGIC
# MAGIC **What to validate:**
# MAGIC - Instance Type has DBU rates defined (for compute cost)
# MAGIC - Instance Type has VM costs defined for Cloud + Region + Pricing Tier + Payment Option
# MAGIC
# MAGIC **Validation queries:**
# MAGIC ```sql
# MAGIC -- Check DBU rates exist for instance type
# MAGIC SELECT * FROM lakemeter.sync_ref_instance_dbu_rates
# MAGIC WHERE UPPER(cloud) = UPPER('AWS')
# MAGIC   AND UPPER(instance_type) = UPPER('i3.xlarge');
# MAGIC
# MAGIC -- Check VM costs exist for region + pricing tier + payment option
# MAGIC SELECT * FROM lakemeter.sync_pricing_vm_costs
# MAGIC WHERE UPPER(cloud) = UPPER('AWS')
# MAGIC   AND UPPER(region) = UPPER('us-east-1')
# MAGIC   AND UPPER(instance_type) = UPPER('i3.xlarge')
# MAGIC   AND UPPER(pricing_tier) = UPPER('on_demand')
# MAGIC   AND UPPER(payment_option) = UPPER('NA');
# MAGIC ```
# MAGIC
# MAGIC **Note:** `pricing_tier` = on_demand/spot/reserved_1y/reserved_3y, `payment_option` = NA/no_upfront/partial_upfront/all_upfront
# MAGIC
# MAGIC If this query returns rows → Valid combination ✅  
# MAGIC If this query returns 0 rows → Invalid combination ❌ (will result in $0 VM cost)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 📋 Example Scenario
# MAGIC
# MAGIC **Use Case:** All-purpose (interactive) cluster for data exploration and notebooks
# MAGIC
# MAGIC **Scenario Details:**
# MAGIC - Classic compute cluster for interactive workloads (notebooks, ad-hoc queries)
# MAGIC - 1 driver node + 4 worker nodes with fixed configuration
# MAGIC - Photon enabled for better query performance
# MAGIC - Runs 8 hours per day (typical business hours usage)
# MAGIC - On-demand VM pricing for both driver and workers
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 📊 Parameter Values Explained
# MAGIC
# MAGIC | Parameter | Value | What It Represents |
# MAGIC |-----------|-------|-------------------|
# MAGIC | **Core Identifiers** | | |
# MAGIC | `p_workload_type` | `'ALL_PURPOSE'` | Interactive/all-purpose workload |
# MAGIC | `p_cloud` | `'AWS'` | Amazon Web Services |
# MAGIC | `p_region` | `'us-east-1'` | US East region |
# MAGIC | `p_tier` | `'PREMIUM'` | Databricks pricing tier |
# MAGIC | **Compute Configuration** | | |
# MAGIC | `p_serverless_enabled` | `FALSE` | Classic compute (not serverless) |
# MAGIC | `p_photon_enabled` | `TRUE` | Photon enabled (optional for classic) |
# MAGIC | `p_driver_node_type` | `'i3.xlarge'` | Driver instance type |
# MAGIC | `p_worker_node_type` | `'i3.2xlarge'` | Worker instance type |
# MAGIC | `p_num_workers` | `4` | 4 worker nodes in cluster |
# MAGIC | **VM Pricing** | | |
# MAGIC | `p_driver_pricing_tier` | `'on_demand'` | Driver uses on-demand pricing |
# MAGIC | `p_worker_pricing_tier` | `'on_demand'` | Workers use on-demand pricing |
# MAGIC | `p_driver_payment_option` | `'NA'` | Not AWS reserved |
# MAGIC | `p_worker_payment_option` | `'NA'` | Not AWS reserved |
# MAGIC | **Usage Pattern** | | |
# MAGIC | `p_runs_per_day` | `1` | Cluster runs once per day |
# MAGIC | `p_avg_runtime_minutes` | `480` | Runs for 8 hours (480 minutes) |
# MAGIC | `p_days_per_month` | `30` | 30 days per month |
# MAGIC | `p_hours_per_month` | `NULL` | Auto-calculated: 1 × 8 × 30 = 240 hours |
# MAGIC | **All Other Parameters** | `NULL` or defaults | Not applicable for ALL_PURPOSE workload |
# MAGIC
# MAGIC **Key Points for AI Agents:**
# MAGIC 1. **ALL_PURPOSE = Interactive workload** (notebooks, ad-hoc queries)
# MAGIC 2. **Has both DBU and VM costs** (classic compute)
# MAGIC 3. **Photon is OPTIONAL** for classic (vs mandatory for serverless)
# MAGIC 4. **Different from JOBS** - used for exploratory/interactive work
# MAGIC 5. **Usage pattern** typically follows business hours (not 24/7)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 💻 Function Call

# COMMAND ----------

%run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
import pandas as pd

def get_connection():
    return psycopg2.connect(host=LAKEBASE_HOST, port=LAKEBASE_PORT, database=LAKEBASE_DB, user=LAKEBASE_USER, password=LAKEBASE_PASSWORD)

def execute_query(query):
    conn = get_connection()
    try:
        return pd.read_sql(query, conn)
    finally:
        conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Example Usage

# COMMAND ----------

query = """
SELECT * FROM lakemeter.calculate_line_item_costs(
    'ALL_PURPOSE'::VARCHAR,                  -- workload_type
    'AWS'::VARCHAR,
    'us-east-1'::VARCHAR,
    'PREMIUM'::VARCHAR,
    FALSE::BOOLEAN,                          -- Classic
    TRUE::BOOLEAN,                           -- Photon
    NULL::VARCHAR,
    'i3.xlarge'::VARCHAR,
    'i3.2xlarge'::VARCHAR,
    4::INT,
    'on_demand'::VARCHAR,
    'on_demand'::VARCHAR,
    1::INT,                                  -- 1 "run" per day
    720::INT,                                -- 12 hours × 60 min
    30::INT,
    NULL::INT,                               -- Auto-calc: 1 × 12 × 30 = 360 hours/month
    NULL::VARCHAR, NULL::VARCHAR, NULL::VARCHAR, 1::INT, 'NA'::VARCHAR,
    NULL::VARCHAR, 0::DECIMAL, NULL::VARCHAR, NULL::VARCHAR, NULL::VARCHAR,
    'global'::VARCHAR, 'all'::VARCHAR, 'input_token'::VARCHAR,
    0::BIGINT, 0::INT, 1::INT,
    'NA'::VARCHAR, 'NA'::VARCHAR, 'NA'::VARCHAR
);
"""

result = execute_query(query)
display(result)

