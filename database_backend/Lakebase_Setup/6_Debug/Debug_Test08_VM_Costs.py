# Databricks notebook source
# MAGIC %md
# MAGIC # 🔍 Debug Test_Func_08 VM Costs
# MAGIC
# MAGIC Test why DBSQL Pro is showing $0 VM costs even though parameters are passed correctly.

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import pandas as pd

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Specific Scenario

# COMMAND ----------

print("=" * 100)
print("TESTING: AWS PREMIUM 2X-Large, reserved_3y, partial_upfront")
print("=" * 100)

# Test calling calculate_dbsql_vm_costs directly
test_query = """
SELECT * FROM lakemeter.calculate_dbsql_vm_costs(
    'AWS'::VARCHAR,
    'us-east-1'::VARCHAR,
    'PRO'::VARCHAR,
    '2X-Large'::VARCHAR,
    2::INT,
    'reserved_3y'::VARCHAR,
    240.0::DECIMAL,
    'partial_upfront'::VARCHAR
);
"""

print("\n🎯 Calling calculate_dbsql_vm_costs() directly...")
print(f"   Cloud: AWS")
print(f"   Region: us-east-1")
print(f"   Warehouse Type: PRO")
print(f"   Warehouse Size: 2X-Large")
print(f"   Num Clusters: 2")
print(f"   VM Pricing Tier: reserved_3y")
print(f"   Hours/Month: 240")
print(f"   Payment Option: partial_upfront")

try:
    result = execute_query(test_query)
    print(f"\n✅ Function returned {len(result)} row(s)")
    display(result)
except Exception as e:
    print(f"\n❌ Error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check Warehouse Configuration

# COMMAND ----------

print("=" * 100)
print("WAREHOUSE CONFIGURATION LOOKUP")
print("=" * 100)

config_query = """
SELECT 
    cloud,
    warehouse_type,
    warehouse_size,
    driver_instance_type,
    worker_instance_type,
    worker_count
FROM lakemeter.sync_ref_dbsql_warehouse_config
WHERE cloud = 'AWS'
  AND warehouse_type = 'pro'
  AND warehouse_size = '2X-Large'
LIMIT 5;
"""

try:
    config = execute_query(config_query)
    print(f"\n✅ Found {len(config)} configuration(s)")
    display(config)
    
    if not config.empty:
        driver = config.iloc[0]['driver_instance_type']
        worker = config.iloc[0]['worker_instance_type']
        worker_count = config.iloc[0]['worker_count']
        
        print(f"\n📊 Configuration:")
        print(f"   Driver: {driver}")
        print(f"   Worker: {worker} (x{worker_count})")
        
        # Now check pricing for these instance types
        print("\n" + "=" * 100)
        print("VM PRICING LOOKUP")
        print("=" * 100)
        
        pricing_query = f"""
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
          AND pricing_tier = 'reserved_3y'
          AND payment_option = 'partial_upfront'
        ORDER BY instance_type;
        """
        
        pricing = execute_query(pricing_query)
        print(f"\n✅ Found {len(pricing)} pricing record(s)")
        display(pricing)
        
        if pricing.empty:
            print("\n⚠️  NO PRICING FOUND! Checking what IS available...")
            alt_query = f"""
            SELECT DISTINCT
                pricing_tier,
                payment_option,
                COUNT(*) as record_count
            FROM lakemeter.sync_pricing_vm_costs
            WHERE cloud = 'AWS'
              AND region = 'us-east-1'
              AND instance_type IN ('{driver}', '{worker}')
            GROUP BY pricing_tier, payment_option
            ORDER BY pricing_tier, payment_option;
            """
            alt_pricing = execute_query(alt_query)
            display(alt_pricing)
except Exception as e:
    print(f"\n❌ Error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Call calculate_line_item_costs() for Full Test

# COMMAND ----------

print("=" * 100)
print("FULL calculate_line_item_costs() TEST")
print("=" * 100)

full_test_query = """
SELECT * FROM lakemeter.calculate_line_item_costs(
    'DBSQL'::VARCHAR,
    'AWS'::VARCHAR,
    'us-east-1'::VARCHAR,
    'PREMIUM'::VARCHAR,
    NULL::VARCHAR,
    NULL::VARCHAR,
    0::INT,
    FALSE::BOOLEAN,
    'standard'::VARCHAR,
    NULL::VARCHAR,
    FALSE::BOOLEAN,
    FALSE::BOOLEAN,
    'light'::VARCHAR,
    8::INT,
    60::INT,
    30::INT,
    'standard'::VARCHAR,
    'PRO'::VARCHAR,
    '2X-Large'::VARCHAR,
    2::INT,
    'reserved_3y'::VARCHAR,
    NULL::VARCHAR,
    0::DECIMAL,
    NULL::VARCHAR,
    NULL::VARCHAR,
    NULL::VARCHAR,
    'global'::VARCHAR,
    'standard'::VARCHAR,
    'pay_per_token'::VARCHAR,
    0::BIGINT,
    0::BIGINT,
    0::INT,
    1::INT,
    'NA'::VARCHAR,
    'NA'::VARCHAR,
    'partial_upfront'::VARCHAR
);
"""

try:
    full_result = execute_query(full_test_query)
    print(f"\n✅ Function returned {len(full_result)} row(s)")
    
    if not full_result.empty:
        # Show key cost columns
        display(full_result[[
            'dbu_price', 'dbu_per_hour', 'dbu_per_month',
            'dbu_cost_per_month', 'vm_cost_per_month', 'cost_per_month'
        ]])
        
        dbu_cost = full_result.iloc[0]['dbu_cost_per_month']
        vm_cost = full_result.iloc[0]['vm_cost_per_month']
        total_cost = full_result.iloc[0]['cost_per_month']
        
        print(f"\n💰 Costs:")
        print(f"   DBU Cost: ${dbu_cost:,.2f}")
        print(f"   VM Cost:  ${vm_cost:,.2f}")
        print(f"   Total:    ${total_cost:,.2f}")
        
        if vm_cost == 0:
            print("\n❌ VM COST IS ZERO!")
        else:
            print("\n✅ VM cost is calculated correctly")
except Exception as e:
    print(f"\n❌ Error: {e}")



