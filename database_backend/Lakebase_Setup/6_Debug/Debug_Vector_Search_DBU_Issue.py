# Databricks notebook source
# MAGIC %md
# MAGIC # 🔍 Debug: Vector Search DBU Calculation Issue
# MAGIC 
# MAGIC **Issue:** dbu_price shows (0.07) but dbu_per_month is 0
# MAGIC 
# MAGIC **Check:**
# MAGIC 1. What does calculate_vector_search_dbu() return?
# MAGIC 2. Is it returning monthly or hourly DBU?
# MAGIC 3. What does the full calculate_line_item_costs() return?

# COMMAND ----------

# Load Lakebase configuration
%run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
import pandas as pd

print(f"✅ Config loaded - Host: {LAKEBASE_HOST}")

def get_connection():
    """Create and return a PostgreSQL connection"""
    return psycopg2.connect(
        host=LAKEBASE_HOST,
        port=LAKEBASE_PORT,
        database=LAKEBASE_DB,
        user=LAKEBASE_USER,
        password=LAKEBASE_PASSWORD
    )

def execute_query(query, params=None):
    conn = get_connection()
    try:
        df = pd.read_sql_query(query, conn, params=params)
        return df
    finally:
        conn.close()

print("✅ Connection functions defined!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1️⃣ Test calculate_vector_search_dbu() Directly

# COMMAND ----------

print("=" * 100)
print("STEP 1: Call calculate_vector_search_dbu() directly")
print("=" * 100)

query = """
SELECT lakemeter.calculate_vector_search_dbu(
    'AWS'::VARCHAR,
    'standard'::VARCHAR,
    3::DECIMAL
) AS dbu_value;
"""

result = execute_query(query)
dbu_value = result.iloc[0]['dbu_value']

print(f"\n✅ Direct call: calculate_vector_search_dbu('AWS', 'standard', 3) = {dbu_value}")
print(f"   Is this monthly or hourly? Let's check...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2️⃣ Check Vector Search Rates Table

# COMMAND ----------

print("=" * 100)
print("STEP 2: What are the actual rates in sync_product_serverless_rates?")
print("=" * 100)

query = """
SELECT cloud, product, size_or_model, dbu_rate
FROM lakemeter.sync_product_serverless_rates
WHERE product = 'vector_search'
ORDER BY cloud, size_or_model;
"""

df = execute_query(query)
print("\n📋 Vector Search rates:")
print(df.to_string(index=False))

print("\n💡 If these are hourly rates, DBU should be ~4 for standard mode")
print("💡 If these are monthly rates, DBU should match directly")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3️⃣ Test Full calculate_line_item_costs()

# COMMAND ----------

print("=" * 100)
print("STEP 3: Test full calculate_line_item_costs() for Vector Search")
print("=" * 100)

query = """
SELECT *
FROM lakemeter.calculate_line_item_costs(
    'VECTOR_SEARCH'::VARCHAR,           -- workload_type
    'AWS'::VARCHAR,                      -- cloud
    'us-east-1'::VARCHAR,                -- region
    'PREMIUM'::VARCHAR,                  -- tier
    FALSE::BOOLEAN,                      -- serverless_enabled
    FALSE::BOOLEAN,                      -- photon_enabled
    NULL::VARCHAR,                       -- dlt_edition
    NULL::VARCHAR,                       -- driver_node_type
    NULL::VARCHAR,                       -- worker_node_type
    0::INT,                              -- num_workers
    NULL::VARCHAR,                       -- driver_pricing_tier
    NULL::VARCHAR,                       -- worker_pricing_tier
    0::INT,                              -- runs_per_day
    0::INT,                              -- avg_runtime_minutes
    30::INT,                             -- days_per_month
    720::INT,                            -- hours_per_month (24*30 for 24/7 availability)
    NULL::VARCHAR,                       -- serverless_mode
    NULL::VARCHAR,                       -- dbsql_warehouse_type
    NULL::VARCHAR,                       -- dbsql_warehouse_size
    NULL::INT,                           -- dbsql_num_clusters
    NULL::VARCHAR,                       -- dbsql_vm_pricing_tier
    'standard'::VARCHAR,                 -- vector_search_mode
    3::DECIMAL,                          -- vector_search_capacity_millions
    NULL::VARCHAR,                       -- serverless_size
    NULL::VARCHAR,                       -- fmapi_model
    NULL::VARCHAR,                       -- fmapi_provider
    'global'::VARCHAR,                   -- fmapi_endpoint_type
    'standard'::VARCHAR,                 -- fmapi_context_length
    'pay_per_token'::VARCHAR,            -- fmapi_provisioned_type
    0::BIGINT,                           -- fmapi_input_tokens_per_month
    0::BIGINT,                           -- fmapi_output_tokens_per_month
    0::INT,                              -- lakebase_cu
    1::INT,                              -- lakebase_ha_nodes
    'NA'::VARCHAR,                       -- driver_payment_option
    'NA'::VARCHAR,                       -- worker_payment_option
    'NA'::VARCHAR                        -- dbsql_vm_payment_option
);
"""

result = execute_query(query)

print("\n📊 Full calculation result:")
for col in ['dbu_per_hour', 'dbu_per_month', 'dbu_price', 'dbu_cost_per_month', 'vm_cost_per_month', 'cost_per_month']:
    if col in result.columns:
        val = result.iloc[0][col]
        print(f"   {col:25} = {val}")

# Check results
dbu_per_hour = result.iloc[0]['dbu_per_hour'] if 'dbu_per_hour' in result.columns else 0
dbu_per_month = result.iloc[0]['dbu_per_month'] if 'dbu_per_month' in result.columns else 0
dbu_price = result.iloc[0]['dbu_price'] if 'dbu_price' in result.columns else 0
dbu_cost = result.iloc[0]['dbu_cost_per_month'] if 'dbu_cost_per_month' in result.columns else 0

print(f"\n🔍 Analysis:")
print(f"   Direct function returned: {dbu_value}")
print(f"   Orchestrator dbu_per_hour: {dbu_per_hour}")
print(f"   Orchestrator dbu_per_month: {dbu_per_month}")
print(f"   Expected: {dbu_value} * 240 = {float(dbu_value) * 240} (if hourly)")
print(f"   Expected: {dbu_value} (if monthly)")

if dbu_per_month == 0:
    print(f"\n❌ PROBLEM: dbu_per_month is 0!")
    print(f"   This means calculate_vector_search_dbu() returned 0 or NULL")
elif float(dbu_per_month) == float(dbu_value) * 240:
    print(f"\n⚠️  PROBLEM: Function returns hourly, orchestrator treats as hourly")
    print(f"   But Vector Search should be monthly-based!")
elif float(dbu_per_month) == float(dbu_value):
    print(f"\n⚠️  PROBLEM: Function returns monthly, but orchestrator multiplies by hours")
    print(f"   Need to fix orchestrator to NOT multiply for Vector Search")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4️⃣ Check the Orchestrator Code

# COMMAND ----------

print("=" * 100)
print("STEP 4: Check what the orchestrator is doing")
print("=" * 100)

query = """
SELECT 
    lakemeter.calculate_vector_search_dbu('AWS'::VARCHAR, 'standard'::VARCHAR, 3::DECIMAL) as direct_dbu,
    240 as hours_per_month,
    lakemeter.calculate_vector_search_dbu('AWS'::VARCHAR, 'standard'::VARCHAR, 3::DECIMAL) * 240 as if_multiplied
"""

result = execute_query(query)
print("\n📊 What would happen if we multiply by hours_per_month?")
print(result.to_string(index=False))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📋 Summary
# MAGIC 
# MAGIC This notebook checks if Vector Search DBU is monthly or hourly and if the orchestrator handles it correctly.

