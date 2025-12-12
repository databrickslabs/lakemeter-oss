# Databricks notebook source
# MAGIC %md
# MAGIC # Test Case: JOBS Classic Compute
# MAGIC 
# MAGIC **Objective:** Validate cost calculations for JOBS workload type with classic compute across:
# MAGIC - 3 clouds: AWS, Azure, GCP
# MAGIC - 2 regions per cloud (US + Europe)
# MAGIC - Multiple configurations:
# MAGIC   - Photon enabled/disabled
# MAGIC   - Different instance types
# MAGIC   - Different worker counts
# MAGIC   - Different VM pricing tiers (on_demand, spot, reserved)
# MAGIC   - Different usage patterns
# MAGIC 
# MAGIC **Test Matrix:**
# MAGIC - Cloud: AWS (us-east-1, eu-west-1), Azure (eastus, westeurope), GCP (us-central1, europe-west1)
# MAGIC - Instance types: Small (i3.xlarge), Medium (i3.2xlarge), Large (i3.4xlarge)
# MAGIC - Photon: Enabled, Disabled
# MAGIC - VM Pricing: on_demand, spot (50%), reserved_1y
# MAGIC - Usage: Light (4 runs/day, 30 min), Medium (12 runs/day, 60 min), Heavy (24 runs/day, 120 min)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Setup - Install Dependencies & Connect to Lakebase

# COMMAND ----------

# Install psycopg2 for PostgreSQL connection
%pip install psycopg2-binary pandas tabulate

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import psycopg2
import pandas as pd
import uuid
from datetime import datetime
from tabulate import tabulate

# Lakebase connection parameters
LAKEBASE_HOST = "lakebase-pricing.postgres.database.azure.com"
LAKEBASE_PORT = 5432
LAKEBASE_DB = "lakemeter_pricing"
LAKEBASE_USER = "lakemeter_sync_role"
LAKEBASE_PASSWORD = "Lak3m3t3r_Sync_2024!"

def get_connection():
    """Create and return a PostgreSQL connection"""
    return psycopg2.connect(
        host=LAKEBASE_HOST,
        port=LAKEBASE_PORT,
        database=LAKEBASE_DB,
        user=LAKEBASE_USER,
        password=LAKEBASE_PASSWORD
    )

def execute_query(query, params=None, fetch=True):
    """Execute a query and optionally fetch results"""
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

print("✅ Connection setup complete!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Test Data Preparation
# MAGIC 
# MAGIC Create test user, estimate, and line items for JOBS Classic scenarios

# COMMAND ----------

# Generate unique IDs for this test run
TEST_RUN_ID = str(uuid.uuid4())[:8]
TEST_USER_ID = str(uuid.uuid4())
TEST_ESTIMATE_ID = str(uuid.uuid4())

print(f"🧪 Test Run ID: {TEST_RUN_ID}")
print(f"👤 Test User ID: {TEST_USER_ID}")
print(f"📊 Test Estimate ID: {TEST_ESTIMATE_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 2.1 Create Test User

# COMMAND ----------

create_user_sql = """
INSERT INTO lakemeter.users (user_id, username, email, role, is_active, created_at)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (user_id) DO NOTHING;
"""

execute_query(
    create_user_sql,
    (TEST_USER_ID, f'test_jobs_classic_{TEST_RUN_ID}', f'test_{TEST_RUN_ID}@databricks.com', 
     'admin', True, datetime.now()),
    fetch=False
)

print(f"✅ Test user created: test_jobs_classic_{TEST_RUN_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 2.2 Create Test Estimate

# COMMAND ----------

create_estimate_sql = """
INSERT INTO lakemeter.estimates (
    estimate_id, estimate_name, owner_user_id, customer_name,
    cloud, region, tier, status, created_at, updated_at, updated_by
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (estimate_id) DO NOTHING;
"""

execute_query(
    create_estimate_sql,
    (TEST_ESTIMATE_ID, f'JOBS Classic Test - {TEST_RUN_ID}', TEST_USER_ID, 
     'Test Customer - JOBS Classic', 'AWS', 'us-east-1', 'PREMIUM', 'draft',
     datetime.now(), datetime.now(), TEST_USER_ID),
    fetch=False
)

print(f"✅ Test estimate created: JOBS Classic Test - {TEST_RUN_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Test Scenarios - JOBS Classic
# MAGIC 
# MAGIC ### Test Matrix:
# MAGIC 1. **AWS us-east-1** - Small cluster, Photon OFF, On-Demand, Light usage
# MAGIC 2. **AWS us-east-1** - Medium cluster, Photon ON, On-Demand, Medium usage
# MAGIC 3. **AWS us-east-1** - Large cluster, Photon ON, Spot 50%, Heavy usage
# MAGIC 4. **AWS eu-west-1** - Medium cluster, Photon ON, Reserved 1Y, Medium usage
# MAGIC 5. **Azure eastus** - Small cluster, Photon OFF, On-Demand, Light usage
# MAGIC 6. **Azure eastus** - Medium cluster, Photon ON, On-Demand, Medium usage
# MAGIC 7. **Azure westeurope** - Large cluster, Photon ON, Spot 50%, Heavy usage
# MAGIC 8. **GCP us-central1** - Small cluster, Photon OFF, On-Demand, Light usage
# MAGIC 9. **GCP us-central1** - Medium cluster, Photon ON, On-Demand, Medium usage
# MAGIC 10. **GCP europe-west1** - Large cluster, Photon ON, On-Demand, Heavy usage

# COMMAND ----------

# Define test scenarios
test_scenarios = [
    # AWS us-east-1
    {
        'scenario_id': 1,
        'workload_name': 'AWS US-East Light ETL (No Photon)',
        'cloud': 'AWS',
        'region': 'us-east-1',
        'driver_node_type': 'i3.xlarge',
        'worker_node_type': 'i3.xlarge',
        'num_workers': 2,
        'photon_enabled': False,
        'vm_pricing_tier': 'on_demand',
        'vm_payment_option': 'NA',
        'spot_percentage': 0,
        'runs_per_day': 4,
        'avg_runtime_minutes': 30,
        'days_per_month': 30,
        'notes': 'Small cluster, no Photon, on-demand pricing, light daily ETL'
    },
    {
        'scenario_id': 2,
        'workload_name': 'AWS US-East Medium ETL (Photon)',
        'cloud': 'AWS',
        'region': 'us-east-1',
        'driver_node_type': 'i3.xlarge',
        'worker_node_type': 'i3.2xlarge',
        'num_workers': 4,
        'photon_enabled': True,
        'vm_pricing_tier': 'on_demand',
        'vm_payment_option': 'NA',
        'spot_percentage': 0,
        'runs_per_day': 12,
        'avg_runtime_minutes': 60,
        'days_per_month': 30,
        'notes': 'Medium cluster, Photon enabled, on-demand, frequent ETL'
    },
    {
        'scenario_id': 3,
        'workload_name': 'AWS US-East Heavy ETL (Spot)',
        'cloud': 'AWS',
        'region': 'us-east-1',
        'driver_node_type': 'i3.2xlarge',
        'worker_node_type': 'i3.4xlarge',
        'num_workers': 8,
        'photon_enabled': True,
        'vm_pricing_tier': 'spot',
        'vm_payment_option': 'NA',
        'spot_percentage': 50,
        'runs_per_day': 24,
        'avg_runtime_minutes': 120,
        'days_per_month': 30,
        'notes': 'Large cluster, Photon, 50% spot instances, hourly heavy ETL'
    },
    # AWS eu-west-1
    {
        'scenario_id': 4,
        'workload_name': 'AWS EU-West Reserved ETL',
        'cloud': 'AWS',
        'region': 'eu-west-1',
        'driver_node_type': 'i3.xlarge',
        'worker_node_type': 'i3.2xlarge',
        'num_workers': 4,
        'photon_enabled': True,
        'vm_pricing_tier': 'reserved_1y',
        'vm_payment_option': 'no_upfront',
        'spot_percentage': 0,
        'runs_per_day': 12,
        'avg_runtime_minutes': 60,
        'days_per_month': 22,
        'notes': 'Medium cluster, Photon, 1-year reserved, business days only'
    },
    # Azure eastus
    {
        'scenario_id': 5,
        'workload_name': 'Azure US-East Light ETL',
        'cloud': 'AZURE',
        'region': 'eastus',
        'driver_node_type': 'Standard_D8s_v3',
        'worker_node_type': 'Standard_D8s_v3',
        'num_workers': 2,
        'photon_enabled': False,
        'vm_pricing_tier': 'on_demand',
        'vm_payment_option': 'NA',
        'spot_percentage': 0,
        'runs_per_day': 4,
        'avg_runtime_minutes': 30,
        'days_per_month': 30,
        'notes': 'Azure small cluster, no Photon, on-demand'
    },
    {
        'scenario_id': 6,
        'workload_name': 'Azure US-East Medium ETL (Photon)',
        'cloud': 'AZURE',
        'region': 'eastus',
        'driver_node_type': 'Standard_D8s_v3',
        'worker_node_type': 'Standard_D16s_v3',
        'num_workers': 4,
        'photon_enabled': True,
        'vm_pricing_tier': 'on_demand',
        'vm_payment_option': 'NA',
        'spot_percentage': 0,
        'runs_per_day': 12,
        'avg_runtime_minutes': 60,
        'days_per_month': 30,
        'notes': 'Azure medium cluster, Photon enabled'
    },
    # Azure westeurope
    {
        'scenario_id': 7,
        'workload_name': 'Azure EU-West Heavy ETL (Spot)',
        'cloud': 'AZURE',
        'region': 'westeurope',
        'driver_node_type': 'Standard_D16s_v3',
        'worker_node_type': 'Standard_D32s_v3',
        'num_workers': 8,
        'photon_enabled': True,
        'vm_pricing_tier': 'spot',
        'vm_payment_option': 'NA',
        'spot_percentage': 50,
        'runs_per_day': 24,
        'avg_runtime_minutes': 120,
        'days_per_month': 30,
        'notes': 'Azure large cluster, Photon, 50% spot'
    },
    # GCP us-central1
    {
        'scenario_id': 8,
        'workload_name': 'GCP US-Central Light ETL',
        'cloud': 'GCP',
        'region': 'us-central1',
        'driver_node_type': 'n1-standard-8',
        'worker_node_type': 'n1-standard-8',
        'num_workers': 2,
        'photon_enabled': False,
        'vm_pricing_tier': 'on_demand',
        'vm_payment_option': 'NA',
        'spot_percentage': 0,
        'runs_per_day': 4,
        'avg_runtime_minutes': 30,
        'days_per_month': 30,
        'notes': 'GCP small cluster, no Photon'
    },
    {
        'scenario_id': 9,
        'workload_name': 'GCP US-Central Medium ETL (Photon)',
        'cloud': 'GCP',
        'region': 'us-central1',
        'driver_node_type': 'n1-standard-8',
        'worker_node_type': 'n1-standard-16',
        'num_workers': 4,
        'photon_enabled': True,
        'vm_pricing_tier': 'on_demand',
        'vm_payment_option': 'NA',
        'spot_percentage': 0,
        'runs_per_day': 12,
        'avg_runtime_minutes': 60,
        'days_per_month': 30,
        'notes': 'GCP medium cluster, Photon enabled'
    },
    # GCP europe-west1
    {
        'scenario_id': 10,
        'workload_name': 'GCP EU-West Heavy ETL',
        'cloud': 'GCP',
        'region': 'europe-west1',
        'driver_node_type': 'n1-standard-16',
        'worker_node_type': 'n1-standard-32',
        'num_workers': 8,
        'photon_enabled': True,
        'vm_pricing_tier': 'on_demand',
        'vm_payment_option': 'NA',
        'spot_percentage': 0,
        'runs_per_day': 24,
        'avg_runtime_minutes': 120,
        'days_per_month': 30,
        'notes': 'GCP large cluster, Photon, heavy usage'
    }
]

print(f"📋 Prepared {len(test_scenarios)} test scenarios for JOBS Classic")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 3.1 Insert Test Line Items

# COMMAND ----------

insert_line_item_sql = """
INSERT INTO lakemeter.line_items (
    line_item_id, estimate_id, display_order, workload_name, workload_type,
    serverless_enabled, serverless_mode, photon_enabled, vector_search_mode,
    driver_node_type, worker_node_type, num_workers,
    runs_per_day, avg_runtime_minutes, days_per_month,
    vm_pricing_tier, vm_payment_option, spot_percentage,
    notes, created_at, updated_at
) VALUES (
    %s, %s, %s, %s, %s,
    %s, %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s
);
"""

# Track inserted line item IDs
line_item_ids = []

for scenario in test_scenarios:
    line_item_id = str(uuid.uuid4())
    line_item_ids.append(line_item_id)
    
    execute_query(
        insert_line_item_sql,
        (
            line_item_id,
            TEST_ESTIMATE_ID,
            scenario['scenario_id'],
            scenario['workload_name'],
            'JOBS',  # workload_type
            False,  # serverless_enabled (Classic compute)
            None,   # serverless_mode
            scenario['photon_enabled'],
            None,   # vector_search_mode
            scenario['driver_node_type'],
            scenario['worker_node_type'],
            scenario['num_workers'],
            scenario['runs_per_day'],
            scenario['avg_runtime_minutes'],
            scenario['days_per_month'],
            scenario['vm_pricing_tier'],
            scenario['vm_payment_option'],
            scenario['spot_percentage'],
            scenario['notes'],
            datetime.now(),
            datetime.now()
        ),
        fetch=False
    )
    
    print(f"✅ Scenario {scenario['scenario_id']}: {scenario['workload_name']}")

print(f"\n✅ Inserted {len(line_item_ids)} test line items")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Execute Cost Calculation View & Display Results

# COMMAND ----------

# Query the cost calculation view
query_results_sql = """
SELECT 
    c.display_order,
    c.workload_name,
    c.workload_type,
    -- Configuration
    c.driver_node_type,
    c.worker_node_type,
    c.num_workers,
    c.photon_enabled,
    c.serverless_enabled,
    -- Usage
    c.runs_per_day,
    c.avg_runtime_minutes,
    c.days_per_month,
    c.hours_per_month,
    -- Pricing
    c.vm_pricing_tier,
    c.spot_percentage,
    -- DBU Calculation
    c.driver_dbu_rate,
    c.worker_dbu_rate,
    c.photon_multiplier,
    c.dbu_per_hour,
    c.dbu_per_month,
    -- VM Costs
    c.driver_vm_cost_per_hour,
    c.worker_vm_cost_per_hour,
    c.vm_cost_per_hour,
    c.vm_cost_per_month,
    -- DBU Pricing
    c.dbu_price,
    c.dbu_cost_per_month,
    -- Total
    c.cost_per_month,
    c.notes
FROM lakemeter.v_line_items_with_costs c
WHERE c.estimate_id = %s
ORDER BY c.display_order;
"""

results_df = execute_query(query_results_sql, (TEST_ESTIMATE_ID,))

print(f"✅ Retrieved {len(results_df)} cost calculation results")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Display Results - Summary View

# COMMAND ----------

# Create summary view with key metrics
summary_df = results_df[[
    'display_order',
    'workload_name',
    'num_workers',
    'photon_enabled',
    'vm_pricing_tier',
    'runs_per_day',
    'avg_runtime_minutes',
    'hours_per_month',
    'dbu_per_month',
    'dbu_cost_per_month',
    'vm_cost_per_month',
    'cost_per_month'
]].copy()

summary_df['photon_enabled'] = summary_df['photon_enabled'].map({True: 'Yes', False: 'No'})
summary_df['dbu_per_month'] = summary_df['dbu_per_month'].round(2)
summary_df['dbu_cost_per_month'] = summary_df['dbu_cost_per_month'].round(2)
summary_df['vm_cost_per_month'] = summary_df['vm_cost_per_month'].round(2)
summary_df['cost_per_month'] = summary_df['cost_per_month'].round(2)

print("=" * 180)
print("JOBS CLASSIC - COST CALCULATION SUMMARY")
print("=" * 180)
print(tabulate(summary_df, headers='keys', tablefmt='grid', showindex=False))
print("=" * 180)

# Display Spark DataFrame for better Databricks visualization
display(summary_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Detailed Breakdown by Cloud & Region

# COMMAND ----------

# AWS breakdown
aws_scenarios = [s for s in test_scenarios if s['cloud'] == 'AWS']
aws_results = results_df[results_df['display_order'].isin([s['scenario_id'] for s in aws_scenarios])]

print("\n" + "=" * 120)
print("AWS RESULTS")
print("=" * 120)
print(f"US-East-1 Scenarios: {len([s for s in aws_scenarios if s['region'] == 'us-east-1'])}")
print(f"EU-West-1 Scenarios: {len([s for s in aws_scenarios if s['region'] == 'eu-west-1'])}")
print(f"Total Monthly Cost: ${aws_results['cost_per_month'].sum():,.2f}")
print(f"Total DBUs: {aws_results['dbu_per_month'].sum():,.2f}")
print("=" * 120)

display(aws_results[['workload_name', 'photon_enabled', 'vm_pricing_tier', 
                      'dbu_per_month', 'cost_per_month']])

# COMMAND ----------

# Azure breakdown
azure_scenarios = [s for s in test_scenarios if s['cloud'] == 'AZURE']
azure_results = results_df[results_df['display_order'].isin([s['scenario_id'] for s in azure_scenarios])]

print("\n" + "=" * 120)
print("AZURE RESULTS")
print("=" * 120)
print(f"East US Scenarios: {len([s for s in azure_scenarios if s['region'] == 'eastus'])}")
print(f"West Europe Scenarios: {len([s for s in azure_scenarios if s['region'] == 'westeurope'])}")
print(f"Total Monthly Cost: ${azure_results['cost_per_month'].sum():,.2f}")
print(f"Total DBUs: {azure_results['dbu_per_month'].sum():,.2f}")
print("=" * 120)

display(azure_results[['workload_name', 'photon_enabled', 'vm_pricing_tier', 
                        'dbu_per_month', 'cost_per_month']])

# COMMAND ----------

# GCP breakdown
gcp_scenarios = [s for s in test_scenarios if s['cloud'] == 'GCP']
gcp_results = results_df[results_df['display_order'].isin([s['scenario_id'] for s in gcp_scenarios])]

print("\n" + "=" * 120)
print("GCP RESULTS")
print("=" * 120)
print(f"US-Central1 Scenarios: {len([s for s in gcp_scenarios if s['region'] == 'us-central1'])}")
print(f"Europe-West1 Scenarios: {len([s for s in gcp_scenarios if s['region'] == 'europe-west1'])}")
print(f"Total Monthly Cost: ${gcp_results['cost_per_month'].sum():,.2f}")
print(f"Total DBUs: {gcp_results['dbu_per_month'].sum():,.2f}")
print("=" * 120)

display(gcp_results[['workload_name', 'photon_enabled', 'vm_pricing_tier', 
                      'dbu_per_month', 'cost_per_month']])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Validation & Analysis

# COMMAND ----------

# MAGIC %md
# MAGIC ### 7.1 Photon Impact Analysis

# COMMAND ----------

photon_analysis = results_df.groupby('photon_enabled').agg({
    'dbu_per_month': 'sum',
    'cost_per_month': 'sum',
    'display_order': 'count'
}).rename(columns={'display_order': 'scenario_count'})

photon_analysis['avg_cost_per_scenario'] = photon_analysis['cost_per_month'] / photon_analysis['scenario_count']
photon_analysis['photon_enabled'] = photon_analysis.index.map({True: 'Photon ON', False: 'Photon OFF'})

print("\n" + "=" * 80)
print("PHOTON IMPACT ANALYSIS")
print("=" * 80)
print(tabulate(photon_analysis, headers='keys', tablefmt='grid'))
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ### 7.2 VM Pricing Tier Comparison

# COMMAND ----------

pricing_analysis = results_df.groupby('vm_pricing_tier').agg({
    'vm_cost_per_month': 'sum',
    'cost_per_month': 'sum',
    'display_order': 'count'
}).rename(columns={'display_order': 'scenario_count'})

pricing_analysis['avg_vm_cost_per_scenario'] = pricing_analysis['vm_cost_per_month'] / pricing_analysis['scenario_count']

print("\n" + "=" * 80)
print("VM PRICING TIER COMPARISON")
print("=" * 80)
print(tabulate(pricing_analysis, headers='keys', tablefmt='grid'))
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ### 7.3 Usage Pattern Analysis

# COMMAND ----------

# Categorize by usage
def categorize_usage(row):
    if row['runs_per_day'] <= 4:
        return 'Light'
    elif row['runs_per_day'] <= 12:
        return 'Medium'
    else:
        return 'Heavy'

results_df['usage_category'] = results_df.apply(categorize_usage, axis=1)

usage_analysis = results_df.groupby('usage_category').agg({
    'hours_per_month': 'mean',
    'dbu_per_month': 'mean',
    'cost_per_month': 'mean',
    'display_order': 'count'
}).rename(columns={'display_order': 'scenario_count'})

print("\n" + "=" * 80)
print("USAGE PATTERN ANALYSIS")
print("=" * 80)
print(tabulate(usage_analysis, headers='keys', tablefmt='grid'))
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Export Full Results to CSV

# COMMAND ----------

# Export full results
output_path = f"/dbfs/tmp/test_jobs_classic_{TEST_RUN_ID}.csv"
results_df.to_csv(output_path, index=False)

print(f"✅ Full results exported to: {output_path}")
print(f"   Download via: /tmp/test_jobs_classic_{TEST_RUN_ID}.csv")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Cleanup - Remove Test Data

# COMMAND ----------

# Delete test line items
delete_line_items_sql = "DELETE FROM lakemeter.line_items WHERE estimate_id = %s;"
execute_query(delete_line_items_sql, (TEST_ESTIMATE_ID,), fetch=False)

# Delete test estimate
delete_estimate_sql = "DELETE FROM lakemeter.estimates WHERE estimate_id = %s;"
execute_query(delete_estimate_sql, (TEST_ESTIMATE_ID,), fetch=False)

# Delete test user
delete_user_sql = "DELETE FROM lakemeter.users WHERE user_id = %s;"
execute_query(delete_user_sql, (TEST_USER_ID,), fetch=False)

print("✅ Cleanup complete - all test data removed")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Test Summary

# COMMAND ----------

print("\n" + "=" * 100)
print("TEST EXECUTION SUMMARY - JOBS CLASSIC")
print("=" * 100)
print(f"Test Run ID: {TEST_RUN_ID}")
print(f"Total Scenarios: {len(test_scenarios)}")
print(f"Clouds Tested: AWS, Azure, GCP")
print(f"Regions Tested: 6 (2 per cloud)")
print(f"")
print(f"Configuration Coverage:")
print(f"  - Photon Enabled: {len(results_df[results_df['photon_enabled'] == True])}")
print(f"  - Photon Disabled: {len(results_df[results_df['photon_enabled'] == False])}")
print(f"  - On-Demand Pricing: {len(results_df[results_df['vm_pricing_tier'] == 'on_demand'])}")
print(f"  - Spot Pricing: {len(results_df[results_df['vm_pricing_tier'] == 'spot'])}")
print(f"  - Reserved Pricing: {len(results_df[results_df['vm_pricing_tier'] == 'reserved_1y'])}")
print(f"")
print(f"Total Monthly Cost (All Scenarios): ${results_df['cost_per_month'].sum():,.2f}")
print(f"Total DBUs (All Scenarios): {results_df['dbu_per_month'].sum():,.2f}")
print(f"")
print(f"Results exported to: /tmp/test_jobs_classic_{TEST_RUN_ID}.csv")
print("=" * 100)
print("\n✅ TEST COMPLETE!")

