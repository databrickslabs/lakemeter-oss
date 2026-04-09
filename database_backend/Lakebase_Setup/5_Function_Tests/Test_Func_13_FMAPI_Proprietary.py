# Databricks notebook source
# MAGIC %md
# MAGIC # Function Test: FMAPI Proprietary (One Line = One rate_type)
# MAGIC
# MAGIC **NEW DESIGN:** Each line item represents ONE rate_type for clean cost breakdown!
# MAGIC
# MAGIC Tests `calculate_fmapi_proprietary_dbu()` with all rate_types:
# MAGIC - **input_token** - Input tokens (prompt)
# MAGIC - **output_token** - Output tokens (response)
# MAGIC - **cache_read** - Reading from prompt cache
# MAGIC - **cache_write** - Writing to prompt cache
# MAGIC - **batch_inference** - Batch processing (hourly)
# MAGIC
# MAGIC **Providers:**
# MAGIC - OpenAI: gpt-4o, gpt-5
# MAGIC - Anthropic: claude-sonnet-4, claude-opus-4
# MAGIC - Google: gemini-2-5-pro
# MAGIC
# MAGIC **Key Change:** Instead of combining input+output in one line, we create separate lines for each rate_type!

# COMMAND ----------

%run ../00_Lakebase_Config

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Scenarios: One Line = One rate_type
# MAGIC
# MAGIC We'll test by creating **separate line items** for each rate_type to demonstrate the clean design.

# COMMAND ----------

import pandas as pd

# Test configuration
test_data = []

# Scenario 1: Standard API Usage (input + output as separate lines)
# AWS PREMIUM - Anthropic Claude Sonnet
test_data.append({
    'line_name': 'Claude Sonnet - Input Tokens',
    'cloud': 'AWS',
    'region': 'us-east-1',
    'tier': 'PREMIUM',
    'provider': 'anthropic',
    'model': 'claude-sonnet-4-1',
    'endpoint_type': 'global',
    'context_length': 'all',
    'rate_type': 'input_token',
    'quantity': 10_000_000  # 10M tokens
})

test_data.append({
    'line_name': 'Claude Sonnet - Output Tokens',
    'cloud': 'AWS',
    'region': 'us-east-1',
    'tier': 'PREMIUM',
    'provider': 'anthropic',
    'model': 'claude-sonnet-4-1',
    'endpoint_type': 'global',
    'context_length': 'all',
    'rate_type': 'output_token',
    'quantity': 5_000_000  # 5M tokens
})

# Scenario 2: Cached API Usage (cache_read + cache_write as separate lines)
# AWS ENTERPRISE - Anthropic Claude Haiku
test_data.append({
    'line_name': 'Claude Haiku - Cache Read',
    'cloud': 'AWS',
    'region': 'us-east-1',
    'tier': 'ENTERPRISE',
    'provider': 'anthropic',
    'model': 'claude-haiku-4-5',
    'endpoint_type': 'global',
    'context_length': 'all',
    'rate_type': 'cache_read',
    'quantity': 20_000_000  # 20M cached tokens read
})

test_data.append({
    'line_name': 'Claude Haiku - Cache Write',
    'cloud': 'AWS',
    'region': 'us-east-1',
    'tier': 'ENTERPRISE',
    'provider': 'anthropic',
    'model': 'claude-haiku-4-5',
    'endpoint_type': 'global',
    'context_length': 'all',
    'rate_type': 'cache_write',
    'quantity': 5_000_000  # 5M tokens written to cache
})

# Scenario 3: Batch Inference (hourly pricing)
# AWS PREMIUM - Anthropic Claude Opus
test_data.append({
    'line_name': 'Claude Opus - Batch Processing',
    'cloud': 'AWS',
    'region': 'us-east-1',
    'tier': 'PREMIUM',
    'provider': 'anthropic',
    'model': 'claude-opus-4',
    'endpoint_type': 'global',
    'context_length': 'all',
    'rate_type': 'batch_inference',
    'quantity': 720  # 720 hours (24/7 for 30 days)
})

# Scenario 4: Azure - OpenAI GPT
test_data.append({
    'line_name': 'GPT-5 - Input Tokens',
    'cloud': 'AZURE',
    'region': 'eastus',
    'tier': 'PREMIUM',
    'provider': 'openai',
    'model': 'gpt-5',
    'endpoint_type': 'global',
    'context_length': 'all',
    'rate_type': 'input_token',
    'quantity': 15_000_000
})

test_data.append({
    'line_name': 'GPT-5 - Output Tokens',
    'cloud': 'AZURE',
    'region': 'eastus',
    'tier': 'PREMIUM',
    'provider': 'openai',
    'model': 'gpt-5',
    'endpoint_type': 'global',
    'context_length': 'all',
    'rate_type': 'output_token',
    'quantity': 7_500_000
})

# Scenario 5: GCP - Google Gemini
test_data.append({
    'line_name': 'Gemini Pro - Input Tokens',
    'cloud': 'GCP',
    'region': 'us-central1',
    'tier': 'ENTERPRISE',
    'provider': 'google',
    'model': 'gemini-2-5-pro',
    'endpoint_type': 'global',
    'context_length': 'short',
    'rate_type': 'input_token',
    'quantity': 12_000_000
})

test_data.append({
    'line_name': 'Gemini Pro - Output Tokens',
    'cloud': 'GCP',
    'region': 'us-central1',
    'tier': 'ENTERPRISE',
    'provider': 'google',
    'model': 'gemini-2-5-pro',
    'endpoint_type': 'global',
    'context_length': 'short',
    'rate_type': 'output_token',
    'quantity': 6_000_000
})

print(f"✅ Created {len(test_data)} test line items (ONE line = ONE rate_type)")
print("\n📋 Test Scenarios:")
for i, item in enumerate(test_data, 1):
    print(f"   {i}. {item['line_name']} - {item['rate_type']} ({item['quantity']:,})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Execute Tests: Call Simplified Function

# COMMAND ----------

# Call the orchestrator function for each line item
results = []

for item in test_data:
    # Call calculate_line_item_costs() - the MAIN orchestrator!
    query = f"""
    SELECT *
    FROM lakemeter.calculate_line_item_costs(
        'FMAPI_PROPRIETARY'::VARCHAR,      -- p_workload_type
        '{item['cloud']}'::VARCHAR,         -- p_cloud
        '{item['region']}'::VARCHAR,        -- p_region
        '{item['tier']}'::VARCHAR,          -- p_tier
        FALSE::BOOLEAN,                     -- p_serverless_enabled
        FALSE::BOOLEAN,                     -- p_photon_enabled
        NULL::VARCHAR,                      -- p_dlt_edition
        NULL::VARCHAR,                      -- p_driver_node_type
        NULL::VARCHAR,                      -- p_worker_node_type
        0::INT,                             -- p_num_workers
        'on_demand'::VARCHAR,               -- p_driver_pricing_tier
        'on_demand'::VARCHAR,               -- p_worker_pricing_tier
        0::INT,                             -- p_runs_per_day
        0::INT,                             -- p_avg_runtime_minutes
        30::INT,                            -- p_days_per_month
        NULL::INT,                          -- p_hours_per_month
        'standard'::VARCHAR,                -- p_serverless_mode
        NULL::VARCHAR,                      -- p_dbsql_warehouse_type
        NULL::VARCHAR,                      -- p_dbsql_warehouse_size
        1::INT,                             -- p_dbsql_num_clusters
        'on_demand'::VARCHAR,               -- p_dbsql_vm_pricing_tier
        NULL::VARCHAR,                      -- p_vector_search_mode
        0::DECIMAL,                         -- p_vector_search_capacity_millions
        NULL::VARCHAR,                      -- p_serverless_size
        '{item['model']}'::VARCHAR,         -- p_fmapi_model
        '{item['provider']}'::VARCHAR,      -- p_fmapi_provider
        '{item['endpoint_type']}'::VARCHAR, -- p_fmapi_endpoint_type
        '{item['context_length']}'::VARCHAR,-- p_fmapi_context_length
        '{item['rate_type']}'::VARCHAR,     -- p_fmapi_rate_type
        {item['quantity']}::BIGINT,         -- p_fmapi_quantity
        0::INT,                             -- p_lakebase_cu
        1::INT,                             -- p_lakebase_ha_nodes
        'NA'::VARCHAR,                      -- p_driver_payment_option
        'NA'::VARCHAR,                      -- p_worker_payment_option
        'NA'::VARCHAR                       -- p_dbsql_vm_payment_option
    )
    """
    
    result = execute_query(query)
    if result and len(result) > 0:
        row = result[0]
        # Orchestrator returns: dbu_per_hour, hours_per_month, dbu_per_month, dbu_price, 
        #                       dbu_cost_per_month, driver_vm_cost_per_hour, worker_vm_cost_per_hour,
        #                       total_vm_cost_per_hour, driver_vm_cost_per_month, total_worker_vm_cost_per_month,
        #                       vm_cost_per_month, cost_per_month
        results.append({
            'line_item': item['line_name'],
            'cloud': item['cloud'],
            'region': item['region'],
            'tier': item['tier'],
            'provider': item['provider'],
            'model': item['model'],
            'rate_type': item['rate_type'],
            'quantity': item['quantity'],
            'dbu_per_hour': float(row[0]) if row[0] else 0,
            'hours_per_month': float(row[1]) if row[1] else 0,
            'dbu_per_month': float(row[2]) if row[2] else 0,
            'dbu_price': float(row[3]) if row[3] else 0,
            'dbu_cost_per_month': float(row[4]) if row[4] else 0,
            'vm_cost_per_month': float(row[10]) if row[10] else 0,
            'cost_per_month': float(row[11]) if row[11] else 0
        })

results_df = pd.DataFrame(results)
print(f"\n✅ Executed {len(results)} test scenarios")
display(results_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation: Check Results

# COMMAND ----------

# Validation checks
print("=" * 100)
print("🔍 VALIDATION RESULTS")
print("=" * 100)

# Check 1: All scenarios should have positive DBU values
zero_dbu = results_df[results_df['dbu_per_month'] == 0]
if len(zero_dbu) > 0:
    print(f"\n❌ FAIL: {len(zero_dbu)} scenarios have $0 DBU:")
    display(zero_dbu[['line_item', 'cloud', 'tier', 'rate_type', 'dbu_per_month']])
else:
    print("\n✅ PASS: All scenarios have positive DBU values")

# Check 2: All scenarios should have positive costs
zero_cost = results_df[results_df['cost_per_month'] == 0]
if len(zero_cost) > 0:
    print(f"\n❌ FAIL: {len(zero_cost)} scenarios have $0 costs:")
    display(zero_cost[['line_item', 'cloud', 'tier', 'rate_type', 'cost_per_month']])
else:
    print("\n✅ PASS: All scenarios have positive costs")

# Check 3: Batch inference should have higher DBU (it's hourly × 720 hours)
batch_items = results_df[results_df['rate_type'] == 'batch_inference']
if len(batch_items) > 0:
    avg_batch_dbu = batch_items['dbu_per_month'].mean()
    token_items = results_df[results_df['rate_type'].isin(['input_token', 'output_token'])]
    avg_token_dbu = token_items['dbu_per_month'].mean()
    
    if avg_batch_dbu > avg_token_dbu:
        print(f"\n✅ PASS: Batch inference has higher DBU ({avg_batch_dbu:.2f}) than token-based ({avg_token_dbu:.2f})")
    else:
        print(f"\n⚠️  WARNING: Batch DBU ({avg_batch_dbu:.2f}) should be higher than token DBU ({avg_token_dbu:.2f})")

# Check 4: Cache reads should be cheaper than input tokens (same quantity)
cache_read = results_df[results_df['rate_type'] == 'cache_read']
input_tokens = results_df[results_df['rate_type'] == 'input_token']

if len(cache_read) > 0 and len(input_tokens) > 0:
    cache_rate = cache_read.iloc[0]['dbu_per_month'] / cache_read.iloc[0]['quantity']
    input_rate = input_tokens.iloc[0]['dbu_per_month'] / input_tokens.iloc[0]['quantity']
    
    if cache_rate < input_rate:
        print(f"\n✅ PASS: Cache read rate ({cache_rate:.10f}) < Input token rate ({input_rate:.10f})")
    else:
        print(f"\n⚠️  WARNING: Cache read should be cheaper than input tokens")

# Check 5: Output tokens should be more expensive than input tokens
output_tokens = results_df[results_df['rate_type'] == 'output_token']

if len(output_tokens) > 0 and len(input_tokens) > 0:
    output_rate = output_tokens.iloc[0]['dbu_per_month'] / output_tokens.iloc[0]['quantity']
    input_rate = input_tokens.iloc[0]['dbu_per_month'] / input_tokens.iloc[0]['quantity']
    
    if output_rate > input_rate:
        print(f"\n✅ PASS: Output rate ({output_rate:.10f}) > Input rate ({input_rate:.10f})")
    else:
        print(f"\n⚠️  WARNING: Output tokens are typically more expensive than input")

print("\n" + "=" * 100)
print("✅ VALIDATION COMPLETE")
print("=" * 100)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary: Cost Breakdown by rate_type
# MAGIC
# MAGIC This shows the beauty of the one line = one rate_type design!

# COMMAND ----------

# Group by rate_type to show cost breakdown
summary = results_df.groupby('rate_type').agg({
    'quantity': 'sum',
    'dbu_per_month': 'sum',
    'cost_per_month': 'sum'
}).reset_index()

summary['avg_dbu_per_unit'] = summary['dbu_per_month'] / summary['quantity']

print("\n" + "=" * 100)
print("💰 COST BREAKDOWN BY RATE_TYPE")
print("=" * 100)
display(summary)

print("\n✨ KEY INSIGHTS:")
print(f"   • Total Cost: ${summary['cost_per_month'].sum():,.2f}")
print(f"   • Total DBU: {summary['dbu_per_month'].sum():,.2f}")
print(f"   • Tested {len(results_df)} separate line items")
print(f"   • Each line item = ONE rate_type (clean design!)")

# Show example of combining lines for one API usage
print("\n📋 EXAMPLE: Claude Sonnet API Usage")
claude_lines = results_df[results_df['line_item'].str.contains('Claude Sonnet')]
if len(claude_lines) > 0:
    print(f"   Line 1 (Input):  ${claude_lines[claude_lines['rate_type'] == 'input_token']['cost_per_month'].sum():,.2f}")
    print(f"   Line 2 (Output): ${claude_lines[claude_lines['rate_type'] == 'output_token']['cost_per_month'].sum():,.2f}")
    print(f"   TOTAL:           ${claude_lines['cost_per_month'].sum():,.2f}")
    print("\n   ✅ Clean separation! Each cost component is visible.")

print("\n" + "=" * 100)
