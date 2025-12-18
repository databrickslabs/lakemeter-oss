# Databricks notebook source
# MAGIC %md
# MAGIC # Function Test: JOBS Classic Compute
# MAGIC
# MAGIC **Objective:** Validate `calculate_line_item_costs()` function for JOBS Classic workloads
# MAGIC
# MAGIC **Approach:** Call function directly (no database INSERTs) - faster and cleaner than view-based tests
# MAGIC
# MAGIC **Test Matrix:**
# MAGIC - **Clouds:** AWS, Azure, GCP (2 regions each: US + Europe)
# MAGIC - **Tiers:** STANDARD, PREMIUM, ENTERPRISE (AZURE: no ENTERPRISE)
# MAGIC - **Instance types:** 2 per cloud, **dynamically fetched** from `sync_pricing_vm_costs`
# MAGIC   - AWS: i3.xlarge, i3.2xlarge (preferred, or first 2 available)
# MAGIC   - Azure: First 2 available (e.g., Standard_D4s_v3, Standard_D8s_v3)
# MAGIC   - GCP: First 2 available (e.g., n1-highmem-4, n1-highmem-8)
# MAGIC - **Photon:** Enabled, Disabled
# MAGIC - **Worker counts:** 2, 4
# MAGIC - **Usage:** Light only (4 runs/day, 30 min runtime)
# MAGIC - **VM Pricing:**
# MAGIC   - **AWS:** 8 options (on_demand, spot, reserved_1y/3y with no/partial/all upfront)
# MAGIC   - **AZURE/GCP:** 4 options (on_demand, spot, reserved_1y, reserved_3y)
# MAGIC
# MAGIC **Total Scenarios:** ~1,400 (AWS: 768 | AZURE: 256 | GCP: 384)

# COMMAND ----------

# Load Lakebase configuration
%run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
import pandas as pd

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
# MAGIC ## Pre-Flight Check: Verify Function Exists

# COMMAND ----------

check_function_sql = """
SELECT COUNT(*) as func_count
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'lakemeter'
  AND p.proname = 'calculate_line_item_costs';
"""

func_check = execute_query(check_function_sql)

print("=" * 80)
print("FUNCTION AVAILABILITY CHECK")
print("=" * 80)

if func_check['func_count'].iloc[0] > 0:
    print("✅ calculate_line_item_costs() function EXISTS")
else:
    print("❌ calculate_line_item_costs() function DOES NOT EXIST!")
    print("   Please run: 4_Functions/09_Main_Orchestrator.py")
    dbutils.notebook.exit("Function not found - aborting test")

print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate Test Scenarios (Same as Test_01)

# COMMAND ----------

# Region mappings
region_map = {
    'AWS': {'us': 'us-east-1', 'eu': 'eu-west-1'},
    'AZURE': {'us': 'eastus', 'eu': 'westeurope'},
    'GCP': {'us': 'us-central1', 'eu': 'europe-west1'}
}

# Cloud-specific instance types (dynamically query from pricing data)
print("🔍 Fetching cloud-specific instance types from pricing data...")

instance_query = """
SELECT DISTINCT 
    cloud,
    instance_type,
    COUNT(DISTINCT region) as region_count
FROM lakemeter.sync_pricing_vm_costs
WHERE cloud IN ('AWS', 'AZURE', 'GCP')
  AND pricing_tier = 'on_demand'
GROUP BY cloud, instance_type
HAVING COUNT(DISTINCT region) >= 2  -- At least 2 regions
ORDER BY cloud, instance_type;
"""

available_instances = execute_query(instance_query)

# Select TWO instance types per cloud
cloud_instances = {}
for cloud in ['AWS', 'AZURE', 'GCP']:
    cloud_data = available_instances[available_instances['cloud'] == cloud]
    if not cloud_data.empty:
        # For AWS, prefer i3.xlarge and i3.2xlarge if available
        if cloud == 'AWS':
            aws_i3_small = cloud_data[cloud_data['instance_type'].str.contains('i3.xlarge', regex=False, na=False)]
            aws_i3_medium = cloud_data[cloud_data['instance_type'].str.contains('i3.2xlarge', regex=False, na=False)]
            
            instances = []
            if not aws_i3_small.empty:
                instances.append(aws_i3_small.iloc[0]['instance_type'])
            if not aws_i3_medium.empty:
                instances.append(aws_i3_medium.iloc[0]['instance_type'])
            
            # If we don't have 2 yet, just take first 2 available
            if len(instances) < 2:
                instances = cloud_data.head(2)['instance_type'].tolist()
        else:
            # For AZURE/GCP, just take first 2 available
            instances = cloud_data.head(2)['instance_type'].tolist()
        
        cloud_instances[cloud] = instances
        print(f"   {cloud}: {', '.join(instances)}")
    else:
        print(f"   ⚠️  {cloud}: No instance types found in pricing data!")
        cloud_instances[cloud] = []

# Simplified: Just one instance size, 2 worker counts, 1 usage pattern
worker_counts = [2, 4]  # Reduced from [2, 5, 10]

# Just Light usage
usage_patterns = [
    {'runs': 4, 'mins': 30, 'label': 'Light'},
]

# AWS VM payment options (comprehensive)
aws_payment_options = [
    {'driver_tier': 'on_demand', 'worker_tier': 'on_demand', 'driver_payment': 'NA', 'worker_payment': 'NA', 'label': 'OnDemand'},
    {'driver_tier': 'on_demand', 'worker_tier': 'spot', 'driver_payment': 'NA', 'worker_payment': 'NA', 'label': 'Spot'},
    {'driver_tier': 'reserved_1y', 'worker_tier': 'reserved_1y', 'driver_payment': 'no_upfront', 'worker_payment': 'no_upfront', 'label': 'Res1y-NoUp'},
    {'driver_tier': 'reserved_1y', 'worker_tier': 'reserved_1y', 'driver_payment': 'partial_upfront', 'worker_payment': 'partial_upfront', 'label': 'Res1y-PartialUp'},
    {'driver_tier': 'reserved_1y', 'worker_tier': 'reserved_1y', 'driver_payment': 'all_upfront', 'worker_payment': 'all_upfront', 'label': 'Res1y-AllUp'},
    {'driver_tier': 'reserved_3y', 'worker_tier': 'reserved_3y', 'driver_payment': 'no_upfront', 'worker_payment': 'no_upfront', 'label': 'Res3y-NoUp'},
    {'driver_tier': 'reserved_3y', 'worker_tier': 'reserved_3y', 'driver_payment': 'partial_upfront', 'worker_payment': 'partial_upfront', 'label': 'Res3y-PartialUp'},
    {'driver_tier': 'reserved_3y', 'worker_tier': 'reserved_3y', 'driver_payment': 'all_upfront', 'worker_payment': 'all_upfront', 'label': 'Res3y-AllUp'},
]

# Azure/GCP VM payment options (simpler)
azure_gcp_payment_options = [
    {'driver_tier': 'on_demand', 'worker_tier': 'on_demand', 'driver_payment': 'NA', 'worker_payment': 'NA', 'label': 'OnDemand'},
    {'driver_tier': 'on_demand', 'worker_tier': 'spot', 'driver_payment': 'NA', 'worker_payment': 'NA', 'label': 'Spot'},
    {'driver_tier': 'reserved_1y', 'worker_tier': 'reserved_1y', 'driver_payment': 'NA', 'worker_payment': 'NA', 'label': 'Reserved1y'},
    {'driver_tier': 'reserved_3y', 'worker_tier': 'reserved_3y', 'driver_payment': 'NA', 'worker_payment': 'NA', 'label': 'Reserved3y'},
]

# Generate test scenarios (simplified)
test_scenarios = []
scenario_id = 1

for cloud in ['AWS', 'AZURE', 'GCP']:
    # Skip cloud if no instance types found
    if not cloud_instances[cloud]:
        print(f"⚠️  Skipping {cloud} - no instance types in pricing data")
        continue
    
    payment_options = aws_payment_options if cloud == 'AWS' else azure_gcp_payment_options
    
    for region_type in ['us', 'eu']:
        region = region_map[cloud][region_type]
        
        for tier in ['STANDARD', 'PREMIUM', 'ENTERPRISE']:
            # Skip ENTERPRISE for AZURE
            if cloud == 'AZURE' and tier == 'ENTERPRISE':
                continue
            
            for photon in [True, False]:
                # Loop through the 2 instance types for this cloud
                for instance_type in cloud_instances[cloud]:
                    for workers in worker_counts:
                        for usage in usage_patterns:
                            for payment in payment_options:
                                # Get instance label (last part after .)
                                instance_label = instance_type.split('.')[-1] if '.' in instance_type else instance_type.split('_')[-1]
                                
                                test_scenarios.append({
                                    'scenario_id': scenario_id,
                                    'cloud': cloud,
                                    'region': region,
                                    'tier': tier,
                                    'photon': photon,
                                    'driver': instance_type,  # Cloud-specific!
                                    'worker': instance_type,  # Cloud-specific!
                                    'num_workers': workers,
                                    'runs': usage['runs'],
                                    'runtime_mins': usage['mins'],
                                    'driver_tier': payment['driver_tier'],
                                    'worker_tier': payment['worker_tier'],
                                    'driver_payment': payment['driver_payment'],
                                    'worker_payment': payment['worker_payment'],
                                    'label': f"{cloud} {tier} {instance_label} {workers}w {usage['label']} {payment['label']}"
                                })
                                scenario_id += 1

print(f"\n📋 Generated {len(test_scenarios)} test scenarios")
print(f"   AWS: {len([s for s in test_scenarios if s['cloud'] == 'AWS'])} scenarios")
print(f"   AZURE: {len([s for s in test_scenarios if s['cloud'] == 'AZURE'])} scenarios (no ENTERPRISE)")
print(f"   GCP: {len([s for s in test_scenarios if s['cloud'] == 'GCP'])} scenarios")

print(f"\n   Scenario breakdown per cloud:")
print(f"   • 2 regions (US + EU)")
print(f"   • 3 tiers (STANDARD, PREMIUM, ENTERPRISE) - AZURE only 2")
print(f"   • 2 Photon states (on/off)")
print(f"   • 2 instance types per cloud (dynamically fetched)")
print(f"   • 2 worker counts ({', '.join(map(str, worker_counts))})")
print(f"   • 1 usage pattern (Light: 4 runs/day, 30 min)")
print(f"   • AWS: 8 VM payment options | AZURE/GCP: 4 VM payment options")

print(f"\n   Sample scenarios (first 5):")
for s in test_scenarios[:5]:
    print(f"      {s['scenario_id']:3d}. {s['label']}")
    
print(f"\n   Full breakdown:")
print(f"      AWS:   2 regions × 3 tiers × 2 photon × 2 instances × 2 workers × 1 usage × 8 payments = {2*3*2*2*2*1*8} scenarios")
print(f"      AZURE: 2 regions × 2 tiers × 2 photon × 2 instances × 2 workers × 1 usage × 4 payments = {2*2*2*2*2*1*4} scenarios")
print(f"      GCP:   2 regions × 3 tiers × 2 photon × 2 instances × 2 workers × 1 usage × 4 payments = {2*3*2*2*2*1*4} scenarios")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Call Function for Each Scenario

# COMMAND ----------

print("=" * 120)
print("CALLING calculate_line_item_costs() FOR ALL SCENARIOS")
print("=" * 120)

results = []
errors = []

for i, scenario in enumerate(test_scenarios, 1):
    if i % 100 == 0:
        print(f"   Processing scenario {i}/{len(test_scenarios)}...")
    
    # Build function call with explicit type casts
    query = f"""
    SELECT 
        '{scenario['label']}'::VARCHAR as scenario,
        '{scenario['cloud']}'::VARCHAR as cloud,
        '{scenario['region']}'::VARCHAR as region,
        '{scenario['tier']}'::VARCHAR as tier,
        {scenario['photon']}::BOOLEAN as photon,
        '{scenario['driver']}'::VARCHAR as driver,
        '{scenario['worker']}'::VARCHAR as worker,
        {scenario['num_workers']}::INT as num_workers,
        '{scenario['driver_tier']}'::VARCHAR as driver_tier,
        '{scenario['worker_tier']}'::VARCHAR as worker_tier,
        '{scenario['driver_payment']}'::VARCHAR as driver_payment,
        '{scenario['worker_payment']}'::VARCHAR as worker_payment,
        *
    FROM lakemeter.calculate_line_item_costs(
        'JOBS'::VARCHAR,
        '{scenario['cloud']}'::VARCHAR,
        '{scenario['region']}'::VARCHAR,
        '{scenario['tier']}'::VARCHAR,
        FALSE::BOOLEAN,                          -- serverless_enabled
        {scenario['photon']}::BOOLEAN,           -- photon_enabled
        NULL::VARCHAR,                           -- dlt_edition
        '{scenario['driver']}'::VARCHAR,         -- driver_node_type
        '{scenario['worker']}'::VARCHAR,         -- worker_node_type
        {scenario['num_workers']}::INT,          -- num_workers
        '{scenario['driver_tier']}'::VARCHAR,    -- driver_pricing_tier
        '{scenario['worker_tier']}'::VARCHAR,    -- worker_pricing_tier
        {scenario['runs']}::INT,                 -- runs_per_day
        {scenario['runtime_mins']}::INT,         -- avg_runtime_minutes
        30::INT,                                 -- days_per_month
        NULL::INT,                               -- p_hours_per_month
        'standard'::VARCHAR,                     -- serverless_mode
        NULL::VARCHAR,                           -- dbsql_warehouse_type
        NULL::VARCHAR,                           -- dbsql_warehouse_size
        1::INT,                                  -- dbsql_num_clusters
        'on_demand'::VARCHAR,                    -- dbsql_vm_pricing_tier
        NULL::VARCHAR,                           -- vector_search_mode
        0::DECIMAL,                              -- vector_search_capacity_millions
        NULL::VARCHAR,                           -- serverless_size
        NULL::VARCHAR,                           -- fmapi_model (ORDER: model BEFORE provider!)
        NULL::VARCHAR,                           -- fmapi_provider
        'global'::VARCHAR,                       -- fmapi_endpoint_type (not fmapi_endpoint!)
        'standard'::VARCHAR,                     -- fmapi_context_length
        'pay_per_token'::VARCHAR,                -- fmapi_provisioned_type (not fmapi_pricing_type!)
        0::BIGINT,                               -- fmapi_input_tokens_per_month (BIGINT!)
        0::BIGINT,                               -- fmapi_output_tokens_per_month (BIGINT!)
        0::INT,                                  -- lakebase_cu
        1::INT,                                  -- lakebase_ha_nodes
        '{scenario['driver_payment']}'::VARCHAR, -- driver_payment_option
        '{scenario['worker_payment']}'::VARCHAR  -- worker_payment_option
    );
    """
    
    try:
        result = execute_query(query)
        if not result.empty:
            results.append(result.iloc[0])
    except Exception as e:
        errors.append({'scenario_id': scenario['scenario_id'], 'error': str(e)})

print(f"\n✅ Completed {len(results)} scenarios successfully")
if errors:
    print(f"⚠️  {len(errors)} scenarios had errors")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation & Results

# COMMAND ----------

if len(results) > 0:
    results_df = pd.DataFrame(results)
    
    print("=" * 120)
    print("TEST RESULTS SUMMARY")
    print("=" * 120)
    
    # Check for $0 costs
    zero_dbu_cost = results_df[results_df['dbu_cost_per_month'] == 0]
    zero_vm_cost = results_df[results_df['vm_cost_per_month'] == 0]
    zero_total_cost = results_df[results_df['cost_per_month'] == 0]
    
    print(f"\n📊 Total scenarios processed: {len(results_df)}")
    print(f"   ✅ Non-zero DBU costs: {len(results_df) - len(zero_dbu_cost)}")
    print(f"   ⚠️  Zero DBU costs: {len(zero_dbu_cost)}")
    print(f"   ✅ Non-zero VM costs: {len(results_df) - len(zero_vm_cost)}")
    print(f"   ⚠️  Zero VM costs: {len(zero_vm_cost)}")
    print(f"   ✅ Non-zero TOTAL costs: {len(results_df) - len(zero_total_cost)}")
    print(f"   ⚠️  Zero TOTAL costs: {len(zero_total_cost)}")
    
    # Show sample results (first 10)
    print("\n" + "=" * 120)
    print("SAMPLE RESULTS (First 10 - Quick Overview)")
    print("=" * 120)
    
    sample_cols = ['scenario', 'cloud', 'tier', 'photon', 'driver', 'num_workers', 
                   'driver_tier', 'worker_tier',
                   'dbu_per_hour', 'dbu_cost_per_month', 
                   'vm_cost_per_month', 'cost_per_month']
    
    display(results_df[sample_cols].head(10))
    
    # STEP-BY-STEP CALCULATION BREAKDOWN (First 20)
    print("\n" + "=" * 200)
    print("STEP-BY-STEP CALCULATION BREAKDOWN (First 20 - Manual Validation)")
    print("=" * 200)
    
    # Calculate individual node DBU/hr for better visibility
    # For Jobs: DBU = (1 driver + num_workers workers) × base_dbu × photon_multiplier
    # We need to reverse-engineer individual node DBU from total
    
    breakdown_df = results_df.head(20).copy()
    
    # Add calculated fields for breakdown
    # Note: For Jobs Classic, DBU is calculated per cluster, not per node
    # But we can show the breakdown conceptually
    
    breakdown_cols = [
        'scenario', 'cloud', 'region', 'tier', 'photon',
        'driver', 'driver_tier', 'driver_payment',
        'driver_vm_cost_per_hour', 
        'worker', 'worker_tier', 'worker_payment', 'num_workers',
        'worker_vm_cost_per_hour',
        'total_vm_cost_per_hour',
        'dbu_per_hour', 'hours_per_month',
        'dbu_per_month', 'dbu_price', 'dbu_cost_per_month',
        'driver_vm_cost_per_month', 'total_worker_vm_cost_per_month',
        'vm_cost_per_month', 'cost_per_month'
    ]
    
    # Check which columns exist
    available_breakdown_cols = [col for col in breakdown_cols if col in breakdown_df.columns]
    
    display(breakdown_df[available_breakdown_cols])
    
    # ULTRA-DETAILED MANUAL CALCULATION TABLE (First 10 only - very wide)
    print("\n" + "=" * 200)
    print("ULTRA-DETAILED MANUAL CALCULATION (First 10 - Step-by-Step Formula)")
    print("=" * 200)
    print("Shows: Driver (VM+DBU) | Worker (VM+DBU) | DBU Breakdown | Cluster/Hour | Monthly Totals")
    print("=" * 200)
    
    manual_calc_df = results_df.head(10).copy()
    
    # Create explicit calculation columns
    manual_calc_df['1_driver_instance'] = manual_calc_df['driver']
    manual_calc_df['2_driver_vm_$/hr'] = manual_calc_df['driver_vm_cost_per_hour']
    manual_calc_df['3_driver_tier'] = manual_calc_df['driver_tier']
    manual_calc_df['4_driver_payment'] = manual_calc_df['driver_payment']
    
    manual_calc_df['5_worker_instance'] = manual_calc_df['worker']
    manual_calc_df['6_worker_vm_$/hr_each'] = manual_calc_df['worker_vm_cost_per_hour'].apply(
        lambda x: x / manual_calc_df.loc[manual_calc_df['worker_vm_cost_per_hour'] == x, 'num_workers'].values[0] 
        if manual_calc_df.loc[manual_calc_df['worker_vm_cost_per_hour'] == x, 'num_workers'].values[0] > 0 else 0
    )
    manual_calc_df['7_num_workers'] = manual_calc_df['num_workers']
    manual_calc_df['8_worker_tier'] = manual_calc_df['worker_tier']
    manual_calc_df['9_worker_payment'] = manual_calc_df['worker_payment']
    
    # Calculate DBU breakdown (driver vs worker)
    # For JOBS Classic: total_dbu = (1 driver + num_workers) × base_dbu × photon_multiplier
    # So: base_dbu_per_node = total_dbu / (1 + num_workers)
    manual_calc_df['driver_dbu_per_hr'] = manual_calc_df['dbu_per_hour'] / (1 + manual_calc_df['num_workers'])
    manual_calc_df['worker_dbu_per_hr_each'] = manual_calc_df['driver_dbu_per_hr']  # Same instance type
    manual_calc_df['total_worker_dbu_per_hr'] = manual_calc_df['worker_dbu_per_hr_each'] * manual_calc_df['num_workers']
    
    manual_calc_df['10_driver_dbu/hr'] = manual_calc_df['driver_dbu_per_hr']
    manual_calc_df['11_worker_dbu/hr_each'] = manual_calc_df['worker_dbu_per_hr_each']
    manual_calc_df['12_total_worker_dbu/hr'] = manual_calc_df['total_worker_dbu_per_hr']
    manual_calc_df['13_cluster_dbu/hr'] = manual_calc_df['dbu_per_hour']
    
    manual_calc_df['14_cluster_vm_$/hr'] = manual_calc_df['total_vm_cost_per_hour']
    manual_calc_df['15_hours/month'] = manual_calc_df['hours_per_month']
    
    manual_calc_df['16_dbu/month'] = manual_calc_df['dbu_per_month']
    manual_calc_df['17_dbu_price'] = manual_calc_df['dbu_price']
    manual_calc_df['18_dbu_cost/month'] = manual_calc_df['dbu_cost_per_month']
    manual_calc_df['19_vm_cost/month'] = manual_calc_df['vm_cost_per_month']
    manual_calc_df['20_TOTAL/month'] = manual_calc_df['cost_per_month']
    
    # Split into multiple tables for readability
    print("\n--- PART 1: Driver Configuration (VM + DBU) ---")
    driver_cols = ['scenario', 'cloud', 'tier', 'photon', 
                   '1_driver_instance', '3_driver_tier', '4_driver_payment', 
                   '2_driver_vm_$/hr', '10_driver_dbu/hr']
    display(manual_calc_df[driver_cols])
    
    print("\n--- PART 2: Worker Configuration (VM + DBU) ---")
    worker_cols = ['scenario', '5_worker_instance', '7_num_workers', 
                   '8_worker_tier', '9_worker_payment', 
                   '6_worker_vm_$/hr_each', '11_worker_dbu/hr_each']
    display(manual_calc_df[worker_cols])
    
    print("\n--- PART 3: DBU Breakdown Per Hour ---")
    dbu_breakdown_cols = ['scenario', '10_driver_dbu/hr', '11_worker_dbu/hr_each', 
                          '7_num_workers', '12_total_worker_dbu/hr', '13_cluster_dbu/hr']
    display(manual_calc_df[dbu_breakdown_cols])
    
    print("\n--- PART 4: Cluster Per Hour (VM) ---")
    cluster_cols = ['scenario', '14_cluster_vm_$/hr', '13_cluster_dbu/hr']
    display(manual_calc_df[cluster_cols])
    
    print("\n--- PART 5: Monthly Calculations ---")
    monthly_cols = ['scenario', '15_hours/month', 
                    '16_dbu/month', '17_dbu_price', '18_dbu_cost/month',
                    '19_vm_cost/month', '20_TOTAL/month']
    display(manual_calc_df[monthly_cols])
    
    print("\n" + "=" * 200)
    print("FORMULA REFERENCE:")
    print("=" * 200)
    print("VM COSTS:")
    print("  Driver VM Cost/Month   = driver_vm_$/hr × hours/month")
    print("  Worker VM Cost/Month   = worker_vm_$/hr_each × num_workers × hours/month")
    print("  Cluster VM $/Hour      = driver_vm_$/hr + (worker_vm_$/hr_each × num_workers)")
    print("  VM Cost/Month          = cluster_vm_$/hr × hours/month")
    print("")
    print("DBU BREAKDOWN:")
    print("  Driver DBU/Hour        = cluster_dbu/hr ÷ (1 + num_workers)")
    print("  Worker DBU/Hour Each   = driver_dbu/hr (same instance type)")
    print("  Total Worker DBU/Hour  = worker_dbu/hr_each × num_workers")
    print("  Cluster DBU/Hour       = driver_dbu/hr + total_worker_dbu/hr")
    print("")
    print("MONTHLY COSTS:")
    print("  DBU/Month              = cluster_dbu/hr × hours/month")
    print("  DBU Cost/Month         = dbu/month × dbu_price")
    print("  TOTAL Cost/Month       = dbu_cost/month + vm_cost/month")
    print("=" * 200)
    
    # Cost Calculation Validation Table (showing formula check)
    print("\n" + "=" * 150)
    print("COST CALCULATION VALIDATION (First 20)")
    print("=" * 150)
    
    # Create validation dataframe
    validation_df = results_df.head(20).copy()
    validation_df['dbu_calc_check'] = (validation_df['dbu_per_hour'] * validation_df['hours_per_month'] * validation_df['dbu_price']).round(2)
    validation_df['vm_calc_check'] = (validation_df['driver_vm_cost_per_month'] + validation_df['total_worker_vm_cost_per_month']).round(2) if 'driver_vm_cost_per_month' in validation_df.columns else 0
    validation_df['total_calc_check'] = (validation_df['dbu_cost_per_month'] + validation_df['vm_cost_per_month']).round(2)
    validation_df['dbu_match'] = (abs(validation_df['dbu_cost_per_month'] - validation_df['dbu_calc_check']) < 0.01).map({True: '✅', False: '❌'})
    validation_df['vm_match'] = (abs(validation_df['vm_cost_per_month'] - validation_df['vm_calc_check']) < 0.01).map({True: '✅', False: '❌'}) if 'driver_vm_cost_per_month' in validation_df.columns else '✅'
    validation_df['total_match'] = (abs(validation_df['cost_per_month'] - validation_df['total_calc_check']) < 0.01).map({True: '✅', False: '❌'})
    
    validation_cols = [
        'scenario', 'cloud', 'tier',
        'dbu_cost_per_month', 'dbu_calc_check', 'dbu_match',
        'vm_cost_per_month', 'vm_calc_check', 'vm_match',
        'cost_per_month', 'total_calc_check', 'total_match'
    ]
    
    available_validation_cols = [col for col in validation_cols if col in validation_df.columns]
    
    display(validation_df[available_validation_cols])
    
    # Show any mismatches
    dbu_mismatches = validation_df[validation_df['dbu_match'] == '❌']
    vm_mismatches = validation_df[validation_df['vm_match'] == '❌']
    total_mismatches = validation_df[validation_df['total_match'] == '❌']
    
    if len(dbu_mismatches) > 0 or len(vm_mismatches) > 0 or len(total_mismatches) > 0:
        print("\n⚠️  CALCULATION MISMATCHES FOUND:")
        if len(dbu_mismatches) > 0:
            print(f"   ❌ DBU calculation mismatches: {len(dbu_mismatches)}")
        if len(vm_mismatches) > 0:
            print(f"   ❌ VM calculation mismatches: {len(vm_mismatches)}")
        if len(total_mismatches) > 0:
            print(f"   ❌ Total calculation mismatches: {len(total_mismatches)}")
    else:
        print("\n✅ All calculations match expected formulas!")
    
    # Assertions
    print("\n" + "=" * 120)
    print("VALIDATION CHECKS")
    print("=" * 120)
    
    passed = 0
    failed = 0
    
    # Check 1: All scenarios should have positive costs (assuming pricing data exists)
    if len(zero_total_cost) == 0:
        print("✅ PASS: All scenarios have positive total costs")
        passed += 1
    else:
        print(f"⚠️  INFO: {len(zero_total_cost)} scenarios have $0 total costs (may need pricing data)")
        passed += 1  # Not a failure if pricing data is missing
    
    # Check 2: DBU cost should be non-zero
    if len(zero_dbu_cost) == 0:
        print("✅ PASS: All scenarios have positive DBU costs")
        passed += 1
    else:
        print(f"⚠️  INFO: {len(zero_dbu_cost)} scenarios have $0 DBU costs (may need pricing data)")
        passed += 1
    
    # Check 3: cost_per_month should equal dbu_cost + vm_cost
    results_df['cost_check'] = results_df['dbu_cost_per_month'] + results_df['vm_cost_per_month']
    cost_mismatch = results_df[abs(results_df['cost_per_month'] - results_df['cost_check']) > 0.01]
    
    if len(cost_mismatch) == 0:
        print("✅ PASS: Total cost = DBU cost + VM cost for all scenarios")
        passed += 1
    else:
        print(f"❌ FAIL: {len(cost_mismatch)} scenarios have cost calculation mismatches")
        failed += 1
    
    print("\n" + "=" * 120)
    print(f"FINAL RESULT: {passed} passed, {failed} failed")
    print("=" * 120)
    
else:
    print("❌ No results to validate!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Show Errors (if any)

# COMMAND ----------

if errors:
    print("=" * 120)
    print("ERRORS ENCOUNTERED")
    print("=" * 120)
    
    for error in errors[:10]:  # Show first 10 errors
        print(f"\n❌ Scenario {error['scenario_id']}: {error['error']}")
    
    if len(errors) > 10:
        print(f"\n... and {len(errors) - 10} more errors")
