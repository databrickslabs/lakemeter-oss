# Databricks notebook source
# MAGIC %md
# MAGIC # Debug: OpenAI FMAPI Lookup Failure
# MAGIC 
# MAGIC OpenAI shows DBU/Month = 0, meaning the fmapi_calc CTE is not finding matches

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
# MAGIC ## Check ALL OpenAI Records

# COMMAND ----------

print("=" * 150)
print("ALL OPENAI RECORDS IN sync_product_fmapi_proprietary")
print("=" * 150)

query = """
SELECT 
    cloud,
    provider,
    model,
    rate_type,
    endpoint_type,
    context_length,
    dbu_rate,
    input_divisor
FROM lakemeter.sync_product_fmapi_proprietary
WHERE provider = 'openai'
ORDER BY model, rate_type, endpoint_type, context_length;
"""

df = execute_query(query)
print(f"\nTotal OpenAI records: {len(df)}")
display(df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Specific Lookups for gpt-5

# COMMAND ----------

print("=" * 150)
print("TESTING LOOKUPS FOR gpt-5 (Global, Short)")
print("=" * 150)

# Test parameters matching Test_13
test_cloud = 'AWS'
test_model = 'gpt-5'
test_endpoint = 'global'
test_context = 'short'
test_input_tokens = 10000000
test_output_tokens = 5000000

print(f"\nTest parameters:")
print(f"  • Cloud: {test_cloud}")
print(f"  • Model: {test_model}")
print(f"  • Endpoint: {test_endpoint}")
print(f"  • Context: {test_context}")
print(f"  • Input tokens: {test_input_tokens}")
print(f"  • Output tokens: {test_output_tokens}")

# Input token lookup (exact query from view)
print(f"\n{'=' * 100}")
print("INPUT TOKEN LOOKUP (from view logic):")
print(f"{'=' * 100}")

query = """
SELECT 
    cloud, provider, model, rate_type, endpoint_type, context_length,
    dbu_rate, input_divisor,
    (%s / COALESCE(input_divisor, 1000000) * dbu_rate) as calculated_dbu
FROM lakemeter.sync_product_fmapi_proprietary
WHERE cloud = %s
AND provider = 'openai'
AND model = %s
AND rate_type = 'input_token'
AND endpoint_type = %s
AND context_length = %s;
"""

df = execute_query(query, (test_input_tokens, test_cloud, test_model, test_endpoint, test_context))

if len(df) > 0:
    print(f"✅ FOUND input_token record:")
    display(df)
else:
    print(f"❌ NO input_token record found")
    
    # Try to find what's available
    print(f"\n   Checking what IS available for {test_model}...")
    query2 = """
    SELECT DISTINCT endpoint_type, context_length, rate_type
    FROM lakemeter.sync_product_fmapi_proprietary
    WHERE provider = 'openai' AND model = %s
    ORDER BY rate_type, endpoint_type, context_length;
    """
    df2 = execute_query(query2, (test_model,))
    if len(df2) > 0:
        print(f"   Available combinations for {test_model}:")
        display(df2)
    else:
        print(f"   ⚠️  Model '{test_model}' NOT FOUND in pricing table at all!")

# Output token lookup
print(f"\n{'=' * 100}")
print("OUTPUT TOKEN LOOKUP (from view logic):")
print(f"{'=' * 100}")

query = """
SELECT 
    cloud, provider, model, rate_type, endpoint_type, context_length,
    dbu_rate, input_divisor,
    (%s / COALESCE(input_divisor, 1000000) * dbu_rate) as calculated_dbu
FROM lakemeter.sync_product_fmapi_proprietary
WHERE cloud = %s
AND provider = 'openai'
AND model = %s
AND rate_type = 'output_token'
AND endpoint_type = %s
AND context_length = %s;
"""

df = execute_query(query, (test_output_tokens, test_cloud, test_model, test_endpoint, test_context))

if len(df) > 0:
    print(f"✅ FOUND output_token record:")
    display(df)
else:
    print(f"❌ NO output_token record found")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test gpt-5-mini

# COMMAND ----------

print("=" * 150)
print("TESTING LOOKUPS FOR gpt-5-mini (In-Geo, Short)")
print("=" * 150)

test_model = 'gpt-5-mini'
test_endpoint = 'in_geo'
test_context = 'short'

print(f"\nTest parameters:")
print(f"  • Cloud: {test_cloud}")
print(f"  • Model: {test_model}")
print(f"  • Endpoint: {test_endpoint}")
print(f"  • Context: {test_context}")

query = """
SELECT 
    cloud, provider, model, rate_type, endpoint_type, context_length,
    dbu_rate, input_divisor
FROM lakemeter.sync_product_fmapi_proprietary
WHERE cloud = %s
AND provider = 'openai'
AND model = %s
AND endpoint_type = %s
AND context_length = %s
ORDER BY rate_type;
"""

df = execute_query(query, (test_cloud, test_model, test_endpoint, test_context))

if len(df) > 0:
    print(f"✅ FOUND {len(df)} records for {test_model}:")
    display(df)
else:
    print(f"❌ NO records found for {test_model}")
    
    # Check what's available
    query2 = """
    SELECT DISTINCT model, endpoint_type, context_length
    FROM lakemeter.sync_product_fmapi_proprietary
    WHERE provider = 'openai'
    ORDER BY model, endpoint_type, context_length;
    """
    df2 = execute_query(query2)
    print(f"\n   All available OpenAI model combinations:")
    display(df2)

