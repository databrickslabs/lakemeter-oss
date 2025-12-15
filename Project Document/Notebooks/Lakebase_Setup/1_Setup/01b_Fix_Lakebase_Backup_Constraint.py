# Databricks notebook source
# MAGIC %md
# MAGIC # Fix: Lakebase Backup Constraint
# MAGIC 
# MAGIC **Issue:** `chk_lakebase_backup_range` constraint requires 1-35 days, but 0 should be allowed (no backup)
# MAGIC 
# MAGIC **Fix:** Drop and recreate the constraint to allow 0-35 days

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2

def execute_query(query, params=None, fetch=False):
    """Execute a SQL query"""
    conn = get_lakebase_connection()
    try:
        with conn.cursor() as cur:
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            
            if fetch:
                columns = [desc[0] for desc in cur.description] if cur.description else []
                results = cur.fetchall()
                return results
            else:
                conn.commit()
                return True
    except Exception as e:
        conn.rollback()
        print(f"Error executing query: {e}")
        raise
    finally:
        conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Drop Old Constraint

# COMMAND ----------

print("=" * 100)
print("DROPPING OLD CONSTRAINT")
print("=" * 100)

try:
    execute_query("""
    ALTER TABLE lakemeter.line_items 
    DROP CONSTRAINT IF EXISTS chk_lakebase_backup_range;
    """)
    print("\n✅ Old constraint dropped successfully")
except Exception as e:
    print(f"\n⚠️  Warning: {e}")
    print("   (This is OK if constraint doesn't exist)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Add New Constraint (0-35 days)

# COMMAND ----------

print("\n" + "=" * 100)
print("ADDING NEW CONSTRAINT (0-35 days)")
print("=" * 100)

try:
    execute_query("""
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT chk_lakebase_backup_range 
    CHECK (lakebase_backup_retention_days >= 0 AND lakebase_backup_retention_days <= 35);
    """)
    print("\n✅ New constraint added successfully")
    print("\n   Valid range: 0-35 days")
    print("   • 0 = No backup")
    print("   • 1-35 = Backup enabled with retention days")
except Exception as e:
    print(f"\n❌ Error adding constraint: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Constraint

# COMMAND ----------

print("\n" + "=" * 100)
print("VERIFYING CONSTRAINT")
print("=" * 100)

query = """
SELECT 
    conname AS constraint_name,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conname = 'chk_lakebase_backup_range'
AND connamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'lakemeter');
"""

result = execute_query(query, fetch=True)

if result and len(result) > 0:
    print("\n✅ Constraint verified:")
    for row in result:
        print(f"\n   Name: {row[0]}")
        print(f"   Definition: {row[1]}")
else:
    print("\n⚠️  Constraint not found!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC 
# MAGIC ✅ **Constraint updated successfully!**
# MAGIC 
# MAGIC **Old constraint:** `lakebase_backup_retention_days >= 1 AND lakebase_backup_retention_days <= 35`  
# MAGIC **New constraint:** `lakebase_backup_retention_days >= 0 AND lakebase_backup_retention_days <= 35`
# MAGIC 
# MAGIC **Valid values:**
# MAGIC - `0` = No backup (backup disabled)
# MAGIC - `1-35` = Backup enabled with retention period
# MAGIC 
# MAGIC **Now you can run Test_14_LAKEBASE!**

