# Databricks notebook source
# MAGIC %md
# MAGIC # 🔍 COMPREHENSIVE DEBUG: Why is DBSQL Pro VM Cost $0?

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

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

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1️⃣ Check if Function Was Updated

# COMMAND ----------

print("=" * 100)
print("STEP 1: CHECK IF calculate_dbsql_vm_costs WAS UPDATED")
print("=" * 100)

check_function_sql = """
SELECT 
    pg_get_functiondef(p.oid) as function_definition
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'lakemeter' 
  AND p.proname = 'calculate_dbsql_vm_costs';
"""

try:
    result = execute_query(check_function_sql)
    if not result.empty:
        func_def = result.iloc[0]['function_definition']
        
        # Check for case-insensitive logic
        if 'LOWER(p_dbsql_warehouse_type)' in func_def or 'v_warehouse_type := LOWER' in func_def:
            print("✅ Function HAS been updated with case-insensitive logic")
            print("   Found: v_warehouse_type := LOWER(p_dbsql_warehouse_type)")
        else:
            print("❌ Function has NOT been updated yet!")
            print("   Missing: LOWER() conversion logic")
            print("\n🎯 ACTION: Run 4_Functions/08_VM_Cost_Calculators notebook!")
            dbutils.notebook.exit("Function not updated - stopping debug")
            
        # Show first 500 chars of function
        print("\n📄 Function definition (first 500 chars):")
        print(func_def[:500])
    else:
        print("❌ Function does NOT exist!")
        dbutils.notebook.exit("Function missing - stopping debug")
except Exception as e:
    print(f"❌ Error: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2️⃣ Check Warehouse Configuration Table

# COMMAND ----------

print("\n" + "=" * 100)
print("STEP 2: CHECK sync_ref_dbsql_warehouse_config")
print("=" * 100)

# Check what warehouse_type values exist
check_types_sql = """
SELECT DISTINCT 
    cloud,
    warehouse_type,
    COUNT(*) as config_count
FROM lakemeter.sync_ref_dbsql_warehouse_config
WHERE cloud = 'AWS'
GROUP BY cloud, warehouse_type
ORDER BY warehouse_type;
"""

print("\n🔍 What warehouse_type values exist in the table?")
try:
    types_result = execute_query(check_types_sql)
    display(types_result)
    
    if types_result.empty:
        print("\n❌ NO warehouse configs found for AWS!")
    else:
        print(f"\n✅ Found {len(types_result)} warehouse type(s)")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Check specific config for PRO + 2X-Large
print("\n" + "=" * 100)
print("🔍 Looking for: AWS + PRO + 2X-Large")
print("=" * 100)

config_queries = [
    ("UPPERCASE 'PRO'", "WHERE cloud = 'AWS' AND warehouse_type = 'PRO' AND warehouse_size = '2X-Large'"),
    ("LOWERCASE 'pro'", "WHERE cloud = 'AWS' AND warehouse_type = 'pro' AND warehouse_size = '2X-Large'"),
    ("Any case, any size", "WHERE cloud = 'AWS' AND warehouse_type ILIKE '%pro%'"),
]

for label, where_clause in config_queries:
    config_sql = f"""
    SELECT 
        cloud,
        warehouse_type,
        warehouse_size,
        driver_instance_type,
        worker_instance_type,
        worker_count
    FROM lakemeter.sync_ref_dbsql_warehouse_config
    {where_clause}
    LIMIT 5;
    """
    
    print(f"\n🔎 Test {label}:")
    try:
        config = execute_query(config_sql)
        if config.empty:
            print(f"   ❌ NO configs found")
        else:
            print(f"   ✅ Found {len(config)} config(s)")
            display(config)
    except Exception as e:
        print(f"   ❌ Error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3️⃣ Check VM Pricing Table

# COMMAND ----------

print("\n" + "=" * 100)
print("STEP 3: CHECK sync_pricing_vm_costs")
print("=" * 100)

# First, get the instance types from config (if found)
get_instance_types_sql = """
SELECT 
    driver_instance_type,
    worker_instance_type,
    worker_count
FROM lakemeter.sync_ref_dbsql_warehouse_config
WHERE cloud = 'AWS'
  AND warehouse_type = 'pro'
  AND warehouse_size = '2X-Large'
LIMIT 1;
"""

print("\n🔍 Getting instance types from warehouse config...")
try:
    instance_config = execute_query(get_instance_types_sql)
    if instance_config.empty:
        print("❌ NO instance config found for AWS + pro + 2X-Large")
        print("   This is why VM cost is $0!")
    else:
        driver = instance_config.iloc[0]['driver_instance_type']
        worker = instance_config.iloc[0]['worker_instance_type']
        worker_count = instance_config.iloc[0]['worker_count']
        
        print(f"✅ Instance config found:")
        print(f"   Driver: {driver}")
        print(f"   Worker: {worker} (x{worker_count})")
        
        # Now check pricing for these instances
        print("\n" + "=" * 100)
        print("🔍 Checking VM pricing for these instances...")
        print("=" * 100)
        
        pricing_sql = f"""
        SELECT 
            cloud,
            region,
            instance_type,
            pricing_tier,
            payment_option,
            cost_per_hour
        FROM lakemeter.sync_pricing_vm_costs
        WHERE cloud = 'AWS'
          AND region = 'us-east-1'
          AND instance_type IN ('{driver}', '{worker}')
          AND pricing_tier IN ('on_demand', 'reserved_1y', 'reserved_3y')
        ORDER BY instance_type, pricing_tier, payment_option;
        """
        
        pricing = execute_query(pricing_sql)
        if pricing.empty:
            print(f"❌ NO VM pricing found for instances: {driver}, {worker}")
            print("   This is why VM cost is $0!")
        else:
            print(f"✅ Found {len(pricing)} pricing record(s)")
            display(pricing)
            
except Exception as e:
    print(f"❌ Error: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4️⃣ Call calculate_dbsql_vm_costs() Directly

# COMMAND ----------

print("\n" + "=" * 100)
print("STEP 4: CALL calculate_dbsql_vm_costs() DIRECTLY")
print("=" * 100)

test_scenarios = [
    ("UPPERCASE 'PRO'", "'PRO'"),
    ("LOWERCASE 'pro'", "'pro'"),
    ("Mixed case 'Pro'", "'Pro'"),
]

for label, warehouse_type_value in test_scenarios:
    print(f"\n🔎 Test with {label}:")
    print("─" * 100)
    
    test_sql = f"""
    SELECT * FROM lakemeter.calculate_dbsql_vm_costs(
        'AWS'::VARCHAR,
        'us-east-1'::VARCHAR,
        {warehouse_type_value}::VARCHAR,
        '2X-Large'::VARCHAR,
        1::INT,
        'on_demand'::VARCHAR,
        240.0::DECIMAL,
        'NA'::VARCHAR
    );
    """
    
    try:
        result = execute_query(test_sql)
        if result.empty:
            print("   ❌ Function returned NO rows")
        else:
            print(f"   ✅ Function returned {len(result)} row(s)")
            display(result)
            
            vm_cost = result.iloc[0]['total_vm_cost_per_month']
            if vm_cost == 0:
                print(f"   ❌ VM cost is $0!")
            else:
                print(f"   ✅ VM cost: ${vm_cost:,.2f}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5️⃣ Call calculate_line_item_costs() for Full Test

# COMMAND ----------

print("\n" + "=" * 100)
print("STEP 5: CALL calculate_line_item_costs() WITH 'PRO'")
print("=" * 100)

full_test_sql = """
SELECT * FROM lakemeter.calculate_line_item_costs(
    'DBSQL'::VARCHAR,              -- p_workload_type
    'AWS'::VARCHAR,                -- p_cloud
    'us-east-1'::VARCHAR,          -- p_region
    'PREMIUM'::VARCHAR,            -- p_tier
    FALSE::BOOLEAN,                -- p_serverless_enabled
    FALSE::BOOLEAN,                -- p_photon_enabled
    NULL::VARCHAR,                 -- p_dlt_edition
    NULL::VARCHAR,                 -- p_driver_node_type
    NULL::VARCHAR,                 -- p_worker_node_type
    0::INT,                        -- p_num_workers
    'on_demand'::VARCHAR,          -- p_driver_pricing_tier
    'on_demand'::VARCHAR,          -- p_worker_pricing_tier
    8::INT,                        -- p_runs_per_day
    60::INT,                       -- p_avg_runtime_minutes
    30::INT,                       -- p_days_per_month
    'standard'::VARCHAR,           -- p_serverless_mode
    'PRO'::VARCHAR,                -- p_dbsql_warehouse_type
    '2X-Large'::VARCHAR,           -- p_dbsql_warehouse_size
    1::INT,                        -- p_dbsql_num_clusters
    'on_demand'::VARCHAR,          -- p_dbsql_vm_pricing_tier
    NULL::VARCHAR,                 -- p_vector_search_mode
    0::DECIMAL,                    -- p_vector_search_capacity_millions
    NULL::VARCHAR,                 -- p_serverless_size
    NULL::VARCHAR,                 -- p_fmapi_model
    NULL::VARCHAR,                 -- p_fmapi_provider
    'global'::VARCHAR,             -- p_fmapi_endpoint_type
    'standard'::VARCHAR,           -- p_fmapi_context_length
    'pay_per_token'::VARCHAR,      -- p_fmapi_provisioned_type
    0::BIGINT,                     -- p_fmapi_input_tokens_per_month
    0::BIGINT,                     -- p_fmapi_output_tokens_per_month
    0::INT,                        -- p_lakebase_cu
    1::INT,                        -- p_lakebase_ha_nodes
    'NA'::VARCHAR,                 -- p_driver_payment_option
    'NA'::VARCHAR,                 -- p_worker_payment_option
    'NA'::VARCHAR                  -- p_dbsql_vm_payment_option
);
"""

try:
    full_result = execute_query(full_test_sql)
    if full_result.empty:
        print("❌ Function returned NO rows")
    else:
        print(f"✅ Function returned {len(full_result)} row(s)")
        
        # Show key cost columns
        cost_cols = ['dbu_price', 'dbu_per_month', 'dbu_cost_per_month', 
                     'vm_cost_per_month', 'cost_per_month']
        display(full_result[cost_cols])
        
        dbu_cost = full_result.iloc[0]['dbu_cost_per_month']
        vm_cost = full_result.iloc[0]['vm_cost_per_month']
        total_cost = full_result.iloc[0]['cost_per_month']
        
        print(f"\n💰 Costs:")
        print(f"   DBU Cost: ${dbu_cost:,.2f}")
        print(f"   VM Cost:  ${vm_cost:,.2f}")
        print(f"   Total:    ${total_cost:,.2f}")
        
        if vm_cost == 0:
            print("\n❌ VM COST IS STILL ZERO!")
            print("   Check the results above to see where it's failing")
        else:
            print("\n✅ VM cost is calculated correctly")
except Exception as e:
    print(f"❌ Error: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📊 Summary

# COMMAND ----------

print("\n" + "=" * 100)
print("🎯 SUMMARY")
print("=" * 100)

print("\nIf VM cost is STILL $0, the issue is one of these:\n")
print("1. ❌ Function was NOT recreated")
print("   → Run: 4_Functions/08_VM_Cost_Calculators")
print("")
print("2. ❌ Warehouse config is MISSING for AWS + pro + 2X-Large")
print("   → Check: sync_ref_dbsql_warehouse_config table")
print("   → Data sync issue")
print("")
print("3. ❌ VM pricing is MISSING for the instance types")
print("   → Check: sync_pricing_vm_costs table")
print("   → Pricing sync issue")
print("")
print("4. ❌ Main orchestrator function needs to be recreated")
print("   → Run: 4_Functions/09_Main_Orchestrator")
print("")
print("=" * 100)

