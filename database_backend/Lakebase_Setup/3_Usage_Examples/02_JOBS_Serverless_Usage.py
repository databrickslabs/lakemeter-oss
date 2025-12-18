# Databricks notebook source
# MAGIC %md
# MAGIC # 📘 Usage Guide: JOBS Serverless
# MAGIC
# MAGIC **Workload Type:** `JOBS`  
# MAGIC **Compute Mode:** Serverless (Databricks-managed)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 🧮 Cost Formula
# MAGIC
# MAGIC ```
# MAGIC Total Cost = DBU Cost (NO VM COSTS for serverless)
# MAGIC
# MAGIC WHERE:
# MAGIC   DBU Cost = (Driver DBU/hour + Worker DBU/hour × num_workers)
# MAGIC              × Serverless Rate (from sync_product_serverless_rates)
# MAGIC              × Serverless Mode Multiplier (1x standard, 2x performance)
# MAGIC              × Photon Multiplier (from sync_ref_dbu_multipliers, always enabled)
# MAGIC              × hours_per_month
# MAGIC              × DBU Price ($/DBU from sync_pricing_dbu_rates)
# MAGIC
# MAGIC   hours_per_month = runs_per_day × (avg_runtime_minutes / 60) × days_per_month
# MAGIC ```
# MAGIC
# MAGIC **Key Components:**
# MAGIC - **NO VM costs** - serverless is DBU-only pricing
# MAGIC - **Base DBU:** Queried from `sync_ref_instance_dbu_rates` (instance types used for sizing)
# MAGIC - **Serverless rate:** Queried from `sync_product_serverless_rates` by cloud and instance type
# MAGIC - **Photon multiplier:** **MANDATORY for Serverless** - `photon_enabled` must be `TRUE`, multiplier queried from `sync_ref_dbu_multipliers`
# MAGIC - **Mode multiplier:** 1x for standard, 2x for performance
# MAGIC - **DBU price:** Queried from `sync_pricing_dbu_rates`
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
# MAGIC ## 📋 Key Parameters for Jobs Serverless
# MAGIC
# MAGIC | Parameter | Value | Notes |
# MAGIC |-----------|-------|-------|
# MAGIC | `p_workload_type` | `'JOBS'` | Must be JOBS |
# MAGIC | `p_serverless_enabled` | `TRUE` | **Required for serverless** |
# MAGIC | `p_photon_enabled` | `TRUE` | **Always TRUE** for serverless |
# MAGIC | `p_serverless_mode` | `'standard'` or `'performance'` | Performance = 2x cost, 2x speed |
# MAGIC | `p_driver_node_type` | e.g., `'i3.xlarge'` | Used for DBU calculation |
# MAGIC | `p_worker_node_type` | e.g., `'i3.2xlarge'` | Used for DBU calculation |
# MAGIC | `p_num_workers` | e.g., `4` | Number of workers |
# MAGIC | `p_driver_pricing_tier` | `'on_demand'` | **Ignored** (no VM costs) |
# MAGIC | `p_worker_pricing_tier` | `'on_demand'` | **Ignored** (no VM costs) |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 💡 Example Usage

# COMMAND ----------

# Load Lakebase config
%run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2

def get_connection():
    return psycopg2.connect(
        host=LAKEBASE_HOST,
        port=LAKEBASE_PORT,
        database=LAKEBASE_DB,
        user=LAKEBASE_USER,
        password=LAKEBASE_PASSWORD
    )

def execute_query(query, params=None, fetch=True):
    import pandas as pd
    conn = get_connection()
    try:
        if fetch:
            return pd.read_sql(query, conn, params=params)
        else:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            cursor.close()
    finally:
        conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📋 Example Scenario
# MAGIC
# MAGIC **Use Case:** Serverless ETL job on AWS in PREMIUM tier
# MAGIC
# MAGIC **Scenario Details:**
# MAGIC - Job runs 8 times per day, each run takes 60 minutes
# MAGIC - Uses serverless compute (auto-scaling, no fixed cluster)
# MAGIC - Instance types specified only for DBU calculation (NO actual VM costs)
# MAGIC - Photon is ALWAYS enabled for serverless (mandatory)
# MAGIC - Standard serverless mode (not performance mode with 2x multiplier)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 📊 Parameter Values Explained
# MAGIC
# MAGIC | Parameter | Value | What It Represents |
# MAGIC |-----------|-------|-------------------|
# MAGIC | **Core Identifiers** | | |
# MAGIC | `p_workload_type` | `'JOBS'` | Jobs workload (batch/scheduled processing) |
# MAGIC | `p_cloud` | `'AWS'` | Amazon Web Services |
# MAGIC | `p_region` | `'us-east-1'` | US East (N. Virginia) region |
# MAGIC | `p_tier` | `'PREMIUM'` | Databricks pricing tier |
# MAGIC | **Compute Configuration** | | |
# MAGIC | `p_serverless_enabled` | `TRUE` | **Serverless compute mode** |
# MAGIC | `p_photon_enabled` | `TRUE` | **Photon MANDATORY for serverless** (not optional) |
# MAGIC | `p_driver_node_type` | `'i3.xlarge'` | Used for DBU calc ONLY (no actual VM) |
# MAGIC | `p_worker_node_type` | `'i3.2xlarge'` | Used for DBU calc ONLY (no actual VM) |
# MAGIC | `p_num_workers` | `4` | Used for DBU calc ONLY |
# MAGIC | `p_driver_pricing_tier` | `'on_demand'` | Ignored for serverless (no VM costs) |
# MAGIC | `p_worker_pricing_tier` | `'on_demand'` | Ignored for serverless (no VM costs) |
# MAGIC | **Serverless Specific** | | |
# MAGIC | `p_serverless_mode` | `'standard'` | Standard mode (vs 'performance' with 2x multiplier) |
# MAGIC | **Usage Pattern** | | |
# MAGIC | `p_runs_per_day` | `8` | Job executes 8 times daily |
# MAGIC | `p_avg_runtime_minutes` | `60` | Each run takes 60 minutes (1 hour) |
# MAGIC | `p_days_per_month` | `30` | Calculated over 30 days |
# MAGIC | `p_hours_per_month` | `NULL` | Auto-calculated: 8 × 1 × 30 = 240 hours |
# MAGIC | **All Other Parameters** | `NULL` or defaults | Not applicable for Jobs Serverless |
# MAGIC
# MAGIC **Key Points for AI Agents:**
# MAGIC 1. **NO VM costs** for serverless - only DBU costs
# MAGIC 2. **Photon is MANDATORY** (not optional like classic compute)
# MAGIC 3. **Instance types** are used ONLY to calculate base DBU rate
# MAGIC 4. **Standard mode costs** may be $0 in STANDARD tier (check pricing)
# MAGIC 5. **Performance mode** has 2x multiplier vs standard mode
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 💻 Function Call

# COMMAND ----------

query = """
SELECT * FROM lakemeter.calculate_line_item_costs(
    'JOBS'::VARCHAR,
    'AWS'::VARCHAR,
    'us-east-1'::VARCHAR,
    'PREMIUM'::VARCHAR,
    TRUE::BOOLEAN,                           -- serverless_enabled = TRUE
    TRUE::BOOLEAN,                           -- photon_enabled = TRUE (always)
    NULL::VARCHAR,
    'i3.xlarge'::VARCHAR,                    -- driver (for DBU calc)
    'i3.2xlarge'::VARCHAR,                   -- worker (for DBU calc)
    4::INT,                                  -- num_workers
    'on_demand'::VARCHAR,                    -- driver_pricing_tier (ignored)
    'on_demand'::VARCHAR,                    -- worker_pricing_tier (ignored)
    8::INT,                                  -- runs_per_day
    60::INT,                                 -- avg_runtime_minutes
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

