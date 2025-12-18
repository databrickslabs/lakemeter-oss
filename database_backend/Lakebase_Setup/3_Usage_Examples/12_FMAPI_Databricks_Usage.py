# Databricks notebook source
# MAGIC %md
# MAGIC # 📘 Usage Guide: FMAPI Databricks
# MAGIC
# MAGIC **Workload Type:** `FMAPI_DATABRICKS`  
# MAGIC **Pricing Model:** Pay-per-token OR Provisioned throughput
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 🧮 Cost Formula
# MAGIC
# MAGIC ```
# MAGIC Total Cost = DBU Cost (NO VM costs)
# MAGIC
# MAGIC Pay-per-token:
# MAGIC   DBU Cost = (input_tokens / input_divisor × input_dbu_rate +
# MAGIC               output_tokens / output_divisor × output_dbu_rate)
# MAGIC              × DBU Price
# MAGIC
# MAGIC Provisioned throughput (hourly):
# MAGIC   DBU Cost = dbu_rate × hours_per_month × DBU Price
# MAGIC   
# MAGIC   Product Type = varies by model and pricing tier
# MAGIC ```
# MAGIC
# MAGIC **Key Components:**
# MAGIC - **NO VM costs** - serverless API-based pricing
# MAGIC - **Models:** Queried from `sync_product_fmapi_databricks` (e.g., `llama-3-3-70b`, `llama-3-1-8b`)
# MAGIC - **Token-based:** Separate rates for input/output tokens with divisors
# MAGIC - **Provisioned:** Hourly rates for `provisioned_entry` or `provisioned_scaling`
# MAGIC - **DBU rates:** From `sync_product_fmapi_databricks` (then multiply by DBU price like $0.07)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## ✅ How to Validate Your Inputs
# MAGIC
# MAGIC **Validation Table:** `lakemeter.sync_product_fmapi_databricks`
# MAGIC
# MAGIC **What to validate:**
# MAGIC - Cloud + Model combination exists
# MAGIC - Check if model supports pay_per_token (`is_hourly = false`)
# MAGIC - Check if model supports provisioned throughput (`is_hourly = true`)
# MAGIC
# MAGIC **Example validation query:**
# MAGIC ```sql
# MAGIC SELECT DISTINCT 
# MAGIC     model,
# MAGIC     is_hourly,
# MAGIC     COUNT(DISTINCT rate_type) as num_rate_types
# MAGIC FROM lakemeter.sync_product_fmapi_databricks
# MAGIC WHERE UPPER(cloud) = 'AWS'
# MAGIC   AND UPPER(model) = 'LLAMA-3-3-70B'
# MAGIC GROUP BY model, is_hourly;
# MAGIC ```
# MAGIC
# MAGIC If this query returns rows → Valid combination ✅  
# MAGIC If this query returns 0 rows → Invalid combination ❌ (will result in $0 cost)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 📋 Example Scenario
# MAGIC
# MAGIC **Use Case:** Databricks-hosted Foundation Model API (Llama)
# MAGIC
# MAGIC **Scenario Details:**
# MAGIC - Using Databricks-hosted Llama 3.3 70B model
# MAGIC - Pay-per-token pricing model
# MAGIC - Processing 2 million INPUT tokens per month
# MAGIC - Model hosted and managed by Databricks (not via AI Gateway)
# MAGIC
# MAGIC **IMPORTANT - "One Line = One Rate Type" Design:**
# MAGIC - This example shows **INPUT tokens only** (one line item)
# MAGIC - **OUTPUT tokens would be a SEPARATE line item** with `p_fmapi_rate_type='output_token'`
# MAGIC - Each rate type gets its own line item with its own quantity
# MAGIC - Provisioned throughput (hourly) would use `p_fmapi_rate_type='batch_inference'`
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 📊 Parameter Values Explained
# MAGIC
# MAGIC | Parameter | Value | What It Represents |
# MAGIC |-----------|-------|-------------------|
# MAGIC | **Core Identifiers** | | |
# MAGIC | `p_workload_type` | `'FMAPI_DATABRICKS'` | Databricks-hosted FMAPI model |
# MAGIC | `p_cloud` | `'AWS'` | Cloud where model is hosted |
# MAGIC | `p_region` | `'us-east-1'` | Region for DBU pricing lookup |
# MAGIC | `p_tier` | `'PREMIUM'` | Databricks pricing tier |
# MAGIC | **FMAPI Specific** | | |
# MAGIC | `p_fmapi_model` | `'llama-3-3-70b'` | Llama 3.3 70B (from pricing table) |
# MAGIC | `p_fmapi_provider` | `NULL` | N/A for Databricks-hosted models |
# MAGIC | `p_fmapi_endpoint_type` | `'global'` | Default for Databricks models |
# MAGIC | `p_fmapi_context_length` | `'all'` | Default context length |
# MAGIC | `p_fmapi_rate_type` | `'input_token'` | **CRITICAL:** This line is for INPUT tokens only |
# MAGIC | `p_fmapi_quantity` | `2000000` | 2 million INPUT tokens |
# MAGIC | **All Other Parameters** | `NULL` or defaults | Not applicable for FMAPI workload |
# MAGIC
# MAGIC **Key Points for AI Agents:**
# MAGIC 1. **One line item = one rate type** (input OR output, not both)
# MAGIC 2. Create **separate line items** for input_token and output_token
# MAGIC 3. Databricks models: `p_fmapi_provider` = NULL
# MAGIC 4. Proprietary models: `p_fmapi_provider` = 'anthropic'/'openai'/'gemini'
# MAGIC 5. Validate model in `lakemeter.sync_product_fmapi_databricks`
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 💻 Function Call (Input Tokens Only)

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
    'FMAPI_DATABRICKS'::VARCHAR,             -- p_workload_type
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
    1::INT,                                   -- p_runs_per_day
    60::INT,                                  -- p_avg_runtime_minutes
    30::INT,                                  -- p_days_per_month
    NULL::INT,                                -- p_hours_per_month
    'standard'::VARCHAR,                      -- p_serverless_mode
    NULL::VARCHAR,                            -- p_dbsql_warehouse_type
    NULL::VARCHAR,                            -- p_dbsql_warehouse_size
    1::INT,                                   -- p_dbsql_num_clusters
    'on_demand'::VARCHAR,                     -- p_dbsql_vm_pricing_tier
    NULL::VARCHAR,                            -- p_vector_search_mode
    0::DECIMAL,                               -- p_vector_search_capacity_millions
    NULL::VARCHAR,                            -- p_model_serving_gpu_type
    'llama-3-3-70b'::VARCHAR,                 -- p_fmapi_model
    NULL::VARCHAR,                            -- p_fmapi_provider (N/A for Databricks)
    'global'::VARCHAR,                        -- p_fmapi_endpoint_type
    'all'::VARCHAR,                           -- p_fmapi_context_length
    'input_token'::VARCHAR,                   -- p_fmapi_rate_type
    2000000::BIGINT,                          -- p_fmapi_quantity (input tokens)
    0::INT,                                   -- p_lakebase_cu
    1::INT,                                   -- p_lakebase_ha_nodes
    'NA'::VARCHAR,                            -- p_driver_payment_option
    'NA'::VARCHAR,                            -- p_worker_payment_option
    'NA'::VARCHAR                             -- p_dbsql_vm_payment_option
);
"""

result = execute_query(query)
display(result)
