# Databricks notebook source
# MAGIC %md
# MAGIC # Compare line_items Table Structure
# MAGIC 
# MAGIC **Purpose:** Compare column structure between `line_items` and `line_items_backup_20260114`
# MAGIC 
# MAGIC **Tables:**
# MAGIC - `lakemeter.line_items` - Current table
# MAGIC - `lakemeter.line_items_backup_20260114` - Backup table

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
# MAGIC ## 2. Compare Column Structures

# COMMAND ----------

compare_query = """
WITH line_items_cols AS (
    SELECT 
        column_name,
        data_type,
        character_maximum_length,
        is_nullable,
        column_default,
        ordinal_position
    FROM information_schema.columns
    WHERE table_schema = 'lakemeter' 
      AND table_name = 'line_items'
    ORDER BY ordinal_position
),
backup_cols AS (
    SELECT 
        column_name,
        data_type,
        character_maximum_length,
        is_nullable,
        column_default,
        ordinal_position
    FROM information_schema.columns
    WHERE table_schema = 'lakemeter' 
      AND table_name = 'line_items_backup_20260114'
    ORDER BY ordinal_position
)
SELECT 
    COALESCE(li.column_name, b.column_name) as column_name,
    li.ordinal_position as line_items_position,
    b.ordinal_position as backup_position,
    li.data_type as line_items_type,
    b.data_type as backup_type,
    li.is_nullable as line_items_nullable,
    b.is_nullable as backup_nullable,
    CASE 
        WHEN li.column_name IS NULL THEN '❌ Missing in line_items'
        WHEN b.column_name IS NULL THEN '❌ Missing in backup'
        WHEN li.data_type <> b.data_type THEN '⚠️ Type mismatch'
        WHEN li.is_nullable <> b.is_nullable THEN '⚠️ Nullable mismatch'
        ELSE '✅ Match'
    END as status
FROM line_items_cols li
FULL OUTER JOIN backup_cols b ON li.column_name = b.column_name
ORDER BY COALESCE(li.ordinal_position, b.ordinal_position);
"""

conn = get_connection()
df = pd.read_sql(compare_query, conn)
conn.close()

print("=" * 100)
print("COLUMN COMPARISON: line_items vs line_items_backup_20260114")
print("=" * 100)
display(df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Summary Statistics

# COMMAND ----------

# Count mismatches
mismatches = df[df['status'] != '✅ Match']
missing_in_line_items = df[df['status'] == '❌ Missing in line_items']
missing_in_backup = df[df['status'] == '❌ Missing in backup']
type_mismatches = df[df['status'] == '⚠️ Type mismatch']

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total columns compared:           {len(df)}")
print(f"✅ Matching columns:              {len(df[df['status'] == '✅ Match'])}")
print(f"❌ Missing in line_items:         {len(missing_in_line_items)}")
print(f"❌ Missing in backup:             {len(missing_in_backup)}")
print(f"⚠️  Type mismatches:               {len(type_mismatches)}")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Show Mismatches Only

# COMMAND ----------

if len(mismatches) > 0:
    print("=" * 80)
    print("COLUMNS WITH DIFFERENCES")
    print("=" * 80)
    display(mismatches)
    
    if len(missing_in_line_items) > 0:
        print("\n⚠️  Columns missing in line_items (present in backup):")
        for col in missing_in_line_items['column_name']:
            print(f"   - {col}")
    
    if len(missing_in_backup) > 0:
        print("\n⚠️  Columns missing in backup (present in line_items):")
        for col in missing_in_backup['column_name']:
            print(f"   - {col}")
            
    if len(type_mismatches) > 0:
        print("\n⚠️  Columns with type mismatches:")
        for idx, row in type_mismatches.iterrows():
            print(f"   - {row['column_name']}: {row['line_items_type']} vs {row['backup_type']}")
else:
    print("✅ All columns match perfectly!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Column Count Comparison

# COMMAND ----------

count_query = """
SELECT 
    'line_items' as table_name,
    COUNT(*) as column_count
FROM information_schema.columns
WHERE table_schema = 'lakemeter' AND table_name = 'line_items'

UNION ALL

SELECT 
    'line_items_backup_20260114' as table_name,
    COUNT(*) as column_count
FROM information_schema.columns
WHERE table_schema = 'lakemeter' AND table_name = 'line_items_backup_20260114';
"""

conn = get_connection()
count_df = pd.read_sql(count_query, conn)
conn.close()

print("=" * 80)
print("COLUMN COUNT")
print("=" * 80)
display(count_df)
