# Databricks notebook source
# MAGIC %md
# MAGIC # 🐛 DEBUG: Test_Func_09 - Which Scenarios Have $0?

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
import pandas as pd

def get_connection():
    return psycopg2.connect(
        host=LAKEBASE_HOST,
        port=LAKEBASE_PORT,
        database=LAKEBASE_DATABASE,
        user=LAKEBASE_USER,
        password=LAKEBASE_PASSWORD,
        sslmode='require'
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test ONE PREMIUM scenario that's failing

# COMMAND ----------

# Based on Test_Func_09, let's test ONE PREMIUM scenario
query = """
SELECT 
    'AWS us-east-1 PREMIUM X-Small' as test_label,
    *
FROM lakemeter.calculate_line_item_costs(
    'DBSQL'::VARCHAR,
    'AWS'::VARCHAR,
    'us-east-1'::VARCHAR,
    'PREMIUM'::VARCHAR,
    TRUE::BOOLEAN,                          -- serverless_enabled
    TRUE::BOOLEAN,                          -- photon_enabled (always true for serverless)
    NULL::VARCHAR,
    NULL::VARCHAR,
    NULL::VARCHAR,
    0::INT,
    'NA'::VARCHAR,
    'NA'::VARCHAR,
    8::INT,
    60::INT,
    30::INT,
    'standard'::VARCHAR,
    'serverless'::VARCHAR,                  -- dbsql_warehouse_type
    'X-Small'::VARCHAR,                     -- dbsql_warehouse_size
    1::INT,
    'NA'::VARCHAR,                          -- dbsql_vm_pricing_tier (not used for serverless)
    NULL::VARCHAR,
    0::DECIMAL,
    NULL::VARCHAR,
    NULL::VARCHAR,
    NULL::VARCHAR,
    'global'::VARCHAR,
    'standard'::VARCHAR,
    'pay_per_token'::VARCHAR,
    0::BIGINT,
    0::BIGINT,
    0::INT,
    1::INT,
    'NA'::VARCHAR,
    'NA'::VARCHAR,
    'NA'::VARCHAR
);
"""

conn = get_connection()
result = pd.read_sql_query(query, conn)
conn.close()

print("📊 Result for AWS us-east-1 PREMIUM X-Small:")
display(result)

cost = float(result['cost_per_month'].iloc[0])
dbu_cost = float(result['dbu_cost_per_month'].iloc[0])

print(f"\n💰 Costs:")
print(f"   DBU cost: ${dbu_cost:,.2f}")
print(f"   Total cost: ${cost:,.2f}")

if cost == 0:
    print("\n❌ This scenario returns $0!")
    print("\n🔍 Possible causes:")
    print("   1. DBSQL Serverless pricing data missing for this tier")
    print("   2. Wrong warehouse_type value ('serverless' vs something else)")
    print("   3. Product type mapping issue")
else:
    print(f"\n✅ This scenario works correctly!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check DBSQL Serverless pricing data

# COMMAND ----------

pricing_query = """
SELECT 
    cloud,
    tier,
    product_type,
    price_per_dbu
FROM lakemeter.sync_pricing_dbu_rates
WHERE product_type LIKE '%DBSQL%SERVERLESS%'
  AND cloud = 'AWS'
  AND tier IN ('PREMIUM', 'ENTERPRISE')
ORDER BY cloud, tier, product_type
LIMIT 20;
"""

conn = get_connection()
pricing = pd.read_sql_query(pricing_query, conn)
conn.close()

print("🔍 DBSQL Serverless Pricing (AWS, PREMIUM/ENTERPRISE):")
display(pricing)

if len(pricing) == 0:
    print("\n❌ NO DBSQL Serverless pricing found for AWS PREMIUM/ENTERPRISE!")
    print("   This explains the $0 costs!")
else:
    print(f"\n✅ Found {len(pricing)} pricing entries")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check what product_type the function uses

# COMMAND ----------

# DBSQL Serverless should map to 'SQL_SERVERLESS_COMPUTE' or similar
product_check = """
SELECT DISTINCT product_type
FROM lakemeter.sync_pricing_dbu_rates
WHERE product_type LIKE '%SQL%'
  OR product_type LIKE '%DBSQL%'
ORDER BY product_type;
"""

conn = get_connection()
products = pd.read_sql_query(product_check, conn)
conn.close()

print("📋 All SQL-related product types:")
display(products)

