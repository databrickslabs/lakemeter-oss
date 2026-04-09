# Databricks notebook source
# MAGIC %md
# MAGIC # 🔍 Debug: Vector Search $0 Costs
# MAGIC 
# MAGIC **Issue:** All Vector Search scenarios showing $0 costs
# MAGIC 
# MAGIC **Check:**
# MAGIC 1. Product type returned by get_product_type_for_pricing()
# MAGIC 2. DBU rates in sync_product_serverless_rates
# MAGIC 3. Pricing in sync_pricing_dbu_rates
# MAGIC 4. Test the full function

# COMMAND ----------

# Load Lakebase configuration
%run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
import pandas as pd
from decimal import Decimal

# Verify config loaded
print(f"✅ Config loaded - Host: {LAKEBASE_HOST}")
print(f"✅ Config loaded - Database: {LAKEBASE_DB}")

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
# MAGIC ## 1️⃣ Check Product Type for Vector Search

# COMMAND ----------

print("=" * 100)
print("STEP 1: What product type does get_product_type_for_pricing() return?")
print("=" * 100)

query = """
SELECT lakemeter.get_product_type_for_pricing(
    'VECTOR_SEARCH'::VARCHAR,
    FALSE::BOOLEAN,
    FALSE::BOOLEAN,
    NULL::VARCHAR,
    NULL::VARCHAR,
    NULL::VARCHAR
) AS product_type;
"""

result = execute_query(query)
product_type = result.iloc[0]['product_type']

print(f"\n✅ Product Type: {product_type}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2️⃣ Check if this Product Type Exists in Pricing Table

# COMMAND ----------

print("=" * 100)
print(f"STEP 2: Does '{product_type}' exist in sync_pricing_dbu_rates?")
print("=" * 100)

query = """
SELECT DISTINCT product_type, COUNT(*) as price_count
FROM lakemeter.sync_pricing_dbu_rates
GROUP BY product_type
ORDER BY product_type;
"""

df = execute_query(query)
print("\n📋 All product types in pricing table:")
print(df.to_string(index=False))

# Check if our product type exists
if product_type in df['product_type'].values:
    count = df[df['product_type'] == product_type]['price_count'].iloc[0]
    print(f"\n✅ {product_type} EXISTS with {count} pricing records")
else:
    print(f"\n❌ {product_type} NOT FOUND in pricing table!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3️⃣ Check Vector Search Modes in serverless_rates

# COMMAND ----------

print("=" * 100)
print("STEP 3: What Vector Search modes exist in sync_product_serverless_rates?")
print("=" * 100)

query = """
SELECT cloud, product, size_or_model, dbu_rate
FROM lakemeter.sync_product_serverless_rates
WHERE product = 'vector_search'
ORDER BY cloud, size_or_model;
"""

df = execute_query(query)
if len(df) > 0:
    print(f"\n✅ Found {len(df)} Vector Search rate(s):")
    print(df.to_string(index=False))
else:
    print("\n❌ NO Vector Search rates found!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4️⃣ Test calculate_vector_search_dbu() Directly

# COMMAND ----------

print("=" * 100)
print("STEP 4: Test calculate_vector_search_dbu() with different cases")
print("=" * 100)

test_cases = [
    ('AWS', 'standard', 3),
    ('AWS', 'STANDARD', 3),
    ('AWS', 'Standard', 3),
    ('AWS', 'storage_optimized', 10),
    ('AWS', 'STORAGE_OPTIMIZED', 10),
    ('AWS', 'Storage_Optimized', 10),
]

for cloud, mode, capacity in test_cases:
    query = f"""
    SELECT lakemeter.calculate_vector_search_dbu(
        '{cloud}'::VARCHAR,
        '{mode}'::VARCHAR,
        {capacity}::BIGINT
    ) AS dbu_per_month;
    """
    
    result = execute_query(query)
    dbu = result.iloc[0]['dbu_per_month']
    
    if dbu > 0:
        print(f"✅ {cloud:6} | {mode:20} | {capacity:3}M → DBU: {dbu}")
    else:
        print(f"❌ {cloud:6} | {mode:20} | {capacity:3}M → DBU: {dbu}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5️⃣ Test get_dbu_price() for Vector Search

# COMMAND ----------

print("=" * 100)
print(f"STEP 5: Test get_dbu_price() for {product_type}")
print("=" * 100)

test_cases = [
    ('AWS', 'us-east-1', 'STANDARD'),
    ('AWS', 'us-east-1', 'PREMIUM'),
    ('AWS', 'us-east-1', 'ENTERPRISE'),
]

for cloud, region, tier in test_cases:
    query = f"""
    SELECT lakemeter.get_dbu_price(
        '{cloud}'::VARCHAR,
        '{region}'::VARCHAR,
        '{tier}'::VARCHAR,
        '{product_type}'::VARCHAR
    ) AS dbu_price;
    """
    
    result = execute_query(query)
    price = result.iloc[0]['dbu_price']
    
    if price > 0:
        print(f"✅ {cloud:6} | {region:15} | {tier:10} → ${price}")
    else:
        print(f"❌ {cloud:6} | {region:15} | {tier:10} → ${price}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6️⃣ Full Test: calculate_line_item_costs()

# COMMAND ----------

print("=" * 100)
print("STEP 6: Test full calculate_line_item_costs() for Vector Search")
print("=" * 100)

query = """
SELECT *
FROM lakemeter.calculate_line_item_costs(
    'VECTOR_SEARCH'::VARCHAR,           -- workload_type
    'AWS'::VARCHAR,                      -- cloud
    'us-east-1'::VARCHAR,                -- region
    'PREMIUM'::VARCHAR,                  -- tier
    FALSE::BOOLEAN,                      -- serverless_enabled (N/A for vector search)
    FALSE::BOOLEAN,                      -- photon_enabled (N/A)
    NULL::VARCHAR,                       -- dlt_edition
    NULL::VARCHAR,                       -- driver_node_type
    NULL::VARCHAR,                       -- worker_node_type
    0::INT,                              -- num_workers
    NULL::VARCHAR,                       -- driver_pricing_tier
    NULL::VARCHAR,                       -- worker_pricing_tier
    NULL::VARCHAR,                       -- serverless_mode
    NULL::VARCHAR,                       -- dbsql_warehouse_type
    NULL::VARCHAR,                       -- dbsql_warehouse_size
    NULL::INT,                           -- dbsql_num_clusters
    NULL::VARCHAR,                       -- dbsql_vm_pricing_tier
    'standard'::VARCHAR,                 -- vector_search_mode
    3::BIGINT,                           -- vector_search_capacity_millions
    NULL::VARCHAR,                       -- serverless_size
    NULL::BIGINT,                        -- fmapi_input_tokens_per_month
    NULL::BIGINT,                        -- fmapi_output_tokens_per_month
    NULL::VARCHAR,                       -- fmapi_model
    NULL::VARCHAR,                       -- fmapi_provider
    NULL::VARCHAR,                       -- fmapi_endpoint_type
    NULL::VARCHAR,                       -- fmapi_context_length
    NULL::VARCHAR,                       -- fmapi_provisioned_type
    NULL::INT,                           -- lakebase_cu
    NULL::INT,                           -- lakebase_ha_nodes
    240::INT,                            -- hours_per_month
    30::INT,                             -- days_per_month
    NULL::VARCHAR,                       -- driver_payment_option
    NULL::VARCHAR,                       -- worker_payment_option
    NULL::VARCHAR                        -- dbsql_vm_payment_option
);
"""

result = execute_query(query)
print("\n📊 Full calculation result:")
for col in result.columns:
    val = result.iloc[0][col]
    print(f"   {col:30} = {val}")

# Check if costs are positive
dbu_cost = result.iloc[0]['dbu_cost_per_month']
if dbu_cost > 0:
    print(f"\n✅ SUCCESS: DBU Cost = ${dbu_cost:,.2f}")
else:
    print(f"\n❌ FAIL: DBU Cost = ${dbu_cost}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📋 Summary
# MAGIC 
# MAGIC This notebook checks:
# MAGIC 1. Product type mapping
# MAGIC 2. Pricing table has the product type
# MAGIC 3. Serverless rates table has vector search modes
# MAGIC 4. Function returns correct DBU
# MAGIC 5. Pricing lookup works
# MAGIC 6. Full calculation works

