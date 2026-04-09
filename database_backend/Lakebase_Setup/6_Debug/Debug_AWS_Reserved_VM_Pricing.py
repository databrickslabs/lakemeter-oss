# Databricks notebook source
# MAGIC %md
# MAGIC # 🐛 DEBUG: AWS Reserved VM Pricing for DBSQL
# MAGIC
# MAGIC **Problem:** AWS reserved_1y and reserved_3y are showing $0 VM costs for DBSQL Classic
# MAGIC
# MAGIC **Investigation:**
# MAGIC 1. What instance types are used for DBSQL warehouses?
# MAGIC 2. What VM pricing data exists for those instance types?
# MAGIC 3. What's missing for AWS reserved 1y/3y?

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
# MAGIC ## 1️⃣ What instance types are used for DBSQL warehouses?

# COMMAND ----------

query_warehouse_config = """
SELECT 
    cloud,
    warehouse_type,
    warehouse_size,
    driver_instance_type,
    worker_instance_type,
    worker_count
FROM lakemeter.sync_ref_dbsql_warehouse_config
WHERE cloud = 'AWS'
  AND warehouse_type = 'classic'
  AND warehouse_size IN ('2X-Large', '2X-Small')
ORDER BY warehouse_size, cloud;
"""

warehouse_config = pd.read_sql_query(query_warehouse_config, conn)
print("🔍 DBSQL Warehouse Configuration (AWS, classic, 2X-Large/2X-Small):")
print("=" * 100)
display(warehouse_config)

# Get unique instance types
driver_instances = warehouse_config['driver_instance_type'].unique()
worker_instances = warehouse_config['worker_instance_type'].unique()
all_instances = list(set(list(driver_instances) + list(worker_instances)))

print(f"\n📋 Unique instance types used: {all_instances}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2️⃣ What VM pricing data exists for these instance types?

# COMMAND ----------

instance_list = ", ".join([f"'{i}'" for i in all_instances])

query_pricing = f"""
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
  AND instance_type IN ({instance_list})
ORDER BY instance_type, pricing_tier, payment_option;
"""

vm_pricing = pd.read_sql_query(query_pricing, conn)
print(f"🔍 VM Pricing Data (AWS us-east-1, instances: {all_instances}):")
print("=" * 100)
display(vm_pricing)

print(f"\n📊 Total pricing entries: {len(vm_pricing)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3️⃣ What's available for each pricing_tier?

# COMMAND ----------

pricing_summary = vm_pricing.groupby(['instance_type', 'pricing_tier']).agg({
    'payment_option': lambda x: list(x.unique()),
    'cost_per_hour': 'count'
}).reset_index()

pricing_summary.columns = ['instance_type', 'pricing_tier', 'payment_options', 'count']

print("📊 Pricing Tier Summary:")
print("=" * 100)
display(pricing_summary)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4️⃣ Check for missing reserved_1y and reserved_3y entries

# COMMAND ----------

query_check_reserved = f"""
SELECT 
    instance_type,
    pricing_tier,
    COUNT(*) as entry_count,
    STRING_AGG(DISTINCT payment_option, ', ' ORDER BY payment_option) as payment_options
FROM lakemeter.sync_pricing_vm_costs
WHERE cloud = 'AWS'
  AND region = 'us-east-1'
  AND instance_type IN ({instance_list})
  AND pricing_tier IN ('on_demand', 'reserved_1y', 'reserved_3y')
GROUP BY instance_type, pricing_tier
ORDER BY instance_type, pricing_tier;
"""

reserved_check = pd.read_sql_query(query_check_reserved, conn)
print("🔍 Reserved Pricing Availability:")
print("=" * 100)
display(reserved_check)

# Check if reserved_1y and reserved_3y exist
missing_tiers = []
for instance in all_instances:
    for tier in ['reserved_1y', 'reserved_3y']:
        matching = reserved_check[(reserved_check['instance_type'] == instance) & 
                                  (reserved_check['pricing_tier'] == tier)]
        if len(matching) == 0:
            missing_tiers.append(f"{instance} - {tier}")

if missing_tiers:
    print(f"\n❌ MISSING PRICING TIERS ({len(missing_tiers)}):")
    for item in missing_tiers:
        print(f"   • {item}")
else:
    print("\n✅ All instance types have reserved_1y and reserved_3y pricing")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5️⃣ Sample query: What does calculate_dbsql_vm_costs look up?

# COMMAND ----------

# Show what the function is trying to look up
print("🔍 Function Lookup Pattern:")
print("=" * 100)
print("""
SELECT driver_instance_type, worker_instance_type, worker_count
FROM lakemeter.sync_ref_dbsql_warehouse_config
WHERE cloud = 'AWS'
  AND warehouse_type = 'classic'
  AND warehouse_size = '2X-Large'

Then for EACH instance (driver + workers):
SELECT cost_per_hour
FROM lakemeter.sync_pricing_vm_costs
WHERE cloud = 'AWS'
  AND region = 'us-east-1'
  AND instance_type = <driver_instance_type or worker_instance_type>
  AND pricing_tier = <dbsql_vm_pricing_tier>  -- e.g., 'reserved_1y'
  AND payment_option = <dbsql_vm_payment_option>  -- e.g., 'all_upfront'
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6️⃣ Test actual lookup for reserved_1y and reserved_3y (with proper payment_option)

# COMMAND ----------

# Build test query properly:
# - on_demand and spot only use payment_option = 'NA'
# - reserved_1y and reserved_3y use all_upfront, no_upfront, partial_upfront

test_combinations = []
for instance in all_instances:
    # on_demand only uses NA
    test_combinations.append((instance, 'on_demand', 'NA'))
    # reserved uses all three payment options
    for tier in ['reserved_1y', 'reserved_3y']:
        for payment in ['all_upfront', 'no_upfront', 'partial_upfront']:
            test_combinations.append((instance, tier, payment))

print(f"🔍 Testing {len(test_combinations)} pricing lookups...")
print("=" * 100)

# Use a single query with COALESCE to handle missing data
instance_list_str = ", ".join([f"'{i}'" for i in all_instances])

query_all_pricing = f"""
SELECT 
    instance_type,
    pricing_tier,
    payment_option,
    cost_per_hour
FROM lakemeter.sync_pricing_vm_costs
WHERE cloud = 'AWS'
  AND region = 'us-east-1'
  AND instance_type IN ({instance_list_str})
  AND (
    (pricing_tier = 'on_demand' AND payment_option = 'NA')
    OR
    (pricing_tier IN ('reserved_1y', 'reserved_3y') AND payment_option IN ('all_upfront', 'no_upfront', 'partial_upfront'))
  )
ORDER BY instance_type, pricing_tier, payment_option;
"""

all_pricing = pd.read_sql_query(query_all_pricing, conn)
print(f"📊 Found {len(all_pricing)} pricing entries:")
print("=" * 100)
display(all_pricing)

# Check what's missing
found_combinations = set(zip(all_pricing['instance_type'], all_pricing['pricing_tier'], all_pricing['payment_option']))
expected_combinations = set(test_combinations)
missing_combinations = expected_combinations - found_combinations

if missing_combinations:
    print(f"\n❌ MISSING {len(missing_combinations)} pricing combinations:")
    print("=" * 100)
    for instance, tier, payment in sorted(missing_combinations):
        print(f"   • {instance:15s} | {tier:12s} | {payment:15s}")
    print("\n⚠️  These will result in $0 VM costs in the test!")
else:
    print(f"\n✅ All {len(expected_combinations)} expected pricing combinations found!")

conn.close()

