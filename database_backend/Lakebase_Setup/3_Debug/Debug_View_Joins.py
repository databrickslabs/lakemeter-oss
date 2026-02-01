# Databricks notebook source
# MAGIC %md
# MAGIC # 🔍 Debug View Joins - Why Azure/GCP Show $0
# MAGIC 
# MAGIC This notebook diagnoses why Azure/GCP costs are still $0 even though pricing data exists.
# MAGIC 
# MAGIC **Key Checks:**
# MAGIC 1. What instance types are actually in line_items for Azure/GCP?
# MAGIC 2. Do those instance types exist in sync_ref_instance_dbu_rates?
# MAGIC 3. Does the multiplier lookup work?
# MAGIC 4. **Most Important:** Was the view actually updated with the cloud join fix?

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup: Install Dependencies

# COMMAND ----------

# MAGIC %pip install psycopg2-binary tabulate --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup: Connect to Lakebase

# COMMAND ----------

import psycopg2
import pandas as pd
from tabulate import tabulate

# Lakebase connection details
LAKEBASE_CONFIG = {
    'host': 'instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com',
    'port': 5432,
    'database': 'lakemeter_pricing',
    'user': 'lakemeter_sync_role',
    'password': dbutils.secrets.get(scope="lakemeter-credentials", key="lakebase-password"),
    'sslmode': 'require'
}

def execute_query(sql, params=None, fetch=True):
    """Execute SQL query and return results as DataFrame"""
    conn = psycopg2.connect(**LAKEBASE_CONFIG)
    try:
        if fetch:
            df = pd.read_sql_query(sql, conn, params=params)
            return df
        else:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            cursor.close()
    finally:
        conn.close()

print("✅ Connected to Lakebase")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. What's Actually in line_items for Azure/GCP?

# COMMAND ----------

line_items_sql = """
SELECT 
    c.line_item_id,
    c.workload_name,
    e.cloud,
    e.region,
    c.driver_node_type,
    c.worker_node_type,
    c.photon_enabled,
    c.serverless_enabled
FROM lakemeter.line_items c
JOIN lakemeter.estimates e ON e.estimate_id = c.estimate_id
WHERE e.cloud IN ('AZURE', 'GCP')
ORDER BY c.line_item_id;
"""

line_items = execute_query(line_items_sql)
print(f"📋 Found {len(line_items)} Azure/GCP line items:\n")
print(tabulate(line_items, headers='keys', tablefmt='grid', showindex=False))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Driver Instance Type Lookup Test

# COMMAND ----------

driver_lookup_sql = """
SELECT 
    c.line_item_id,
    c.workload_name,
    e.cloud,
    c.driver_node_type,
    d.dbu_rate as driver_dbu_rate
FROM lakemeter.line_items c
JOIN lakemeter.estimates e ON e.estimate_id = c.estimate_id
LEFT JOIN lakemeter.sync_ref_instance_dbu_rates d 
    ON d.cloud = e.cloud 
    AND d.instance_type = c.driver_node_type
WHERE e.cloud IN ('AZURE', 'GCP')
ORDER BY c.line_item_id;
"""

driver_results = execute_query(driver_lookup_sql)
print("🔍 Driver Instance Type Lookups:\n")
print(tabulate(driver_results, headers='keys', tablefmt='grid', showindex=False))

# Check for missing lookups
missing_drivers = driver_results[driver_results['driver_dbu_rate'].isna()]
if len(missing_drivers) > 0:
    print("\n❌ MISSING DRIVER LOOKUPS:")
    for _, row in missing_drivers.iterrows():
        print(f"   - {row['cloud']}: {row['driver_node_type']} not found in sync_ref_instance_dbu_rates")
else:
    print("\n✅ All driver lookups successful!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Worker Instance Type Lookup Test

# COMMAND ----------

worker_lookup_sql = """
SELECT 
    c.line_item_id,
    c.workload_name,
    e.cloud,
    c.worker_node_type,
    w.dbu_rate as worker_dbu_rate
FROM lakemeter.line_items c
JOIN lakemeter.estimates e ON e.estimate_id = c.estimate_id
LEFT JOIN lakemeter.sync_ref_instance_dbu_rates w 
    ON w.cloud = e.cloud 
    AND w.instance_type = c.worker_node_type
WHERE e.cloud IN ('AZURE', 'GCP')
ORDER BY c.line_item_id;
"""

worker_results = execute_query(worker_lookup_sql)
print("🔍 Worker Instance Type Lookups:\n")
print(tabulate(worker_results, headers='keys', tablefmt='grid', showindex=False))

# Check for missing lookups
missing_workers = worker_results[worker_results['worker_dbu_rate'].isna()]
if len(missing_workers) > 0:
    print("\n❌ MISSING WORKER LOOKUPS:")
    for _, row in missing_workers.iterrows():
        print(f"   - {row['cloud']}: {row['worker_node_type']} not found in sync_ref_instance_dbu_rates")
else:
    print("\n✅ All worker lookups successful!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Multiplier Lookup Test

# COMMAND ----------

multiplier_lookup_sql = """
SELECT 
    c.line_item_id,
    c.workload_name,
    e.cloud,
    c.workload_type,
    c.photon_enabled,
    c.serverless_enabled,
    CASE WHEN c.photon_enabled THEN 'photon' ELSE 'standard' END as feature,
    m.multiplier
FROM lakemeter.line_items c
JOIN lakemeter.estimates e ON e.estimate_id = c.estimate_id
LEFT JOIN lakemeter.sync_ref_dbu_multipliers m 
    ON c.serverless_enabled = FALSE
    AND m.cloud = e.cloud
    AND m.feature = CASE WHEN c.photon_enabled THEN 'photon' ELSE 'standard' END
    AND m.sku_type = 'JOBS_COMPUTE'
WHERE e.cloud IN ('AZURE', 'GCP')
ORDER BY c.line_item_id;
"""

multiplier_results = execute_query(multiplier_lookup_sql)
print("🔍 Multiplier Lookups:\n")
print(tabulate(multiplier_results, headers='keys', tablefmt='grid', showindex=False))

# Check for missing lookups
missing_multipliers = multiplier_results[multiplier_results['multiplier'].isna()]
if len(missing_multipliers) > 0:
    print("\n❌ MISSING MULTIPLIER LOOKUPS:")
    for _, row in missing_multipliers.iterrows():
        print(f"   - {row['cloud']}: feature={row['feature']} not found")
else:
    print("\n✅ All multiplier lookups successful!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. 🚨 CRITICAL: Check if View Was Actually Updated

# COMMAND ----------

view_definition_sql = """
SELECT definition
FROM pg_views
WHERE schemaname = 'lakemeter' 
  AND viewname = 'v_line_items_with_costs';
"""

view_def = execute_query(view_definition_sql)
view_text = view_def['definition'].iloc[0]

# Check for the critical fix
print("🔍 Checking if view has the cloud join fix...\n")

if 'AND m.cloud = h.cloud' in view_text:
    print("✅ VIEW HAS BEEN UPDATED!")
    print("   Found: 'AND m.cloud = h.cloud' in multiplier join")
elif 'm.cloud = h.cloud' in view_text:
    print("✅ VIEW HAS BEEN UPDATED!")
    print("   Found: 'm.cloud = h.cloud' in multiplier join")
else:
    print("❌ VIEW WAS NOT UPDATED!")
    print("   The multiplier join is missing 'AND m.cloud = h.cloud'")
    print("\n🔧 ACTION REQUIRED:")
    print("   You must run HOTFIX_Recreate_View.sql in Lakebase SQL Editor")
    print("   Location: /Workspace/Users/steven.tan@databricks.com/lakemeter/Lakebase_Setup/HOTFIX_Recreate_View.sql")

# Show a snippet of the multiplier join section
print("\n📝 Current multiplier join logic:")
start_idx = view_text.find('LEFT JOIN lakemeter.sync_ref_dbu_multipliers')
if start_idx != -1:
    snippet = view_text[start_idx:start_idx+500]
    print(snippet[:500])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Available Instance Types for Azure

# COMMAND ----------

azure_instances_sql = """
SELECT 
    cloud,
    instance_type,
    dbu_rate
FROM lakemeter.sync_ref_instance_dbu_rates
WHERE cloud = 'AZURE'
ORDER BY instance_type
LIMIT 30;
"""

azure_instances = execute_query(azure_instances_sql)
print(f"📋 Available Azure Instance Types ({len(azure_instances)} shown):\n")
print(tabulate(azure_instances, headers='keys', tablefmt='grid', showindex=False))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Available Instance Types for GCP

# COMMAND ----------

gcp_instances_sql = """
SELECT 
    cloud,
    instance_type,
    dbu_rate
FROM lakemeter.sync_ref_instance_dbu_rates
WHERE cloud = 'GCP'
ORDER BY instance_type
LIMIT 30;
"""

gcp_instances = execute_query(gcp_instances_sql)
print(f"📋 Available GCP Instance Types ({len(gcp_instances)} shown):\n")
print(tabulate(gcp_instances, headers='keys', tablefmt='grid', showindex=False))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Query the View Directly - What Does It Return?

# COMMAND ----------

view_results_sql = """
SELECT 
    line_item_id,
    workload_name,
    cloud,
    region,
    driver_node_type,
    worker_node_type,
    photon_enabled,
    driver_dbu_rate,
    worker_dbu_rate,
    photon_multiplier,
    dbu_per_hour,
    cost_per_month
FROM lakemeter.v_line_items_with_costs
WHERE cloud IN ('AZURE', 'GCP')
ORDER BY line_item_id;
"""

view_results = execute_query(view_results_sql)
print("🔍 What the View Actually Returns for Azure/GCP:\n")
print(tabulate(view_results, headers='keys', tablefmt='grid', showindex=False))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📊 Summary & Root Cause
# MAGIC 
# MAGIC Run all sections above to identify:
# MAGIC 
# MAGIC 1. **If lookups find data** → Problem is in the view definition
# MAGIC 2. **If lookups fail** → Problem is instance types in line_items don't match pricing data
# MAGIC 3. **If view definition missing cloud join** → View wasn't updated, must run hotfix
# MAGIC 4. **If view definition has cloud join** → Different issue, need deeper investigation

