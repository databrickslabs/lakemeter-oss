# Databricks notebook source
# MAGIC %md
# MAGIC # 📘 Usage Guide: Model Serving
# MAGIC
# MAGIC **Workload Type:** `MODEL_SERVING`  
# MAGIC **Compute Mode:** Serverless
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 🧮 Cost Formula
# MAGIC
# MAGIC ```
# MAGIC Total Cost = DBU Cost (NO VM costs)
# MAGIC
# MAGIC WHERE:
# MAGIC   DBU Cost = DBU rate (from sync_product_model_serving)
# MAGIC              × hours_per_month
# MAGIC              × DBU Price (from sync_pricing_dbu_rates)
# MAGIC   
# MAGIC   hours_per_month = Use p_hours_per_month to specify runtime
# MAGIC                     (can be 24/7 at 720 hours, or less for on-demand/scheduled endpoints)
# MAGIC   
# MAGIC   Product Type = SERVERLESS_REAL_TIME_INFERENCE
# MAGIC ```
# MAGIC
# MAGIC **Key Components:**
# MAGIC - **NO VM costs** - serverless DBU-only pricing
# MAGIC - **GPU type:** Cloud-specific GPU types (queried from `sync_product_serverless_rates`)
# MAGIC   - Pass via `p_model_serving_gpu_type` (e.g., `'gpu_medium_a10g_1x'` for AWS)
# MAGIC - **Runtime:** Use `p_hours_per_month` to specify hours (e.g., 720 for 24/7, or less for on-demand)
# MAGIC - **DBU rates:** Queried from `sync_product_serverless_rates` by cloud, product='model_serving', and GPU type
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## ✅ How to Validate Your Inputs
# MAGIC
# MAGIC **Validation Table:** `lakemeter.sync_product_serverless_rates`
# MAGIC
# MAGIC **What to validate:**
# MAGIC - Cloud + GPU Type combination exists
# MAGIC - GPU types are cloud-specific (e.g., `gpu_medium_a10g_1x` for AWS)
# MAGIC
# MAGIC **Example validation query:**
# MAGIC ```sql
# MAGIC SELECT * FROM lakemeter.sync_product_serverless_rates
# MAGIC WHERE UPPER(cloud) = UPPER('AWS')
# MAGIC   AND UPPER(size_or_model) = UPPER('gpu_medium_a10g_1x')
# MAGIC   AND UPPER(product) = UPPER('model_serving');
# MAGIC ```
# MAGIC
# MAGIC If this query returns rows → Valid combination ✅  
# MAGIC If this query returns 0 rows → Invalid combination ❌ (will result in $0 cost)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 📋 Example Scenario
# MAGIC
# MAGIC **Use Case:** Real-time ML model inference endpoint with GPU acceleration
# MAGIC
# MAGIC **Scenario Details:**
# MAGIC - Serving a machine learning model on AWS A10G GPU
# MAGIC - GPU type: `gpu_medium_a10g_1x` (cloud-specific, from pricing table)
# MAGIC - Runs 24/7 for continuous real-time inference
# MAGIC - NO VM costs - serverless DBU-only pricing
# MAGIC - GPU types are cloud-specific (check pricing table for valid combinations)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 📊 Parameter Values Explained
# MAGIC
# MAGIC | Parameter | Value | What It Represents |
# MAGIC |-----------|-------|-------------------|
# MAGIC | **Core Identifiers** | | |
# MAGIC | `p_workload_type` | `'MODEL_SERVING'` | Model Serving workload type |
# MAGIC | `p_cloud` | `'AWS'` | Amazon Web Services |
# MAGIC | `p_region` | `'us-east-1'` | US East (N. Virginia) region |
# MAGIC | `p_tier` | `'PREMIUM'` | Databricks pricing tier |
# MAGIC | **Model Serving Specific** | | |
# MAGIC | `p_model_serving_gpu_type` | `'gpu_medium_a10g_1x'` | AWS A10G GPU type (cloud-specific from pricing table) |
# MAGIC | `p_hours_per_month` | `720` | 24/7 operation (24 hours × 30 days = 720) |
# MAGIC | **All Other Parameters** | `NULL` or defaults | Not applicable for Model Serving workload |
# MAGIC
# MAGIC **Key Points:**
# MAGIC - GPU types are **cloud-specific** (e.g., `gpu_medium_a10g_1x` for AWS)
# MAGIC - Validate GPU type exists in `lakemeter.sync_product_serverless_rates` for your cloud
# MAGIC - NO VM costs - this is pure DBU-based pricing
# MAGIC - Use `p_hours_per_month` to specify actual runtime (720 for 24/7, or less for on-demand)
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
    'MODEL_SERVING'::VARCHAR,                 -- p_workload_type
    'AWS'::VARCHAR,                           -- p_cloud
    'us-east-1'::VARCHAR,                     -- p_region
    'PREMIUM'::VARCHAR,                       -- p_tier
    FALSE::BOOLEAN,                           -- p_serverless_enabled
    FALSE::BOOLEAN,                           -- p_photon_enabled
    NULL::VARCHAR,                            -- p_dlt_edition
    NULL::VARCHAR,                            -- p_driver_node_type
    NULL::VARCHAR,                            -- p_worker_node_type
    0::INT,                                   -- p_num_workers
    'on_demand'::VARCHAR,                     -- p_driver_pricing_tier
    'on_demand'::VARCHAR,                     -- p_worker_pricing_tier
    0::INT,                                   -- p_runs_per_day (not used for Model Serving)
    0::INT,                                   -- p_avg_runtime_minutes (not used for Model Serving)
    30::INT,                                  -- p_days_per_month (not used for Model Serving)
    720::INT,                                 -- p_hours_per_month (24/7 = 720 hours)
    'standard'::VARCHAR,                      -- p_serverless_mode
    NULL::VARCHAR,                            -- p_dbsql_warehouse_type
    NULL::VARCHAR,                            -- p_dbsql_warehouse_size
    1::INT,                                   -- p_dbsql_num_clusters
    'on_demand'::VARCHAR,                     -- p_dbsql_vm_pricing_tier
    NULL::VARCHAR,                            -- p_vector_search_mode
    0::DECIMAL,                               -- p_vector_search_capacity_millions
    'gpu_medium_a10g_1x'::VARCHAR,            -- p_model_serving_gpu_type
    NULL::VARCHAR,                            -- p_fmapi_model
    NULL::VARCHAR,                            -- p_fmapi_provider
    'global'::VARCHAR,                        -- p_fmapi_endpoint_type
    'all'::VARCHAR,                           -- p_fmapi_context_length
    'input_token'::VARCHAR,                   -- p_fmapi_rate_type
    0::BIGINT,                                -- p_fmapi_quantity
    0::INT,                                   -- p_lakebase_cu
    1::INT,                                   -- p_lakebase_ha_nodes
    'NA'::VARCHAR,                            -- p_driver_payment_option
    'NA'::VARCHAR,                            -- p_worker_payment_option
    'NA'::VARCHAR                             -- p_dbsql_vm_payment_option
);
"""

result = execute_query(query)
display(result)
