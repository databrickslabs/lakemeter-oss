# Databricks notebook source
# MAGIC %md
# MAGIC # 📘 Usage Guide: DBSQL Classic
# MAGIC
# MAGIC **Workload Type:** `DBSQL`  
# MAGIC **Warehouse Type:** `classic`
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 🧮 Cost Formula
# MAGIC
# MAGIC ```
# MAGIC Total Cost = DBU Cost + VM Cost
# MAGIC
# MAGIC WHERE:
# MAGIC   DBU Cost = DBU per warehouse size (from sync_product_dbsql_rates)
# MAGIC              × dbsql_num_clusters
# MAGIC              × hours_per_month
# MAGIC              × DBU Price (from sync_pricing_dbu_rates)
# MAGIC
# MAGIC   VM Cost = (Driver VM + Worker VM × worker_count) from sync_ref_dbsql_warehouse_config
# MAGIC             × dbsql_num_clusters
# MAGIC             × hours_per_month
# MAGIC
# MAGIC   Product Type = SQL_COMPUTE
# MAGIC ```
# MAGIC
# MAGIC **Key Components:**
# MAGIC - **Warehouse size:** `X-Small`, `Small`, `Medium`, `Large`, `X-Large`, `2X-Large`, `3X-Large`, `4X-Large`
# MAGIC - **DBU rates:** Queried from `sync_product_dbsql_rates` by warehouse size
# MAGIC - **VM configuration:** Queried from `sync_ref_dbsql_warehouse_config` (maps size to driver/worker instances)
# MAGIC - **VM costs:** Calculated from underlying instance types
# MAGIC - **Photon:** Not a separate parameter for DBSQL (included in warehouse pricing)
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
# MAGIC   AND LOWER(warehouse_type) = 'classic'
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
# MAGIC **Use Case:** Classic SQL warehouse for BI dashboards and analytics
# MAGIC
# MAGIC **Scenario Details:**
# MAGIC - Classic warehouse with predefined instance types and cluster sizes
# MAGIC - Warehouse size: Medium (determines instance types and worker count)
# MAGIC - 1 cluster (can scale to multiple clusters for concurrency)
# MAGIC - Runs 12 hours per day (scheduled for business hours)
# MAGIC - **Has BOTH DBU costs AND VM costs** (unlike serverless)
# MAGIC
# MAGIC **DBSQL Warehouse Sizing:**
# MAGIC - Warehouse configuration (instance types, worker count) determined by `warehouse_size`
# MAGIC - Queried from `lakemeter.sync_ref_dbsql_warehouse_config`
# MAGIC - Example: "Medium" → specific driver + worker instances + worker count
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
# MAGIC | **DBSQL Specific** | | |
# MAGIC | `p_serverless_enabled` | `FALSE` | Classic warehouse (not serverless) |
# MAGIC | `p_dbsql_warehouse_type` | `'classic'` | Classic warehouse type |
# MAGIC | `p_dbsql_warehouse_size` | `'Medium'` | Warehouse size (determines instance config) |
# MAGIC | `p_dbsql_num_clusters` | `1` | Number of clusters (for concurrency scaling) |
# MAGIC | `p_dbsql_vm_pricing_tier` | `'on_demand'` | VM pricing tier (on_demand, reserved_1y, etc.) |
# MAGIC | `p_dbsql_vm_payment_option` | `'NA'` | Payment option for AWS reserved (if applicable) |
# MAGIC | **Usage Pattern** | | |
# MAGIC | `p_runs_per_day` | `1` | Warehouse runs once per day |
# MAGIC | `p_avg_runtime_minutes` | `720` | Runs for 12 hours (720 minutes) |
# MAGIC | `p_days_per_month` | `30` | 30 days per month |
# MAGIC | `p_hours_per_month` | `NULL` | Auto-calculated: 1 × 12 × 30 = 360 hours |
# MAGIC | **All Other Parameters** | `NULL` or defaults | Not applicable for DBSQL workload |
# MAGIC
# MAGIC **Cost Components:**
# MAGIC 1. **DBU costs:** Based on warehouse size and DBU rate
# MAGIC 2. **VM costs:** Based on instance types, worker count, and pricing tier
# MAGIC 3. **Total cost = DBU cost + VM cost** (both included for classic)
# MAGIC
# MAGIC **Key Points for AI Agents:**
# MAGIC 1. **Classic DBSQL has VM costs** (unlike serverless)
# MAGIC 2. **Warehouse size** determines instance configuration
# MAGIC 3. **Use `p_dbsql_vm_pricing_tier`** for VM pricing (on_demand, reserved, etc.)
# MAGIC 4. **AWS only:** Use `p_dbsql_vm_payment_option` for reserved upfront options
# MAGIC 5. **Available in STANDARD tier** (unlike Pro/Serverless)
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
    'DBSQL'::VARCHAR,                         -- p_workload_type
    'AWS'::VARCHAR,                           -- p_cloud
    'us-east-1'::VARCHAR,                     -- p_region
    'PREMIUM'::VARCHAR,                       -- p_tier
    FALSE::BOOLEAN,                           -- p_serverless_enabled (Classic)
    FALSE::BOOLEAN,                           -- p_photon_enabled
    NULL::VARCHAR,                            -- p_dlt_edition
    NULL::VARCHAR,                            -- p_driver_node_type
    NULL::VARCHAR,                            -- p_worker_node_type
    0::INT,                                   -- p_num_workers
    'on_demand'::VARCHAR,                     -- p_driver_pricing_tier
    'on_demand'::VARCHAR,                     -- p_worker_pricing_tier
    1::INT,                                   -- p_runs_per_day
    720::INT,                                 -- p_avg_runtime_minutes (12 hours = 720 min)
    30::INT,                                  -- p_days_per_month
    NULL::INT,                                -- p_hours_per_month
    'standard'::VARCHAR,                      -- p_serverless_mode
    'classic'::VARCHAR,                       -- p_dbsql_warehouse_type
    'Medium'::VARCHAR,                        -- p_dbsql_warehouse_size
    1::INT,                                   -- p_dbsql_num_clusters
    'on_demand'::VARCHAR,                     -- p_dbsql_vm_pricing_tier
    NULL::VARCHAR,                            -- p_vector_search_mode
    0::DECIMAL,                               -- p_vector_search_capacity_millions
    NULL::VARCHAR,                            -- p_model_serving_gpu_type
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
