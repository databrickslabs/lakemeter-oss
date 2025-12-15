# Databricks notebook source
# MAGIC %md
# MAGIC # Debug: Anthropic FMAPI Lookup Failures
# MAGIC 
# MAGIC Some Anthropic models show DBU/Month = 0

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
# MAGIC ## Check ALL Anthropic Records

# COMMAND ----------

print("=" * 150)
print("ALL ANTHROPIC RECORDS IN sync_product_fmapi_proprietary")
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
WHERE provider = 'anthropic'
ORDER BY model, endpoint_type, context_length, rate_type;
"""

df = execute_query(query)
print(f"\nTotal Anthropic records: {len(df)}")
display(df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check Available Model Combinations

# COMMAND ----------

print("=" * 150)
print("AVAILABLE ANTHROPIC MODEL COMBINATIONS")
print("=" * 150)

query = """
SELECT DISTINCT model, endpoint_type, context_length
FROM lakemeter.sync_product_fmapi_proprietary
WHERE provider = 'anthropic'
ORDER BY model, endpoint_type, context_length;
"""

df = execute_query(query)
print(f"\nAvailable combinations: {len(df)}")
display(df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Specific Lookups

# COMMAND ----------

print("=" * 150)
print("TESTING SPECIFIC LOOKUPS FROM TEST_13")
print("=" * 150)

test_cases = [
    {'model': 'claude-sonnet-4', 'endpoint': 'global', 'context': 'short', 'status': 'WORKING ✅'},
    {'model': 'claude-opus-4', 'endpoint': 'global', 'context': 'long', 'status': 'FAILING ❌'},
    {'model': 'claude-haiku-4-5', 'endpoint': 'in_geo', 'context': 'short', 'status': 'FAILING ❌'},
]

for test in test_cases:
    print(f"\n{'=' * 100}")
    print(f"Testing: {test['model']} + {test['endpoint']} + {test['context']} - {test['status']}")
    print(f"{'=' * 100}")
    
    query = """
    SELECT cloud, model, rate_type, endpoint_type, context_length, dbu_rate
    FROM lakemeter.sync_product_fmapi_proprietary
    WHERE provider = 'anthropic'
    AND model = %s
    AND endpoint_type = %s
    AND context_length = %s
    ORDER BY rate_type;
    """
    
    df = execute_query(query, (test['model'], test['endpoint'], test['context']))
    
    if len(df) > 0:
        print(f"✅ FOUND {len(df)} records:")
        display(df)
    else:
        print(f"❌ NO records found for this combination")
        
        # Check what IS available for this model
        print(f"\n   Checking what IS available for {test['model']}...")
        query2 = """
        SELECT DISTINCT endpoint_type, context_length
        FROM lakemeter.sync_product_fmapi_proprietary
        WHERE provider = 'anthropic' AND model = %s
        ORDER BY endpoint_type, context_length;
        """
        df2 = execute_query(query2, (test['model'],))
        
        if len(df2) > 0:
            print(f"   Available combinations for {test['model']}:")
            display(df2)
        else:
            print(f"   ⚠️  Model '{test['model']}' NOT FOUND in pricing table at all!")
            
            # Show similar models
            query3 = """
            SELECT DISTINCT model
            FROM lakemeter.sync_product_fmapi_proprietary
            WHERE provider = 'anthropic'
            AND model LIKE %s
            ORDER BY model;
            """
            df3 = execute_query(query3, (test['model'].split('-')[0] + '%',))
            if len(df3) > 0:
                print(f"\n   Similar models found:")
                display(df3)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check Model Name Variations

# COMMAND ----------

print("=" * 150)
print("CHECKING FOR SIMILAR MODEL NAMES")
print("=" * 150)

# Check for variations of the failing models
failing_models = ['claude-opus-4', 'claude-haiku-4-5']

for model in failing_models:
    print(f"\n{'=' * 100}")
    print(f"Searching for variations of: {model}")
    print(f"{'=' * 100}")
    
    # Extract the base name (e.g., "opus" or "haiku")
    parts = model.split('-')
    if len(parts) >= 2:
        base = parts[1]  # "opus" or "haiku"
        
        query = """
        SELECT DISTINCT model, endpoint_type, context_length
        FROM lakemeter.sync_product_fmapi_proprietary
        WHERE provider = 'anthropic'
        AND model LIKE %s
        ORDER BY model, endpoint_type, context_length;
        """
        
        df = execute_query(query, (f'%{base}%',))
        
        if len(df) > 0:
            print(f"Found {len(df)} combinations with '{base}' in the name:")
            display(df)
        else:
            print(f"No models found with '{base}' in the name")

