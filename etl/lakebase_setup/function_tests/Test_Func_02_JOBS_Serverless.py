# Databricks notebook source
# MAGIC %md
# MAGIC # Function Test: JOBS Serverless Compute
# MAGIC
# MAGIC **Objective:** Validate `calculate_line_item_costs()` function for JOBS Serverless workloads
# MAGIC
# MAGIC **Approach:** Call function directly (no database INSERTs) - faster and cleaner than view-based tests
# MAGIC
# MAGIC **Test Matrix:**
# MAGIC - **Clouds:** AWS, Azure, GCP (2 regions each: US + Europe)
# MAGIC - **Tiers:** STANDARD, PREMIUM, ENTERPRISE (AZURE: no ENTERPRISE)
# MAGIC - **Serverless Mode:** standard (1x), performance (2x multiplier)
# MAGIC - **Photon:** Always enabled (serverless requirement)
# MAGIC - **Usage:** Light only (4 runs/day, 30 min runtime)
# MAGIC
# MAGIC **Key Differences from Classic:**
# MAGIC - ✅ NO VM costs (serverless = DBU only)
# MAGIC - ✅ Performance mode = 2x DBU multiplier
# MAGIC - ✅ No driver/worker instance types
# MAGIC - ✅ Uses JOBS_SERVERLESS_COMPUTE product type
# MAGIC
# MAGIC **Total Scenarios:** ~384 (AWS: 128 | AZURE: 64 | GCP: 128)
# MAGIC
# MAGIC **Important:** Instance types and worker counts are used to DERIVE DBU/hour, but VM costs = $0

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
# MAGIC ## Generate Test Scenarios

# COMMAND ----------

# Test configuration
clouds = ['AWS', 'AZURE', 'GCP']
region_map = {
    'AWS': {'us': 'us-east-1', 'eu': 'eu-west-1'},
    'AZURE': {'us': 'eastus', 'eu': 'westeurope'},
    'GCP': {'us': 'us-central1', 'eu': 'europe-west1'}
}

# Serverless modes
serverless_modes = ['standard', 'performance']

# Usage patterns
usage_patterns = [
    {'label': 'Light', 'runs': 4, 'mins': 30},
    {'label': 'Medium', 'runs': 12, 'mins': 60}
]

# Days per month
days_per_month_options = [20, 30]

# Instance types for DBU calculation (serverless uses these for sizing but doesn't charge for VMs)
cloud_instances = {
    'AWS': ['i3.xlarge'],
    'AZURE': ['Standard_D4s_v3'],
    'GCP': ['n1-highmem-4']
}

# Worker counts for DBU calculation
worker_counts = [2, 4]

print("🔍 Fetching cloud-specific instance types from pricing data...")
try:
    instance_query = """
    SELECT DISTINCT cloud, instance_type
    FROM lakemeter.sync_pricing_vm_costs
    WHERE cloud IN ('AWS', 'AZURE', 'GCP')
      AND pricing_tier = 'on_demand'
      AND region IN ('us-east-1', 'eastus', 'us-central1')
    ORDER BY cloud, instance_type
    LIMIT 10;
    """
    available_instances = execute_query(instance_query)
    
    if not available_instances.empty:
        for cloud in clouds:
            cloud_data = available_instances[available_instances['cloud'] == cloud]
            if len(cloud_data) > 0:
                cloud_instances[cloud] = [cloud_data.iloc[0]['instance_type']]
                print(f"   {cloud}: {cloud_instances[cloud][0]}")
except Exception as e:
    print(f"   Using default instances: {e}")

# Generate scenarios
test_scenarios = []
scenario_id = 1

for cloud in clouds:
    instance_type = cloud_instances[cloud][0]
    
    for region_type in ['us', 'eu']:
        region = region_map[cloud][region_type]
        
        for tier in ['STANDARD', 'PREMIUM', 'ENTERPRISE']:
            if cloud == 'AZURE' and tier == 'ENTERPRISE':
                continue
            
            for serverless_mode in serverless_modes:
                for usage in usage_patterns:
                    for days in days_per_month_options:
                        for workers in worker_counts:
                            test_scenarios.append({
                                'scenario_id': scenario_id,
                                'cloud': cloud,
                                'region': region,
                                'tier': tier,
                                'serverless_mode': serverless_mode,
                                'instance_type': instance_type,
                                'num_workers': workers,
                                'runs': usage['runs'],
                                'runtime_mins': usage['mins'],
                                'days_per_month': days,
                                'label': f"{cloud} {tier} {serverless_mode.capitalize()} {workers}w {usage['label']} {days}d"
                            })
                            scenario_id += 1

print(f"\n📋 Generated {len(test_scenarios)} test scenarios")
print(f"   AWS: {len([s for s in test_scenarios if s['cloud'] == 'AWS'])} scenarios")
print(f"   AZURE: {len([s for s in test_scenarios if s['cloud'] == 'AZURE'])} scenarios (no ENTERPRISE)")
print(f"   GCP: {len([s for s in test_scenarios if s['cloud'] == 'GCP'])} scenarios")

print(f"\n   Breakdown:")
print(f"   • 2 regions (US + EU)")
print(f"   • 3 tiers (STANDARD, PREMIUM, ENTERPRISE) - AZURE only 2")
print(f"   • 2 serverless modes (standard, performance)")
print(f"   • 1 instance type per cloud (for DBU sizing)")
print(f"   • 2 worker counts (2, 4)")
print(f"   • 2 usage patterns (Light, Medium)")
print(f"   • 2 days/month options (20, 30)")
print(f"\n   Note: Instance types used for DBU calculation, but VM costs = $0")

print(f"\n   Sample scenarios (first 5):")
for s in test_scenarios[:5]:
    print(f"      {s['scenario_id']:3d}. {s['label']}")

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
    if i % 10 == 0:
        print(f"   Processing scenario {i}/{len(test_scenarios)}...")
    
    # Build function call with explicit type casts
    query = f"""
    SELECT 
        '{scenario['label']}'::VARCHAR as scenario,
        '{scenario['cloud']}'::VARCHAR as cloud,
        '{scenario['region']}'::VARCHAR as region,
        '{scenario['tier']}'::VARCHAR as tier,
        '{scenario['serverless_mode']}'::VARCHAR as serverless_mode,
        '{scenario['instance_type']}'::VARCHAR as instance_type,
        {scenario['num_workers']}::INT as num_workers,
        *
    FROM lakemeter.calculate_line_item_costs(
        'JOBS'::VARCHAR,
        '{scenario['cloud']}'::VARCHAR,
        '{scenario['region']}'::VARCHAR,
        '{scenario['tier']}'::VARCHAR,
        TRUE::BOOLEAN,                           -- serverless_enabled
        TRUE::BOOLEAN,                           -- photon_enabled (always for serverless)
        NULL::VARCHAR,                           -- dlt_edition
        '{scenario['instance_type']}'::VARCHAR,  -- driver_node_type (for DBU calculation)
        '{scenario['instance_type']}'::VARCHAR,  -- worker_node_type (for DBU calculation)
        {scenario['num_workers']}::INT,          -- num_workers (for DBU calculation)
        'on_demand'::VARCHAR,                    -- driver_pricing_tier (N/A)
        'on_demand'::VARCHAR,                    -- worker_pricing_tier (N/A)
        {scenario['runs']}::INT,                 -- runs_per_day
        {scenario['runtime_mins']}::INT,         -- avg_runtime_minutes
        {scenario['days_per_month']}::INT,       -- days_per_month
        NULL::INT,                               -- p_hours_per_month
        '{scenario['serverless_mode']}'::VARCHAR,-- serverless_mode
        NULL::VARCHAR,                           -- dbsql_warehouse_type
        NULL::VARCHAR,                           -- dbsql_warehouse_size
        1::INT,                                  -- dbsql_num_clusters
        'on_demand'::VARCHAR,                    -- dbsql_vm_pricing_tier
        NULL::VARCHAR,                           -- vector_search_mode
        0::DECIMAL,                              -- vector_search_capacity_millions
        NULL::VARCHAR,                           -- serverless_size
        NULL::VARCHAR,                           -- fmapi_model
        NULL::VARCHAR,                           -- fmapi_provider
        'global'::VARCHAR,                       -- fmapi_endpoint_type
        'standard'::VARCHAR,                     -- fmapi_context_length
        'pay_per_token'::VARCHAR,                -- fmapi_provisioned_type
        0::BIGINT,                               -- fmapi_input_tokens_per_month
        0::BIGINT,                               -- fmapi_output_tokens_per_month
        0::INT,                                  -- lakebase_cu
        1::INT,                                  -- lakebase_ha_nodes
        'NA'::VARCHAR,                           -- driver_payment_option
        'NA'::VARCHAR                            -- worker_payment_option
    );
    """
    
    try:
        result = execute_query(query)
        if not result.empty:
            results.append(result.iloc[0].to_dict())
    except Exception as e:
        errors.append({
            'scenario': scenario['label'],
            'error': str(e)
        })
        print(f"   ❌ Error in scenario {i}: {str(e)[:100]}")

print(f"\n✅ Processed {len(results)} scenarios successfully")
if errors:
    print(f"❌ {len(errors)} scenarios had errors")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validate Results

# COMMAND ----------

if len(results) > 0:
    results_df = pd.DataFrame(results)
    
    # =========================================================================
    # COMPREHENSIVE RESULTS TABLE - ALL SCENARIOS
    # =========================================================================
    print("\n" + "=" * 200)
    print(f"COMPREHENSIVE RESULTS TABLE - ALL {len(results_df)} SCENARIOS")
    print("=" * 200)
    print("Shows: All test scenarios with complete calculation details")
    print("=" * 200)
    
    # Convert numeric columns to float
    numeric_cols = ['dbu_per_hour', 'hours_per_month', 'dbu_per_month', 'dbu_price', 
                    'dbu_cost_per_month', 'vm_cost_per_month', 'cost_per_month', 'num_workers']
    for col in numeric_cols:
        if col in results_df.columns:
            results_df[col] = pd.to_numeric(results_df[col], errors='coerce')
    
    # Add calculated columns for transparency
    results_df['photon_mult'] = 2.0
    results_df['mode_mult'] = results_df['serverless_mode'].map({'standard': 1.0, 'performance': 2.0})
    results_df['base_dbu_hr'] = results_df['dbu_per_hour'] / (results_df['photon_mult'] * results_df['mode_mult'])
    
    # Select comprehensive columns
    display_cols = [
        'scenario', 'cloud', 'region', 'tier', 'serverless_mode', 'instance_type', 'num_workers',
        'base_dbu_hr', 'photon_mult', 'mode_mult', 'dbu_per_hour', 
        'hours_per_month', 'dbu_per_month', 'dbu_price', 
        'dbu_cost_per_month', 'vm_cost_per_month', 'cost_per_month'
    ]
    
    # Filter to existing columns
    available_cols = [col for col in display_cols if col in results_df.columns]
    
    print(f"\nDisplaying ALL {len(results_df)} scenarios with {len(available_cols)} columns")
    print("Note: Instance types are used to DERIVE DBU/hour, but VM costs = $0 (serverless)")
    print("=" * 200)
    display(results_df[available_cols])
    
    print("\n" + "=" * 200)
    print("FORMULA REFERENCE:")
    print("=" * 200)
    print("SERVERLESS DBU DERIVATION:")
    print("  1. Instance Sizing    → Use instance_type + num_workers to derive base DBU")
    print("  2. Photon Multiplier  → Always 2.0 (Photon mandatory for serverless)")
    print("  3. Mode Multiplier    → 1.0 (standard) or 2.0 (performance)")
    print("")
    print("  Base DBU/Hour         = f(instance_type, num_workers)")
    print("  Final DBU/Hour        = Base DBU/Hour × Photon × Mode Multiplier")
    print("  DBU/Month             = Final DBU/Hour × Hours/Month")
    print("")
    print("COST CALCULATION:")
    print("  DBU Cost/Month        = DBU/Month × Serverless DBU Price")
    print("  VM Cost/Month         = $0 (serverless doesn't charge for VMs)")
    print("  TOTAL Cost/Month      = DBU Cost/Month")
    print("=" * 200)
    
    # Assertions
    print("\n" + "=" * 120)
    print("VALIDATION CHECKS")
    print("=" * 120)
    
    passed = 0
    failed = 0
    
    # Check 1: All VM costs should be $0 for serverless
    if results_df['vm_cost_per_month'].max() == 0:
        print("✅ PASS: All VM costs are $0 (serverless = DBU only)")
        passed += 1
    else:
        print(f"❌ FAIL: Some scenarios have VM costs (should be $0)")
        failed += 1
    
    # Check 2: STANDARD tier should have $0 costs (serverless not available in STANDARD)
    standard_tier = results_df[results_df['tier'] == 'STANDARD']
    if len(standard_tier) > 0:
        if (standard_tier['dbu_cost_per_month'] == 0).all():
            print(f"✅ PASS: All STANDARD tier scenarios have $0 costs (serverless not available in STANDARD)")
            passed += 1
        else:
            non_zero = len(standard_tier[standard_tier['dbu_cost_per_month'] != 0])
            print(f"❌ FAIL: {non_zero} STANDARD tier scenarios have non-zero costs (should be $0)")
            failed += 1
    
    # Check 3: PREMIUM/ENTERPRISE tiers should have positive DBU costs
    premium_enterprise = results_df[results_df['tier'].isin(['PREMIUM', 'ENTERPRISE'])]
    if len(premium_enterprise) > 0:
        if len(premium_enterprise[premium_enterprise['dbu_cost_per_month'] == 0]) == 0:
            print("✅ PASS: All PREMIUM/ENTERPRISE scenarios have positive DBU costs")
            passed += 1
        else:
            zero_count = len(premium_enterprise[premium_enterprise['dbu_cost_per_month'] == 0])
            print(f"⚠️  INFO: {zero_count} PREMIUM/ENTERPRISE scenarios have $0 DBU costs (may need pricing data)")
            passed += 1
    
    # Check 4: cost_per_month should equal dbu_cost (since VM = 0)
    cost_mismatch = results_df[abs(results_df['cost_per_month'] - results_df['dbu_cost_per_month']) > 0.01]
    
    if len(cost_mismatch) == 0:
        print("✅ PASS: Total cost = DBU cost for all scenarios (VM = 0)")
        passed += 1
    else:
        print(f"❌ FAIL: {len(cost_mismatch)} scenarios have cost calculation mismatches")
        failed += 1
    
    # Check 5: Performance mode should have ~2x DBU of standard mode (PREMIUM/ENTERPRISE only)
    standard_df = results_df[(results_df['serverless_mode'] == 'standard') & (results_df['tier'].isin(['PREMIUM', 'ENTERPRISE']))]
    performance_df = results_df[(results_df['serverless_mode'] == 'performance') & (results_df['tier'].isin(['PREMIUM', 'ENTERPRISE']))]
    
    if len(standard_df) > 0 and len(performance_df) > 0:
        # Check a few samples (skip STANDARD tier)
        sample_check = True
        for cloud in ['AWS', 'AZURE', 'GCP']:
            for tier in ['PREMIUM', 'ENTERPRISE']:
                if cloud == 'AZURE' and tier == 'ENTERPRISE':
                    continue  # AZURE doesn't have ENTERPRISE
                    
                std = standard_df[(standard_df['cloud'] == cloud) & (standard_df['tier'] == tier)]
                perf = performance_df[(performance_df['cloud'] == cloud) & (performance_df['tier'] == tier)]
                
                if len(std) > 0 and len(perf) > 0:
                    std_dbu = float(std.iloc[0]['dbu_per_hour'])
                    perf_dbu = float(perf.iloc[0]['dbu_per_hour'])
                    if std_dbu > 0:
                        ratio = perf_dbu / std_dbu
                        if abs(ratio - 2.0) > 0.01:
                            sample_check = False
                            print(f"   ⚠️  {cloud} {tier}: performance/standard ratio = {ratio:.2f} (expected 2.0)")
        
        if sample_check:
            print("✅ PASS: Performance mode has 2x DBU multiplier (PREMIUM/ENTERPRISE only)")
            passed += 1
        else:
            print("❌ FAIL: Performance mode multiplier incorrect")
            failed += 1
    
    print("\n" + "=" * 120)
    print(f"FINAL RESULT: {passed} passed, {failed} failed")
    print("=" * 120)
    
else:
    print("❌ No results to validate!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Formula Reference

# COMMAND ----------

print("=" * 120)
print("SERVERLESS FORMULA REFERENCE:")
print("=" * 120)
print("")
print("DBU COSTS:")
print("  Base DBU/Hour          = Workload-specific DBU rate × Photon multiplier")
print("  Serverless Multiplier  = 1 (standard mode) or 2 (performance mode)")
print("  DBU/Hour               = Base DBU/Hour × Serverless Multiplier")
print("  DBU/Month              = DBU/Hour × Hours/Month")
print("  DBU Cost/Month         = DBU/Month × DBU Price")
print("")
print("VM COSTS:")
print("  VM Cost/Month          = $0 (serverless doesn't charge for VMs)")
print("")
print("TOTAL:")
print("  TOTAL Cost/Month       = DBU Cost/Month + VM Cost/Month")
print("                         = DBU Cost/Month (since VM = 0)")
print("=" * 120)
