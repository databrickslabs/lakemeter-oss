# Databricks notebook source
# MAGIC %md
# MAGIC # Debug: FMAPI Proprietary Pricing Data
# MAGIC
# MAGIC Check what models are actually available in the pricing table

# COMMAND ----------

%run ../00_Lakebase_Config

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check Available Models in Pricing Table

# COMMAND ----------

import pandas as pd

# Query all available FMAPI proprietary models
query = """
SELECT DISTINCT
    provider,
    model,
    endpoint_type,
    context_length,
    rate_type,
    dbu_rate,
    is_hourly
FROM lakemeter.sync_product_fmapi_proprietary
ORDER BY provider, model, rate_type;
"""

results = execute_query(query)

if results:
    df = pd.DataFrame(results, columns=['provider', 'model', 'endpoint_type', 'context_length', 'rate_type', 'dbu_rate', 'is_hourly'])
    print(f"✅ Found {len(df)} pricing records")
    display(df)
else:
    print("❌ No pricing data found!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check Models Used in Test

# COMMAND ----------

test_models = [
    ('anthropic', 'claude-sonnet-4-1'),
    ('anthropic', 'claude-haiku-4-5'),
    ('anthropic', 'claude-opus-4'),
    ('openai', 'gpt-5'),
    ('google', 'gemini-2-5-pro')
]

print("=" * 100)
print("CHECKING TEST MODELS IN PRICING TABLE")
print("=" * 100)

for provider, model in test_models:
    check_query = f"""
    SELECT COUNT(*) as count, 
           STRING_AGG(DISTINCT rate_type, ', ') as available_rate_types
    FROM lakemeter.sync_product_fmapi_proprietary
    WHERE UPPER(provider) = UPPER('{provider}')
      AND UPPER(model) = UPPER('{model}');
    """
    
    result = execute_query(check_query)
    if result and result[0][0] > 0:
        print(f"\n✅ {provider} {model}")
        print(f"   Found {result[0][0]} pricing records")
        print(f"   Rate types: {result[0][1]}")
    else:
        print(f"\n❌ {provider} {model}")
        print(f"   NOT FOUND in pricing table")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Function Call with Real Data

# COMMAND ----------

# Try calling the function with a model that exists
print("\n" + "=" * 100)
print("TESTING FUNCTION CALL")
print("=" * 100)

# Get first available model from pricing table
test_query = """
SELECT 
    provider,
    model,
    endpoint_type,
    context_length,
    rate_type
FROM lakemeter.sync_product_fmapi_proprietary
LIMIT 1;
"""

result = execute_query(test_query)
if result and len(result) > 0:
    provider, model, endpoint, context, rate_type = result[0]
    
    print(f"\n🧪 Testing with:")
    print(f"   Provider: {provider}")
    print(f"   Model: {model}")
    print(f"   Endpoint: {endpoint}")
    print(f"   Context: {context}")
    print(f"   Rate Type: {rate_type}")
    
    # Call the function
    func_query = f"""
    SELECT lakemeter.calculate_fmapi_proprietary_dbu(
        'AWS'::VARCHAR,
        '{provider}'::VARCHAR,
        '{model}'::VARCHAR,
        '{endpoint}'::VARCHAR,
        '{context}'::VARCHAR,
        '{rate_type}'::VARCHAR,
        10000000::BIGINT
    ) as dbu;
    """
    
    func_result = execute_query(func_query)
    if func_result:
        dbu = func_result[0][0]
        print(f"\n   Result: {dbu} DBU")
        if dbu and dbu > 0:
            print("   ✅ Function is working!")
        else:
            print("   ❌ Function returned 0 or NULL")
else:
    print("\n❌ No pricing data available to test")


