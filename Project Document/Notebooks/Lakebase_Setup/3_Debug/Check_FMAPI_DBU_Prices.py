# Databricks notebook source
# MAGIC %md
# MAGIC # Debug: FMAPI DBU Pricing Lookup
# MAGIC 
# MAGIC Check what product_type values exist in sync_pricing_dbu_rates for FMAPI workloads

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
import pandas as pd

def execute_query(query, params=None):
    """Execute a SQL query and return results as DataFrame"""
    conn = get_lakebase_connection()
    try:
        with conn.cursor() as cur:
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            
            columns = [desc[0] for desc in cur.description] if cur.description else []
            results = cur.fetchall()
            return pd.DataFrame(results, columns=columns)
    finally:
        conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check Available Product Types for FMAPI

# COMMAND ----------

print("=" * 150)
print("SEARCHING FOR FMAPI-RELATED PRODUCT TYPES")
print("=" * 150)

query = """
SELECT DISTINCT product_type, cloud, tier, price_per_dbu
FROM lakemeter.sync_pricing_dbu_rates
WHERE product_type LIKE '%MODEL%' OR product_type LIKE '%FMAPI%' OR product_type LIKE '%INFERENCE%'
ORDER BY product_type, cloud, tier;
"""

df = execute_query(query)
print(f"\nFound {len(df)} rows")
display(df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check Specific Provider Product Types

# COMMAND ----------

print("=" * 150)
print("CHECKING PROVIDER-SPECIFIC PRODUCT TYPES")
print("=" * 150)

# Check if these exist
product_types_to_check = [
    'OPENAI_MODEL_SERVING',
    'ANTHROPIC_MODEL_SERVING',
    'GOOGLE_MODEL_SERVING',
    'SERVERLESS_REAL_TIME_INFERENCE'
]

for pt in product_types_to_check:
    print(f"\n{'=' * 100}")
    print(f"Product Type: {pt}")
    print(f"{'=' * 100}")
    
    query = """
    SELECT cloud, tier, price_per_dbu
    FROM lakemeter.sync_pricing_dbu_rates
    WHERE product_type = %s
    ORDER BY cloud, tier;
    """
    
    df = execute_query(query, (pt,))
    
    if len(df) > 0:
        print(f"✅ FOUND {len(df)} pricing records")
        display(df)
    else:
        print(f"❌ NOT FOUND in sync_pricing_dbu_rates")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check Sample Lookups

# COMMAND ----------

print("=" * 150)
print("SIMULATING DBU PRICE LOOKUPS FROM VIEW")
print("=" * 150)

test_cases = [
    {'cloud': 'AWS', 'region': 'us-east-1', 'tier': 'PREMIUM', 'provider': 'openai', 'expected_product_type': 'OPENAI_MODEL_SERVING'},
    {'cloud': 'AWS', 'region': 'us-east-1', 'tier': 'PREMIUM', 'provider': 'anthropic', 'expected_product_type': 'ANTHROPIC_MODEL_SERVING'},
    {'cloud': 'AWS', 'region': 'us-east-1', 'tier': 'PREMIUM', 'provider': 'google', 'expected_product_type': 'GOOGLE_MODEL_SERVING'},
]

for test in test_cases:
    print(f"\n{'=' * 100}")
    print(f"Testing: {test['provider'].upper()} in {test['cloud']} {test['region']} {test['tier']}")
    print(f"Expected product_type: {test['expected_product_type']}")
    print(f"{'=' * 100}")
    
    query = """
    SELECT price_per_dbu
    FROM lakemeter.sync_pricing_dbu_rates
    WHERE cloud = %s
    AND region = %s
    AND tier = %s
    AND product_type = %s
    LIMIT 1;
    """
    
    df = execute_query(query, (test['cloud'], test['region'], test['tier'], test['expected_product_type']))
    
    if len(df) > 0:
        print(f"✅ FOUND: price_per_dbu = {df.iloc[0]['price_per_dbu']}")
    else:
        print(f"❌ NOT FOUND")
        
        # Try with SERVERLESS_REAL_TIME_INFERENCE
        print(f"\n   Trying with SERVERLESS_REAL_TIME_INFERENCE...")
        df2 = execute_query(query, (test['cloud'], test['region'], test['tier'], 'SERVERLESS_REAL_TIME_INFERENCE'))
        if len(df2) > 0:
            print(f"   ✅ FOUND with SERVERLESS_REAL_TIME_INFERENCE: price_per_dbu = {df2.iloc[0]['price_per_dbu']}")
        else:
            print(f"   ❌ Also not found with SERVERLESS_REAL_TIME_INFERENCE")

