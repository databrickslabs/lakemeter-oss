# Databricks notebook source
# MAGIC %md
# MAGIC # 📘 Usage Guide: Lakebase (Postgres Serverless)
# MAGIC
# MAGIC **Workload Type:** `LAKEBASE`  
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
# MAGIC   DBU Cost = CU × HA nodes
# MAGIC              × hours_per_month
# MAGIC              × DBU Price (from sync_pricing_dbu_rates)
# MAGIC   
# MAGIC   CU = Compute Units (1, 2, 4, or 8) where 1 CU = 1 DBU
# MAGIC   HA nodes = High Availability nodes (1, 2, or 3)
# MAGIC   Total CU = CU × HA nodes (e.g., 2 CU × 2 HA = 4 total CU)
# MAGIC   hours_per_month = Typically 720 for 24/7 database operation, use p_hours_per_month to specify
# MAGIC   
# MAGIC   Product Type = DATABASE_SERVERLESS_COMPUTE
# MAGIC ```
# MAGIC
# MAGIC **Key Components:**
# MAGIC - **NO VM costs** - serverless DBU-only pricing
# MAGIC - **CU (Compute Units):** 1, 2, 4, or 8 CU (1 CU = 1 DBU)
# MAGIC - **HA nodes:** 1, 2, or 3 (for high availability)
# MAGIC - **Total CU:** Calculated as CU × HA nodes
# MAGIC - **Runtime:** Typically 24/7 (720 hours) for database operation, use `p_hours_per_month` to specify
# MAGIC - **Backup retention:** Does not affect pricing
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## ✅ How to Validate Your Inputs
# MAGIC
# MAGIC **Validation Table:** `lakemeter.sync_pricing_dbu_rates`
# MAGIC
# MAGIC **What to validate:**
# MAGIC - Cloud + Region + Tier combination exists
# MAGIC - Product type must be `DATABASE_SERVERLESS_COMPUTE`
# MAGIC
# MAGIC **Example validation query:**
# MAGIC ```sql
# MAGIC SELECT * FROM lakemeter.sync_pricing_dbu_rates
# MAGIC WHERE UPPER(cloud) = UPPER('AWS')
# MAGIC   AND UPPER(region) = UPPER('us-east-1')
# MAGIC   AND UPPER(tier) = UPPER('PREMIUM')
# MAGIC   AND UPPER(product_type) = UPPER('DATABASE_SERVERLESS_COMPUTE');
# MAGIC ```
# MAGIC
# MAGIC If this query returns rows → Valid combination ✅  
# MAGIC If this query returns 0 rows → Invalid combination ❌ (will result in $0 cost)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 📋 Example Scenario
# MAGIC
# MAGIC **Use Case:** Lakebase (PostgreSQL-compatible) instance for OLTP workloads
# MAGIC
# MAGIC **Scenario Details:**
# MAGIC - 2 CU per node (1 CU = 1 DBU for pricing)
# MAGIC - 2 HA (High Availability) nodes + 1 primary = 3 total nodes
# MAGIC - Total DBUs: 2 CU × 3 nodes = 6 DBU/hour
# MAGIC - Runs 24/7 for continuous database availability
# MAGIC - Uses DATABASE_SERVERLESS_COMPUTE product type
# MAGIC
# MAGIC **Compute Units (CU) Explained:**
# MAGIC - Available CU sizes: 1, 2, 4, 8
# MAGIC - 1 CU = 1 DBU for pricing purposes
# MAGIC - CU determines compute power per node
# MAGIC
# MAGIC **High Availability (HA) Nodes:**
# MAGIC - `p_lakebase_ha_nodes=0`: 1 node total (no HA, just primary)
# MAGIC - `p_lakebase_ha_nodes=1`: 2 nodes total (primary + 1 replica)
# MAGIC - `p_lakebase_ha_nodes=2`: 3 nodes total (primary + 2 replicas) ← Maximum
# MAGIC - Total nodes cannot exceed 3
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 📊 Parameter Values Explained
# MAGIC
# MAGIC | Parameter | Value | What It Represents |
# MAGIC |-----------|-------|-------------------|
# MAGIC | **Core Identifiers** | | |
# MAGIC | `p_workload_type` | `'LAKEBASE'` | Lakebase workload (PostgreSQL-compatible) |
# MAGIC | `p_cloud` | `'AWS'` | Amazon Web Services |
# MAGIC | `p_region` | `'us-east-1'` | US East region |
# MAGIC | `p_tier` | `'PREMIUM'` | Databricks pricing tier |
# MAGIC | **Lakebase Specific** | | |
# MAGIC | `p_lakebase_cu` | `2` | 2 CU per node (1 CU = 1 DBU) |
# MAGIC | `p_lakebase_ha_nodes` | `2` | 2 HA replicas → 3 total nodes (max) |
# MAGIC | `p_hours_per_month` | `720` | 24/7 operation (24 × 30 = 720 hours) |
# MAGIC | **All Other Parameters** | `NULL` or defaults | Not applicable for Lakebase |
# MAGIC
# MAGIC **Cost Calculation Example:**
# MAGIC ```
# MAGIC Total DBUs per hour = p_lakebase_cu × (1 + p_lakebase_ha_nodes)
# MAGIC                     = 2 CU × (1 + 2)
# MAGIC                     = 2 CU × 3 nodes
# MAGIC                     = 6 DBU/hour
# MAGIC
# MAGIC Monthly DBUs = 6 DBU/hour × 720 hours = 4,320 DBU
# MAGIC Monthly Cost = 4,320 DBU × $0.07/DBU = $302.40 (example)
# MAGIC ```
# MAGIC
# MAGIC **Key Points for AI Agents:**
# MAGIC 1. **1 CU = 1 DBU** for pricing
# MAGIC 2. **Total nodes** = 1 (primary) + p_lakebase_ha_nodes
# MAGIC 3. **Total DBU/hour** = CU × total nodes
# MAGIC 4. **Maximum 3 nodes** (p_lakebase_ha_nodes ≤ 2)
# MAGIC 5. **Always 24/7** (`p_hours_per_month=720`)
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
    'LAKEBASE'::VARCHAR,                     -- p_workload_type
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
    60::INT,                                 -- p_avg_runtime_minutes
    30::INT,                                 -- p_days_per_month
    720::INT,                                -- p_hours_per_month (24/7)
    NULL::VARCHAR,                           -- p_serverless_mode
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
    2::INT,                                  -- p_lakebase_cu
    2::INT,                                  -- p_lakebase_ha_nodes
    'NA'::VARCHAR, 'NA'::VARCHAR, 'NA'::VARCHAR
);
"""

result = execute_query(query)
display(result)
