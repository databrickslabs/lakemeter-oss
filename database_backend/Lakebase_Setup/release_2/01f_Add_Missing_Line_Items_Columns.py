# Databricks notebook source
# MAGIC %md
# MAGIC # Add Missing Columns to line_items Table
# MAGIC 
# MAGIC **Purpose:** Add columns that exist in backup but missing in line_items
# MAGIC 
# MAGIC **Columns to add:**
# MAGIC - `model_servings_number_endpoints` - INTEGER (nullable)
# MAGIC - `databricks_apps_num_apps` - INTEGER (nullable)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Setup

# COMMAND ----------

%pip install psycopg2-binary --quiet
dbutils.library.restartPython()

# COMMAND ----------

# Import Lakebase configuration
%run ../../00_Lakebase_Config

# COMMAND ----------

import psycopg2
from datetime import datetime

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

print("✅ Connection setup complete!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Check Current Structure

# COMMAND ----------

check_query = """
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'lakemeter' 
  AND table_name = 'line_items'
  AND column_name IN ('model_servings_number_endpoints', 'databricks_apps_num_apps');
"""

conn = get_connection()
cur = conn.cursor()
cur.execute(check_query)
existing_cols = cur.fetchall()
cur.close()
conn.close()

if existing_cols:
    print("⚠️  Some columns already exist:")
    for col in existing_cols:
        print(f"   - {col[0]}: {col[1]}, Nullable: {col[2]}")
else:
    print("✅ Neither column exists - ready to add both")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Add model_servings_number_endpoints Column

# COMMAND ----------

add_model_servings_col = """
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS model_servings_number_endpoints INTEGER;
"""

try:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(add_model_servings_col)
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Added column: model_servings_number_endpoints (INTEGER)")
except Exception as e:
    print(f"❌ Error adding model_servings_number_endpoints: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Add databricks_apps_num_apps Column

# COMMAND ----------

add_apps_col = """
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS databricks_apps_num_apps INTEGER;
"""

try:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(add_apps_col)
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Added column: databricks_apps_num_apps (INTEGER)")
except Exception as e:
    print(f"❌ Error adding databricks_apps_num_apps: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Verify Columns Were Added

# COMMAND ----------

verify_query = """
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns
WHERE table_schema = 'lakemeter' 
  AND table_name = 'line_items'
  AND column_name IN ('model_servings_number_endpoints', 'databricks_apps_num_apps')
ORDER BY ordinal_position;
"""

conn = get_connection()
cur = conn.cursor()
cur.execute(verify_query)
results = cur.fetchall()
cur.close()
conn.close()

if results:
    print("=" * 80)
    print("✅ VERIFICATION SUCCESSFUL - Columns Added")
    print("=" * 80)
    for row in results:
        print(f"\nColumn: {row[0]}")
        print(f"  Type:     {row[1]}")
        print(f"  Nullable: {row[2]}")
        print(f"  Default:  {row[3]}")
        print(f"  Position: {row[4]}")
    print("=" * 80)
else:
    print("❌ Columns not found after adding!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Complete!
# MAGIC 
# MAGIC Both columns have been added to the `line_items` table:
# MAGIC - `model_servings_number_endpoints` (INTEGER, nullable)
# MAGIC - `databricks_apps_num_apps` (INTEGER, nullable)
