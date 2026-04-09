# Databricks notebook source
# MAGIC %md
# MAGIC # Test Case: DBSQL Pro Warehouse
# MAGIC 
# MAGIC **Objective:** Validate DBSQL Pro cost calculations across ALL payment options
# MAGIC 
# MAGIC **DBSQL Pro Characteristics:**
# MAGIC - **Product type:** SQL_PRO_COMPUTE
# MAGIC - **Enhanced performance** vs Classic
# MAGIC - **Same warehouse sizes** as Classic (X-Small, Small, Medium, Large)
# MAGIC - **Underlying VMs:** Uses sync_ref_dbsql_warehouse_config for driver/worker instance types
# MAGIC 
# MAGIC **VM Payment Options Tested:**
# MAGIC - **AWS (8 combinations):**
# MAGIC   - On-Demand (driver + worker)
# MAGIC   - Spot (driver=on_demand, worker=spot)
# MAGIC   - Reserved 1 Year: No Upfront, Partial Upfront, All Upfront
# MAGIC   - Reserved 3 Year: No Upfront, Partial Upfront, All Upfront
# MAGIC - **Azure/GCP (4 combinations):**
# MAGIC   - On-Demand
# MAGIC   - Spot
# MAGIC   - Reserved 1 Year
# MAGIC   - Reserved 3 Year
# MAGIC 
# MAGIC **Test Matrix:**
# MAGIC - **AWS:** 2 regions × 2 tiers × 4 sizes × 3 clusters × 2 usage × 8 payment options = **768 scenarios**
# MAGIC - **AZURE:** 2 regions × 1 tier × 4 sizes × 3 clusters × 2 usage × 4 payment options = **192 scenarios**
# MAGIC - **GCP:** 2 regions × 2 tiers × 4 sizes × 3 clusters × 2 usage × 4 payment options = **384 scenarios**
# MAGIC - **TOTAL: ~1,344 scenarios** (DBSQL Pro not available in STANDARD tier)

# COMMAND ----------

# Load Lakebase configuration
%run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2, pandas as pd, uuid
from datetime import datetime
from tabulate import tabulate

def get_connection():
    return psycopg2.connect(host=LAKEBASE_HOST, port=LAKEBASE_PORT, database=LAKEBASE_DB, user=LAKEBASE_USER, password=LAKEBASE_PASSWORD)

def execute_query(query, params=None, fetch=True):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch:
                columns = [desc[0] for desc in cur.description] if cur.description else []
                results = cur.fetchall()
                conn.commit()
                return pd.DataFrame(results, columns=columns) if results else pd.DataFrame()
            else:
                conn.commit()
                return None
    finally:
        conn.close()

print("✅ Setup complete!")

# COMMAND ----------

TEST_RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
TEST_USER_ID = str(uuid.uuid4())
execute_query("INSERT INTO lakemeter.users (user_id, full_name, email, role, is_active, created_at) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;",
              (TEST_USER_ID, f'test_dbsql_pro_{TEST_RUN_ID}', f'test_{TEST_RUN_ID}@databricks.com', 'admin', True, datetime.now()), fetch=False)

available_regions_df = execute_query("SELECT DISTINCT cloud, region_code FROM lakemeter.sync_ref_sku_region_map WHERE (cloud = 'AWS' AND (region_code LIKE 'us-east-%' OR region_code LIKE 'eu-west-%')) OR (cloud = 'AZURE' AND region_code IN ('eastus', 'westeurope')) OR (cloud = 'GCP' AND (region_code LIKE 'us-central%' OR region_code LIKE 'europe-west%')) ORDER BY cloud, region_code;")
# Get 1 US + 1 EU region per cloud
region_map = {}
for cloud in ['AWS', 'AZURE', 'GCP']:
    cloud_regions = available_regions_df[available_regions_df['cloud'] == cloud]
    if len(cloud_regions) >= 2:
        us_region = cloud_regions[cloud_regions['region_code'].str.contains('us')].iloc[0]['region_code']
        eu_region = cloud_regions[cloud_regions['region_code'].str.contains('eu')].iloc[0]['region_code']
        region_map[cloud] = {'us': us_region, 'eu': eu_region}

print("=" * 100)
print("📊 SELECTED REGIONS (US + EU)")
print("=" * 100)
for cloud, regions in region_map.items():
    print(f"{cloud}: US={regions['us']}, EU={regions['eu']}")
print("=" * 100)

# COMMAND ----------

test_scenarios = []
scenario_id = 1
warehouse_sizes = ['X-Small', 'Small', 'Medium', 'Large']
num_clusters_options = [1, 2, 4]
usage_patterns = [{'runs': 8, 'mins': 60}, {'runs': 24, 'mins': 60}]

# COMPREHENSIVE PAYMENT OPTIONS (like Test_01, Test_05, Test_07)
# AWS: All payment options with different upfront modes
aws_payment_options = [
    {'driver_tier': 'on_demand', 'worker_tier': 'on_demand', 'payment_option': 'on_demand', 'label': 'OnDemand'},
    {'driver_tier': 'on_demand', 'worker_tier': 'spot', 'payment_option': 'spot', 'label': 'Spot'},
    {'driver_tier': 'reserved_1y', 'worker_tier': 'reserved_1y', 'payment_option': 'no_upfront', 'label': 'Res1y-NoUp'},
    {'driver_tier': 'reserved_1y', 'worker_tier': 'reserved_1y', 'payment_option': 'partial_upfront', 'label': 'Res1y-PartialUp'},
    {'driver_tier': 'reserved_1y', 'worker_tier': 'reserved_1y', 'payment_option': 'all_upfront', 'label': 'Res1y-AllUp'},
    {'driver_tier': 'reserved_3y', 'worker_tier': 'reserved_3y', 'payment_option': 'no_upfront', 'label': 'Res3y-NoUp'},
    {'driver_tier': 'reserved_3y', 'worker_tier': 'reserved_3y', 'payment_option': 'partial_upfront', 'label': 'Res3y-PartialUp'},
    {'driver_tier': 'reserved_3y', 'worker_tier': 'reserved_3y', 'payment_option': 'all_upfront', 'label': 'Res3y-AllUp'},
]

# Azure/GCP: On-demand, Spot, Reserved (no payment options)
azure_gcp_payment_options = [
    {'driver_tier': 'on_demand', 'worker_tier': 'on_demand', 'payment_option': 'NA', 'label': 'OnDemand'},
    {'driver_tier': 'on_demand', 'worker_tier': 'spot', 'payment_option': 'NA', 'label': 'Spot'},
    {'driver_tier': 'reserved_1y', 'worker_tier': 'reserved_1y', 'payment_option': 'NA', 'label': 'Reserved1y'},
    {'driver_tier': 'reserved_3y', 'worker_tier': 'reserved_3y', 'payment_option': 'NA', 'label': 'Reserved3y'},
]

for cloud in ['AWS', 'AZURE', 'GCP']:
    # Select payment options for this cloud
    payment_options = aws_payment_options if cloud == 'AWS' else azure_gcp_payment_options
    
    for region_type in ['us', 'eu']:  # Test both US and EU regions
        region = region_map[cloud][region_type]
        for tier in ['STANDARD', 'PREMIUM', 'ENTERPRISE']:
            # DBSQL Pro not available in STANDARD tier
            if tier == 'STANDARD':
                continue
            if cloud == 'AZURE' and tier == 'ENTERPRISE':
                continue
            for size in warehouse_sizes:
                for num_clusters in num_clusters_options:
                    for usage in usage_patterns:
                        # COMPREHENSIVE: Test all payment options
                        for payment in payment_options:
                            test_scenarios.append({
                                'scenario_id': scenario_id, 'cloud': cloud, 'region': region, 'tier': tier,
                                'workload_name': f"{cloud} {tier} {size} {num_clusters}cl {usage['runs']}h {payment['label']} PRO",
                                'dbsql_warehouse_type': 'PRO', 'dbsql_warehouse_size': size, 'dbsql_num_clusters': num_clusters,
                                'runs_per_day': usage['runs'], 'avg_runtime_minutes': usage['mins'], 'days_per_month': 30,
                                'driver_pricing_tier': payment['driver_tier'],
                                'worker_pricing_tier': payment['worker_tier'],
                                'vm_payment_option': payment['payment_option'],
                                'notes': f"DBSQL Pro {size} {num_clusters}cl | D:{payment['driver_tier']} W:{payment['worker_tier']}"
                            })
                            scenario_id += 1

print(f"✅ Generated {len(test_scenarios)} scenarios")
print(f"   AWS: {len([s for s in test_scenarios if s['cloud'] == 'AWS'])} scenarios")
print(f"   AZURE: {len([s for s in test_scenarios if s['cloud'] == 'AZURE'])} scenarios")
print(f"   GCP: {len([s for s in test_scenarios if s['cloud'] == 'GCP'])} scenarios")

# COMMAND ----------

unique_combos = {f"{s['cloud']}_{s['region']}_{s['tier']}": {'cloud': s['cloud'], 'region': s['region'], 'tier': s['tier']} for s in test_scenarios}
estimate_map = {}
for key, combo in unique_combos.items():
    estimate_id = str(uuid.uuid4())
    estimate_map[key] = estimate_id
    execute_query("INSERT INTO lakemeter.estimates (estimate_id, owner_user_id, estimate_name, cloud, region, tier, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);",
                  (estimate_id, TEST_USER_ID, f"Test: {combo['cloud']} {combo['region']} {combo['tier']}", combo['cloud'], combo['region'], combo['tier'], datetime.now(), datetime.now()), fetch=False)

line_item_ids = []
for scenario in test_scenarios:
    line_item_id = str(uuid.uuid4())
    line_item_ids.append(line_item_id)
    estimate_key = f"{scenario['cloud']}_{scenario['region']}_{scenario['tier']}"
    execute_query("""INSERT INTO lakemeter.line_items (line_item_id, estimate_id, display_order, workload_name, workload_type, serverless_enabled, dbsql_warehouse_type, dbsql_warehouse_size, dbsql_num_clusters, runs_per_day, avg_runtime_minutes, days_per_month, driver_pricing_tier, worker_pricing_tier, vm_payment_option, notes, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                  (line_item_id, estimate_map[estimate_key], scenario['scenario_id'], scenario['workload_name'], 'DBSQL', False, 'PRO', scenario['dbsql_warehouse_size'], scenario['dbsql_num_clusters'], scenario['runs_per_day'], scenario['avg_runtime_minutes'], scenario['days_per_month'], scenario['driver_pricing_tier'], scenario['worker_pricing_tier'], scenario['vm_payment_option'], scenario['notes'], datetime.now(), datetime.now()), fetch=False)

print(f"✅ Created {len(estimate_map)} estimates, {len(line_item_ids)} line items")

# COMMAND ----------

query_results_sql = """
SELECT 
    c.display_order,
    c.workload_name,
    c.workload_type,
    -- Context (cloud/region/tier)
    c.cloud,
    c.region,
    c.tier,
    -- Configuration
    c.dbsql_warehouse_type,
    c.dbsql_warehouse_size,
    c.dbsql_num_clusters,
    -- DBSQL Warehouse Node Configuration
    c.resolved_driver_node_type as driver_node_type,
    c.resolved_worker_node_type as worker_node_type,
    c.dbsql_driver_count as driver_count,
    c.resolved_num_workers as num_workers,
    -- Usage
    c.runs_per_day,
    c.avg_runtime_minutes,
    c.days_per_month,
    c.hours_per_month,
    -- Pricing Tiers
    c.driver_pricing_tier,
    c.worker_pricing_tier,
    c.vm_payment_option,
    -- DBU Calculation
    c.dbu_per_hour,
    c.dbu_per_month,
    -- VM Costs - Detailed Breakdown
    c.driver_vm_cost_per_hour,
    c.worker_vm_cost_per_hour,
    c.total_worker_vm_cost_per_hour,
    c.total_vm_cost_per_hour,
    c.driver_vm_cost_per_month,
    c.total_worker_vm_cost_per_month,
    c.vm_cost_per_month,
    -- DBU Pricing
    c.price_per_dbu,
    c.product_type_for_pricing,
    c.dbu_cost_per_month,
    -- Total (DBU + VM)
    c.cost_per_month,
    c.notes
FROM lakemeter.v_line_items_with_costs c
WHERE c.line_item_id = ANY(%s::uuid[])
ORDER BY c.display_order;
"""

results_df = execute_query(query_results_sql, (line_item_ids,))

# Convert numeric columns
numeric_columns = ['dbsql_num_clusters', 'driver_count', 'num_workers', 'hours_per_month', 'dbu_per_hour', 'price_per_dbu', 
                   'driver_vm_cost_per_hour', 'worker_vm_cost_per_hour', 'total_worker_vm_cost_per_hour', 'total_vm_cost_per_hour',
                   'driver_vm_cost_per_month', 'total_worker_vm_cost_per_month', 'vm_cost_per_month', 'dbu_cost_per_month', 'cost_per_month']
for col in numeric_columns:
    if col in results_df.columns:
        results_df[col] = pd.to_numeric(results_df[col], errors='coerce')

# Display summary with payment options
summary_display_df = results_df[[
    'workload_name', 'cloud', 'region', 'tier',
    'dbsql_warehouse_size', 'dbsql_num_clusters',
    'driver_node_type', 'worker_node_type', 'num_workers', 'driver_count',
    'driver_pricing_tier', 'worker_pricing_tier', 'vm_payment_option',
    'hours_per_month', 'dbu_per_hour', 'price_per_dbu',
    'driver_vm_cost_per_hour', 'worker_vm_cost_per_hour',
    'total_worker_vm_cost_per_hour', 'total_vm_cost_per_hour',
    'driver_vm_cost_per_month', 'total_worker_vm_cost_per_month',
    'vm_cost_per_month', 'dbu_cost_per_month', 'cost_per_month'
]].copy()

summary_display_df['dbu_per_hour'] = summary_display_df['dbu_per_hour'].round(4)
summary_display_df['price_per_dbu'] = summary_display_df['price_per_dbu'].round(6)
summary_display_df['cost_per_month'] = summary_display_df['cost_per_month'].round(2)

print("=" * 180)
print("DBSQL PRO - COMPREHENSIVE VM PAYMENT OPTION TESTING")
print("=" * 180)
print(tabulate(summary_display_df.head(30), headers='keys', tablefmt='grid', showindex=False, maxcolwidths=30))
display(summary_display_df)

# DBSQL Pro validation
# DBSQL Pro is NOT available in STANDARD tier (scenarios not created)
# PREMIUM/ENTERPRISE: Should have positive costs
print("\n" + "=" * 180)
print("VALIDATION RESULTS")
print("=" * 180)

# Assert no STANDARD tier scenarios (Pro not available in STANDARD)
standard_df = results_df[results_df['tier'] == 'STANDARD']
assert len(standard_df) == 0, "DBSQL Pro should not have any STANDARD tier scenarios"
print(f"✅ STANDARD tier: 0 scenarios (DBSQL Pro not available in STANDARD tier)")

# Validate PREMIUM/ENTERPRISE tiers (all should have positive costs)
assert (results_df['cost_per_month'] > 0).all(), "All DBSQL Pro scenarios should have positive costs"
print(f"✅ PREMIUM/ENTERPRISE tiers: {len(results_df)} scenarios with positive costs")

# Cost breakdown by tier
tier_summary = results_df.groupby('tier').agg({
    'cost_per_month': ['count', 'mean', 'min', 'max'],
    'vm_cost_per_month': 'mean',
    'dbu_cost_per_month': 'mean'
}).round(2)
print("\n📊 Cost Summary by Tier:")
print(tabulate(tier_summary, headers='keys', tablefmt='grid'))

# Payment option breakdown
payment_summary = results_df.groupby(['cloud', 'driver_pricing_tier', 'worker_pricing_tier']).agg({
    'cost_per_month': ['count', 'mean']
}).round(2)
print("\n📊 Cost Summary by Payment Option:")
print(tabulate(payment_summary.head(20), headers='keys', tablefmt='grid'))

print(f"\n✅ All {len(test_scenarios)} DBSQL Pro scenarios validated!")
print(f"   • All scenarios in PREMIUM/ENTERPRISE tiers")
print(f"   • All payment options tested (on_demand, spot, reserved 1y/3y)")
print(f"   • AWS: {len([s for s in test_scenarios if s['cloud'] == 'AWS'])} scenarios (8 payment options)")
print(f"   • AZURE: {len([s for s in test_scenarios if s['cloud'] == 'AZURE'])} scenarios (4 payment options)")
print(f"   • GCP: {len([s for s in test_scenarios if s['cloud'] == 'GCP'])} scenarios (4 payment options)")

# COMMAND ----------
