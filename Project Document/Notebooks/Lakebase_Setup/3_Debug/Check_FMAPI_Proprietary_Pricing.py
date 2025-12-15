# Databricks notebook source
# MAGIC %md
# MAGIC # Debug: FMAPI Proprietary Pricing Lookup
# MAGIC 
# MAGIC Diagnose why FMAPI Proprietary models show $0 DBU/Month

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
# MAGIC ## Check what's in sync_product_fmapi_proprietary

# COMMAND ----------

print("=" * 150)
print("ALL FMAPI PROPRIETARY PRICING DATA")
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
    input_divisor,
    sku_product_type
FROM lakemeter.sync_product_fmapi_proprietary
ORDER BY provider, model, rate_type, endpoint_type, context_length;
"""

df = execute_query(query)
print(f"\nTotal rows: {len(df)}")
display(df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check OpenAI Models

# COMMAND ----------

print("=" * 150)
print("OPENAI MODELS")
print("=" * 150)

query = """
SELECT 
    cloud,
    model,
    rate_type,
    endpoint_type,
    context_length,
    dbu_rate
FROM lakemeter.sync_product_fmapi_proprietary
WHERE provider = 'openai'
ORDER BY model, rate_type, endpoint_type, context_length;
"""

df = execute_query(query)
print(f"\nOpenAI models: {len(df)} rows")
display(df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check Anthropic Models

# COMMAND ----------

print("=" * 150)
print("ANTHROPIC MODELS")
print("=" * 150)

query = """
SELECT 
    cloud,
    model,
    rate_type,
    endpoint_type,
    context_length,
    dbu_rate
FROM lakemeter.sync_product_fmapi_proprietary
WHERE provider = 'anthropic'
ORDER BY model, rate_type, endpoint_type, context_length;
"""

df = execute_query(query)
print(f"\nAnthropic models: {len(df)} rows")
display(df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check Google Models

# COMMAND ----------

print("=" * 150)
print("GOOGLE MODELS")
print("=" * 150)

query = """
SELECT 
    cloud,
    model,
    rate_type,
    endpoint_type,
    context_length,
    dbu_rate
FROM lakemeter.sync_product_fmapi_proprietary
WHERE provider = 'google'
ORDER BY model, rate_type, endpoint_type, context_length;
"""

df = execute_query(query)
print(f"\nGoogle models: {len(df)} rows")
display(df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Specific Lookups (Simulating View Logic)

# COMMAND ----------

print("=" * 150)
print("TESTING SPECIFIC LOOKUPS")
print("=" * 150)

# Test the exact query from the view for a specific scenario
test_cases = [
    {'cloud': 'AWS', 'provider': 'openai', 'model': 'gpt-5', 'endpoint': 'global', 'context': 'standard'},
    {'cloud': 'AWS', 'provider': 'openai', 'model': 'gpt-5-mini', 'endpoint': 'in_geo', 'context': 'standard'},
    {'cloud': 'AWS', 'provider': 'anthropic', 'model': 'claude-sonnet-4', 'endpoint': 'global', 'context': 'standard'},
    {'cloud': 'AWS', 'provider': 'anthropic', 'model': 'claude-opus-4', 'endpoint': 'global', 'context': 'standard'},
    {'cloud': 'AWS', 'provider': 'google', 'model': 'gemini-2-5-pro', 'endpoint': 'global', 'context': 'standard'},
]

for test in test_cases:
    print(f"\n{'=' * 100}")
    print(f"Testing: {test['provider'].upper()} - {test['model']} ({test['endpoint']}, {test['context']})")
    print(f"{'=' * 100}")
    
    # Input token lookup
    query = """
    SELECT 
        cloud, provider, model, rate_type, endpoint_type, context_length, dbu_rate
    FROM lakemeter.sync_product_fmapi_proprietary
    WHERE cloud = %s
    AND provider = %s
    AND model = %s
    AND rate_type = 'input_token'
    AND endpoint_type = %s
    AND context_length = %s;
    """
    
    df = execute_query(query, (test['cloud'], test['provider'], test['model'], test['endpoint'], test['context']))
    
    if len(df) > 0:
        print(f"✅ FOUND input_token pricing:")
        display(df)
    else:
        print(f"❌ NO input_token pricing found for this combination")
        print(f"   Trying with different filters...")
        
        # Try without endpoint filter
        query2 = """
        SELECT DISTINCT endpoint_type, context_length
        FROM lakemeter.sync_product_fmapi_proprietary
        WHERE provider = %s AND model = %s;
        """
        df2 = execute_query(query2, (test['provider'], test['model']))
        if len(df2) > 0:
            print(f"   Available endpoint/context combinations for {test['model']}:")
            display(df2)
        else:
            print(f"   ⚠️  Model '{test['model']}' not found in pricing table at all!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check Model Names Match

# COMMAND ----------

print("=" * 150)
print("DISTINCT MODELS IN PRICING TABLE vs TEST")
print("=" * 150)

query = """
SELECT DISTINCT provider, model
FROM lakemeter.sync_product_fmapi_proprietary
ORDER BY provider, model;
"""

pricing_models = execute_query(query)
print("\n📊 Models in sync_product_fmapi_proprietary:")
display(pricing_models)

print("\n📋 Models used in Test_13:")
test_models = pd.DataFrame([
    {'provider': 'openai', 'model': 'gpt-5'},
    {'provider': 'openai', 'model': 'gpt-5-mini'},
    {'provider': 'anthropic', 'model': 'claude-sonnet-4'},
    {'provider': 'anthropic', 'model': 'claude-opus-4'},
    {'provider': 'anthropic', 'model': 'claude-haiku-4-5'},
    {'provider': 'google', 'model': 'gemini-2-5-pro'},
    {'provider': 'google', 'model': 'gemini-2-5-flash'},
])
display(test_models)

print("\n🔍 Checking for mismatches...")
for idx, row in test_models.iterrows():
    match = pricing_models[(pricing_models['provider'] == row['provider']) & 
                          (pricing_models['model'] == row['model'])]
    if len(match) == 0:
        print(f"❌ MISMATCH: {row['provider']} / {row['model']} NOT in pricing table")
    else:
        print(f"✅ Match: {row['provider']} / {row['model']}")

