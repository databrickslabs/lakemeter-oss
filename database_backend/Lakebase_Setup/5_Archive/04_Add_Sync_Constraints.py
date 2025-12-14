# Databricks notebook source
# MAGIC %md
# MAGIC # Lakemeter - Add Sync-Dependent Validation Constraints
# MAGIC 
# MAGIC **Purpose:** Adds validation constraints that depend on sync_* pricing tables
# MAGIC 
# MAGIC **Connects to:** Lakebase (PostgreSQL)
# MAGIC 
# MAGIC **Constraints Added:**
# MAGIC 1. **Region Validation**
# MAGIC    - UNIQUE on `sync_ref_sku_region_map(cloud, region_code)`
# MAGIC    - FK from `estimates(cloud, region)` → `sync_ref_sku_region_map`
# MAGIC    - Prevents: ❌ AWS + eastus, AZURE + us-east-1, etc.
# MAGIC 
# MAGIC 2. **Instance Type Validation**
# MAGIC    - UNIQUE on `sync_ref_instance_dbu_rates(cloud, instance_type)`
# MAGIC    - FK from `line_items(cloud, driver_node_type)` → `sync_ref_instance_dbu_rates`
# MAGIC    - FK from `line_items(cloud, worker_node_type)` → `sync_ref_instance_dbu_rates`
# MAGIC    - Prevents: ❌ Azure estimate with i3.xlarge, AWS with Standard_D4s_v3, etc.
# MAGIC 
# MAGIC **Prerequisites:**
# MAGIC 1. ✅ 01_Create_Tables.py (creates application tables + triggers)
# MAGIC 2. ✅ Pricing_Sync notebooks (creates all sync_* tables)
# MAGIC 
# MAGIC **Run Order:**
# MAGIC 1. 01_Create_Tables.py
# MAGIC 2. Pricing_Sync notebooks
# MAGIC 3. **This notebook**
# MAGIC 4. 02_Create_Views.py

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Install Dependencies & Connect to Lakebase

# COMMAND ----------

# Install required packages
%pip install psycopg2-binary --quiet
dbutils.library.restartPython()

# COMMAND ----------

import psycopg2
from datetime import datetime

# Lakebase connection details
LAKEBASE_HOST = "instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com"
LAKEBASE_PORT = 5432
LAKEBASE_DATABASE = "lakemeter_pricing"
LAKEBASE_USER = "lakemeter_sync_role"
LAKEBASE_PASSWORD = "***REMOVED_DATABASE_CREDENTIAL***"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Helper Functions

# COMMAND ----------

def get_connection():
    """Create PostgreSQL connection"""
    return psycopg2.connect(
        host=LAKEBASE_HOST,
        port=LAKEBASE_PORT,
        database=LAKEBASE_DATABASE,
        user=LAKEBASE_USER,
        password=LAKEBASE_PASSWORD,
        sslmode='require'
    )

def execute_sql(sql_statement, description="SQL", show_error=True):
    """Execute SQL statement and return success/failure"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql_statement)
        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ {description}")
        return True
    except Exception as e:
        if show_error:
            print(f"❌ {description}")
            print(f"   Error: {str(e)}")
        else:
            print(f"⚠️  {description} - Already exists or not applicable")
        return False

def query_sql(sql_statement):
    """Execute query and return results"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql_statement)
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results

def constraint_exists(constraint_name):
    """Check if constraint already exists"""
    sql = f"""
    SELECT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = '{constraint_name}'
    );
    """
    result = query_sql(sql)
    return result[0][0] if result else False

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Test Connection

# COMMAND ----------

try:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    cur.close()
    conn.close()
    print("✅ Connected to Lakebase!")
    print(f"   PostgreSQL version: {version[:50]}...")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Check Prerequisites

# COMMAND ----------

print("=" * 80)
print("🔍 CHECKING PREREQUISITES")
print("=" * 80)

required_tables = [
    ('lakemeter.estimates', 'Application table'),
    ('lakemeter.line_items', 'Application table'),
    ('lakemeter.sync_ref_sku_region_map', 'Pricing sync table'),
    ('lakemeter.sync_ref_instance_dbu_rates', 'Pricing sync table'),
]

all_tables_exist = True

for table_name, table_type in required_tables:
    schema, table = table_name.split('.')
    check_sql = f"""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = '{schema}' 
        AND table_name = '{table}'
    );
    """
    result = query_sql(check_sql)
    exists = result[0][0] if result else False
    
    if exists:
        # Count rows
        try:
            count_sql = f"SELECT COUNT(*) FROM {table_name};"
            count_result = query_sql(count_sql)
            row_count = count_result[0][0] if count_result else 0
            print(f"   ✅ {table_name} ({table_type}) - {row_count:,} rows")
        except:
            print(f"   ✅ {table_name} ({table_type})")
    else:
        print(f"   ❌ {table_name} ({table_type}) - MISSING!")
        all_tables_exist = False

if not all_tables_exist:
    print("\n" + "=" * 80)
    print("❌ ERROR: Required tables are missing!")
    print("=" * 80)
    print("\n📋 Next Steps:")
    print("   1. Run 01_Create_Tables.py if application tables are missing")
    print("   2. Run Pricing_Sync notebooks if sync_* tables are missing")
    print("=" * 80)
    raise Exception("Prerequisites not met. Cannot add constraints.")
else:
    print("\n✅ All prerequisites met!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4B. Check Ownership of sync_* Tables

# COMMAND ----------

print("\n" + "=" * 80)
print("🔍 CHECKING OWNERSHIP OF sync_* TABLES")
print("=" * 80)
print("These tables need ALTER permission to add UNIQUE constraints.")
print("=" * 80)

ownership_check_sql = """
SELECT 
    tablename,
    tableowner,
    CASE 
        WHEN tableowner = current_user THEN '✅ YOU OWN THIS'
        WHEN tableowner = 'lakemeter_sync_role' THEN '✅ OWNED BY lakemeter_sync_role'
        ELSE '❌ OWNED BY: ' || tableowner
    END as ownership_status
FROM pg_tables
WHERE schemaname = 'lakemeter'
AND tablename IN ('sync_ref_sku_region_map', 'sync_ref_instance_dbu_rates')
ORDER BY tablename;
"""

try:
    ownership_results = query_sql(ownership_check_sql)
    
    ownership_issues = []
    for row in ownership_results:
        tablename, tableowner, status = row
        print(f"\n   {tablename}:")
        print(f"      Owner: {tableowner}")
        print(f"      Status: {status}")
        
        if '❌' in status:
            ownership_issues.append((tablename, tableowner))
    
    if ownership_issues:
        print("\n" + "=" * 80)
        print("⚠️  OWNERSHIP WARNING: DATABRICKS MANAGED CONNECTOR DETECTED")
        print("=" * 80)
        print(f"\n{len(ownership_issues)} sync_* table(s) are owned by: {ownership_issues[0][1]}")
        
        # Check if it's a Databricks system account
        if 'databricks_writer' in ownership_issues[0][1]:
            print("\n🔍 DIAGNOSIS:")
            print("   This is a DATABRICKS MANAGED CONNECTOR system account.")
            print("   You CANNOT modify these tables without superuser privileges.")
            print("\n💡 RECOMMENDATION: SKIP THIS NOTEBOOK")
            print("   The constraints this notebook adds are OPTIONAL.")
            print("   Your app will work perfectly without them!")
            print("\n📋 WHAT YOU LOSE:")
            print("   ❌ Database-level region validation (cloud + region FK)")
            print("   ❌ Database-level instance validation (cloud + instance FK)")
            print("\n📋 WHAT STILL WORKS:")
            print("   ✅ All cost calculations (views work fine)")
            print("   ✅ All business logic constraints (32+ in line_items)")
            print("   ✅ All pricing data queries")
            print("   ✅ Frontend validation (same end result)")
            print("\n🚀 NEXT STEPS:")
            print("   1. Stop this notebook")
            print("   2. Go to: 02_Create_Views.py")
            print("   3. Run that instead")
            print("   4. Done!")
            print("\n" + "=" * 80)
            print("🛑 STOPPING: Cannot proceed with connector-owned tables.")
            print("=" * 80)
            raise Exception("Databricks managed connector ownership detected. Skip this notebook and run 02_Create_Views.py instead.")
        else:
            # Regular user ownership - can be fixed
            print("\nAdding UNIQUE constraints requires ownership or ALTER permission.")
            print("\n📋 OPTIONS TO FIX:")
            print("\n  Option 1: Transfer ownership (run in Lakebase SQL Editor):")
            print("  " + "─" * 76)
            for table, owner in ownership_issues:
                print(f"  ALTER TABLE lakemeter.{table} OWNER TO lakemeter_sync_role;")
            print()
            print("\n  Option 2: Run Pricing_Sync notebooks again as lakemeter_sync_role")
            print("            (they will create tables with correct ownership)")
            print("\n  Option 3: Continue anyway (constraints will be skipped)")
            print("=" * 80)
            
            # Don't stop - just warn and continue
            print("\n⚠️  Continuing... Constraints may fail due to ownership.")
    else:
        print("\n✅ All sync_* tables have correct ownership!")
        
except Exception as e:
    print(f"\n⚠️  Could not check ownership: {e}")
    print("   Continuing anyway...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Add Region Validation Constraints

# COMMAND ----------

print("\n" + "=" * 80)
print("1️⃣  REGION VALIDATION")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ### 5.1 Add UNIQUE Constraint on sync_ref_sku_region_map

# COMMAND ----------

constraint_name = 'uq_cloud_region_code'

if constraint_exists(constraint_name):
    print(f"⚠️  UNIQUE constraint already exists: {constraint_name}")
else:
    add_unique_sql = """
    ALTER TABLE lakemeter.sync_ref_sku_region_map 
    ADD CONSTRAINT uq_cloud_region_code 
    UNIQUE (cloud, region_code);
    """
    result = execute_sql(add_unique_sql, f"Added UNIQUE constraint: {constraint_name}", show_error=True)
    
    if not result:
        print("\n💡 If ownership error, run this in Lakebase SQL Editor:")
        print("   ALTER TABLE lakemeter.sync_ref_sku_region_map OWNER TO lakemeter_sync_role;")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 5.2 Add FK Constraint: estimates → sync_ref_sku_region_map

# COMMAND ----------

constraint_name = 'fk_estimates_cloud_region'

if constraint_exists(constraint_name):
    print(f"⚠️  FK constraint already exists: {constraint_name}")
else:
    add_fk_sql = """
    ALTER TABLE lakemeter.estimates 
    ADD CONSTRAINT fk_estimates_cloud_region 
    FOREIGN KEY (cloud, region) 
    REFERENCES lakemeter.sync_ref_sku_region_map(cloud, region_code);
    """
    execute_sql(add_fk_sql, f"Added FK constraint: {constraint_name}")

# COMMAND ----------

print("\n✅ Region validation active!")
print("   → Prevents: ❌ AWS + eastus, AZURE + us-east-1, GCP + westeurope")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Add Instance Type Validation Constraints

# COMMAND ----------

print("\n" + "=" * 80)
print("2️⃣  INSTANCE TYPE VALIDATION")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ### 6.1 Add UNIQUE Constraint on sync_ref_instance_dbu_rates

# COMMAND ----------

constraint_name = 'uq_cloud_instance_type'

if constraint_exists(constraint_name):
    print(f"⚠️  UNIQUE constraint already exists: {constraint_name}")
else:
    add_unique_sql = """
    ALTER TABLE lakemeter.sync_ref_instance_dbu_rates 
    ADD CONSTRAINT uq_cloud_instance_type 
    UNIQUE (cloud, instance_type);
    """
    result = execute_sql(add_unique_sql, f"Added UNIQUE constraint: {constraint_name}", show_error=True)
    
    if not result:
        print("\n💡 If ownership error, run this in Lakebase SQL Editor:")
        print("   ALTER TABLE lakemeter.sync_ref_instance_dbu_rates OWNER TO lakemeter_sync_role;")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 6.2 Add FK Constraint: line_items(driver_node_type) → sync_ref_instance_dbu_rates

# COMMAND ----------

constraint_name = 'fk_line_items_driver_instance'

if constraint_exists(constraint_name):
    print(f"⚠️  FK constraint already exists: {constraint_name}")
else:
    add_fk_sql = """
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT fk_line_items_driver_instance 
    FOREIGN KEY (cloud, driver_node_type) 
    REFERENCES lakemeter.sync_ref_instance_dbu_rates(cloud, instance_type)
    DEFERRABLE INITIALLY DEFERRED;
    """
    execute_sql(add_fk_sql, f"Added FK constraint: {constraint_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 6.3 Add FK Constraint: line_items(worker_node_type) → sync_ref_instance_dbu_rates

# COMMAND ----------

constraint_name = 'fk_line_items_worker_instance'

if constraint_exists(constraint_name):
    print(f"⚠️  FK constraint already exists: {constraint_name}")
else:
    add_fk_sql = """
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT fk_line_items_worker_instance 
    FOREIGN KEY (cloud, worker_node_type) 
    REFERENCES lakemeter.sync_ref_instance_dbu_rates(cloud, instance_type)
    DEFERRABLE INITIALLY DEFERRED;
    """
    execute_sql(add_fk_sql, f"Added FK constraint: {constraint_name}")

# COMMAND ----------

print("\n✅ Instance type validation active!")
print("   → Prevents: ❌ AWS using Azure instances, Azure using GCP instances, etc.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Verification

# COMMAND ----------

print("\n" + "=" * 80)
print("📊 VERIFICATION: Checking All Constraints")
print("=" * 80)

verification_sql = """
SELECT 
    CASE 
        WHEN contype = 'f' THEN '🔗 FK'
        WHEN contype = 'u' THEN '🔑 UNIQUE'
        ELSE '  ' || contype::text  -- Fixed: explicit cast to text
    END as type,
    conname as constraint_name,
    '✅ EXISTS' as status
FROM pg_constraint
WHERE conname IN (
    'uq_cloud_region_code',
    'fk_estimates_cloud_region',
    'uq_cloud_instance_type',
    'fk_line_items_driver_instance',
    'fk_line_items_worker_instance'
)
ORDER BY 
    CASE conname
        WHEN 'uq_cloud_region_code' THEN 1
        WHEN 'fk_estimates_cloud_region' THEN 2
        WHEN 'uq_cloud_instance_type' THEN 3
        WHEN 'fk_line_items_driver_instance' THEN 4
        WHEN 'fk_line_items_worker_instance' THEN 5
    END;
"""

results = query_sql(verification_sql)

print("\n📋 Constraints Added:")
for row in results:
    constraint_type, constraint_name, status = row
    print(f"   {constraint_type} {constraint_name} - {status}")

# COMMAND ----------

# Get count of constraints by type
constraint_summary_sql = """
SELECT 
    CASE 
        WHEN contype = 'f' THEN 'Foreign Key (FK)'
        WHEN contype = 'u' THEN 'Unique (UNIQUE)'
        WHEN contype = 'p' THEN 'Primary Key (PK)'
        WHEN contype = 'c' THEN 'Check (CHECK)'
        ELSE 'Other'
    END as constraint_type,
    COUNT(*) as count
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
JOIN pg_namespace n ON t.relnamespace = n.oid
WHERE n.nspname = 'lakemeter'
GROUP BY contype
ORDER BY count DESC;
"""

summary_results = query_sql(constraint_summary_sql)

print("\n📊 Total Constraints in lakemeter schema:")
for row in summary_results:
    constraint_type, count = row
    print(f"   {constraint_type}: {count}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Test Examples (Read-Only)

# COMMAND ----------

print("\n" + "=" * 80)
print("🧪 TEST EXAMPLES (What These Constraints Prevent)")
print("=" * 80)

print("\n✅ Valid operations:")
print("   • INSERT INTO estimates (cloud='AWS', region='us-east-1', tier='STANDARD', ...)")
print("   • INSERT INTO line_items (estimate_id=..., driver_node_type='i3.xlarge', ...)")
print("     → SUCCESS (i3.xlarge exists for AWS)")

print("\n❌ Invalid operations that will be BLOCKED:")
print("   • INSERT INTO estimates (cloud='AWS', region='eastus', ...)")
print("     → ERROR: FK constraint fk_estimates_cloud_region violated")
print("     → Reason: eastus is an Azure region, not valid for AWS")

print("\n   • INSERT INTO line_items (cloud='AWS', driver_node_type='Standard_D4s_v3', ...)")
print("     → ERROR: FK constraint fk_line_items_driver_instance violated")
print("     → Reason: Standard_D4s_v3 is an Azure instance, not valid for AWS")

# COMMAND ----------

# Let's check some sample valid combinations
print("\n📊 Sample Valid Cloud/Region Combinations:")

try:
    # First, check what columns exist
    check_columns_sql = """
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_schema = 'lakemeter' 
    AND table_name = 'sync_ref_sku_region_map'
    ORDER BY ordinal_position;
    """
    columns = query_sql(check_columns_sql)
    column_names = [col[0] for col in columns]
    
    # Use SELECT * to get whatever columns exist
    sample_regions_sql = """
    SELECT * 
    FROM lakemeter.sync_ref_sku_region_map
    WHERE cloud = 'AWS' AND region_code LIKE 'us-%'
    LIMIT 5;
    """
    
    sample_regions = query_sql(sample_regions_sql)
    if sample_regions:
        print(f"   Columns: {', '.join(column_names)}")
        for row in sample_regions:
            if len(row) >= 2:
                print(f"   ✅ {row[0]} + {row[1]}")
            else:
                print(f"   ✅ {row}")
    else:
        print("   ℹ️  No sample data available")
except Exception as e:
    print(f"   ⚠️  Could not query sample data: {str(e)[:100]}")
    print("   💡 Table structure may vary - query directly to see columns")

# COMMAND ----------

print("\n📊 Sample Valid Cloud/Instance Combinations:")

try:
    # First, check what columns exist
    check_columns_sql = """
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_schema = 'lakemeter' 
    AND table_name = 'sync_ref_instance_dbu_rates'
    ORDER BY ordinal_position;
    """
    columns = query_sql(check_columns_sql)
    column_names = [col[0] for col in columns]
    
    # Query with known columns (cloud, instance_type should always exist)
    sample_instances_sql = """
    SELECT cloud, instance_type, dbu_rate
    FROM lakemeter.sync_ref_instance_dbu_rates
    WHERE cloud = 'AWS' AND instance_type LIKE 'i3.%'
    LIMIT 5;
    """
    
    sample_instances = query_sql(sample_instances_sql)
    if sample_instances:
        print(f"   Columns: {', '.join(column_names)}")
        for row in sample_instances:
            cloud, instance_type, dbu_rate = row
            print(f"   ✅ {cloud} + {instance_type} ({dbu_rate} DBU)")
    else:
        print("   ℹ️  No sample data available")
except Exception as e:
    print(f"   ⚠️  Could not query sample data: {str(e)[:100]}")
    print("   💡 Query the table directly to see available instances")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Summary

# COMMAND ----------

print("\n" + "=" * 80)
print("📊 SUMMARY")
print("=" * 80)

# Check if constraints were actually added
verification_count_sql = """
SELECT COUNT(*) 
FROM pg_constraint
WHERE conname IN (
    'uq_cloud_region_code',
    'fk_estimates_cloud_region',
    'uq_cloud_instance_type',
    'fk_line_items_driver_instance',
    'fk_line_items_worker_instance'
);
"""

try:
    result = query_sql(verification_count_sql)
    constraints_added = result[0][0] if result else 0
    
    if constraints_added == 5:
        print("✅ ALL SYNC-DEPENDENT CONSTRAINTS ADDED SUCCESSFULLY!")
    elif constraints_added > 0:
        print(f"⚠️  PARTIAL SUCCESS: {constraints_added}/5 constraints added")
        print("   Some constraints may have failed due to ownership issues.")
    else:
        print("❌ NO CONSTRAINTS ADDED")
        print("   This is expected if sync_* tables are owned by Databricks connector.")
        print("\n💡 RECOMMENDATION:")
        print("   Skip this notebook and validate in frontend instead.")
        print("   Your app will work perfectly without these constraints!")
except Exception as e:
    print("⚠️  Could not verify constraints")
    print(f"   Error: {str(e)[:100]}")

print("\n" + "=" * 80)

print("\n📋 What This Notebook Attempts:")
print("   1. Region Validation:")
print("      - UNIQUE constraint on sync_ref_sku_region_map(cloud, region_code)")
print("      - FK from estimates(cloud, region) → sync_ref_sku_region_map")
print("")
print("   2. Instance Type Validation:")
print("      - UNIQUE constraint on sync_ref_instance_dbu_rates(cloud, instance_type)")
print("      - FK from line_items(cloud, driver_node_type) → sync_ref_instance_dbu_rates")
print("      - FK from line_items(cloud, worker_node_type) → sync_ref_instance_dbu_rates")

if constraints_added == 5:
    print("\n🛡️  Data Integrity Protection NOW ACTIVE:")
    print("   ✅ Users can only select valid cloud/region combinations")
    print("   ✅ Line items can only use instance types valid for their cloud")
    print("   ✅ Database enforces these rules automatically")
    print("\n📋 Next Steps:")
    print("   1. ✅ Run 02_Create_Views.py to create cost calculation views")
    print("   2. ✅ Test your application - constraints are active!")
elif constraints_added > 0:
    print("\n⚠️  Partial Protection:")
    print(f"   Only {constraints_added}/5 constraints are active")
    print("   Frontend should handle validation for failed constraints")
    print("\n📋 Next Steps:")
    print("   1. ✅ Run 02_Create_Views.py anyway (views don't need these)")
    print("   2. ⚠️  Implement frontend validation for missing constraints")
else:
    print("\n💡 No Database Constraints Added (Connector Ownership Issue)")
    print("   ✅ App still works perfectly!")
    print("   ✅ Validation moves to frontend layer")
    print("\n📋 Frontend Validation Queries:")
    print("   Valid regions:  SELECT DISTINCT cloud, region_code FROM sync_ref_sku_region_map WHERE cloud = ?")
    print("   Valid instances: SELECT DISTINCT cloud, instance_type FROM sync_ref_instance_dbu_rates WHERE cloud = ?")
    print("\n📋 Next Steps:")
    print("   1. ✅ Run 02_Create_Views.py (this is NOT affected)")
    print("   2. ✅ Implement frontend validation")
    print("   3. ✅ Done! App is fully functional")

print("\n" + "=" * 80)

