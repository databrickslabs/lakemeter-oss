# Databricks notebook source
# MAGIC %md
# MAGIC # 📘 Usage Guide: DBSQL Pro
# MAGIC
# MAGIC **Workload Type:** `DBSQL`  
# MAGIC **Warehouse Type:** `pro`
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
# MAGIC              × DBU Price (from sync_pricing_dbu_rates, product_type = SQL_PRO_COMPUTE)
# MAGIC
# MAGIC   VM Cost = (Driver VM + Worker VM × worker_count) from sync_ref_dbsql_warehouse_config
# MAGIC             × dbsql_num_clusters
# MAGIC             × hours_per_month
# MAGIC
# MAGIC   Product Type = SQL_PRO_COMPUTE
# MAGIC ```
# MAGIC
# MAGIC **Key Components:**
# MAGIC - **Warehouse type:** `pro` - higher DBU price than classic
# MAGIC - **STANDARD tier:** Not supported (returns $0)
# MAGIC - **VM costs:** Calculated from underlying instance types
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
# MAGIC WHERE UPPER(cloud) = UPPER('AWS')
# MAGIC   AND LOWER(warehouse_type) = LOWER('pro')
# MAGIC   AND UPPER(warehouse_size) = UPPER('X-SMALL')
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
# MAGIC **Use Case:** DBSQL Pro warehouse for high-concurrency BI workloads
# MAGIC
# MAGIC **Scenario Details:**
# MAGIC - Pro warehouse with enhanced performance and concurrency
# MAGIC - Warehouse size: Medium (determines configuration)
# MAGIC - 1 cluster (can scale to multiple for concurrency)
# MAGIC - Runs 12 hours per day for business hours
# MAGIC - **Has BOTH DBU costs AND VM costs** (unlike serverless)
# MAGIC - **NOT available in STANDARD tier** (PREMIUM/ENTERPRISE only)
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
# MAGIC | `p_serverless_enabled` | `FALSE` | Classic/Pro warehouse (not serverless) |
# MAGIC | `p_dbsql_warehouse_type` | `'pro'` | **Pro warehouse** (enhanced performance) |
# MAGIC | `p_dbsql_warehouse_size` | `'Medium'` | Warehouse size (determines instance config) |
# MAGIC | `p_dbsql_num_clusters` | `1` | Number of clusters |
# MAGIC | `p_dbsql_vm_pricing_tier` | `'on_demand'` | VM pricing tier |
# MAGIC | `p_dbsql_vm_payment_option` | `'NA'` | Payment option (AWS reserved if applicable) |
# MAGIC | **Usage Pattern** | | |
# MAGIC | `p_runs_per_day` | `1` | Warehouse runs once per day |
# MAGIC | `p_avg_runtime_minutes` | `720` | Runs for 12 hours (720 min) |
# MAGIC | `p_days_per_month` | `30` | 30 days per month |
# MAGIC | `p_hours_per_month` | `NULL` | Auto-calculated: 1 × 12 × 30 = 360 hours |
# MAGIC | **All Other Parameters** | `NULL` or defaults | Not applicable for DBSQL Pro |
# MAGIC
# MAGIC **Key Points for AI Agents:**
# MAGIC 1. **Pro warehouse has VM costs** (unlike serverless)
# MAGIC 2. **NOT available in STANDARD tier** (PREMIUM/ENTERPRISE only)
# MAGIC 3. **Pro = enhanced performance** vs Classic
# MAGIC 4. **Warehouse size** determines instance configuration
# MAGIC 5. **Use `p_dbsql_vm_pricing_tier`** for VM pricing
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
    FALSE::BOOLEAN,                           -- p_serverless_enabled
    FALSE::BOOLEAN,                           -- p_photon_enabled
    NULL::VARCHAR,                            -- p_dlt_edition
    NULL::VARCHAR,                            -- p_driver_node_type
    NULL::VARCHAR,                            -- p_worker_node_type
    0::INT,                                   -- p_num_workers
    'on_demand'::VARCHAR,                     -- p_driver_pricing_tier
    'on_demand'::VARCHAR,                     -- p_worker_pricing_tier
    1::INT,                                   -- p_runs_per_day
    720::INT,                                 -- p_avg_runtime_minutes
    30::INT,                                  -- p_days_per_month
    NULL::INT,                                -- p_hours_per_month
    'standard'::VARCHAR,                      -- p_serverless_mode
    'pro'::VARCHAR,                           -- p_dbsql_warehouse_type
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
