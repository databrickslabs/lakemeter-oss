# Databricks notebook source
# MAGIC %md
# MAGIC # 📘 Usage Guide: DLT Classic
# MAGIC
# MAGIC **Workload Type:** `DLT`  
# MAGIC **Compute Mode:** Classic
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
# MAGIC   Product Type = DLT_{EDITION}_COMPUTE or DLT_{EDITION}_COMPUTE_(PHOTON)
# MAGIC ```
# MAGIC
# MAGIC **Key Components:**
# MAGIC - **DLT Edition:** `CORE`, `PRO`, or `ADVANCED` - affects product type and DBU pricing
# MAGIC - **Photon multiplier:** **OPTIONAL for Classic** - set `photon_enabled = TRUE` or `FALSE`
# MAGIC - **DBU rates:** Queried from `sync_ref_instance_dbu_rates`
# MAGIC - **VM costs:** Queried from `sync_pricing_vm_costs`
# MAGIC - **Product type:** Based on edition (e.g., `DLT_CORE_COMPUTE`, `DLT_PRO_COMPUTE_(PHOTON)`)
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
# MAGIC **Use Case:** Delta Live Tables (DLT) pipeline on classic compute
# MAGIC
# MAGIC **Scenario Details:**
# MAGIC - DLT pipeline for incremental data processing (ETL/ELT)
# MAGIC - Classic compute with fixed cluster configuration
# MAGIC - Advanced edition (includes expectations, SLAs, deep clone)
# MAGIC - Photon enabled for better performance
# MAGIC - Runs 4 times per day, each run takes 120 minutes
# MAGIC - On-demand VM pricing
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 📊 Parameter Values Explained
# MAGIC
# MAGIC | Parameter | Value | What It Represents |
# MAGIC |-----------|-------|-------------------|
# MAGIC | **Core Identifiers** | | |
# MAGIC | `p_workload_type` | `'DLT'` | Delta Live Tables workload |
# MAGIC | `p_cloud` | `'AWS'` | Amazon Web Services |
# MAGIC | `p_region` | `'us-east-1'` | US East region |
# MAGIC | `p_tier` | `'PREMIUM'` | Databricks pricing tier |
# MAGIC | **Compute Configuration** | | |
# MAGIC | `p_serverless_enabled` | `FALSE` | Classic compute (not serverless) |
# MAGIC | `p_photon_enabled` | `TRUE` | Photon enabled (optional for classic) |
# MAGIC | `p_dlt_edition` | `'advanced'` | **Advanced edition** (vs 'core') |
# MAGIC | `p_driver_node_type` | `'i3.xlarge'` | Driver instance type |
# MAGIC | `p_worker_node_type` | `'i3.2xlarge'` | Worker instance type |
# MAGIC | `p_num_workers` | `4` | 4 worker nodes |
# MAGIC | **VM Pricing** | | |
# MAGIC | `p_driver_pricing_tier` | `'on_demand'` | Driver on-demand pricing |
# MAGIC | `p_worker_pricing_tier` | `'on_demand'` | Workers on-demand pricing |
# MAGIC | **Usage Pattern** | | |
# MAGIC | `p_runs_per_day` | `4` | Pipeline runs 4 times daily |
# MAGIC | `p_avg_runtime_minutes` | `120` | Each run takes 2 hours (120 min) |
# MAGIC | `p_days_per_month` | `30` | 30 days per month |
# MAGIC | `p_hours_per_month` | `NULL` | Auto-calculated: 4 × 2 × 30 = 240 hours |
# MAGIC | **All Other Parameters** | `NULL` or defaults | Not applicable for DLT Classic |
# MAGIC
# MAGIC **DLT Editions:**
# MAGIC - **Core:** Basic DLT features
# MAGIC - **Advanced:** Expectations, SLAs, deep clone, enhanced monitoring
# MAGIC
# MAGIC **Key Points for AI Agents:**
# MAGIC 1. **DLT = Delta Live Tables** for streaming/batch ETL
# MAGIC 2. **Has both DBU and VM costs** (classic compute)
# MAGIC 3. **Edition matters** - advanced has higher DBU rates
# MAGIC 4. **Photon OPTIONAL** for classic DLT
# MAGIC 5. **DLT has special product types** for pricing lookup
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

query = """
SELECT * FROM lakemeter.calculate_line_item_costs(
    'DLT'::VARCHAR,
    'AWS'::VARCHAR,
    'us-east-1'::VARCHAR,
    'PREMIUM'::VARCHAR,
    FALSE::BOOLEAN,                          -- serverless_enabled (Classic)
    TRUE::BOOLEAN,                           -- photon_enabled (optional)
    'CORE'::VARCHAR,                         -- dlt_edition
    'i3.xlarge'::VARCHAR,
    'i3.2xlarge'::VARCHAR,
    4::INT,
    'on_demand'::VARCHAR,
    'on_demand'::VARCHAR,
    8::INT,
    60::INT,
    30::INT,
    NULL::INT,
    NULL::VARCHAR,
    NULL::VARCHAR, NULL::VARCHAR, 1::INT, 'NA'::VARCHAR,
    NULL::VARCHAR, 0::DECIMAL, NULL::VARCHAR,
    NULL::VARCHAR, NULL::VARCHAR,
    'global'::VARCHAR, 'all'::VARCHAR, 'input_token'::VARCHAR,
    0::BIGINT, 0::INT, 1::INT,
    'NA'::VARCHAR, 'NA'::VARCHAR, 'NA'::VARCHAR
);
"""

result = execute_query(query)
display(result)
