# Databricks notebook source
# MAGIC %md
# MAGIC # Test_Func_12: FMAPI Databricks Cost Calculation
# MAGIC
# MAGIC **Test Matrix:**
# MAGIC - **Models:** llama-3-3-70b, llama-3-1-8b (token-based), llama-3-3-70b (provisioned)
# MAGIC - **Clouds:** AWS, Azure, GCP
# MAGIC - **Tiers:** PREMIUM, ENTERPRISE
# MAGIC - **Pricing Types:** pay_per_token, provisioned_entry, provisioned_scaling

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
import pandas as pd

def get_connection():
    return psycopg2.connect(
        host=LAKEBASE_HOST, port=LAKEBASE_PORT, database=LAKEBASE_DATABASE,
        user=LAKEBASE_USER, password=LAKEBASE_PASSWORD, sslmode='require'
    )

def execute_query(query):
    conn = get_connection()
    try:
        df = pd.read_sql(query, conn)
        return df
    finally:
        conn.close()

print("✅ Connection setup complete!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate Test Scenarios

# COMMAND ----------

clouds = ['AWS', 'AZURE', 'GCP']
region_map = {'AWS': 'us-east-1', 'AZURE': 'eastus', 'GCP': 'us-central1'}

# Token-based scenarios (using models that exist in sync_product_fmapi_databricks)
token_scenarios = [
    {'model': 'llama-3-3-70b', 'endpoint': 'standard', 'context': '32k', 'input_tokens': 10000000, 'output_tokens': 5000000},
    {'model': 'llama-3-1-8b', 'endpoint': 'standard', 'context': '32k', 'input_tokens': 20000000, 'output_tokens': 10000000},
]

# Provisioned throughput scenarios (hourly charges)
provisioned_scenarios = [
    {'model': 'llama-3-3-70b', 'endpoint': 'standard', 'provisioned_type': 'provisioned_entry', 'hours_per_month': 240},
    {'model': 'llama-3-3-70b', 'endpoint': 'standard', 'provisioned_type': 'provisioned_scaling', 'hours_per_month': 480},
]

test_scenarios = []
scenario_id = 1

# Token-based
for cloud in clouds:
    for tier in ['PREMIUM', 'ENTERPRISE']:
        if cloud == 'AZURE' and tier == 'ENTERPRISE':
            continue
        for token_sc in token_scenarios:
            test_scenarios.append({
                'scenario_id': scenario_id,
                'cloud': cloud,
                'region': region_map[cloud],
                'tier': tier,
                'model': token_sc['model'],
                'endpoint': token_sc['endpoint'],
                'context': token_sc['context'],
                'pricing_type': 'pay_per_token',
                'input_tokens': token_sc['input_tokens'],
                'output_tokens': token_sc['output_tokens'],
                'label': f"{cloud} {tier} {token_sc['model']} token"
            })
            scenario_id += 1

# Provisioned throughput
for cloud in clouds:
    for tier in ['PREMIUM', 'ENTERPRISE']:
        if cloud == 'AZURE' and tier == 'ENTERPRISE':
            continue
        for prov_sc in provisioned_scenarios:
            test_scenarios.append({
                'scenario_id': scenario_id,
                'cloud': cloud,
                'region': region_map[cloud],
                'tier': tier,
                'model': prov_sc['model'],
                'endpoint': prov_sc['endpoint'],
                'context': '32k',
                'pricing_type': prov_sc['provisioned_type'],
                'input_tokens': 0,
                'output_tokens': 0,
                'hours_per_month': prov_sc['hours_per_month'],
                'label': f"{cloud} {tier} {prov_sc['model']} {prov_sc['provisioned_type']}"
            })
            scenario_id += 1

print(f"📋 Generated {len(test_scenarios)} scenarios (token-based + provisioned)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Execute Function Calls

# COMMAND ----------

sql_parts = []
for scenario in test_scenarios:
    hours = scenario.get('hours_per_month', 0)
    runs_per_day = int(hours / 30) if hours > 0 else 0
    hours_param = f"{hours}::INT" if hours > 0 else "NULL::INT"  # Pass actual hours for provisioned
    
    sql_parts.append(f"""
    SELECT 
        {scenario['scenario_id']} as scenario_id,
        '{scenario['label']}'::VARCHAR as label,
        '{scenario['cloud']}'::VARCHAR as cloud,
        '{scenario['tier']}'::VARCHAR as tier,
        '{scenario['model']}'::VARCHAR as model,
        '{scenario['pricing_type']}'::VARCHAR as pricing_type,
        *
    FROM lakemeter.calculate_line_item_costs(
        'FMAPI_DATABRICKS'::VARCHAR, '{scenario['cloud']}'::VARCHAR, '{scenario['region']}'::VARCHAR,
        '{scenario['tier']}'::VARCHAR, FALSE::BOOLEAN, FALSE::BOOLEAN, NULL::VARCHAR,
        NULL::VARCHAR, NULL::VARCHAR, 0::INT, 'NA'::VARCHAR, 'NA'::VARCHAR,
        {runs_per_day}::INT, 60::INT, 30::INT, {hours_param},
        'standard'::VARCHAR,
        NULL::VARCHAR, NULL::VARCHAR, 1::INT, 'NA'::VARCHAR, NULL::VARCHAR, 0::DECIMAL, NULL::VARCHAR,
        '{scenario['model']}'::VARCHAR, 'databricks'::VARCHAR,
        '{scenario['endpoint']}'::VARCHAR, '{scenario['context']}'::VARCHAR,
        '{scenario['pricing_type']}'::VARCHAR,
        {scenario['input_tokens']}::BIGINT, {scenario['output_tokens']}::BIGINT,
        0::INT, 1::INT, 'NA'::VARCHAR, 'NA'::VARCHAR, 'NA'::VARCHAR
    )
    """)

full_query = " UNION ALL ".join(sql_parts) + ";"

print(f"🔧 Executing {len(test_scenarios)} function calls...")
results_df = execute_query(full_query)

numeric_cols = ['dbu_per_month', 'dbu_price', 'dbu_cost_per_month', 'cost_per_month']
for col in numeric_cols:
    if col in results_df.columns:
        results_df[col] = pd.to_numeric(results_df[col], errors='coerce')

print(f"✅ Retrieved {len(results_df)} results")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Fetch Pricing Details for Validation

# COMMAND ----------

# Get detailed pricing info from sync_product_fmapi_databricks
pricing_query = """
SELECT 
    cloud,
    model,
    rate_type,
    dbu_rate,
    input_divisor,
    is_hourly
FROM lakemeter.sync_product_fmapi_databricks
WHERE model IN ('llama-3-3-70b', 'llama-3-1-8b')
ORDER BY cloud, model, rate_type;
"""

pricing_details = execute_query(pricing_query)
print("📋 Pricing details from sync_product_fmapi_databricks:")
display(pricing_details)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Display & Validate

# COMMAND ----------

# Add input/output tokens and hours to results for validation
for idx, row in results_df.iterrows():
    scenario = test_scenarios[idx]
    results_df.at[idx, 'input_tokens'] = scenario.get('input_tokens', 0)
    results_df.at[idx, 'output_tokens'] = scenario.get('output_tokens', 0)
    results_df.at[idx, 'hours'] = scenario.get('hours_per_month', 0)

# Separate token-based and provisioned for display
token_based_df = results_df[results_df['pricing_type'] == 'pay_per_token'].copy()
provisioned_df = results_df[results_df['pricing_type'].isin(['provisioned_entry', 'provisioned_scaling'])].copy()

print("=" * 80)
print("FMAPI DATABRICKS TEST RESULTS - TOKEN-BASED")
print("=" * 80)
token_display_cols = ['scenario_id', 'cloud', 'tier', 'model', 'input_tokens', 'output_tokens', 
                      'dbu_per_month', 'dbu_price', 'cost_per_month']
display(token_based_df[[col for col in token_display_cols if col in token_based_df.columns]])

print("\n" + "=" * 80)
print("FMAPI DATABRICKS TEST RESULTS - PROVISIONED")
print("=" * 80)
prov_display_cols = ['scenario_id', 'cloud', 'tier', 'model', 'pricing_type', 'hours',
                     'dbu_per_month', 'dbu_price', 'cost_per_month']
display(provisioned_df[[col for col in prov_display_cols if col in provisioned_df.columns]])

print("\n" + "=" * 80)
print("VALIDATION")
print("=" * 80)

# Check 1: All scenarios should have positive costs
zero_costs = results_df[results_df['cost_per_month'] == 0]
if len(zero_costs) == 0:
    print(f"✅ PASS: All {len(results_df)} scenarios have positive costs")
else:
    print(f"❌ FAIL: {len(zero_costs)} scenarios have $0 costs")
    display(zero_costs[available_cols])

# Check 2: Separate validation for token-based vs provisioned
token_based = results_df[results_df['pricing_type'] == 'pay_per_token']
provisioned = results_df[results_df['pricing_type'].isin(['provisioned_entry', 'provisioned_scaling'])]

print(f"\n📊 Token-based scenarios: {len(token_based)}")
token_zero = token_based[token_based['dbu_per_month'] == 0]
if len(token_zero) == 0:
    print(f"   ✅ PASS: All token-based scenarios have positive dbu_per_month")
else:
    print(f"   ❌ FAIL: {len(token_zero)} token-based scenarios have dbu_per_month=0")
    display(token_zero[available_cols])

print(f"\n📊 Provisioned scenarios: {len(provisioned)}")
prov_zero = provisioned[provisioned['dbu_per_month'] == 0]
if len(prov_zero) == 0:
    print(f"   ✅ PASS: All provisioned scenarios have positive dbu_per_month")
else:
    print(f"   ❌ FAIL: {len(prov_zero)} provisioned scenarios have dbu_per_month=0")
    display(prov_zero[available_cols])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Manual Validation - Sample Calculations

# COMMAND ----------

print("=" * 80)
print("MANUAL VALIDATION - TOKEN-BASED")
print("=" * 80)

# Get pricing rates for llama-3-3-70b
llama_70b_pricing = pricing_details[pricing_details['model'] == 'llama-3-3-70b']
if len(llama_70b_pricing) >= 2:
    input_rate_row = llama_70b_pricing[llama_70b_pricing['rate_type'] == 'input_token'].iloc[0]
    output_rate_row = llama_70b_pricing[llama_70b_pricing['rate_type'] == 'output_token'].iloc[0]
    
    input_rate = float(input_rate_row['dbu_rate'])
    output_rate = float(output_rate_row['dbu_rate'])
    input_divisor = float(input_rate_row['input_divisor'])
    output_divisor = float(output_rate_row['input_divisor'])
    
    # Sample: 10M input, 5M output
    input_tokens = 10000000
    output_tokens = 5000000
    
    print(f"\n📊 Model: llama-3-3-70b")
    print(f"\nInput Token Calculation:")
    print(f"  • Input tokens: {input_tokens:,}")
    print(f"  • Input divisor: {input_divisor:,.0f}")
    print(f"  • Input DBU rate: {input_rate}")
    print(f"  • Input DBU = {input_tokens:,} / {input_divisor:,.0f} × {input_rate} = {input_tokens / input_divisor * input_rate:.4f}")
    
    print(f"\nOutput Token Calculation:")
    print(f"  • Output tokens: {output_tokens:,}")
    print(f"  • Output divisor: {output_divisor:,.0f}")
    print(f"  • Output DBU rate: {output_rate}")
    print(f"  • Output DBU = {output_tokens:,} / {output_divisor:,.0f} × {output_rate} = {output_tokens / output_divisor * output_rate:.4f}")
    
    total_dbu = (input_tokens / input_divisor * input_rate) + (output_tokens / output_divisor * output_rate)
    dbu_price = 0.07
    total_cost = total_dbu * dbu_price
    
    print(f"\nTotal Calculation:")
    print(f"  • Total DBU = {total_dbu:.4f}")
    print(f"  • DBU price = ${dbu_price}")
    print(f"  • Total cost = {total_dbu:.4f} × ${dbu_price} = ${total_cost:.2f}")
    
    # Compare with test results
    test_result = token_based_df[
        (token_based_df['model'] == 'llama-3-3-70b') & 
        (token_based_df['cloud'] == 'AWS') &
        (token_based_df['tier'] == 'PREMIUM')
    ]
    if len(test_result) > 0:
        actual_dbu = float(test_result['dbu_per_month'].iloc[0])
        actual_cost = float(test_result['cost_per_month'].iloc[0])
        print(f"\nTest Result Comparison:")
        print(f"  • Expected DBU: {total_dbu:.4f}")
        print(f"  • Actual DBU:   {actual_dbu:.4f}")
        print(f"  • Match: {'✅' if abs(total_dbu - actual_dbu) < 0.01 else '❌'}")
        print(f"  • Expected Cost: ${total_cost:.2f}")
        print(f"  • Actual Cost:   ${actual_cost:.2f}")
        print(f"  • Match: {'✅' if abs(total_cost - actual_cost) < 0.01 else '❌'}")

print("\n" + "=" * 80)
print("MANUAL VALIDATION - PROVISIONED")
print("=" * 80)

# Get provisioned rates
llama_prov_entry = pricing_details[
    (pricing_details['model'] == 'llama-3-3-70b') & 
    (pricing_details['rate_type'] == 'provisioned_entry') &
    (pricing_details['is_hourly'] == True)
]

if len(llama_prov_entry) > 0:
    entry_rate = float(llama_prov_entry['dbu_rate'].iloc[0])
    hours = 240
    
    print(f"\n📊 Model: llama-3-3-70b (provisioned_entry)")
    print(f"\nProvisioned Entry Calculation:")
    print(f"  • DBU per hour: {entry_rate}")
    print(f"  • Hours per month: {hours}")
    print(f"  • Total DBU = {entry_rate} × {hours} = {entry_rate * hours:.2f}")
    
    total_dbu_prov = entry_rate * hours
    total_cost_prov = total_dbu_prov * 0.07
    
    print(f"\nTotal Calculation:")
    print(f"  • Total DBU = {total_dbu_prov:.2f}")
    print(f"  • DBU price = $0.07")
    print(f"  • Total cost = {total_dbu_prov:.2f} × $0.07 = ${total_cost_prov:.2f}")
    
    # Compare with test results
    test_result_prov = provisioned_df[
        (provisioned_df['model'] == 'llama-3-3-70b') & 
        (provisioned_df['pricing_type'] == 'provisioned_entry') &
        (provisioned_df['cloud'] == 'AWS') &
        (provisioned_df['tier'] == 'PREMIUM')
    ]
    if len(test_result_prov) > 0:
        actual_dbu_prov = float(test_result_prov['dbu_per_month'].iloc[0])
        actual_cost_prov = float(test_result_prov['cost_per_month'].iloc[0])
        print(f"\nTest Result Comparison:")
        print(f"  • Expected DBU: {total_dbu_prov:.2f}")
        print(f"  • Actual DBU:   {actual_dbu_prov:.2f}")
        print(f"  • Match: {'✅' if abs(total_dbu_prov - actual_dbu_prov) < 0.01 else '❌'}")
        print(f"  • Expected Cost: ${total_cost_prov:.2f}")
        print(f"  • Actual Cost:   ${actual_cost_prov:.2f}")
        print(f"  • Match: {'✅' if abs(total_cost_prov - actual_cost_prov) < 0.01 else '❌'}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 80)
print("FMAPI DATABRICKS TEST COMPLETE")
print("=" * 80)
