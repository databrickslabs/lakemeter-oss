# Databricks notebook source
# MAGIC %md
# MAGIC # Function Test: LAKEBASE (Postgres Serverless)
# MAGIC
# MAGIC Tests `calculate_line_item_costs()` for Lakebase workload:
# MAGIC - **Sizing:** 1, 2, 4, 8 CU (Compute Units, where 1 CU = 1 DBU)
# MAGIC - **Product type:** DATABASE_SERVERLESS_COMPUTE
# MAGIC - **No VM costs** (serverless)
# MAGIC - **HA nodes:** 1, 2, 3 (high availability replicas)
# MAGIC - **Pricing:** 24/7 operation (720 hours/month)
# MAGIC
# MAGIC **Formula:** `total_cu = lakebase_cu × lakebase_ha_nodes`

# COMMAND ----------

%run ../00_Lakebase_Config

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate Test Scenarios

# COMMAND ----------

clouds = ['AWS', 'AZURE', 'GCP']
region_map = {'AWS': 'us-east-1', 'AZURE': 'eastus', 'GCP': 'us-central1'}

# Lakebase configuration
cu_sizes = [1, 2, 4, 8]  # Compute Units
ha_nodes_options = [1, 2, 3]  # High Availability nodes

test_scenarios = []
scenario_id = 1

# Generate comprehensive test scenarios
for cloud in clouds:
    for tier in ['STANDARD', 'PREMIUM', 'ENTERPRISE']:
        if cloud == 'AZURE' and tier == 'ENTERPRISE':
            continue  # Azure doesn't have ENTERPRISE tier
        
        for cu in cu_sizes:
            for ha_nodes in ha_nodes_options:
                total_cu = cu * ha_nodes
                
                test_scenarios.append({
                    'scenario_id': scenario_id,
                    'cloud': cloud,
                    'region': region_map[cloud],
                    'tier': tier,
                    'cu': cu,
                    'ha_nodes': ha_nodes,
                    'total_cu': total_cu,
                    'label': f"{cloud} {tier} {cu}CU {ha_nodes}HA"
                })
                scenario_id += 1

print(f"📋 Generated {len(test_scenarios)} LAKEBASE scenarios")
print(f"   • CU sizes: {cu_sizes}")
print(f"   • HA nodes: {ha_nodes_options}")
print(f"   • Pricing: 24/7 operation (auto-calculated as 720 hours/month)")
print(f"   • Total scenarios: {len(clouds)} clouds × {len(cu_sizes)} CU × {len(ha_nodes_options)} HA nodes × tiers")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Execute Function Calls

# COMMAND ----------

sql_parts = []
for scenario in test_scenarios:
    sql_parts.append(f"""
    SELECT 
        {scenario['scenario_id']} as scenario_id,
        '{scenario['label']}'::VARCHAR as label,
        '{scenario['cloud']}'::VARCHAR as cloud,
        '{scenario['tier']}'::VARCHAR as tier,
        {scenario['cu']}::INT as cu,
        {scenario['ha_nodes']}::INT as ha_nodes,
        {scenario['total_cu']}::INT as total_cu,
        *
    FROM lakemeter.calculate_line_item_costs(
        'LAKEBASE'::VARCHAR, '{scenario['cloud']}'::VARCHAR, '{scenario['region']}'::VARCHAR,
        '{scenario['tier']}'::VARCHAR, FALSE::BOOLEAN, FALSE::BOOLEAN, NULL::VARCHAR,
        NULL::VARCHAR, NULL::VARCHAR, 0::INT, 'NA'::VARCHAR, 'NA'::VARCHAR,
        8::INT, 60::INT, 30::INT, NULL::INT,
        'standard'::VARCHAR,
        NULL::VARCHAR, NULL::VARCHAR, 1::INT, 'NA'::VARCHAR, NULL::VARCHAR, 0::DECIMAL, NULL::VARCHAR,
        NULL::VARCHAR, NULL::VARCHAR, 'global'::VARCHAR, 'standard'::VARCHAR, 'pay_per_token'::VARCHAR,
        0::BIGINT, 0::BIGINT,
        {scenario['cu']}::INT, {scenario['ha_nodes']}::INT,
        'NA'::VARCHAR, 'NA'::VARCHAR, 'NA'::VARCHAR
    )
    """)

full_query = " UNION ALL ".join(sql_parts) + ";"

print("🔄 Executing function calls via PostgreSQL...")
results_df = execute_query(full_query)

print(f"✅ Retrieved {len(results_df)} results")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Display & Validate

# COMMAND ----------

print("=" * 120)
print("LAKEBASE TEST RESULTS")
print("=" * 120)
display_cols = ['scenario_id', 'cloud', 'tier', 'cu', 'ha_nodes', 'total_cu',
                'dbu_per_hour', 'hours_per_month', 'dbu_per_month', 'dbu_price', 'cost_per_month']
display(results_df[[col for col in display_cols if col in results_df.columns]])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Manual Validation - Sample Calculations

# COMMAND ----------

print("=" * 120)
print("MANUAL VALIDATION - LAKEBASE PRICING")
print("=" * 120)

# Get DBU price for DATABASE_SERVERLESS_COMPUTE
pricing_query = """
SELECT 
    cloud,
    region,
    tier,
    product_type,
    price_per_dbu
FROM lakemeter.sync_pricing_dbu_rates
WHERE product_type = 'DATABASE_SERVERLESS_COMPUTE'
  AND cloud = 'AWS'
  AND region = 'us-east-1'
  AND tier IN ('STANDARD', 'PREMIUM', 'ENTERPRISE')
ORDER BY tier;
"""

pricing_info = execute_query(pricing_query)
print("📋 Lakebase pricing (DATABASE_SERVERLESS_COMPUTE):")
display(pricing_info)

# Manual calculation example
print("\n" + "=" * 120)
print("EXAMPLE CALCULATION: AWS PREMIUM 2CU with 2 HA nodes")
print("=" * 120)

if len(pricing_info[pricing_info['tier'] == 'PREMIUM']) > 0:
    dbu_price = float(pricing_info[pricing_info['tier'] == 'PREMIUM']['price_per_dbu'].iloc[0])
    
    cu = 2
    ha_nodes = 2
    total_cu = cu * ha_nodes
    hours_per_month = 720  # 24/7 operation (auto-calculated by function)
    
    print(f"\n📊 Configuration:")
    print(f"  • Lakebase CU: {cu}")
    print(f"  • HA nodes: {ha_nodes}")
    print(f"  • Total CU: {cu} × {ha_nodes} = {total_cu} CU")
    print(f"  • Hours per month: {hours_per_month} (24/7 operation)")
    
    print(f"\nDBU Calculation:")
    print(f"  • DBU per hour: {total_cu} CU = {total_cu} DBU/hour (1 CU = 1 DBU)")
    print(f"  • DBU per month: {total_cu} × {hours_per_month} = {total_cu * hours_per_month:,.0f} DBU")
    
    print(f"\nCost Calculation:")
    print(f"  • DBU price: ${dbu_price}")
    print(f"  • Total cost: {total_cu * hours_per_month:,.0f} × ${dbu_price} = ${total_cu * hours_per_month * dbu_price:,.2f}")
    
    # Compare with test results
    test_result = results_df[
        (results_df['cloud'] == 'AWS') &
        (results_df['tier'] == 'PREMIUM') &
        (results_df['cu'] == cu) &
        (results_df['ha_nodes'] == ha_nodes)
    ]
    
    if len(test_result) > 0:
        actual_dbu_per_month = float(test_result['dbu_per_month'].iloc[0])
        actual_cost = float(test_result['cost_per_month'].iloc[0])
        expected_dbu_per_month = total_cu * hours_per_month
        expected_cost = expected_dbu_per_month * dbu_price
        
        print(f"\nTest Result Comparison:")
        print(f"  • Expected DBU/month: {expected_dbu_per_month:,.0f}")
        print(f"  • Actual DBU/month:   {actual_dbu_per_month:,.0f}")
        print(f"  • Match: {'✅' if abs(expected_dbu_per_month - actual_dbu_per_month) < 0.01 else '❌'}")
        print(f"  • Expected Cost: ${expected_cost:,.2f}")
        print(f"  • Actual Cost:   ${actual_cost:,.2f}")
        print(f"  • Match: {'✅' if abs(expected_cost - actual_cost) < 0.01 else '❌'}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 120)
print("VALIDATION")
print("=" * 120)

# All scenarios should have positive costs
zero_cost_count = len(results_df[results_df['cost_per_month'] == 0])
positive_cost_count = len(results_df[results_df['cost_per_month'] > 0])

print(f"\n✅ Scenarios with positive costs: {positive_cost_count}/{len(results_df)}")

# Summary by dimensions
print("\n📊 Coverage Summary:")
print(f"   • Clouds: {results_df['cloud'].nunique()} ({', '.join(results_df['cloud'].unique())})")
print(f"   • Tiers: {results_df['tier'].nunique()} ({', '.join(results_df['tier'].unique())})")
print(f"   • CU sizes: {results_df['cu'].nunique()} ({', '.join(map(str, sorted(results_df['cu'].unique())))})")
print(f"   • HA nodes: {results_df['ha_nodes'].nunique()} ({', '.join(map(str, sorted(results_df['ha_nodes'].unique())))})")

# Check for $0 costs (should only be STANDARD tier if applicable)
if zero_cost_count > 0:
    print(f"\n⚠️  Scenarios with $0 costs: {zero_cost_count}")
    zero_cost_df = results_df[results_df['cost_per_month'] == 0]
    print("\nZero-cost scenarios:")
    display(zero_cost_df[['cloud', 'tier', 'cu', 'ha_nodes', 'dbu_price', 'dbu_per_month', 'cost_per_month']])
    
    # Check if all $0 costs are STANDARD tier
    if (zero_cost_df['tier'] == 'STANDARD').all():
        print("   ℹ️  All $0 costs are STANDARD tier (expected if DATABASE_SERVERLESS_COMPUTE not available in STANDARD)")
    else:
        print("   ❌ Some PREMIUM/ENTERPRISE scenarios have $0 costs - unexpected!")

# Check hours_per_month is always 720 (24/7)
if 'hours_per_month' in results_df.columns:
    unique_hours = results_df['hours_per_month'].unique()
    if len(unique_hours) == 1 and float(unique_hours[0]) == 720:
        print(f"\n✅ All scenarios use 24/7 operation (720 hours/month)")
    else:
        print(f"\n⚠️  Unexpected hours_per_month values: {unique_hours}")

# Validate DBU calculation (should be cu × ha_nodes × hours)
results_df['expected_dbu'] = results_df['cu'] * results_df['ha_nodes'] * 720
results_df['dbu_match'] = abs(results_df['dbu_per_month'] - results_df['expected_dbu']) < 0.01
dbu_mismatches = len(results_df[~results_df['dbu_match']])

if dbu_mismatches == 0:
    print(f"✅ All DBU calculations correct (cu × ha_nodes × 720)")
else:
    print(f"❌ {dbu_mismatches} scenarios have incorrect DBU calculations")
    display(results_df[~results_df['dbu_match']][['cloud', 'tier', 'cu', 'ha_nodes', 'expected_dbu', 'dbu_per_month']])

assert positive_cost_count > 0, f"❌ FAIL: At least some scenarios should have positive costs"

print("\n" + "=" * 120)
print("✅ LAKEBASE TEST COMPLETE")
print("=" * 120)

# COMMAND ----------

