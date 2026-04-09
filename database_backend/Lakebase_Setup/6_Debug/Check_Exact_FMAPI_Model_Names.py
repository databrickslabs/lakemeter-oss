# Databricks notebook source
# MAGIC %md
# MAGIC # Debug: Check Exact FMAPI Proprietary Model Names

# COMMAND ----------

%run ../00_Lakebase_Config

# COMMAND ----------

import pandas as pd

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check All Anthropic Models

# COMMAND ----------

query = """
SELECT DISTINCT
    provider,
    model,
    endpoint_type,
    context_length,
    COUNT(DISTINCT rate_type) as rate_types_count
FROM lakemeter.sync_product_fmapi_proprietary
WHERE UPPER(provider) = 'ANTHROPIC'
GROUP BY provider, model, endpoint_type, context_length
ORDER BY model;
"""

results = execute_query(query)

if results:
    df = pd.DataFrame(results, columns=['provider', 'model', 'endpoint_type', 'context_length', 'rate_types_count'])
    print(f"✅ Found {len(df)} Anthropic model configurations")
    print("\n📋 Available Anthropic models:")
    display(df)
else:
    print("❌ No Anthropic models found!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check All OpenAI Models

# COMMAND ----------

query = """
SELECT DISTINCT
    provider,
    model,
    endpoint_type,
    context_length,
    COUNT(DISTINCT rate_type) as rate_types_count
FROM lakemeter.sync_product_fmapi_proprietary
WHERE UPPER(provider) = 'OPENAI'
GROUP BY provider, model, endpoint_type, context_length
ORDER BY model;
"""

results = execute_query(query)

if results:
    df = pd.DataFrame(results, columns=['provider', 'model', 'endpoint_type', 'context_length', 'rate_types_count'])
    print(f"✅ Found {len(df)} OpenAI model configurations")
    print("\n📋 Available OpenAI models:")
    display(df)
else:
    print("❌ No OpenAI models found!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check All Google Models

# COMMAND ----------

query = """
SELECT DISTINCT
    provider,
    model,
    endpoint_type,
    context_length,
    COUNT(DISTINCT rate_type) as rate_types_count
FROM lakemeter.sync_product_fmapi_proprietary
WHERE UPPER(provider) = 'GOOGLE'
GROUP BY provider, model, endpoint_type, context_length
ORDER BY model;
"""

results = execute_query(query)

if results:
    df = pd.DataFrame(results, columns=['provider', 'model', 'endpoint_type', 'context_length', 'rate_types_count'])
    print(f"✅ Found {len(df)} Google model configurations")
    print("\n📋 Available Google models:")
    display(df)
else:
    print("❌ No Google models found!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Specific Model Lookup

# COMMAND ----------

test_model = 'claude-sonnet-4-1'

query = f"""
SELECT 
    provider,
    model,
    endpoint_type,
    context_length,
    rate_type,
    dbu_rate
FROM lakemeter.sync_product_fmapi_proprietary
WHERE UPPER(provider) = 'ANTHROPIC'
  AND UPPER(model) = UPPER('{test_model}')
ORDER BY rate_type;
"""

results = execute_query(query)

print(f"\n🔍 Looking for: {test_model}")
if results:
    df = pd.DataFrame(results, columns=['provider', 'model', 'endpoint_type', 'context_length', 'rate_type', 'dbu_rate'])
    print(f"✅ FOUND {len(results)} pricing records")
    display(df)
else:
    print(f"❌ NOT FOUND in pricing table!")
    print("\n💡 Try checking for similar models with LIKE:")
    
    like_query = f"""
    SELECT DISTINCT model
    FROM lakemeter.sync_product_fmapi_proprietary
    WHERE UPPER(provider) = 'ANTHROPIC'
      AND UPPER(model) LIKE '%SONNET%'
    ORDER BY model;
    """
    
    like_results = execute_query(like_query)
    if like_results:
        print("\n   Models containing 'SONNET':")
        for row in like_results:
            print(f"   • {row[0]}")


