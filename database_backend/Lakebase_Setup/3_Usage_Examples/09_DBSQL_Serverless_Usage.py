# Databricks notebook source
# MAGIC %md
# MAGIC # 📘 Usage Guide: DBSQL Serverless
# MAGIC
# MAGIC **Workload Type:** `DBSQL`  
# MAGIC **Warehouse Type:** `serverless`
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 🧮 Cost Formula
# MAGIC
# MAGIC ```
# MAGIC Total Cost = DBU Cost (NO VM costs for serverless)
# MAGIC
# MAGIC WHERE:
# MAGIC   DBU Cost = DBU per warehouse size (from sync_product_dbsql_rates)
# MAGIC              × dbsql_num_clusters
# MAGIC              × hours_per_month
# MAGIC              × DBU Price (from sync_pricing_dbu_rates, product_type = SERVERLESS_SQL_COMPUTE)
# MAGIC
# MAGIC   Product Type = SERVERLESS_SQL_COMPUTE
# MAGIC ```
# MAGIC
# MAGIC **Key Components:**
# MAGIC - **NO VM costs** - serverless is DBU-only pricing
# MAGIC - **Warehouse size:** `X-Small` through `4X-Large`
# MAGIC - **DBU rates:** Queried from `sync_product_dbsql_rates` by warehouse size and type `serverless`
# MAGIC - **STANDARD tier:** Not supported (returns $0)
# MAGIC - **GCP STANDARD tier:** Not supported
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## ✅ How to Validate Your Inputs
# MAGIC
# MAGIC **Validation Tables:** `lakemeter.sync_product_dbsql_rates` + `lakemeter.sync_ref_dbsql_warehouse_config`
# MAGIC
# MAGIC **What to validate:**
# MAGIC - Cloud + Warehouse Type + Warehouse Size combination exists
# MAGIC - DBU rate is available for that configuration
# MAGIC
# MAGIC **Example validation query:**
# MAGIC ```sql
# MAGIC SELECT * FROM lakemeter.sync_product_dbsql_rates
# MAGIC WHERE UPPER(cloud) = 'AWS'
# MAGIC   AND LOWER(warehouse_type) = 'serverless'
# MAGIC   AND UPPER(warehouse_size) = 'X-SMALL'
# MAGIC   AND dbu_per_hour IS NOT NULL;
# MAGIC ```
# MAGIC
# MAGIC If this query returns rows → Valid combination ✅  
# MAGIC If this query returns 0 rows → Invalid combination ❌ (will result in $0 cost)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 📋 Example Scenario
# MAGIC
# MAGIC **Use Case:** Serverless SQL warehouse for BI dashboards and real-time analytics
# MAGIC
# MAGIC **Scenario Details:**
# MAGIC - Serverless SQL warehouse with **Medium** size (auto-scales within capacity)
# MAGIC - Photon ALWAYS enabled (mandatory for serverless)
# MAGIC - NO VM costs (serverless DBU-only pricing)
# MAGIC - **Auto-suspends when idle** - only charges for active query time
# MAGIC - Example: 120 hours of actual query processing per month
# MAGIC - **NOT 720 hours** - that would mean queries run continuously (rare!)
# MAGIC - **NOT available in STANDARD tier** (PREMIUM/ENTERPRISE only)
# MAGIC - **Warehouse sizes:** X-Small, Small, Medium, Large, X-Large, 2X-Large, 3X-Large, 4X-Large
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 📊 Parameter Values Explained
# MAGIC
# MAGIC | Parameter | Value | What It Represents |
# MAGIC |-----------|-------|-------------------|
# MAGIC | **Core Identifiers** | | |
# MAGIC | `p_workload_type` | `'DBSQL'` | Databricks SQL workload |
# MAGIC | `p_cloud` | `'AWS'` | Amazon Web Services |
# MAGIC | `p_region` | `'us-east-1'` | US East region |
# MAGIC | `p_tier` | `'PREMIUM'` | Databricks pricing tier |
# MAGIC | **DBSQL Serverless Specific** | | |
# MAGIC | `p_serverless_enabled` | `FALSE` | Misleading - use warehouse_type instead |
# MAGIC | `p_photon_enabled` | `FALSE` | Photon always enabled (not a parameter) |
# MAGIC | `p_dbsql_warehouse_type` | `'serverless'` | **Serverless SQL warehouse** |
# MAGIC | `p_dbsql_warehouse_size` | `'Medium'` | Warehouse size (controls capacity & cost) |
# MAGIC | `p_dbsql_num_clusters` | `1` | Default |
# MAGIC | `p_dbsql_vm_pricing_tier` | `'on_demand'` | N/A (no VM costs) |
# MAGIC | **Usage Pattern** | | |
# MAGIC | `p_hours_per_month` | `120` | **Actual query processing hours** (auto-suspends when idle) |
# MAGIC | **All Other Parameters** | `NULL` or defaults | Not applicable for DBSQL Serverless |
# MAGIC
# MAGIC **Key Points for AI Agents:**
# MAGIC 1. **NO VM costs** for serverless - only DBU costs
# MAGIC 2. **Photon ALWAYS enabled** (not a configuration option)
# MAGIC 3. **NOT available in STANDARD tier** (must be PREMIUM/ENTERPRISE)
# MAGIC 4. **Warehouse size IS required** (X-Small, Small, Medium, Large, etc.) - controls capacity & DBU rate
# MAGIC 5. **Auto-scales within size** - scales up/down automatically within the warehouse capacity
# MAGIC 6. **Auto-suspends when idle** - specify ACTUAL query processing hours, not 24/7 availability
# MAGIC 7. **Use p_hours_per_month** for actual runtime (e.g., 120 hrs business hours, not 720 hrs)
# MAGIC 8. **Product type:** `SERVERLESS_SQL_COMPUTE`
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
    'DBSQL'::VARCHAR,                        -- p_workload_type
    'AWS'::VARCHAR,                          -- p_cloud
    'us-east-1'::VARCHAR,                    -- p_region
    'PREMIUM'::VARCHAR,                      -- p_tier
    FALSE::BOOLEAN,                          -- p_serverless_enabled
    FALSE::BOOLEAN,                          -- p_photon_enabled
    NULL::VARCHAR,                           -- p_dlt_edition
    NULL::VARCHAR,                           -- p_driver_node_type
    NULL::VARCHAR,                           -- p_worker_node_type
    0::INT,                                  -- p_num_workers
    'on_demand'::VARCHAR,                    -- p_driver_pricing_tier
    'on_demand'::VARCHAR,                    -- p_worker_pricing_tier
    1::INT,                                  -- p_runs_per_day
    120::INT,                                -- p_avg_runtime_minutes (2 hours/day)
    30::INT,                                 -- p_days_per_month
    120::INT,                                -- p_hours_per_month (actual query processing time)
    'standard'::VARCHAR,                     -- p_serverless_mode
    'serverless'::VARCHAR,                   -- p_dbsql_warehouse_type
    'Medium'::VARCHAR,                       -- p_dbsql_warehouse_size (required!)
    1::INT,                                  -- p_dbsql_num_clusters
    'on_demand'::VARCHAR,                    -- p_dbsql_vm_pricing_tier (N/A)
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
