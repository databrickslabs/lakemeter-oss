# Databricks notebook source
# MAGIC %md
# MAGIC # 🐛 Debug: FMAPI Zero Costs Issue
# MAGIC
# MAGIC Trace through the entire calculation flow to find why all costs are $0

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import pandas as pd
import psycopg2
from decimal import Decimal

print("✅ Config loaded")
print(f"   Host: {LAKEBASE_HOST}")
print(f"   Database: {LAKEBASE_DATABASE}")

# COMMAND ----------

def get_connection():
    return psycopg2.connect(
        host=LAKEBASE_HOST,
        port=LAKEBASE_PORT,
        database=LAKEBASE_DATABASE,
        user=LAKEBASE_USER,
        password=LAKEBASE_PASSWORD
    )

def execute_query(query):
    conn = get_connection()
    try:
        df = pd.read_sql_query(query, conn)
        return df
    finally:
        conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Scenario: AWS PREMIUM dbrx-instruct pay-per-token

# COMMAND ----------

test_params = {
    'cloud': 'AWS',
    'region': 'us-east-1',
    'tier': 'PREMIUM',
    'model': 'dbrx-instruct',
    'pricing_type': 'pay_per_token',
    'endpoint': 'standard',
    'context': '32k',
    'input_tokens': 1000000,
    'output_tokens': 500000,
    'runs_per_day': 0,
    'avg_runtime': 60,
    'days_per_month': 30,
    'hours_per_month': None
}

print("=" * 80)
print("TEST SCENARIO")
print("=" * 80)
for k, v in test_params.items():
    print(f"  {k}: {v}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Check FMAPI Pricing Data

# COMMAND ----------

print("=" * 80)
print("STEP 1: Check sync_product_fmapi_databricks pricing")
print("=" * 80)

query = f"""
SELECT 
    cloud,
    model,
    rate_type,
    dbu_rate,
    input_divisor,
    is_hourly
FROM lakemeter.sync_product_fmapi_databricks
WHERE UPPER(cloud) = '{test_params['cloud']}'
  AND UPPER(model) = '{test_params['model']}'
ORDER BY rate_type;
"""

pricing_df = execute_query(query)
print(f"\n✅ Found {len(pricing_df)} pricing records:")
display(pricing_df)

if len(pricing_df) == 0:
    print("❌ NO PRICING DATA! This explains zero costs!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Test calculate_hours_per_month()

# COMMAND ----------

print("=" * 80)
print("STEP 2: Test calculate_hours_per_month()")
print("=" * 80)

# Test with NULL hours_per_month (should return 0 for token-based)
query1 = f"""
SELECT lakemeter.calculate_hours_per_month(
    'FMAPI_DATABRICKS'::VARCHAR,
    {test_params['runs_per_day']}::INT,
    {test_params['avg_runtime']}::INT,
    {test_params['days_per_month']}::INT,
    '{test_params['pricing_type']}'::VARCHAR,
    NULL::INT
) as hours_per_month;
"""

result1 = execute_query(query1)
hours_null = float(result1.iloc[0]['hours_per_month'])
print(f"\n🔎 With NULL hours_per_month (token-based):")
print(f"   Hours: {hours_null}")
print(f"   Expected: 0 (token-based has no hourly charges)")
if hours_null == 0:
    print("   ✅ CORRECT")
else:
    print(f"   ❌ WRONG! Should be 0, got {hours_null}")

# Test with explicit 720 hours (for provisioned)
query2 = f"""
SELECT lakemeter.calculate_hours_per_month(
    'FMAPI_DATABRICKS'::VARCHAR,
    30::INT,
    60::INT,
    30::INT,
    'provisioned_entry'::VARCHAR,
    720::INT
) as hours_per_month;
"""

result2 = execute_query(query2)
hours_explicit = float(result2.iloc[0]['hours_per_month'])
print(f"\n🔎 With explicit 720 hours (provisioned):")
print(f"   Hours: {hours_explicit}")
print(f"   Expected: 720")
if hours_explicit == 720:
    print("   ✅ CORRECT")
else:
    print(f"   ❌ WRONG! Should be 720, got {hours_explicit}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Test calculate_fmapi_databricks_dbu()

# COMMAND ----------

print("=" * 80)
print("STEP 3: Test calculate_fmapi_databricks_dbu()")
print("=" * 80)

query = f"""
SELECT lakemeter.calculate_fmapi_databricks_dbu(
    '{test_params['cloud']}'::VARCHAR,
    '{test_params['model']}'::VARCHAR,
    '{test_params['pricing_type']}'::VARCHAR,
    {test_params['input_tokens']}::BIGINT,
    {test_params['output_tokens']}::BIGINT,
    0::DECIMAL
) as dbu_per_month;
"""

result = execute_query(query)
dbu_per_month = float(result.iloc[0]['dbu_per_month'])

print(f"\n🔎 DBU Calculation:")
print(f"   Input tokens: {test_params['input_tokens']:,}")
print(f"   Output tokens: {test_params['output_tokens']:,}")
print(f"   DBU per month: {dbu_per_month}")

# Manual calculation
if len(pricing_df) >= 2:
    input_row = pricing_df[pricing_df['rate_type'] == 'input_token']
    output_row = pricing_df[pricing_df['rate_type'] == 'output_token']
    
    if len(input_row) > 0 and len(output_row) > 0:
        input_rate = input_row['dbu_rate'].iloc[0]
        output_rate = output_row['dbu_rate'].iloc[0]
        input_divisor = input_row['input_divisor'].iloc[0] if 'input_divisor' in input_row else 1000000
        output_divisor = output_row['input_divisor'].iloc[0] if 'input_divisor' in output_row else 1000000
        
        expected_dbu = (test_params['input_tokens'] / input_divisor * input_rate) + \
                       (test_params['output_tokens'] / output_divisor * output_rate)
        print(f"\n📊 Manual Calculation:")
        print(f"   Input: {test_params['input_tokens']:,} / {input_divisor:,} × {input_rate} = {test_params['input_tokens'] / input_divisor * input_rate:.4f}")
        print(f"   Output: {test_params['output_tokens']:,} / {output_divisor:,} × {output_rate} = {test_params['output_tokens'] / output_divisor * output_rate:.4f}")
        print(f"   Total: {expected_dbu:.4f}")
        
        if abs(dbu_per_month - expected_dbu) < 0.01:
            print("   ✅ MATCH!")
        else:
            print(f"   ❌ MISMATCH! Function returned {dbu_per_month}, expected {expected_dbu}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Test get_dbu_price()

# COMMAND ----------

print("=" * 80)
print("STEP 4: Test get_dbu_price()")
print("=" * 80)

# First check what product type should be used
query_product = f"""
SELECT lakemeter.get_product_type_for_pricing(
    'FMAPI_DATABRICKS'::VARCHAR,
    NULL::VARCHAR,
    NULL::VARCHAR,
    NULL::VARCHAR,
    'databricks'::VARCHAR,
    NULL::VARCHAR
) as product_type;
"""

result = execute_query(query_product)
product_type = result.iloc[0]['product_type']
print(f"\n🔎 Product type for FMAPI_DATABRICKS: {product_type}")

# Check if this product type exists in pricing
query_check = f"""
SELECT 
    tier,
    price_per_dbu
FROM lakemeter.sync_pricing_dbu_rates
WHERE UPPER(cloud) = '{test_params['cloud']}'
  AND UPPER(region) = '{test_params['region']}'
  AND UPPER(product_type) = '{product_type}'
ORDER BY tier;
"""

pricing_check = execute_query(query_check)
print(f"\n✅ Found {len(pricing_check)} pricing records for {product_type}:")
display(pricing_check)

# Now test get_dbu_price
query_price = f"""
SELECT lakemeter.get_dbu_price(
    '{test_params['cloud']}'::VARCHAR,
    '{test_params['region']}'::VARCHAR,
    '{test_params['tier']}'::VARCHAR,
    '{product_type}'::VARCHAR
) as dbu_price;
"""

result = execute_query(query_price)
dbu_price = float(result.iloc[0]['dbu_price'])
print(f"\n🔎 DBU Price: ${dbu_price}")

if dbu_price == 0:
    print("   ❌ ZERO PRICE! This is the problem!")
else:
    print("   ✅ Has price")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Test Full calculate_line_item_costs()

# COMMAND ----------

print("=" * 80)
print("STEP 5: Test calculate_line_item_costs()")
print("=" * 80)

query = f"""
SELECT *
FROM lakemeter.calculate_line_item_costs(
    'FMAPI_DATABRICKS'::VARCHAR,
    '{test_params['cloud']}'::VARCHAR,
    '{test_params['region']}'::VARCHAR,
    '{test_params['tier']}'::VARCHAR,
    FALSE::BOOLEAN,
    FALSE::BOOLEAN,
    NULL::VARCHAR,
    NULL::VARCHAR,
    NULL::VARCHAR,
    0::INT,
    'NA'::VARCHAR,
    'NA'::VARCHAR,
    {test_params['runs_per_day']}::INT,
    {test_params['avg_runtime']}::INT,
    {test_params['days_per_month']}::INT,
    NULL::INT,
    'standard'::VARCHAR,
    NULL::VARCHAR,
    NULL::VARCHAR,
    1::INT,
    'NA'::VARCHAR,
    NULL::VARCHAR,
    0::DECIMAL,
    NULL::VARCHAR,
    '{test_params['model']}'::VARCHAR,
    'databricks'::VARCHAR,
    '{test_params['endpoint']}'::VARCHAR,
    '{test_params['context']}'::VARCHAR,
    '{test_params['pricing_type']}'::VARCHAR,
    {test_params['input_tokens']}::BIGINT,
    {test_params['output_tokens']}::BIGINT,
    0::INT,
    1::INT,
    'NA'::VARCHAR,
    'NA'::VARCHAR,
    'NA'::VARCHAR
);
"""

result = execute_query(query)
print(f"\n✅ Function returned {len(result)} row(s)")

# Convert to numeric
numeric_cols = ['hours_per_month', 'dbu_per_hour', 'dbu_per_month', 'dbu_price', 'dbu_cost_per_month', 'cost_per_month']
for col in numeric_cols:
    if col in result.columns:
        result[col] = pd.to_numeric(result[col], errors='coerce')

print("\n📊 Results:")
display_cols = [col for col in numeric_cols if col in result.columns]
display(result[display_cols])

print("\n" + "=" * 80)
print("FINAL DIAGNOSIS")
print("=" * 80)

if result['cost_per_month'].iloc[0] == 0:
    print("❌ Cost is ZERO!")
    print("\nChecking each component:")
    print(f"  • dbu_per_month: {result['dbu_per_month'].iloc[0]}")
    print(f"  • dbu_price: {result['dbu_price'].iloc[0]}")
    
    if result['dbu_per_month'].iloc[0] == 0:
        print("\n❌ DBU per month is 0 - check calculate_fmapi_databricks_dbu()")
    elif result['dbu_price'].iloc[0] == 0:
        print("\n❌ DBU price is 0 - check get_dbu_price() and product type mapping")
    else:
        print("\n❌ Both values exist but cost still 0 - check multiplication logic")
else:
    print(f"✅ Cost is ${result['cost_per_month'].iloc[0]:,.2f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Check Provisioned Throughput (if applicable)

# COMMAND ----------

print("=" * 80)
print("STEP 6: Test Provisioned Throughput Scenario")
print("=" * 80)

# Test provisioned_entry with 720 hours
query = f"""
SELECT *
FROM lakemeter.calculate_line_item_costs(
    'FMAPI_DATABRICKS'::VARCHAR,
    'AWS'::VARCHAR,
    'us-east-1'::VARCHAR,
    'PREMIUM'::VARCHAR,
    FALSE::BOOLEAN,
    FALSE::BOOLEAN,
    NULL::VARCHAR,
    NULL::VARCHAR,
    NULL::VARCHAR,
    0::INT,
    'NA'::VARCHAR,
    'NA'::VARCHAR,
    30::INT,
    60::INT,
    30::INT,
    720::INT,
    'standard'::VARCHAR,
    NULL::VARCHAR,
    NULL::VARCHAR,
    1::INT,
    'NA'::VARCHAR,
    NULL::VARCHAR,
    0::DECIMAL,
    NULL::VARCHAR,
    'mixtral-8x7b-instruct'::VARCHAR,
    'databricks'::VARCHAR,
    'standard'::VARCHAR,
    '32k'::VARCHAR,
    'provisioned_entry'::VARCHAR,
    0::BIGINT,
    0::BIGINT,
    0::INT,
    1::INT,
    'NA'::VARCHAR,
    'NA'::VARCHAR,
    'NA'::VARCHAR
);
"""

result = execute_query(query)
print(f"\n✅ Function returned {len(result)} row(s)")

# Convert to numeric
for col in numeric_cols:
    if col in result.columns:
        result[col] = pd.to_numeric(result[col], errors='coerce')

print("\n📊 Provisioned Entry Results:")
display(result[display_cols])

if result['cost_per_month'].iloc[0] == 0:
    print("\n❌ Provisioned cost is also ZERO!")
    print(f"  • hours_per_month: {result['hours_per_month'].iloc[0]}")
    print(f"  • dbu_per_hour: {result['dbu_per_hour'].iloc[0] if 'dbu_per_hour' in result.columns else 'N/A'}")
    print(f"  • dbu_per_month: {result['dbu_per_month'].iloc[0]}")
    print(f"  • dbu_price: {result['dbu_price'].iloc[0]}")
else:
    print(f"\n✅ Provisioned cost is ${result['cost_per_month'].iloc[0]:,.2f}")

