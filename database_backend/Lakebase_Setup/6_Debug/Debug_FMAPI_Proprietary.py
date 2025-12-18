# Databricks notebook source
# MAGIC %md
# MAGIC # Debug: FMAPI Proprietary Empty Schema

# COMMAND ----------

%run ../00_Lakebase_Config

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Check if sync_product_fmapi_proprietary table exists and has data

# COMMAND ----------

check_table_query = """
SELECT COUNT(*) as row_count 
FROM lakemeter.sync_product_fmapi_proprietary;
"""

try:
    result = execute_query(check_table_query)
    print(f"✅ Table exists with {result['row_count'].iloc[0]} rows")
except Exception as e:
    print(f"❌ Error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Check available providers and models

# COMMAND ----------

providers_query = """
SELECT DISTINCT provider, model
FROM lakemeter.sync_product_fmapi_proprietary
ORDER BY provider, model;
"""

try:
    providers = execute_query(providers_query)
    print("Available providers and models:")
    display(providers)
except Exception as e:
    print(f"❌ Error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Check for specific models we're testing

# COMMAND ----------

test_models = ['gpt-4o', 'gpt-4o-mini', 'claude-sonnet-4-20250514', 'claude-haiku-4', 'gemini-2.5-pro-preview-05-06']

for model in test_models:
    check_query = f"""
    SELECT COUNT(*) as count, cloud, provider
    FROM lakemeter.sync_product_fmapi_proprietary
    WHERE model = '{model}'
    GROUP BY cloud, provider;
    """
    
    try:
        result = execute_query(check_query)
        if len(result) > 0:
            print(f"✅ {model}: Found in {len(result)} cloud(s)")
            display(result)
        else:
            print(f"⚠️  {model}: NOT FOUND")
    except Exception as e:
        print(f"❌ {model}: Error - {e}")
    print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Test function call with a simple scenario

# COMMAND ----------

test_query = """
SELECT *
FROM lakemeter.calculate_line_item_costs(
    'FMAPI_PROPRIETARY'::VARCHAR, 'AWS'::VARCHAR, 'us-east-1'::VARCHAR,
    'PREMIUM'::VARCHAR, FALSE::BOOLEAN, FALSE::BOOLEAN, NULL::VARCHAR,
    NULL::VARCHAR, NULL::VARCHAR, 0::INT, 'NA'::VARCHAR, 'NA'::VARCHAR,
    0::INT, 0::INT, 30::INT, NULL::INT,
    'standard'::VARCHAR,
    NULL::VARCHAR, NULL::VARCHAR, 1::INT, 'NA'::VARCHAR, NULL::VARCHAR, 0::DECIMAL, NULL::VARCHAR,
    'gpt-4o'::VARCHAR, 'openai'::VARCHAR,
    'global'::VARCHAR, 'all'::VARCHAR, 'pay_per_token'::VARCHAR,
    10000000::BIGINT, 5000000::BIGINT,
    0::INT, 1::INT, 'NA'::VARCHAR, 'NA'::VARCHAR, 'NA'::VARCHAR
);
"""

print("Testing function call with gpt-4o...")
try:
    result = execute_query(test_query)
    print("✅ Function call successful")
    display(result)
except Exception as e:
    print(f"❌ Error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Check pricing details query

# COMMAND ----------

pricing_query = """
SELECT 
    cloud,
    provider,
    model,
    rate_type,
    dbu_rate,
    input_divisor,
    endpoint_type,
    context_length
FROM lakemeter.sync_product_fmapi_proprietary
WHERE provider IN ('openai', 'anthropic', 'google')
  AND model IN ('gpt-4o', 'gpt-4o-mini', 'claude-sonnet-4-20250514', 'claude-haiku-4', 'gemini-2.5-pro-preview-05-06')
ORDER BY cloud, provider, model, rate_type
LIMIT 50;
"""

print("Testing pricing details query...")
try:
    pricing = execute_query(pricing_query)
    if len(pricing) > 0:
        print(f"✅ Found {len(pricing)} pricing records")
        display(pricing)
    else:
        print("⚠️  No pricing records found!")
        print("\nLet's check what models ARE available:")
        all_models_query = """
        SELECT DISTINCT provider, model
        FROM lakemeter.sync_product_fmapi_proprietary
        ORDER BY provider, model
        LIMIT 100;
        """
        all_models = execute_query(all_models_query)
        display(all_models)
except Exception as e:
    print(f"❌ Error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Check if calculate_fmapi_proprietary_dbu function exists

# COMMAND ----------

check_function_query = """
SELECT 
    p.proname as function_name,
    p.pronargs as num_params
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'lakemeter'
  AND p.proname LIKE '%fmapi%';
"""

try:
    functions = execute_query(check_function_query)
    print("FMAPI-related functions:")
    display(functions)
except Exception as e:
    print(f"❌ Error: {e}")

# COMMAND ----------


