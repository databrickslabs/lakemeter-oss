# Databricks notebook source
# MAGIC %md
# MAGIC # 🐛 DEBUG: AWS Reserved VM Lookup in Function
# MAGIC
# MAGIC **Problem:** AWS reserved instances still showing $0 VM costs after adding p_dbsql_vm_payment_option
# MAGIC
# MAGIC **Investigation:**
# MAGIC 1. Test the function with explicit parameters
# MAGIC 2. Manually query what the function should find
# MAGIC 3. Compare to see where the mismatch is

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
import pandas as pd

conn = psycopg2.connect(
    host=LAKEBASE_HOST,
    port=LAKEBASE_PORT,
    database=LAKEBASE_DATABASE,
    user=LAKEBASE_USER,
    password=LAKEBASE_PASSWORD,
    sslmode='require'
)

print(f"✅ Connected to Lakebase")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1️⃣ Test: Call function with reserved_1y + all_upfront

# COMMAND ----------

test_query = """
SELECT 
    'Test: reserved_1y all_upfront' as test_label,
    *
FROM lakemeter.calculate_line_item_costs(
    'DBSQL'::VARCHAR,
    'AWS'::VARCHAR,
    'us-east-1'::VARCHAR,
    'STANDARD'::VARCHAR,
    FALSE::BOOLEAN,
    FALSE::BOOLEAN,
    NULL::VARCHAR,
    NULL::VARCHAR,
    NULL::VARCHAR,
    0::INT,
    'NA'::VARCHAR,
    'NA'::VARCHAR,
    8::INT,
    60::INT,
    30::INT,
    'standard'::VARCHAR,
    'classic'::VARCHAR,
    '2X-Large'::VARCHAR,
    1::INT,
    'reserved_1y'::VARCHAR,         -- dbsql_vm_pricing_tier
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
    'all_upfront'::VARCHAR          -- dbsql_vm_payment_option
);
"""

print("🧪 Testing function call with reserved_1y + all_upfront...")
print("=" * 100)

result = pd.read_sql_query(test_query, conn)
display(result)

print(f"\n📊 Results:")
print(f"   VM cost per month: ${float(result['vm_cost_per_month'].iloc[0]):,.2f}")
print(f"   Total cost per month: ${float(result['cost_per_month'].iloc[0]):,.2f}")

if float(result['vm_cost_per_month'].iloc[0]) == 0:
    print("\n❌ VM cost is $0 - function is NOT finding the pricing!")
else:
    print(f"\n✅ VM cost is positive - function is working!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2️⃣ Manual: What SHOULD the function find?

# COMMAND ----------

# First, get the warehouse config
config_query = """
SELECT 
    driver_instance_type,
    worker_instance_type,
    worker_count
FROM lakemeter.sync_ref_dbsql_warehouse_config
WHERE cloud = 'AWS'
  AND warehouse_type = 'classic'
  AND warehouse_size = '2X-Large'
LIMIT 1;
"""

config = pd.read_sql_query(config_query, conn)
print("📋 DBSQL Warehouse Config (AWS, classic, 2X-Large):")
display(config)

driver_instance = config['driver_instance_type'].iloc[0]
worker_instance = config['worker_instance_type'].iloc[0]
worker_count = int(config['worker_count'].iloc[0])

print(f"\n   Driver: {driver_instance}")
print(f"   Worker: {worker_instance} × {worker_count}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3️⃣ Manual: Lookup driver VM cost

# COMMAND ----------

driver_query = f"""
SELECT 
    instance_type,
    pricing_tier,
    payment_option,
    cost_per_hour
FROM lakemeter.sync_pricing_vm_costs
WHERE cloud = 'AWS'
  AND region = 'us-east-1'
  AND instance_type = '{driver_instance}'
  AND pricing_tier = 'reserved_1y'
  AND payment_option = 'all_upfront'
LIMIT 1;
"""

driver_pricing = pd.read_sql_query(driver_query, conn)
print(f"🔍 Driver VM Pricing ({driver_instance}, reserved_1y, all_upfront):")
display(driver_pricing)

if len(driver_pricing) == 0:
    print("❌ NO PRICING FOUND for driver!")
else:
    driver_cost = float(driver_pricing['cost_per_hour'].iloc[0])
    print(f"✅ Driver cost: ${driver_cost:.4f}/hour")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4️⃣ Manual: Lookup worker VM cost

# COMMAND ----------

worker_query = f"""
SELECT 
    instance_type,
    pricing_tier,
    payment_option,
    cost_per_hour
FROM lakemeter.sync_pricing_vm_costs
WHERE cloud = 'AWS'
  AND region = 'us-east-1'
  AND instance_type = '{worker_instance}'
  AND pricing_tier = 'reserved_1y'
  AND payment_option = 'all_upfront'
LIMIT 1;
"""

worker_pricing = pd.read_sql_query(worker_query, conn)
print(f"🔍 Worker VM Pricing ({worker_instance}, reserved_1y, all_upfront):")
display(worker_pricing)

if len(worker_pricing) == 0:
    print("❌ NO PRICING FOUND for worker!")
else:
    worker_cost = float(worker_pricing['cost_per_hour'].iloc[0])
    print(f"✅ Worker cost: ${worker_cost:.4f}/hour × {worker_count} = ${worker_cost * worker_count:.4f}/hour")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5️⃣ Calculate: What SHOULD the total VM cost be?

# COMMAND ----------

if len(driver_pricing) > 0 and len(worker_pricing) > 0:
    driver_cost_hr = float(driver_pricing['cost_per_hour'].iloc[0])
    worker_cost_hr = float(worker_pricing['cost_per_hour'].iloc[0])
    
    total_vm_cost_hr = driver_cost_hr + (worker_cost_hr * worker_count)
    hours_per_month = 8 * 30  # 8 hrs/day × 30 days
    total_vm_cost_month = total_vm_cost_hr * hours_per_month
    
    print("💰 EXPECTED VM COSTS:")
    print("=" * 100)
    print(f"   Driver: ${driver_cost_hr:.4f}/hr")
    print(f"   Workers: ${worker_cost_hr:.4f}/hr × {worker_count} = ${worker_cost_hr * worker_count:.4f}/hr")
    print(f"   Total: ${total_vm_cost_hr:.4f}/hr")
    print(f"   Monthly (@ {hours_per_month} hrs): ${total_vm_cost_month:,.2f}")
    print("=" * 100)
    
    # Compare to function result
    function_vm_cost = float(result['vm_cost_per_month'].iloc[0])
    print(f"\n📊 COMPARISON:")
    print(f"   Expected: ${total_vm_cost_month:,.2f}")
    print(f"   Function: ${function_vm_cost:,.2f}")
    
    if abs(function_vm_cost - total_vm_cost_month) < 0.01:
        print("\n✅ MATCH! Function is calculating correctly!")
    else:
        print(f"\n❌ MISMATCH! Difference: ${abs(function_vm_cost - total_vm_cost_month):,.2f}")
        if function_vm_cost == 0:
            print("   → Function returned $0, which means it's NOT finding the pricing data!")
else:
    print("❌ Cannot calculate expected cost - pricing data missing!")

conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📋 Conclusion
# MAGIC
# MAGIC If the function returns $0 but manual lookup finds pricing:
# MAGIC - The function is NOT using the p_dbsql_vm_payment_option parameter correctly
# MAGIC - OR it's defaulting to 'NA' instead of 'all_upfront'
# MAGIC - OR the parameter isn't being passed through to calculate_dbsql_vm_costs()



