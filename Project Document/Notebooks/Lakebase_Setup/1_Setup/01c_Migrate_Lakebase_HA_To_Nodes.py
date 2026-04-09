# Databricks notebook source
# MAGIC %md
# MAGIC # Migration: Lakebase HA Boolean → HA Nodes Integer
# MAGIC 
# MAGIC **Change:** Replace `lakebase_ha_enabled` (BOOLEAN) with `lakebase_ha_nodes` (INT 1-3)
# MAGIC 
# MAGIC **Reason:** 
# MAGIC - Pricing is based on number of HA nodes, not just enabled/disabled
# MAGIC - **Total CU = CU per node × number of HA nodes**
# MAGIC - Max 3 nodes supported
# MAGIC 
# MAGIC **Migration Strategy:**
# MAGIC 1. Add new `lakebase_ha_nodes` column (default 1)
# MAGIC 2. Migrate data: TRUE → 2 nodes, FALSE → 1 node
# MAGIC 3. Drop old `lakebase_ha_enabled` column
# MAGIC 4. Add constraint: 1-3 nodes

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
# MAGIC ## Step 1: Add New Column

# COMMAND ----------

print("=" * 100)
print("STEP 1: ADDING lakebase_ha_nodes COLUMN")
print("=" * 100)

try:
    execute_query("""
    ALTER TABLE lakemeter.line_items 
    ADD COLUMN IF NOT EXISTS lakebase_ha_nodes INT DEFAULT 1;
    """)
    print("\n✅ Column lakebase_ha_nodes added successfully")
    print("   Default value: 1 (no HA)")
except Exception as e:
    print(f"\n❌ Error: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Migrate Data

# COMMAND ----------

print("\n" + "=" * 100)
print("STEP 2: MIGRATING DATA FROM lakebase_ha_enabled TO lakebase_ha_nodes")
print("=" * 100)

try:
    # Check if old column exists
    check_column = """
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_schema = 'lakemeter' 
    AND table_name = 'line_items' 
    AND column_name = 'lakebase_ha_enabled';
    """
    result = execute_query(check_column, fetch=True)
    
    if result and len(result) > 0:
        print("\n✅ Old column lakebase_ha_enabled found. Migrating data...")
        
        # Migrate: TRUE → 2 nodes, FALSE → 1 node
        execute_query("""
        UPDATE lakemeter.line_items 
        SET lakebase_ha_nodes = CASE 
            WHEN lakebase_ha_enabled = TRUE THEN 2 
            ELSE 1 
        END
        WHERE workload_type = 'LAKEBASE';
        """)
        
        # Get migration stats
        stats = execute_query("""
        SELECT 
            lakebase_ha_nodes,
            COUNT(*) as count
        FROM lakemeter.line_items
        WHERE workload_type = 'LAKEBASE'
        GROUP BY lakebase_ha_nodes
        ORDER BY lakebase_ha_nodes;
        """, fetch=True)
        
        print("\n✅ Data migrated successfully:")
        for row in stats:
            nodes = row[0]
            count = row[1]
            label = "No HA" if nodes == 1 else f"HA ({nodes} nodes)"
            print(f"   • {nodes} node(s) ({label}): {count} line items")
    else:
        print("\n⚠️  Old column lakebase_ha_enabled not found")
        print("   This is OK if it was already dropped or never existed")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Drop Old Column

# COMMAND ----------

print("\n" + "=" * 100)
print("STEP 3: DROPPING OLD lakebase_ha_enabled COLUMN")
print("=" * 100)

try:
    execute_query("""
    ALTER TABLE lakemeter.line_items 
    DROP COLUMN IF EXISTS lakebase_ha_enabled;
    """)
    print("\n✅ Old column lakebase_ha_enabled dropped successfully")
except Exception as e:
    print(f"\n⚠️  Warning: {e}")
    print("   (This is OK if column doesn't exist)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Add Constraint

# COMMAND ----------

print("\n" + "=" * 100)
print("STEP 4: ADDING CONSTRAINT (1-3 nodes)")
print("=" * 100)

try:
    # Drop if exists
    execute_query("""
    ALTER TABLE lakemeter.line_items 
    DROP CONSTRAINT IF EXISTS chk_lakebase_ha_nodes_range;
    """)
    
    # Add new constraint
    execute_query("""
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT chk_lakebase_ha_nodes_range 
    CHECK (lakebase_ha_nodes >= 1 AND lakebase_ha_nodes <= 3);
    """)
    print("\n✅ Constraint added successfully")
    print("\n   Valid range: 1-3 nodes")
    print("   • 1 = No HA (single node)")
    print("   • 2 = HA with 2 nodes")
    print("   • 3 = HA with 3 nodes (maximum)")
except Exception as e:
    print(f"\n❌ Error adding constraint: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Verify Migration

# COMMAND ----------

print("\n" + "=" * 100)
print("STEP 5: VERIFYING MIGRATION")
print("=" * 100)

# Check column exists
check_column = """
SELECT column_name, data_type, column_default
FROM information_schema.columns 
WHERE table_schema = 'lakemeter' 
AND table_name = 'line_items' 
AND column_name = 'lakebase_ha_nodes';
"""
result = execute_query(check_column, fetch=True)

if result and len(result) > 0:
    print("\n✅ Column verified:")
    for row in result:
        print(f"   • Name: {row[0]}")
        print(f"   • Type: {row[1]}")
        print(f"   • Default: {row[2]}")
else:
    print("\n❌ Column not found!")

# Check constraint
check_constraint = """
SELECT 
    conname AS constraint_name,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conname = 'chk_lakebase_ha_nodes_range'
AND connamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'lakemeter');
"""
result = execute_query(check_constraint, fetch=True)

if result and len(result) > 0:
    print("\n✅ Constraint verified:")
    for row in result:
        print(f"   • Name: {row[0]}")
        print(f"   • Definition: {row[1]}")
else:
    print("\n⚠️  Constraint not found")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC 
# MAGIC ✅ **Migration completed successfully!**
# MAGIC 
# MAGIC **Changes:**
# MAGIC - ❌ Removed: `lakebase_ha_enabled` (BOOLEAN)
# MAGIC - ✅ Added: `lakebase_ha_nodes` (INT, 1-3)
# MAGIC 
# MAGIC **Data migration:**
# MAGIC - `FALSE` → `1` (no HA, single node)
# MAGIC - `TRUE` → `2` (HA enabled, 2 nodes)
# MAGIC 
# MAGIC **Pricing calculation:**
# MAGIC - **Total CU = lakebase_cu × lakebase_ha_nodes**
# MAGIC - Example: 2 CU, 3 nodes = 6 CU total
# MAGIC 
# MAGIC **Valid values:**
# MAGIC - `1` = No HA (single node)
# MAGIC - `2` = HA with 2 nodes
# MAGIC - `3` = HA with 3 nodes (maximum)
# MAGIC 
# MAGIC **Now you can run Test_14_LAKEBASE!**

