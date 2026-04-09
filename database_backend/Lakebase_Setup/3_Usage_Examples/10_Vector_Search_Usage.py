# Databricks notebook source
# MAGIC %md
# MAGIC # 📘 Usage Guide: Vector Search
# MAGIC
# MAGIC **Workload Type:** `VECTOR_SEARCH`  
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
# MAGIC   DBU Cost = CEILING(capacity_millions / divisor) × hours_per_month × DBU Price
# MAGIC   
# MAGIC   divisor = 2M for standard mode, 64M for storage-optimized mode
# MAGIC   hours_per_month = Specify with p_hours_per_month (e.g., 720 for 24/7, or less if not always-on)
# MAGIC   
# MAGIC   Product Type = SERVERLESS_REAL_TIME_INFERENCE
# MAGIC ```
# MAGIC
# MAGIC **Key Components:**
# MAGIC - **NO VM costs** - serverless DBU-only pricing
# MAGIC - **Capacity:** Specified in millions of vectors
# MAGIC - **Mode:** `standard` (2M per unit) or `storage-optimized` (64M per unit)
# MAGIC - **Units:** CEILING function rounds up (e.g., 3M / 2M = 1.5 → 2 units)
# MAGIC - **Runtime:** Typically 24/7 (720 hours), use `p_hours_per_month` to specify hours
# MAGIC - **DBU rates:** Queried from `sync_product_vector_search` by mode
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## ✅ How to Validate Your Inputs
# MAGIC
# MAGIC **Validation Table:** `lakemeter.sync_product_serverless_rates`
# MAGIC
# MAGIC **What to validate:**
# MAGIC - Cloud + Vector Search Mode combination exists
# MAGIC - Serverless rate is available for Vector Search product
# MAGIC
# MAGIC **Example validation query:**
# MAGIC ```sql
# MAGIC SELECT * FROM lakemeter.sync_product_serverless_rates
# MAGIC WHERE UPPER(product) = UPPER('vector_search')
# MAGIC   AND UPPER(size_or_model) = UPPER('standard')  -- or 'storage_optimized'
# MAGIC   AND UPPER(cloud) = UPPER('AWS');
# MAGIC ```
# MAGIC
# MAGIC If this query returns rows → Valid combination ✅  
# MAGIC If this query returns 0 rows → Invalid combination ❌ (will result in $0 cost)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 📋 Example Scenario
# MAGIC
# MAGIC **Use Case:** Vector Search endpoint for RAG (Retrieval-Augmented Generation) applications
# MAGIC
# MAGIC **Scenario Details:**
# MAGIC - Vector search index storing 10 million vectors
# MAGIC - Standard mode: 2 million vectors per unit → 10M / 2M = 5 units (rounded up)
# MAGIC - Runs 24/7 for continuous search availability
# MAGIC - NO VM costs - serverless DBU-only pricing
# MAGIC
# MAGIC **Capacity Calculation:**
# MAGIC - **Standard mode:** 2M vectors per unit
# MAGIC - **Storage-optimized mode:** 64M vectors per unit
# MAGIC - Units are calculated as: CEILING(capacity_millions / divisor)
# MAGIC - Example: 10M / 2M = 5 units
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 📊 Parameter Values Explained
# MAGIC
# MAGIC | Parameter | Value | What It Represents |
# MAGIC |-----------|-------|-------------------|
# MAGIC | **Core Identifiers** | | |
# MAGIC | `p_workload_type` | `'VECTOR_SEARCH'` | Vector Search workload |
# MAGIC | `p_cloud` | `'AWS'` | Amazon Web Services |
# MAGIC | `p_region` | `'us-east-1'` | US East region |
# MAGIC | `p_tier` | `'PREMIUM'` | Databricks pricing tier |
# MAGIC | **Vector Search Specific** | | |
# MAGIC | `p_vector_search_mode` | `'standard'` | Standard mode (2M per unit) vs 'storage_optimized' (64M per unit) |
# MAGIC | `p_vector_search_capacity_millions` | `10` | 10 million vectors total capacity |
# MAGIC | `p_hours_per_month` | `720` | 24/7 operation (24 × 30 = 720 hours) |
# MAGIC | **All Other Parameters** | `NULL` or defaults | Not applicable for Vector Search |
# MAGIC
# MAGIC **Key Points for AI Agents:**
# MAGIC 1. **Capacity-based pricing:** Cost is based on vector capacity, not API calls
# MAGIC 2. **Units calculation:** CEILING(capacity_millions / divisor)
# MAGIC 3. **Divisors:** standard = 2M, storage_optimized = 64M
# MAGIC 4. **Always 24/7:** Vector search indexes run continuously (`p_hours_per_month=720`)
# MAGIC 5. **NO VM costs:** Pure DBU-based pricing
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
    'VECTOR_SEARCH'::VARCHAR,
    'AWS'::VARCHAR,
    'us-east-1'::VARCHAR,
    'PREMIUM'::VARCHAR,
    FALSE::BOOLEAN, FALSE::BOOLEAN, NULL::VARCHAR,
    NULL::VARCHAR, NULL::VARCHAR, 0::INT,
    'NA'::VARCHAR, 'NA'::VARCHAR,
    1::INT, 60::INT, 30::INT,
    720::INT,                                -- p_hours_per_month (24/7)
    NULL::VARCHAR, NULL::VARCHAR, NULL::VARCHAR, 1::INT, 'NA'::VARCHAR,
    'standard'::VARCHAR,                     -- vector_search_mode
    10::DECIMAL,                             -- vector_search_capacity_millions
    NULL::VARCHAR,
    NULL::VARCHAR, NULL::VARCHAR,
    'global'::VARCHAR, 'all'::VARCHAR, 'input_token'::VARCHAR,
    0::BIGINT, 0::INT, 1::INT,
    'NA'::VARCHAR, 'NA'::VARCHAR, 'NA'::VARCHAR
);
"""

result = execute_query(query)
display(result)
