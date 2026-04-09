# Databricks notebook source
# MAGIC %md
# MAGIC # 📘 Usage Guide: ALL_PURPOSE Serverless
# MAGIC
# MAGIC **Workload Type:** `ALL_PURPOSE`  
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
# MAGIC              × DBU Price ($/DBU from sync_pricing_dbu_rates)
# MAGIC
# MAGIC   hours_per_month = runs_per_day × (avg_runtime_minutes / 60) × days_per_month
# MAGIC ```
# MAGIC
# MAGIC **Key Components:**
# MAGIC - **NO VM costs** - serverless is DBU-only pricing
# MAGIC - **Base DBU:** Queried from `sync_ref_instance_dbu_rates` (instance types used for sizing)
# MAGIC - **Serverless rate:** Queried from `sync_product_serverless_rates`
# MAGIC - **Photon multiplier:** **MANDATORY for Serverless** - `photon_enabled` must be `TRUE`
# MAGIC - **Mode multiplier:** 1x for standard, 2x for performance
# MAGIC - **DBU price:** Queried from `sync_pricing_dbu_rates` - product type: `ALL_PURPOSE_SERVERLESS_COMPUTE`
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
# MAGIC **Use Case:** Serverless all-purpose cluster for interactive data exploration
# MAGIC
# MAGIC **Scenario Details:**
# MAGIC - Serverless interactive compute (auto-scaling, no fixed cluster)
# MAGIC - Used for notebooks and ad-hoc queries
# MAGIC - Instance types for DBU calculation only (NO actual VM costs)
# MAGIC - Photon ALWAYS enabled (mandatory for serverless)
# MAGIC - Standard serverless mode (not performance 2x mode)
# MAGIC - Runs 8 hours per day for business hours usage
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 📊 Parameter Values Explained
# MAGIC
# MAGIC | Parameter | Value | What It Represents |
# MAGIC |-----------|-------|-------------------|
# MAGIC | **Core Identifiers** | | |
# MAGIC | `p_workload_type` | `'ALL_PURPOSE'` | Interactive/all-purpose workload |
# MAGIC | `p_cloud` | `'AWS'` | Amazon Web Services |
# MAGIC | `p_region` | `'us-east-1'` | US East region |
# MAGIC | `p_tier` | `'PREMIUM'` | Databricks pricing tier |
# MAGIC | **Compute Configuration** | | |
# MAGIC | `p_serverless_enabled` | `TRUE` | **Serverless compute mode** |
# MAGIC | `p_photon_enabled` | `TRUE` | **Photon MANDATORY for serverless** |
# MAGIC | `p_driver_node_type` | `'i3.xlarge'` | For DBU calc ONLY (no VM cost) |
# MAGIC | `p_worker_node_type` | `'i3.2xlarge'` | For DBU calc ONLY (no VM cost) |
# MAGIC | `p_num_workers` | `4` | For DBU calc ONLY |
# MAGIC | `p_driver_pricing_tier` | `'on_demand'` | Ignored (no VM costs) |
# MAGIC | `p_worker_pricing_tier` | `'on_demand'` | Ignored (no VM costs) |
# MAGIC | **Serverless Specific** | | |
# MAGIC | `p_serverless_mode` | `'standard'` | Standard mode (vs 'performance' 2x) |
# MAGIC | **Usage Pattern** | | |
# MAGIC | `p_runs_per_day` | `1` | Cluster runs once per day |
# MAGIC | `p_avg_runtime_minutes` | `480` | Runs for 8 hours (480 min) |
# MAGIC | `p_days_per_month` | `30` | 30 days per month |
# MAGIC | `p_hours_per_month` | `NULL` | Auto-calculated: 1 × 8 × 30 = 240 hours |
# MAGIC | **All Other Parameters** | `NULL` or defaults | Not applicable for ALL_PURPOSE Serverless |
# MAGIC
# MAGIC **Key Points for AI Agents:**
# MAGIC 1. **NO VM costs** for serverless - only DBU costs
# MAGIC 2. **Photon MANDATORY** for serverless (not optional)
# MAGIC 3. **Instance types** used ONLY for base DBU rate calculation
# MAGIC 4. **Standard mode costs** may be $0 in STANDARD tier (check pricing)
# MAGIC 5. **Performance mode** has 2x multiplier vs standard
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
    'ALL_PURPOSE'::VARCHAR,
    'AWS'::VARCHAR,
    'us-east-1'::VARCHAR,
    'PREMIUM'::VARCHAR,
    TRUE::BOOLEAN,                           -- serverless_enabled
    TRUE::BOOLEAN,                           -- photon_enabled (mandatory)
    NULL::VARCHAR,
    'i3.xlarge'::VARCHAR,                    -- driver (for DBU calc)
    'i3.2xlarge'::VARCHAR,                   -- worker (for DBU calc)
    4::INT,
    'on_demand'::VARCHAR,                    -- ignored
    'on_demand'::VARCHAR,                    -- ignored
    1::INT,
    720::INT,                                -- 12 hours
    30::INT,
    NULL::INT,                               -- auto-calc hours
    'standard'::VARCHAR,                     -- serverless_mode
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

