# Databricks notebook source
# MAGIC %md
# MAGIC # Debug: VM Pricing Lookup Issues
# MAGIC 
# MAGIC **Purpose:** Diagnose why Azure/GCP VM costs are returning $0 in cost calculations.
# MAGIC 
# MAGIC **What This Checks:**
# MAGIC 1. Which clouds have VM pricing data
# MAGIC 2. How many regions/instance types per cloud
# MAGIC 3. Specific regions for Azure and GCP
# MAGIC 4. Instance types available for test regions
# MAGIC 5. Case sensitivity issues
# MAGIC 
# MAGIC **Common Issues:**
# MAGIC - Missing data: Azure/GCP VM costs not synced
# MAGIC - Region mismatch: `eastus` vs `East US`
# MAGIC - Instance type mismatch: `Standard_D8s_v3` vs different casing
# MAGIC - Cloud name mismatch: `AZURE` vs `azure`

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
from tabulate import tabulate

# Lakebase connection parameters
LAKEBASE_HOST = "instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com"
LAKEBASE_PORT = 5432
LAKEBASE_DB = "lakemeter_pricing"
LAKEBASE_USER = "lakemeter_sync_role"
LAKEBASE_PASSWORD = dbutils.secrets.get(scope="lakemeter-credentials", key="lakebase-password")

def get_connection():
    """Create and return a PostgreSQL connection"""
    return psycopg2.connect(
        host=LAKEBASE_HOST,
        port=LAKEBASE_PORT,
        database=LAKEBASE_DB,
        user=LAKEBASE_USER,
        password=LAKEBASE_PASSWORD
    )

def execute_query(query, params=None):
    """Execute a query and return results as DataFrame"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            columns = [desc[0] for desc in cur.description] if cur.description else []
            results = cur.fetchall()
            conn.commit()
            return pd.DataFrame(results, columns=columns) if results else pd.DataFrame()
    finally:
        conn.close()

print("✅ Connection setup complete!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Overview: VM Pricing Data Availability by Cloud

# COMMAND ----------

query_1 = """
SELECT 
    cloud,
    COUNT(*) as row_count,
    COUNT(DISTINCT region) as region_count,
    COUNT(DISTINCT instance_type) as instance_type_count,
    COUNT(DISTINCT pricing_tier) as pricing_tier_count
FROM lakemeter.sync_pricing_vm_costs
GROUP BY cloud
ORDER BY cloud;
"""

result_1 = execute_query(query_1)

print("=" * 100)
print("VM PRICING DATA AVAILABILITY BY CLOUD")
print("=" * 100)

if len(result_1) > 0:
    print(tabulate(result_1, headers='keys', tablefmt='grid', showindex=False))
    
    # Check for missing clouds
    available_clouds = set(result_1['cloud'].tolist())
    required_clouds = {'AWS', 'AZURE', 'GCP'}
    missing_clouds = required_clouds - available_clouds
    
    print("\n")
    if missing_clouds:
        print(f"❌ MISSING CLOUDS: {', '.join(missing_clouds)}")
        print(f"   Action: Run Pricing_Sync notebooks for these clouds")
    else:
        print("✅ All required clouds (AWS, AZURE, GCP) have data")
else:
    print("❌ NO DATA FOUND in sync_pricing_vm_costs!")
    print("   Action: Run all Pricing_Sync notebooks (03_Fetch_AWS_VM.ipynb, 04_Fetch_Azure_VM.ipynb, 05_Fetch_GCP_VM.ipynb)")

print("=" * 100)

display(result_1)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Azure Regions Available

# COMMAND ----------

query_2 = """
SELECT DISTINCT 
    region,
    COUNT(DISTINCT instance_type) as instance_type_count,
    COUNT(DISTINCT pricing_tier) as pricing_tier_count
FROM lakemeter.sync_pricing_vm_costs 
WHERE cloud = 'AZURE'
GROUP BY region
ORDER BY region;
"""

result_2 = execute_query(query_2)

print("=" * 100)
print("AZURE REGIONS IN sync_pricing_vm_costs")
print("=" * 100)

if len(result_2) > 0:
    print(tabulate(result_2, headers='keys', tablefmt='grid', showindex=False))
    print(f"\n✅ Found {len(result_2)} Azure regions")
    
    # Check for test regions
    test_regions = ['eastus', 'westeurope']
    available_regions = [r.lower() for r in result_2['region'].tolist()]
    
    for test_region in test_regions:
        if test_region in available_regions:
            print(f"   ✅ Test region '{test_region}' exists")
        else:
            print(f"   ❌ Test region '{test_region}' NOT FOUND")
            print(f"      Available regions: {', '.join(result_2['region'].tolist()[:5])}...")
else:
    print("❌ NO AZURE REGIONS FOUND")
    print("   Action: Run 04_Fetch_Azure_VM.ipynb")

print("=" * 100)

display(result_2)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. GCP Regions Available

# COMMAND ----------

query_3 = """
SELECT DISTINCT 
    region,
    COUNT(DISTINCT instance_type) as instance_type_count,
    COUNT(DISTINCT pricing_tier) as pricing_tier_count
FROM lakemeter.sync_pricing_vm_costs 
WHERE cloud = 'GCP'
GROUP BY region
ORDER BY region;
"""

result_3 = execute_query(query_3)

print("=" * 100)
print("GCP REGIONS IN sync_pricing_vm_costs")
print("=" * 100)

if len(result_3) > 0:
    print(tabulate(result_3, headers='keys', tablefmt='grid', showindex=False))
    print(f"\n✅ Found {len(result_3)} GCP regions")
    
    # Check for test regions
    test_regions = ['us-central1', 'europe-west1']
    available_regions = [r.lower() for r in result_3['region'].tolist()]
    
    for test_region in test_regions:
        if test_region in available_regions:
            print(f"   ✅ Test region '{test_region}' exists")
        else:
            print(f"   ❌ Test region '{test_region}' NOT FOUND")
            print(f"      Available regions: {', '.join(result_3['region'].tolist()[:5])}...")
else:
    print("❌ NO GCP REGIONS FOUND")
    print("   Action: Run 05_Fetch_GCP_VM.ipynb")

print("=" * 100)

display(result_3)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Azure Instance Types for eastus (Test Region)

# COMMAND ----------

query_4 = """
SELECT DISTINCT 
    instance_type, 
    pricing_tier, 
    cost_per_hour,
    payment_option
FROM lakemeter.sync_pricing_vm_costs 
WHERE cloud = 'AZURE' 
  AND region = 'eastus'
ORDER BY instance_type, pricing_tier
LIMIT 50;
"""

result_4 = execute_query(query_4)

print("=" * 100)
print("AZURE INSTANCE TYPES FOR REGION: eastus")
print("=" * 100)

if len(result_4) > 0:
    print(tabulate(result_4.head(20), headers='keys', tablefmt='grid', showindex=False))
    print(f"\n✅ Found {len(result_4)} instance types (showing first 20)")
    
    # Check for test instance types (UPDATED to v4 instances)
    test_instances = ['Standard_D8d_v4', 'Standard_D16d_v4', 'Standard_D32d_v4']
    available_instances = [i.lower() for i in result_4['instance_type'].tolist()]
    
    print("\n🔍 Checking test instance types:")
    for test_instance in test_instances:
        if test_instance.lower() in available_instances:
            print(f"   ✅ '{test_instance}' exists")
        else:
            print(f"   ❌ '{test_instance}' NOT FOUND")
            # Try case-insensitive partial match
            matches = [i for i in result_4['instance_type'].tolist() if 'd8d' in i.lower() or 'd16d' in i.lower() or 'd32d' in i.lower()]
            if matches:
                print(f"      Similar instances: {', '.join(matches[:3])}...")
else:
    print("❌ NO INSTANCE TYPES FOUND for Azure eastus")
    print("   Possible issues:")
    print("   - Region name mismatch (table might use 'East US' instead of 'eastus')")
    print("   - No data synced for this region")

print("=" * 100)

display(result_4)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. GCP Instance Types for us-central1 (Test Region)

# COMMAND ----------

query_5 = """
SELECT DISTINCT 
    instance_type, 
    pricing_tier, 
    cost_per_hour,
    payment_option
FROM lakemeter.sync_pricing_vm_costs 
WHERE cloud = 'GCP' 
  AND region = 'us-central1'
ORDER BY instance_type, pricing_tier
LIMIT 50;
"""

result_5 = execute_query(query_5)

print("=" * 100)
print("GCP INSTANCE TYPES FOR REGION: us-central1")
print("=" * 100)

if len(result_5) > 0:
    print(tabulate(result_5.head(20), headers='keys', tablefmt='grid', showindex=False))
    print(f"\n✅ Found {len(result_5)} instance types (showing first 20)")
    
    # Check for test instance types
    test_instances = ['n1-standard-8', 'n1-standard-16', 'n1-standard-32']
    available_instances = [i.lower() for i in result_5['instance_type'].tolist()]
    
    print("\n🔍 Checking test instance types:")
    for test_instance in test_instances:
        if test_instance.lower() in available_instances:
            print(f"   ✅ '{test_instance}' exists")
        else:
            print(f"   ❌ '{test_instance}' NOT FOUND")
            # Try case-insensitive partial match
            matches = [i for i in result_5['instance_type'].tolist() if 'n1' in i.lower()]
            if matches:
                print(f"      Similar instances: {', '.join(matches[:3])}...")
else:
    print("❌ NO INSTANCE TYPES FOUND for GCP us-central1")
    print("   Possible issues:")
    print("   - Region name mismatch (table might use different format)")
    print("   - No data synced for this region")

print("=" * 100)

display(result_5)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Case-Insensitive Search: Azure Instance Types

# COMMAND ----------

query_6 = """
SELECT 
    cloud, 
    region, 
    instance_type, 
    pricing_tier, 
    cost_per_hour,
    payment_option
FROM lakemeter.sync_pricing_vm_costs 
WHERE UPPER(cloud) = 'AZURE'
  AND (LOWER(instance_type) LIKE '%d8d%' 
       OR LOWER(instance_type) LIKE '%d16d%'
       OR LOWER(instance_type) LIKE '%d32d%'
       OR LOWER(instance_type) LIKE '%d8as%'
       OR LOWER(instance_type) LIKE '%d16as%')
LIMIT 30;
"""

result_6 = execute_query(query_6)

print("=" * 100)
print("AZURE INSTANCE TYPES (Case-Insensitive Search: D8d, D16d, D32d, D-as series)")
print("=" * 100)

if len(result_6) > 0:
    print(tabulate(result_6, headers='keys', tablefmt='grid', showindex=False))
    print(f"\n✅ Found {len(result_6)} matching instances")
    
    # Show unique regions
    unique_regions = result_6['region'].unique()
    print(f"\n📍 Available in regions: {', '.join(unique_regions[:5])}{'...' if len(unique_regions) > 5 else ''}")
else:
    print("❌ NO AZURE D-SERIES INSTANCES FOUND")
    print("   Action: Check if Azure VM pricing sync is working")

print("=" * 100)

display(result_6)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Case-Insensitive Search: GCP Instance Types

# COMMAND ----------

query_7 = """
SELECT 
    cloud, 
    region, 
    instance_type, 
    pricing_tier, 
    cost_per_hour,
    payment_option
FROM lakemeter.sync_pricing_vm_costs 
WHERE UPPER(cloud) = 'GCP'
  AND (LOWER(instance_type) LIKE '%n1-standard%' 
       OR LOWER(instance_type) LIKE '%n2-standard%')
LIMIT 30;
"""

result_7 = execute_query(query_7)

print("=" * 100)
print("GCP INSTANCE TYPES (Case-Insensitive Search: n1-standard, n2-standard)")
print("=" * 100)

if len(result_7) > 0:
    print(tabulate(result_7, headers='keys', tablefmt='grid', showindex=False))
    print(f"\n✅ Found {len(result_7)} matching instances")
    
    # Show unique regions
    unique_regions = result_7['region'].unique()
    print(f"\n📍 Available in regions: {', '.join(unique_regions[:5])}{'...' if len(unique_regions) > 5 else ''}")
else:
    print("❌ NO GCP N-SERIES INSTANCES FOUND")
    print("   Action: Check if GCP VM pricing sync is working")

print("=" * 100)

display(result_7)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Test Query: Simulate View Lookup for Azure

# COMMAND ----------

# Simulate the exact query the view uses (UPDATED to v4 instance)
test_cloud = 'AZURE'
test_region = 'eastus'
test_instance = 'Standard_D8d_v4'
test_pricing_tier = 'on_demand'

query_8 = """
SELECT 
    cloud,
    region,
    instance_type,
    pricing_tier,
    payment_option,
    cost_per_hour
FROM lakemeter.sync_pricing_vm_costs 
WHERE cloud = %s
  AND region = %s
  AND instance_type = %s
  AND pricing_tier = %s
LIMIT 5;
"""

result_8 = execute_query(query_8, (test_cloud, test_region, test_instance, test_pricing_tier))

print("=" * 100)
print("SIMULATED VIEW LOOKUP FOR AZURE")
print("=" * 100)
print(f"Query Parameters:")
print(f"  cloud = '{test_cloud}'")
print(f"  region = '{test_region}'")
print(f"  instance_type = '{test_instance}'")
print(f"  pricing_tier = '{test_pricing_tier}'")
print("=" * 100)

if len(result_8) > 0:
    print("\n✅ MATCH FOUND! This lookup should work.")
    print(tabulate(result_8, headers='keys', tablefmt='grid', showindex=False))
else:
    print("\n❌ NO MATCH! This is why VM cost = $0")
    print("\n🔍 Trying case-insensitive search...")
    
    # Try case-insensitive
    query_8b = """
    SELECT 
        cloud,
        region,
        instance_type,
        pricing_tier,
        payment_option,
        cost_per_hour
    FROM lakemeter.sync_pricing_vm_costs 
    WHERE UPPER(cloud) = UPPER(%s)
      AND LOWER(region) = LOWER(%s)
      AND LOWER(instance_type) = LOWER(%s)
      AND LOWER(pricing_tier) = LOWER(%s)
    LIMIT 5;
    """
    
    result_8b = execute_query(query_8b, (test_cloud, test_region, test_instance, test_pricing_tier))
    
    if len(result_8b) > 0:
        print("   ✅ Found with case-insensitive search!")
        print(tabulate(result_8b, headers='keys', tablefmt='grid', showindex=False))
        print("\n   ⚠️  ISSUE: Case mismatch between test data and pricing table")
        print("   ACTION: Fix test data to match exact casing in pricing table")
    else:
        print("   ❌ Still no match. Data doesn't exist or names are completely different.")

print("=" * 100)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Test Query: Simulate View Lookup for GCP

# COMMAND ----------

# Simulate the exact query the view uses
test_cloud = 'GCP'
test_region = 'us-central1'
test_instance = 'n1-standard-8'
test_pricing_tier = 'on_demand'

query_9 = """
SELECT 
    cloud,
    region,
    instance_type,
    pricing_tier,
    payment_option,
    cost_per_hour
FROM lakemeter.sync_pricing_vm_costs 
WHERE cloud = %s
  AND region = %s
  AND instance_type = %s
  AND pricing_tier = %s
LIMIT 5;
"""

result_9 = execute_query(query_9, (test_cloud, test_region, test_instance, test_pricing_tier))

print("=" * 100)
print("SIMULATED VIEW LOOKUP FOR GCP")
print("=" * 100)
print(f"Query Parameters:")
print(f"  cloud = '{test_cloud}'")
print(f"  region = '{test_region}'")
print(f"  instance_type = '{test_instance}'")
print(f"  pricing_tier = '{test_pricing_tier}'")
print("=" * 100)

if len(result_9) > 0:
    print("\n✅ MATCH FOUND! This lookup should work.")
    print(tabulate(result_9, headers='keys', tablefmt='grid', showindex=False))
else:
    print("\n❌ NO MATCH! This is why VM cost = $0")
    print("\n🔍 Trying case-insensitive search...")
    
    # Try case-insensitive
    query_9b = """
    SELECT 
        cloud,
        region,
        instance_type,
        pricing_tier,
        payment_option,
        cost_per_hour
    FROM lakemeter.sync_pricing_vm_costs 
    WHERE UPPER(cloud) = UPPER(%s)
      AND LOWER(region) = LOWER(%s)
      AND LOWER(instance_type) = LOWER(%s)
      AND LOWER(pricing_tier) = LOWER(%s)
    LIMIT 5;
    """
    
    result_9b = execute_query(query_9b, (test_cloud, test_region, test_instance, test_pricing_tier))
    
    if len(result_9b) > 0:
        print("   ✅ Found with case-insensitive search!")
        print(tabulate(result_9b, headers='keys', tablefmt='grid', showindex=False))
        print("\n   ⚠️  ISSUE: Case mismatch between test data and pricing table")
        print("   ACTION: Fix test data to match exact casing in pricing table")
    else:
        print("   ❌ Still no match. Data doesn't exist or names are completely different.")

print("=" * 100)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 11. Summary & Recommendations

# COMMAND ----------

print("=" * 100)
print("DIAGNOSTIC SUMMARY & NEXT STEPS")
print("=" * 100)
print("")
print("📋 CHECKLIST:")
print("")
print("1. Data Availability:")
print("   - Run Section 2 to see which clouds have VM pricing data")
print("   - If Azure/GCP missing: Run Pricing_Sync notebooks 04 & 05")
print("")
print("2. Region Match:")
print("   - Run Sections 3-4 to see available regions")
print("   - Compare with test data regions (eastus, westeurope, us-central1, europe-west1)")
print("   - If mismatch: Update test data OR pricing sync to use consistent names")
print("")
print("3. Instance Type Match:")
print("   - Run Sections 5-6 to see available instance types")
print("   - Compare with test instance types:")
print("     - Azure: Standard_D8s_v3, Standard_D16s_v3, Standard_D32s_v3")
print("     - GCP: n1-standard-8, n1-standard-16, n1-standard-32")
print("   - If mismatch: Update test data to match exact names from pricing table")
print("")
print("4. Case Sensitivity:")
print("   - Run Sections 7-8 for case-insensitive search")
print("   - If found: Case mismatch issue")
print("   - Solution: Match exact casing between test & pricing data")
print("")
print("5. Exact Lookup Simulation:")
print("   - Run Sections 9-10 to test exact view lookup")
print("   - This simulates what the v_line_items_with_costs view does")
print("   - If fails: Pinpoints exact mismatch (cloud/region/instance/tier)")
print("")
print("=" * 100)
print("\n✅ DIAGNOSTIC COMPLETE!")
print("   Review results above to identify the root cause of $0 VM costs.")

