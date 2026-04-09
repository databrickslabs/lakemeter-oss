# Databricks notebook source
# MAGIC %md
# MAGIC # 📘 Usage Guide: FMAPI Proprietary
# MAGIC
# MAGIC **Workload Type:** `FMAPI_PROPRIETARY`  
# MAGIC **Pricing Model:** Pay-per-token (models served by external providers via Databricks)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 🧮 Cost Formula
# MAGIC
# MAGIC ```
# MAGIC Total Cost = DBU Cost (NO VM costs)
# MAGIC
# MAGIC   DBU Cost = (input_tokens / input_divisor × input_dbu_rate +
# MAGIC               output_tokens / output_divisor × output_dbu_rate)
# MAGIC              × DBU Price
# MAGIC   
# MAGIC   Product Type = varies by provider and pricing tier
# MAGIC ```
# MAGIC
# MAGIC **Key Components:**
# MAGIC - **NO VM costs** - API-based pricing
# MAGIC - **Providers:** `openai`, `anthropic`, `google`
# MAGIC - **Models:** Queried from `sync_product_fmapi_proprietary` (e.g., `gpt-4o`, `claude-sonnet-4-1`, `gemini-2-5-pro`)
# MAGIC - **Endpoint type:** `global` or `in_geo`
# MAGIC - **Context length:** `all`, `short`, or `long`
# MAGIC - **Rate types:** `input_token`, `output_token`, `cache_read`, `cache_write`, `batch_inference`
# MAGIC - **DBU rates:** From `sync_product_fmapi_proprietary` (then multiply by DBU price)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## ✅ How to Validate Your Inputs
# MAGIC
# MAGIC **⚠️ IMPORTANT:** Not every model supports all combinations of `endpoint_type` and `context_length`!
# MAGIC
# MAGIC **Validation Table:** `lakemeter.sync_product_fmapi_proprietary`
# MAGIC
# MAGIC **Steps to validate:**
# MAGIC 1. Choose a provider and model
# MAGIC 2. Query `sync_product_fmapi_proprietary` to see which `endpoint_type` and `context_length` combinations exist
# MAGIC 3. Only use combinations that return results
# MAGIC
# MAGIC **Example validation query:**
# MAGIC ```sql
# MAGIC SELECT DISTINCT 
# MAGIC     endpoint_type, 
# MAGIC     context_length,
# MAGIC     COUNT(DISTINCT rate_type) as num_rate_types
# MAGIC FROM lakemeter.sync_product_fmapi_proprietary
# MAGIC WHERE UPPER(provider) = 'ANTHROPIC'
# MAGIC   AND UPPER(model) = 'CLAUDE-SONNET-4-1'
# MAGIC GROUP BY endpoint_type, context_length
# MAGIC ORDER BY endpoint_type, context_length;
# MAGIC ```
# MAGIC
# MAGIC If this query returns rows → Valid combination ✅  
# MAGIC If this query returns 0 rows → Invalid combination ❌ (will result in $0 cost)

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
# MAGIC ---
# MAGIC
# MAGIC ## 📋 Example Scenario
# MAGIC
# MAGIC **Use Case:** Proprietary LLM (Claude) served by Databricks
# MAGIC
# MAGIC **Scenario Details:**
# MAGIC - Using Anthropic Claude Sonnet 4.1 served by Databricks
# MAGIC - In-region endpoint (`in_geo`) for lower latency
# MAGIC - Short context window (pricing varies by context length)
# MAGIC - Pay-per-token pricing model
# MAGIC - Processing 2 million INPUT tokens per month
# MAGIC
# MAGIC **IMPORTANT - "One Line = One Rate Type" Design:**
# MAGIC - This example shows **INPUT tokens only** (one line item)
# MAGIC - **OUTPUT tokens would be a SEPARATE line item** with `p_fmapi_rate_type='output_token'`
# MAGIC - Each rate type (input_token, output_token, cache_read, cache_write, batch_inference) gets its own line
# MAGIC - Different rate types have different DBU rates in the pricing table
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 📊 Parameter Values Explained
# MAGIC
# MAGIC | Parameter | Value | What It Represents |
# MAGIC |-----------|-------|-------------------|
# MAGIC | **Core Identifiers** | | |
# MAGIC | `p_workload_type` | `'FMAPI_PROPRIETARY'` | Proprietary model served by Databricks |
# MAGIC | `p_cloud` | `'AWS'` | Cloud where API calls are made |
# MAGIC | `p_region` | `'us-east-1'` | Region for DBU pricing lookup |
# MAGIC | `p_tier` | `'PREMIUM'` | Databricks pricing tier |
# MAGIC | **FMAPI Specific** | | |
# MAGIC | `p_fmapi_provider` | `'anthropic'` | Model provider (anthropic, openai, gemini) |
# MAGIC | `p_fmapi_model` | `'claude-sonnet-4-1'` | Specific model name (from pricing table) |
# MAGIC | `p_fmapi_endpoint_type` | `'in_geo'` | In-region endpoint (vs 'global' for cross-region) |
# MAGIC | `p_fmapi_context_length` | `'short'` | Context window size (short/long/all - pricing varies) |
# MAGIC | `p_fmapi_rate_type` | `'input_token'` | **CRITICAL:** Rate type for THIS line item |
# MAGIC | `p_fmapi_quantity` | `2000000` | 2 million INPUT tokens for this month |
# MAGIC | **All Other Parameters** | `NULL` or defaults | Not applicable for FMAPI workload |
# MAGIC
# MAGIC **Key Points for AI Agents:**
# MAGIC 1. **One line item = one rate type** (e.g., input_token OR output_token, not both)
# MAGIC 2. If you have both input and output tokens, create **TWO separate line items**
# MAGIC 3. Validate model exists: Check `lakemeter.sync_product_fmapi_proprietary`
# MAGIC 4. Rate types available: `input_token`, `output_token`, `cache_read`, `cache_write`, `batch_inference`
# MAGIC 5. Different rate types have different DBU rates (check pricing table)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 💻 Function Call (Input Tokens Only)

# COMMAND ----------

query = """
SELECT * FROM lakemeter.calculate_line_item_costs(
    'FMAPI_PROPRIETARY'::VARCHAR,            -- p_workload_type
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
    'claude-sonnet-4-1'::VARCHAR,             -- p_fmapi_model
    'anthropic'::VARCHAR,                     -- p_fmapi_provider
    'in_geo'::VARCHAR,                        -- p_fmapi_endpoint_type
    'short'::VARCHAR,                         -- p_fmapi_context_length
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
