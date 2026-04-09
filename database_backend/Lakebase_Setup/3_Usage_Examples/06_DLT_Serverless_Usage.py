# Databricks notebook source
# MAGIC %md
# MAGIC # 📘 Usage Guide: DLT Serverless
# MAGIC
# MAGIC **Workload Type:** `DLT`  
# MAGIC **Compute Mode:** Serverless
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 🧮 Cost Formula
# MAGIC
# MAGIC ```
# MAGIC Total Cost = DBU Cost (NO VM costs for serverless)
# MAGIC
# MAGIC WHERE:
# MAGIC   DBU Cost = (Driver DBU/hour + Worker DBU/hour × num_workers)
# MAGIC              × Serverless Rate (from sync_product_serverless_rates)
# MAGIC              × Serverless Mode Multiplier (1x standard, 2x performance)
# MAGIC              × Photon Multiplier (from sync_ref_dbu_multipliers, always enabled)
# MAGIC              × hours_per_month
# MAGIC              × DBU Price ($/DBU)
# MAGIC
# MAGIC   Product Type = JOBS_SERVERLESS_COMPUTE (DLT Serverless uses same as JOBS Serverless)
# MAGIC ```
# MAGIC
# MAGIC **Key Components:**
# MAGIC - **NO VM costs** - serverless is DBU-only pricing
# MAGIC - **Photon multiplier:** **MANDATORY for Serverless** - `photon_enabled` must be `TRUE`
# MAGIC - **DLT Edition:** Still specified but pricing uses JOBS_SERVERLESS_COMPUTE product type
# MAGIC - **Mode multiplier:** 1x for standard, 2x for performance
# MAGIC - **STANDARD tier:** Not supported (returns $0)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## ✅ How to Validate Your Inputs
# MAGIC
# MAGIC **Validation Table:** `lakemeter.sync_ref_instance_dbu_rates`
# MAGIC
# MAGIC **What to validate:**
# MAGIC - Instance Type has DBU rates defined
# MAGIC
# MAGIC **Validation query:**
# MAGIC ```sql
# MAGIC SELECT * FROM lakemeter.sync_ref_instance_dbu_rates
# MAGIC WHERE UPPER(cloud) = UPPER('AWS')
# MAGIC   AND UPPER(instance_type) = UPPER('i3.xlarge');
# MAGIC ```
# MAGIC
# MAGIC If this query returns rows → Valid combination ✅  
# MAGIC If this query returns 0 rows → Invalid combination ❌ (will result in $0 cost)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 📋 Example Scenario
# MAGIC
# MAGIC **Use Case:** Delta Live Tables (DLT) pipeline on serverless compute
# MAGIC
# MAGIC **Scenario Details:**
# MAGIC - DLT pipeline with serverless compute (auto-scaling)
# MAGIC - **NO edition concept** for serverless (editions are Classic-only)
# MAGIC - Photon ALWAYS enabled (mandatory for serverless)
# MAGIC - Instance types for DBU calculation only (NO actual VM costs)
# MAGIC - Standard serverless mode (not performance mode with 2x multiplier)
# MAGIC - Runs 4 times per day, each run takes 120 minutes
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
# MAGIC | `p_serverless_enabled` | `TRUE` | **Serverless compute mode** |
# MAGIC | `p_photon_enabled` | `TRUE` | **Photon MANDATORY for serverless** |
# MAGIC | `p_dlt_edition` | `NULL` | **N/A - editions are Classic-only** |
# MAGIC | `p_driver_node_type` | `'i3.xlarge'` | For DBU calc ONLY (no VM cost) |
# MAGIC | `p_worker_node_type` | `'i3.2xlarge'` | For DBU calc ONLY (no VM cost) |
# MAGIC | `p_num_workers` | `4` | For DBU calc ONLY |
# MAGIC | `p_driver_pricing_tier` | `'on_demand'` | Ignored (no VM costs) |
# MAGIC | `p_worker_pricing_tier` | `'on_demand'` | Ignored (no VM costs) |
# MAGIC | **Serverless Specific** | | |
# MAGIC | `p_serverless_mode` | `'standard'` | Standard mode (vs 'performance' 2x) |
# MAGIC | **Usage Pattern** | | |
# MAGIC | `p_runs_per_day` | `4` | Pipeline runs 4 times daily |
# MAGIC | `p_avg_runtime_minutes` | `120` | Each run takes 2 hours (120 min) |
# MAGIC | `p_days_per_month` | `30` | 30 days per month |
# MAGIC | `p_hours_per_month` | `NULL` | Auto-calculated: 4 × 2 × 30 = 240 hours |
# MAGIC | **All Other Parameters** | `NULL` or defaults | Not applicable for DLT Serverless |
# MAGIC
# MAGIC **Key Points for AI Agents:**
# MAGIC 1. **NO VM costs** for serverless - only DBU costs
# MAGIC 2. **Photon MANDATORY** for serverless DLT
# MAGIC 3. **NO editions** for DLT Serverless - editions (Core/Advanced) are **Classic-only**
# MAGIC 4. **Instance types** used ONLY for base DBU rate calculation
# MAGIC 5. **DLT Serverless** uses `JOBS_SERVERLESS_COMPUTE` product type
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
    TRUE::BOOLEAN,                           -- serverless_enabled
    TRUE::BOOLEAN,                           -- photon_enabled (mandatory)
    NULL::VARCHAR,                           -- dlt_edition (N/A for serverless)
    'i3.xlarge'::VARCHAR,                    -- for DBU calc
    'i3.2xlarge'::VARCHAR,                   -- for DBU calc
    4::INT,
    'on_demand'::VARCHAR,                    -- ignored
    'on_demand'::VARCHAR,                    -- ignored
    8::INT,                                  -- p_runs_per_day
    60::INT,                                 -- p_avg_runtime_minutes
    30::INT,                                 -- p_days_per_month
    NULL::INT,                               -- p_hours_per_month (auto)
    'standard'::VARCHAR,                     -- p_serverless_mode
    NULL::VARCHAR,                           -- p_dbsql_warehouse_type
    NULL::VARCHAR,                           -- p_dbsql_warehouse_size
    1::INT,                                  -- p_dbsql_num_clusters
    'on_demand'::VARCHAR,                    -- p_dbsql_vm_pricing_tier
    NULL::VARCHAR,                           -- p_vector_search_mode
    0::DECIMAL,                              -- p_vector_search_capacity_millions
    NULL::VARCHAR,                           -- p_model_serving_gpu_type
    NULL::VARCHAR,                           -- p_fmapi_model
    NULL::VARCHAR,                           -- p_fmapi_provider
    'global'::VARCHAR,                       -- p_fmapi_endpoint_type
    'all'::VARCHAR,                          -- p_fmapi_context_length
    'input_token'::VARCHAR,                  -- p_fmapi_rate_type
    0::BIGINT,                               -- p_fmapi_quantity
    0::INT,                                  -- p_lakebase_cu
    1::INT,                                  -- p_lakebase_ha_nodes
    'NA'::VARCHAR,                           -- p_driver_payment_option
    'NA'::VARCHAR,                           -- p_worker_payment_option
    'NA'::VARCHAR                            -- p_dbsql_vm_payment_option
);
"""

result = execute_query(query)
display(result)
