# Databricks notebook source
# MAGIC %md
# MAGIC # Release 3: Alter Model Serving & Lakebase Columns
# MAGIC 
# MAGIC **Purpose:** 
# MAGIC 1. Add `model_serving_concurrency` column for scale-out support
# MAGIC 2. Change `lakebase_cu` from INT to DECIMAL(5,1) to support 0.5 CU
# MAGIC 
# MAGIC **Target Tables:** 
# MAGIC - `lakemeter.line_items` (main)
# MAGIC - `lakemeter.line_items_backup` (if exists)
# MAGIC 
# MAGIC **Changes:**
# MAGIC | Change | Column | Before | After |
# MAGIC |--------|--------|--------|-------|
# MAGIC | ADD | `model_serving_concurrency` | (does not exist) | `INT DEFAULT 4` |
# MAGIC | ALTER | `lakebase_cu` | `INT` | `DECIMAL(5,1)` |

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Install Dependencies & Connect to Lakebase

# COMMAND ----------

# Install required packages
%pip install psycopg2-binary --quiet
dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
from datetime import datetime

print("✅ Lakebase connection configured")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Helper Functions

# COMMAND ----------

def execute_sql(sql_statement, description="SQL", show_error=True):
    """Execute SQL statement and return success/failure"""
    try:
        conn = get_lakebase_connection()
        cursor = conn.cursor()
        
        cursor.execute(sql_statement)
        
        # Try to fetch results if available
        try:
            results = cursor.fetchall()
            colnames = [desc[0] for desc in cursor.description] if cursor.description else []
        except:
            results = None
            colnames = None
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ {description}")
        
        # Return results if any
        if results and colnames:
            return results, colnames
        return True
        
    except Exception as e:
        if show_error:
            print(f"❌ {description}")
            print(f"   Error: {str(e)}")
        return False

def query_sql(sql_statement, description="Query"):
    """Execute query and return results as list of dicts"""
    try:
        conn = get_lakebase_connection()
        cursor = conn.cursor()
        
        cursor.execute(sql_statement)
        results = cursor.fetchall()
        colnames = [desc[0] for desc in cursor.description]
        
        cursor.close()
        conn.close()
        
        # Convert to list of dicts
        result_dicts = []
        for row in results:
            result_dicts.append(dict(zip(colnames, row)))
        
        print(f"✅ {description} - {len(result_dicts)} rows")
        return result_dicts
        
    except Exception as e:
        print(f"❌ {description}")
        print(f"   Error: {str(e)}")
        return None

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Verify Connection & Target Tables

# COMMAND ----------

# Test connection
print("🔍 Testing Lakebase connection...")
result = execute_sql(
    "SELECT current_database(), current_user, version();",
    "Connection test"
)

# Verify main table exists
print("\n🔍 Checking if main table exists...")
table_check = query_sql(
    """
    SELECT table_name,
           (SELECT count(*) FROM lakemeter.line_items) as row_count
    FROM information_schema.tables
    WHERE table_schema = 'lakemeter'
      AND table_name = 'line_items';
    """,
    "Main table check"
)

if table_check:
    print(f"✅ Main table exists with {table_check[0]['row_count']} rows")
else:
    print("❌ Main table NOT found!")
    raise Exception("Main table lakemeter.line_items does not exist")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3b. Verify Table Ownership (Required for ALTER TABLE)

# COMMAND ----------

print("\n🔍 Checking table ownership...")
print("   ALTER TABLE requires ownership of the table.\n")

ownership_check = query_sql("""
SELECT t.tablename, t.tableowner, current_user as connected_as,
       (t.tableowner = current_user) as can_alter
FROM pg_tables t
WHERE t.schemaname = 'lakemeter'
  AND t.tablename IN ('line_items')
ORDER BY t.tablename;
""", "Ownership check")

if ownership_check:
    for row in ownership_check:
        can_alter = row['can_alter']
        print(f"   Table: {row['tablename']}")
        print(f"   Owner: {row['tableowner']}")
        print(f"   Connected as: {row['connected_as']}")
        print(f"   Can ALTER: {'✅ YES' if can_alter else '❌ NO'}")

        if not can_alter:
            print(f"\n   ⚠️  Connected role '{row['connected_as']}' does not own '{row['tablename']}'.")
            print(f"   Attempting ownership transfer...")

            # Try to transfer ownership (works if current user has appropriate privileges)
            transfer_result = execute_sql(
                f"ALTER TABLE lakemeter.{row['tablename']} OWNER TO {row['connected_as']}",
                f"Transfer ownership of {row['tablename']} to {row['connected_as']}"
            )

            if not transfer_result:
                print(f"\n   ❌ CANNOT PROCEED: Need the table owner ('{row['tableowner']}') to run:")
                print(f"      ALTER TABLE lakemeter.{row['tablename']} OWNER TO {row['connected_as']};")
                print(f"\n   Or run this migration notebook as '{row['tableowner']}' instead.")
                print(f"\n   💡 TIP: Run 01_Create_Tables.py first — it includes ownership verification.")
                raise Exception(
                    f"Table '{row['tablename']}' is owned by '{row['tableowner']}', "
                    f"not '{row['connected_as']}'. Transfer ownership first."
                )
            else:
                print(f"   ✅ Ownership transferred successfully!")
else:
    print("   ❌ Could not check ownership")
    raise Exception("Cannot verify table ownership")

# Check if backup table exists
print("\n🔍 Checking if backup table exists...")
backup_check = query_sql(
    """
    SELECT table_name
    FROM information_schema.tables 
    WHERE table_schema = 'lakemeter'
      AND table_name LIKE 'line_items_backup%';
    """,
    "Backup table check"
)

if backup_check:
    backup_tables = [r['table_name'] for r in backup_check]
    print(f"✅ Found backup table(s): {', '.join(backup_tables)}")
else:
    print("⚠️  No backup tables found (will skip backup table alterations)")
    backup_tables = []

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Pre-Migration: Check Current Column State

# COMMAND ----------

print("=" * 80)
print("PRE-MIGRATION: Current column state")
print("=" * 80)

# Check model_serving_concurrency existence
pre_check = query_sql("""
SELECT 
    table_name,
    column_name, 
    data_type, 
    numeric_precision,
    numeric_scale,
    column_default,
    is_nullable
FROM information_schema.columns 
WHERE table_schema = 'lakemeter'
  AND table_name = 'line_items'
  AND column_name IN ('model_serving_concurrency', 'model_serving_gpu_type', 'lakebase_cu')
ORDER BY column_name;
""", "Check existing columns in main table")

if pre_check:
    for col in pre_check:
        dtype = col['data_type']
        if col['numeric_precision']:
            dtype += f"({col['numeric_precision']},{col['numeric_scale']})"
        print(f"  • {col['column_name']:<35} {dtype:<20} default={col['column_default']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Add Column: model_serving_concurrency (Main Table)

# COMMAND ----------

print("=" * 80)
print("1. MODEL SERVING CONCURRENCY - Main Table")
print("=" * 80)

execute_sql("""
ALTER TABLE lakemeter.line_items
ADD COLUMN IF NOT EXISTS model_serving_concurrency INT DEFAULT 4
CHECK (model_serving_concurrency >= 4 AND model_serving_concurrency % 4 = 0);
""", "Added model_serving_concurrency column (multiples of 4, default 4)")

execute_sql("""
ALTER TABLE lakemeter.line_items
ADD COLUMN IF NOT EXISTS model_serving_scale_out VARCHAR(20)
CHECK (model_serving_scale_out IS NULL OR model_serving_scale_out IN ('small', 'medium', 'large', 'custom'));
""", "Added model_serving_scale_out column (small/medium/large/custom)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Add Column: model_serving_concurrency (Backup Table)

# COMMAND ----------

print("=" * 80)
print("2. MODEL SERVING CONCURRENCY - Backup Table(s)")
print("=" * 80)

if backup_tables:
    for backup_table in backup_tables:
        execute_sql(f"""
ALTER TABLE lakemeter.{backup_table}
ADD COLUMN IF NOT EXISTS model_serving_concurrency INT DEFAULT 4;
""", f"Added model_serving_concurrency to {backup_table}")
        execute_sql(f"""
ALTER TABLE lakemeter.{backup_table}
ADD COLUMN IF NOT EXISTS model_serving_scale_out VARCHAR(20);
""", f"Added model_serving_scale_out to {backup_table}")
else:
    print("⚠️  No backup tables found, skipping")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Alter Column: lakebase_cu INT → DECIMAL(5,1) (Main Table)

# COMMAND ----------

print("=" * 80)
print("3. LAKEBASE CU TYPE CHANGE - Main Table")
print("=" * 80)

execute_sql("""
ALTER TABLE lakemeter.line_items 
ALTER COLUMN lakebase_cu TYPE DECIMAL(5,1);
""", "Changed lakebase_cu from INT to DECIMAL(5,1) to support 0.5 CU")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Alter Column: lakebase_cu INT → DECIMAL(5,1) (Backup Table)

# COMMAND ----------

print("=" * 80)
print("4. LAKEBASE CU TYPE CHANGE - Backup Table(s)")
print("=" * 80)

if backup_tables:
    for backup_table in backup_tables:
        execute_sql(f"""
ALTER TABLE lakemeter.{backup_table} 
ALTER COLUMN lakebase_cu TYPE DECIMAL(5,1);
""", f"Changed lakebase_cu to DECIMAL(5,1) in {backup_table}")
else:
    print("⚠️  No backup tables found, skipping")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Add Column Comments

# COMMAND ----------

print("=" * 80)
print("5. ADDING COLUMN COMMENTS")
print("=" * 80)

execute_sql("""
COMMENT ON COLUMN lakemeter.line_items.model_serving_concurrency IS 
'Model Serving scale-out concurrency. Multiples of 4 (4, 8, 12, ..., 64). DBU/hr = gpu_dbu_rate x concurrency.';
""", "Added comment for model_serving_concurrency (main)")

execute_sql("""
COMMENT ON COLUMN lakemeter.line_items.lakebase_cu IS 
'Lakebase CU per node. Valid values: 0.5, 1-10, 12, 14, 16, 24, 28, 32 (autoscale) or 36-112 (fixed). Each CU is approx 2 GB RAM.';
""", "Added comment for lakebase_cu (main)")

if backup_tables:
    for backup_table in backup_tables:
        execute_sql(f"""
COMMENT ON COLUMN lakemeter.{backup_table}.model_serving_concurrency IS 
'Model Serving scale-out concurrency. Multiples of 4 (4, 8, 12, ..., 64). DBU/hr = gpu_dbu_rate x concurrency.';
""", f"Added comment for model_serving_concurrency ({backup_table})")

        execute_sql(f"""
COMMENT ON COLUMN lakemeter.{backup_table}.lakebase_cu IS 
'Lakebase CU per node. Valid values: 0.5, 1-10, 12, 14, 16, 24, 28, 32 (autoscale) or 36-112 (fixed). Each CU is approx 2 GB RAM.';
""", f"Added comment for lakebase_cu ({backup_table})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Post-Migration: Verify Changes

# COMMAND ----------

print("\n" + "=" * 80)
print("VERIFICATION: Check all changes applied")
print("=" * 80)

# Check main table
post_check_main = query_sql("""
SELECT 
    column_name, 
    data_type, 
    numeric_precision,
    numeric_scale,
    column_default,
    is_nullable
FROM information_schema.columns 
WHERE table_schema = 'lakemeter'
  AND table_name = 'line_items'
  AND column_name IN ('model_serving_concurrency', 'lakebase_cu')
ORDER BY column_name;
""", "Verify main table columns")

if post_check_main:
    print("\n📊 Main table (lakemeter.line_items):")
    print("-" * 80)
    for col in post_check_main:
        dtype = col['data_type']
        if col['numeric_precision']:
            dtype += f"({col['numeric_precision']},{col['numeric_scale']})"
        print(f"  • {col['column_name']:<35} {dtype:<20} default={col['column_default']}")

# Check backup table(s)
if backup_tables:
    for backup_table in backup_tables:
        post_check_backup = query_sql(f"""
SELECT 
    column_name, 
    data_type, 
    numeric_precision,
    numeric_scale,
    column_default,
    is_nullable
FROM information_schema.columns 
WHERE table_schema = 'lakemeter'
  AND table_name = '{backup_table}'
  AND column_name IN ('model_serving_concurrency', 'lakebase_cu')
ORDER BY column_name;
""", f"Verify {backup_table} columns")

        if post_check_backup:
            print(f"\n📊 Backup table (lakemeter.{backup_table}):")
            print("-" * 80)
            for col in post_check_backup:
                dtype = col['data_type']
                if col['numeric_precision']:
                    dtype += f"({col['numeric_precision']},{col['numeric_scale']})"
                print(f"  • {col['column_name']:<35} {dtype:<20} default={col['column_default']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 11. Verify Constraints

# COMMAND ----------

print("\n" + "=" * 80)
print("VERIFICATION: Check constraints")
print("=" * 80)

constraints = query_sql("""
SELECT 
    tc.constraint_name,
    tc.table_name,
    cc.check_clause
FROM information_schema.table_constraints tc
JOIN information_schema.check_constraints cc 
    ON tc.constraint_name = cc.constraint_name
WHERE tc.table_schema = 'lakemeter'
  AND tc.table_name = 'line_items'
  AND tc.constraint_type = 'CHECK'
  AND (cc.check_clause LIKE '%model_serving_concurrency%')
ORDER BY tc.constraint_name;
""", "Check constraints for model_serving_concurrency")

if constraints:
    for c in constraints:
        print(f"  • {c['constraint_name']}: {c['check_clause']}")
else:
    print("  ⚠️  No constraints found (constraint may have been applied inline)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 12. Summary

# COMMAND ----------

print("\n" + "=" * 80)
print("🎉 RELEASE 3 MIGRATION COMPLETE")
print("=" * 80)
print(f"""
✅ Changes Applied:

  1. MODEL SERVING CONCURRENCY (new column)
     - Column: model_serving_concurrency INT DEFAULT 4
     - Constraint: Must be >= 4 and multiples of 4
     - Purpose: Scale-out concurrency for Model Serving endpoints
     - Formula: DBU/hr = gpu_dbu_rate × concurrency
     - Tables: line_items + backup table(s)

  2. LAKEBASE CU TYPE CHANGE (altered column)
     - Column: lakebase_cu INT → DECIMAL(5,1)
     - Purpose: Support 0.5 CU and new CU sizes (0.5 to 112)
     - Valid values: 0.5, 1-10, 12, 14, 16, 24, 28, 32 (autoscale)
                     36, 40, 44, 48, 52, 56, 60, 64, 72, 80, 88, 96, 104, 112 (fixed)
     - Tables: line_items + backup table(s)

📊 Next Steps:
   1. Sync notebook to Databricks workspace:
      databricks sync database_backend/Lakebase_Setup /Workspace/Users/steven.tan@databricks.com/lakemeter/Lakebase_Setup --profile lakemeter
   2. Run this notebook in the Databricks workspace
   3. Update API endpoints to use new columns
   4. Update frontend to show concurrency selector for Model Serving
""")
print("=" * 80)

# COMMAND ----------
