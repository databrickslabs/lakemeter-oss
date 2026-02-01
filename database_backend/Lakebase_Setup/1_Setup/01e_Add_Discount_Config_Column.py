# Databricks notebook source
# MAGIC %md
# MAGIC # Add discount_config Column to estimates Table
# MAGIC 
# MAGIC **Purpose:** Add missing `discount_config` JSONB column to `lakemeter.estimates` table
# MAGIC 
# MAGIC **Why:** Column exists in `estimates_backup_20260119` but missing in main `estimates` table
# MAGIC 
# MAGIC **Column Details:**
# MAGIC - Name: `discount_config`
# MAGIC - Type: `JSONB`
# MAGIC - Nullable: `YES`

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Install Dependencies & Import Config

# COMMAND ----------

%pip install psycopg2-binary --quiet
dbutils.library.restartPython()

# COMMAND ----------

# Import Lakebase configuration
%run ../00_Lakebase_Config

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

# Check if column already exists
check_query = """
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'lakemeter' 
  AND table_name = 'estimates'
  AND column_name = 'discount_config';
"""

conn = get_connection()
cur = conn.cursor()
cur.execute(check_query)
result = cur.fetchone()
cur.close()
conn.close()

if result:
    print("⚠️  Column 'discount_config' already exists!")
    print(f"   Type: {result[1]}, Nullable: {result[2]}")
else:
    print("✅ Column 'discount_config' does not exist - ready to add")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Add discount_config Column

# COMMAND ----------

add_column_sql = """
ALTER TABLE lakemeter.estimates 
ADD COLUMN IF NOT EXISTS discount_config JSONB;
"""

try:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(add_column_sql)
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Column 'discount_config' added successfully!")
except Exception as e:
    print(f"❌ Error adding column: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Verify Column Was Added

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
  AND table_name = 'estimates'
  AND column_name = 'discount_config';
"""

conn = get_connection()
cur = conn.cursor()
cur.execute(verify_query)
result = cur.fetchone()

if result:
    print("=" * 80)
    print("✅ VERIFICATION SUCCESSFUL")
    print("=" * 80)
    print(f"Column Name:     {result[0]}")
    print(f"Data Type:       {result[1]}")
    print(f"Nullable:        {result[2]}")
    print(f"Default:         {result[3]}")
    print(f"Position:        {result[4]}")
    print("=" * 80)
else:
    print("❌ Column not found after adding!")

cur.close()
conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Check Backup Data

# COMMAND ----------

# Check if backup has any discount_config data
backup_check_query = """
SELECT 
    COUNT(*) as total_records,
    COUNT(discount_config) as records_with_discount_config,
    COUNT(*) - COUNT(discount_config) as records_without_discount_config
FROM lakemeter.estimates_backup_20260119;
"""

conn = get_connection()
cur = conn.cursor()
cur.execute(backup_check_query)
result = cur.fetchone()
cur.close()
conn.close()

print("=" * 80)
print("BACKUP DATA ANALYSIS")
print("=" * 80)
print(f"Total records in backup:           {result[0]:,}")
print(f"Records with discount_config:      {result[1]:,}")
print(f"Records without discount_config:   {result[2]:,}")
print("=" * 80)

if result[1] > 0:
    print(f"\n⚠️  Found {result[1]:,} records with discount_config data in backup")
    print("   Consider migrating this data to the main table")
else:
    print("\n✅ No discount_config data in backup - no migration needed")

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Complete!
# MAGIC 
# MAGIC The `discount_config` column has been added to the `estimates` table.
