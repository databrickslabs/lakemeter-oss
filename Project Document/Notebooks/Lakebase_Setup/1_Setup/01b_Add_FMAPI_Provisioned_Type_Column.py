# Databricks notebook source
# MAGIC %md
# MAGIC # Add fmapi_provisioned_type Column to line_items
# MAGIC 
# MAGIC **Purpose:** Add the new `fmapi_provisioned_type` column to support provisioned throughput pricing for FMAPI Databricks models.
# MAGIC 
# MAGIC **Use this if:**
# MAGIC - You want to preserve existing data in line_items
# MAGIC - You don't want to recreate all tables
# MAGIC 
# MAGIC **What it does:**
# MAGIC - Adds `fmapi_provisioned_type VARCHAR(50)` column to `line_items` table
# MAGIC - Default value: NULL (will default to 'pay_per_token' in view logic)
# MAGIC - Safe to run multiple times (uses IF NOT EXISTS check)
# MAGIC 
# MAGIC **After running this:**
# MAGIC - Run `02_Create_Views.py` to update views
# MAGIC - Run `Test_12_FMAPI_Databricks.py` to test

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2

def execute_sql(sql, description, show_error=True):
    """Execute SQL and return True if successful"""
    conn = get_lakebase_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            conn.commit()
            print(f"✅ {description}")
            return True
    except Exception as e:
        conn.rollback()
        if show_error:
            print(f"❌ {description}: {e}")
        return False
    finally:
        conn.close()

# COMMAND ----------

print("=" * 80)
print("ADDING fmapi_provisioned_type COLUMN TO line_items")
print("=" * 80)

# COMMAND ----------

# Check if column already exists
check_sql = """
SELECT column_name 
FROM information_schema.columns 
WHERE table_schema = 'lakemeter' 
AND table_name = 'line_items' 
AND column_name = 'fmapi_provisioned_type';
"""

conn = get_lakebase_connection()
cur = conn.cursor()
cur.execute(check_sql)
existing = cur.fetchone()
conn.close()

if existing:
    print("⚠️  Column fmapi_provisioned_type already exists!")
    print("   No action needed.")
else:
    print("📝 Column fmapi_provisioned_type does not exist. Adding it now...")
    
    # Add the column
    add_column_sql = """
    ALTER TABLE lakemeter.line_items 
    ADD COLUMN fmapi_provisioned_type VARCHAR(50);
    """
    
    result = execute_sql(add_column_sql, "Added fmapi_provisioned_type column")
    
    if result:
        print("\n✅ Column added successfully!")
        print("   • Column: fmapi_provisioned_type")
        print("   • Type: VARCHAR(50)")
        print("   • Values: 'pay_per_token', 'provisioned_entry', 'provisioned_scaling'")
        print("\n📋 Next steps:")
        print("   1. Run 02_Create_Views.py to update views")
        print("   2. Run Test_12_FMAPI_Databricks.py to test")

# COMMAND ----------

# Verify the column was added
verify_sql = """
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns 
WHERE table_schema = 'lakemeter' 
AND table_name = 'line_items' 
AND column_name = 'fmapi_provisioned_type';
"""

print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)

conn = get_lakebase_connection()
cur = conn.cursor()
cur.execute(verify_sql)
result = cur.fetchone()
conn.close()

if result:
    print(f"✅ Column exists:")
    print(f"   • Name: {result[0]}")
    print(f"   • Type: {result[1]}")
    print(f"   • Max Length: {result[2]}")
else:
    print("❌ Column not found! Something went wrong.")

# COMMAND ----------

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("✅ Schema update complete!")
print("\n📋 Next steps:")
print("   1. Run: 02_Create_Views.py")
print("      (Updates views to support provisioned throughput)")
print("")
print("   2. Run: Test_12_FMAPI_Databricks.py")
print("      (Tests token-based and provisioned throughput pricing)")
print("=" * 80)

