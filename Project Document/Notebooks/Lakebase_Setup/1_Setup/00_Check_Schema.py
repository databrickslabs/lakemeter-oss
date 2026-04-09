# Databricks notebook source
# MAGIC %md
# MAGIC # Check Current line_items Schema
# MAGIC 
# MAGIC This notebook checks which columns currently exist in the line_items table.

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2

conn = get_lakebase_connection()
cur = conn.cursor()

# Check what columns exist in line_items
cur.execute("""
    SELECT column_name, data_type, character_maximum_length
    FROM information_schema.columns 
    WHERE table_schema = 'lakemeter' 
    AND table_name = 'line_items'
    ORDER BY ordinal_position;
""")

print("=" * 80)
print("CURRENT COLUMNS IN line_items TABLE:")
print("=" * 80)

columns = cur.fetchall()
for col in columns:
    print(f"  • {col[0]:<40} {col[1]:<20} {col[2] if col[2] else ''}")

print(f"\n✅ Total columns: {len(columns)}")

# Check specifically for fmapi_provisioned_type
print("\n" + "=" * 80)
print("CHECKING FOR fmapi_provisioned_type:")
print("=" * 80)

fmapi_prov_type = [c for c in columns if c[0] == 'fmapi_provisioned_type']
if fmapi_prov_type:
    print("✅ fmapi_provisioned_type EXISTS!")
    print(f"   Type: {fmapi_prov_type[0][1]}")
    print(f"   Max Length: {fmapi_prov_type[0][2]}")
else:
    print("❌ fmapi_provisioned_type DOES NOT EXIST!")
    print("\n🔧 This means 01_Create_Tables did not execute successfully.")
    print("   You need to run 01_Create_Tables again.")

conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Expected Result
# MAGIC 
# MAGIC If `01_Create_Tables` was executed successfully, you should see:
# MAGIC - ✅ fmapi_provisioned_type EXISTS!
# MAGIC - Type: character varying
# MAGIC - Max Length: 50
# MAGIC 
# MAGIC If you see "DOES NOT EXIST", you need to:
# MAGIC 1. Go back to `01_Create_Tables`
# MAGIC 2. Run ALL cells (don't skip any)
# MAGIC 3. Check for any error messages
# MAGIC 4. Come back here and verify again

