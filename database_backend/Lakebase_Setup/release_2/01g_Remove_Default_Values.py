# Databricks notebook source
# MAGIC %md
# MAGIC # Remove Default Values from line_items Columns
# MAGIC 
# MAGIC **Purpose:** Remove default values from specific columns in `line_items` table
# MAGIC 
# MAGIC **Columns to update:**
# MAGIC - `serverless_enabled` (currently: false)
# MAGIC - `photon_enabled` (currently: false)
# MAGIC - `dbsql_num_clusters` (currently: 1)
# MAGIC - `dbsql_vm_pricing_tier` (currently: 'on_demand')
# MAGIC - `dbsql_vm_payment_option` (currently: 'NA')
# MAGIC - `lakebase_ha_nodes` (currently: 1)
# MAGIC - `lakebase_backup_retention_days` (currently: 7)
# MAGIC - `days_per_month` (currently: 30)
# MAGIC - `driver_payment_option` (currently: 'NA')
# MAGIC - `worker_payment_option` (currently: 'NA')

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Setup

# COMMAND ----------

%pip install psycopg2-binary pandas --quiet
dbutils.library.restartPython()

# COMMAND ----------

# Import Lakebase configuration
%run ../../00_Lakebase_Config

# COMMAND ----------

import psycopg2
import pandas as pd

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
# MAGIC ## 2. Check Current Default Values

# COMMAND ----------

check_query = """
SELECT 
    column_name,
    data_type,
    column_default
FROM information_schema.columns
WHERE table_schema = 'lakemeter' 
  AND table_name = 'line_items'
  AND column_name IN (
    'serverless_enabled',
    'photon_enabled',
    'dbsql_num_clusters',
    'dbsql_vm_pricing_tier',
    'dbsql_vm_payment_option',
    'lakebase_ha_nodes',
    'lakebase_backup_retention_days',
    'days_per_month',
    'driver_payment_option',
    'worker_payment_option'
  )
ORDER BY column_name;
"""

conn = get_connection()
df_before = pd.read_sql(check_query, conn)
conn.close()

print("=" * 80)
print("CURRENT DEFAULT VALUES")
print("=" * 80)
display(df_before)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Remove Default Values

# COMMAND ----------

columns_to_update = [
    'serverless_enabled',
    'photon_enabled',
    'dbsql_num_clusters',
    'dbsql_vm_pricing_tier',
    'dbsql_vm_payment_option',
    'lakebase_ha_nodes',
    'lakebase_backup_retention_days',
    'days_per_month',
    'driver_payment_option',
    'worker_payment_option'
]

print("=" * 80)
print("REMOVING DEFAULT VALUES")
print("=" * 80)

conn = get_connection()
cur = conn.cursor()

for column in columns_to_update:
    try:
        drop_default_sql = f"""
        ALTER TABLE lakemeter.line_items 
        ALTER COLUMN {column} DROP DEFAULT;
        """
        cur.execute(drop_default_sql)
        conn.commit()
        print(f"✅ Removed default from: {column}")
    except Exception as e:
        print(f"❌ Error removing default from {column}: {e}")
        conn.rollback()

cur.close()
conn.close()

print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Verify Defaults Were Removed

# COMMAND ----------

conn = get_connection()
df_after = pd.read_sql(check_query, conn)
conn.close()

print("=" * 80)
print("AFTER REMOVING DEFAULTS")
print("=" * 80)
display(df_after)

# Check if any still have defaults
still_has_defaults = df_after[df_after['column_default'].notna()]

if len(still_has_defaults) > 0:
    print("\n⚠️  Some columns still have defaults:")
    display(still_has_defaults)
else:
    print("\n✅ All default values successfully removed!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Compare Before and After

# COMMAND ----------

print("=" * 80)
print("BEFORE vs AFTER COMPARISON")
print("=" * 80)

comparison = df_before.merge(
    df_after,
    on='column_name',
    suffixes=('_before', '_after')
)

display(comparison[['column_name', 'column_default_before', 'column_default_after']])

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Complete!
# MAGIC 
# MAGIC All 10 columns now have no default values.
# MAGIC New rows will have NULL for these columns unless explicitly specified.
