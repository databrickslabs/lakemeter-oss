# Databricks notebook source
# MAGIC %md
# MAGIC # Debug: Why Claude Sonnet 4-1 Returns 0 DBU

# COMMAND ----------

%run ../00_Lakebase_Config

# COMMAND ----------

import pandas as pd

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check All Data for claude-sonnet-4-1

# COMMAND ----------

query = """
SELECT 
    cloud,
    provider,
    model,
    endpoint_type,
    context_length,
    rate_type,
    dbu_rate,
    input_divisor,
    is_hourly
FROM lakemeter.sync_product_fmapi_proprietary
WHERE UPPER(model) = 'CLAUDE-SONNET-4-1'
ORDER BY cloud, endpoint_type, context_length, rate_type;
"""

results = execute_query(query)

if results:
    df = pd.DataFrame(results, columns=['cloud', 'provider', 'model', 'endpoint_type', 'context_length', 'rate_type', 'dbu_rate', 'input_divisor', 'is_hourly'])
    print(f"✅ Found {len(df)} pricing records for claude-sonnet-4-1")
    display(df)
else:
    print("❌ No pricing data found for claude-sonnet-4-1!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Function Call with Test Parameters

# COMMAND ----------

print("=" * 100)
print("TESTING: calculate_fmapi_proprietary_dbu()")
print("=" * 100)

test_params = {
    'cloud': 'AWS',
    'provider': 'anthropic',
    'model': 'claude-sonnet-4-1',
    'endpoint_type': 'global',
    'context_length': 'all',
    'rate_type': 'input_token',
    'quantity': 10000000
}

print("\nTest Parameters:")
for key, value in test_params.items():
    print(f"  {key}: {value}")

query = f"""
SELECT lakemeter.calculate_fmapi_proprietary_dbu(
    '{test_params['cloud']}'::VARCHAR,
    '{test_params['provider']}'::VARCHAR,
    '{test_params['model']}'::VARCHAR,
    '{test_params['endpoint_type']}'::VARCHAR,
    '{test_params['context_length']}'::VARCHAR,
    '{test_params['rate_type']}'::VARCHAR,
    {test_params['quantity']}::BIGINT
) as dbu;
"""

result = execute_query(query)

if result:
    dbu = result[0][0]
    print(f"\n✅ Function returned: {dbu} DBU")
    
    if dbu and dbu > 0:
        print(f"   ✅ SUCCESS: Function is working!")
    else:
        print(f"   ❌ FAIL: Function returned 0!")
        print("\n   Let's check what the function is looking for...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check What Pricing Query Would Find

# COMMAND ----------

test_params = {
    'cloud': 'AWS',
    'provider': 'anthropic',
    'model': 'claude-sonnet-4-1',
    'endpoint_type': 'global',
    'context_length': 'all',
    'rate_type': 'input_token'
}

print("=" * 100)
print("CHECKING: What does the pricing query find?")
print("=" * 100)

# This is the exact query the function uses
query = f"""
SELECT 
    dbu_rate,
    COALESCE(input_divisor, 1) as divisor,
    COALESCE(is_hourly, FALSE) as is_hourly
FROM lakemeter.sync_product_fmapi_proprietary
WHERE UPPER(cloud) = UPPER('{test_params['cloud']}')
  AND UPPER(provider) = UPPER('{test_params['provider']}')
  AND UPPER(model) = UPPER('{test_params['model']}')
  AND LOWER(endpoint_type) = LOWER('{test_params['endpoint_type']}')
  AND LOWER(context_length) = LOWER('{test_params['context_length']}')
  AND rate_type = '{test_params['rate_type']}'
LIMIT 1;
"""

print("\nQuery:")
print(query)

result = execute_query(query)

if result and len(result) > 0:
    dbu_rate, divisor, is_hourly = result[0]
    print(f"\n✅ FOUND pricing data:")
    print(f"   DBU rate: {dbu_rate}")
    print(f"   Divisor: {divisor}")
    print(f"   Is hourly: {is_hourly}")
    
    # Calculate what DBU should be
    quantity = 10000000
    if is_hourly:
        expected_dbu = quantity * dbu_rate
    else:
        expected_dbu = (quantity / divisor) * dbu_rate
    
    print(f"\n   Expected DBU for {quantity:,} tokens: {expected_dbu:,.2f}")
else:
    print(f"\n❌ NOT FOUND!")
    print("\n   Trying to find what DOES exist...")
    
    # Try to find what combinations exist
    relaxed_query = f"""
    SELECT DISTINCT
        cloud,
        endpoint_type,
        context_length,
        rate_type
    FROM lakemeter.sync_product_fmapi_proprietary
    WHERE UPPER(provider) = 'ANTHROPIC'
      AND UPPER(model) = 'CLAUDE-SONNET-4-1'
    ORDER BY cloud, endpoint_type, context_length, rate_type;
    """
    
    relaxed_results = execute_query(relaxed_query)
    if relaxed_results:
        print("\n   Available combinations for claude-sonnet-4-1:")
        for row in relaxed_results:
            print(f"   • cloud={row[0]}, endpoint={row[1]}, context={row[2]}, rate_type={row[3]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Try All Possible Combinations

# COMMAND ----------

clouds = ['AWS', 'AZURE', 'GCP']
endpoints = ['global', 'in_geo']
contexts = ['short', 'standard', 'long', 'all']
rate_types = ['input_token', 'output_token', 'cache_read', 'cache_write', 'batch_inference']

print("=" * 100)
print("TESTING ALL COMBINATIONS")
print("=" * 100)

successful_combos = []

for cloud in clouds:
    for endpoint in endpoints:
        for context in contexts:
            for rate_type in rate_types:
                query = f"""
                SELECT COUNT(*) as count
                FROM lakemeter.sync_product_fmapi_proprietary
                WHERE UPPER(cloud) = UPPER('{cloud}')
                  AND UPPER(provider) = 'ANTHROPIC'
                  AND UPPER(model) = 'CLAUDE-SONNET-4-1'
                  AND LOWER(endpoint_type) = LOWER('{endpoint}')
                  AND LOWER(context_length) = LOWER('{context}')
                  AND rate_type = '{rate_type}';
                """
                
                result = execute_query(query)
                if result and result[0][0] > 0:
                    successful_combos.append(f"{cloud}/{endpoint}/{context}/{rate_type}")

print(f"\n✅ Found {len(successful_combos)} valid combinations:")
for combo in successful_combos[:20]:  # Show first 20
    print(f"   • {combo}")

if len(successful_combos) > 20:
    print(f"   ... and {len(successful_combos) - 20} more")


