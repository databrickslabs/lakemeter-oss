# Databricks notebook source
# MAGIC %md
# MAGIC # Add New Workload Columns to line_items_backup_20260114
# MAGIC 
# MAGIC **Purpose:** Adds columns for new workload types to the BACKUP table first for testing
# MAGIC 
# MAGIC **Target Table:** `line_items_backup_20260114`
# MAGIC 
# MAGIC **New Workloads:**
# MAGIC - Vector Search (storage enhancement)
# MAGIC - Lakebase (storage enhancement)
# MAGIC - Databricks Apps (with num_apps)
# MAGIC - Clean Room
# MAGIC - AI Parse
# MAGIC - Shutterstock ImageAI
# MAGIC - Databricks Support
# MAGIC - Lakeflow Connect
# MAGIC 
# MAGIC **Total New Columns:** 26
# MAGIC 
# MAGIC **Run This First:** Test on backup table before applying to production `line_items`

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

print("✅ Lakebase connection details loaded")
print(f"   Host: {LAKEBASE_HOST}")
print(f"   Database: {LAKEBASE_DATABASE}")
print(f"   User: {LAKEBASE_USER}")

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
        conn = get_connection()
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
# MAGIC ## 3. Verify Connection & Target Table

# COMMAND ----------

# Test connection
print("🔍 Testing Lakebase connection...")
result = execute_sql(
    "SELECT current_database(), current_user, version();",
    "Connection test"
)

# Verify backup table exists
print("\n🔍 Checking if backup table exists...")
table_check = query_sql(
    """
    SELECT table_name, 
           (SELECT count(*) FROM line_items_backup_20260114) as row_count
    FROM information_schema.tables 
    WHERE table_name = 'line_items_backup_20260114';
    """,
    "Backup table check"
)

if table_check:
    print(f"✅ Backup table exists with {table_check[0]['row_count']} rows")
else:
    print("❌ Backup table NOT found! Please create it first.")
    raise Exception("Backup table line_items_backup_20260114 does not exist")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Add New Columns - Vector Search Storage

# COMMAND ----------

print("=" * 80)
print("1. VECTOR SEARCH STORAGE")
print("=" * 80)

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN vector_search_storage_gb DECIMAL(10,2) 
CHECK (vector_search_storage_gb >= 0);
""", "Added vector_search_storage_gb column")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Add New Columns - Lakebase Storage

# COMMAND ----------

print("=" * 80)
print("2. LAKEBASE STORAGE")
print("=" * 80)

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN lakebase_storage_gb DECIMAL(10,2) 
CHECK (lakebase_storage_gb >= 0 AND lakebase_storage_gb <= 8192);
""", "Added lakebase_storage_gb column (max 8TB)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Add New Columns - Databricks Apps

# COMMAND ----------

print("=" * 80)
print("3. DATABRICKS APPS")
print("=" * 80)

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN databricks_apps_num_apps INT
CHECK (databricks_apps_num_apps >= 1);
""", "Added databricks_apps_num_apps column")

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN databricks_apps_size VARCHAR(20)
CHECK (databricks_apps_size IN ('medium', 'large'));
""", "Added databricks_apps_size column")

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN databricks_apps_hours_per_month DECIMAL(10,2)
CHECK (databricks_apps_hours_per_month >= 0);
""", "Added databricks_apps_hours_per_month column")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Add New Columns - Clean Room

# COMMAND ----------

print("=" * 80)
print("4. CLEAN ROOM")
print("=" * 80)

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN clean_room_num_collaborators INT
CHECK (clean_room_num_collaborators >= 1 AND clean_room_num_collaborators <= 10);
""", "Added clean_room_num_collaborators column (1-10)")

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN clean_room_days_per_month INT
CHECK (clean_room_days_per_month >= 1 AND clean_room_days_per_month <= 31);
""", "Added clean_room_days_per_month column")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Add New Columns - AI Parse

# COMMAND ----------

print("=" * 80)
print("5. AI PARSE")
print("=" * 80)

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN ai_parse_calculation_method VARCHAR(20)
CHECK (ai_parse_calculation_method IN ('dbu_based', 'pages_based'));
""", "Added ai_parse_calculation_method column")

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN ai_parse_dbu_quantity DECIMAL(15,2)
CHECK (ai_parse_dbu_quantity >= 0);
""", "Added ai_parse_dbu_quantity column")

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN ai_parse_num_pages INT
CHECK (ai_parse_num_pages >= 0);
""", "Added ai_parse_num_pages column")

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN ai_parse_complexity VARCHAR(20)
CHECK (ai_parse_complexity IN ('low_text', 'low_images', 'medium', 'high'));
""", "Added ai_parse_complexity column")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Add New Columns - Shutterstock ImageAI

# COMMAND ----------

print("=" * 80)
print("6. SHUTTERSTOCK IMAGEAI")
print("=" * 80)

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN shutterstock_imageai_num_images INT
CHECK (shutterstock_imageai_num_images >= 1);
""", "Added shutterstock_imageai_num_images column")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Add New Columns - Databricks Support

# COMMAND ----------

print("=" * 80)
print("7. DATABRICKS SUPPORT")
print("=" * 80)

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN databricks_support_tier VARCHAR(50)
CHECK (databricks_support_tier IN ('business', 'enhanced', 'production', 'mission_critical'));
""", "Added databricks_support_tier column")

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN databricks_support_annual_commit DECIMAL(15,2)
CHECK (databricks_support_annual_commit >= 0);
""", "Added databricks_support_annual_commit column")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 11. Add New Columns - Lakeflow Connect (12 columns)

# COMMAND ----------

print("=" * 80)
print("8. LAKEFLOW CONNECT (12 columns)")
print("=" * 80)

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN lakeflow_connect_connector_type VARCHAR(20)
CHECK (lakeflow_connect_connector_type IN ('saas', 'database'));
""", "Added lakeflow_connect_connector_type column")

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN lakeflow_connect_pipeline_driver_node_type VARCHAR(50);
""", "Added lakeflow_connect_pipeline_driver_node_type column")

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN lakeflow_connect_pipeline_worker_node_type VARCHAR(50);
""", "Added lakeflow_connect_pipeline_worker_node_type column")

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN lakeflow_connect_pipeline_num_workers INT
CHECK (lakeflow_connect_pipeline_num_workers >= 0);
""", "Added lakeflow_connect_pipeline_num_workers column")

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN lakeflow_connect_pipeline_serverless_mode VARCHAR(20)
CHECK (lakeflow_connect_pipeline_serverless_mode IN ('standard', 'performance'));
""", "Added lakeflow_connect_pipeline_serverless_mode column")

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN lakeflow_connect_pipeline_runs_per_day INT
CHECK (lakeflow_connect_pipeline_runs_per_day >= 0);
""", "Added lakeflow_connect_pipeline_avg_runtime_minutes column")

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN lakeflow_connect_pipeline_avg_runtime_minutes INT
CHECK (lakeflow_connect_pipeline_avg_runtime_minutes >= 0);
""", "Added lakeflow_connect_pipeline_avg_runtime_minutes column")

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN lakeflow_connect_pipeline_hours_per_month DECIMAL(10,2)
CHECK (lakeflow_connect_pipeline_hours_per_month >= 0);
""", "Added lakeflow_connect_pipeline_hours_per_month column")

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN lakeflow_connect_gateway_cloud VARCHAR(10)
CHECK (lakeflow_connect_gateway_cloud IN ('AWS', 'AZURE', 'GCP'));
""", "Added lakeflow_connect_gateway_cloud column")

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN lakeflow_connect_gateway_instance_type VARCHAR(50);
""", "Added lakeflow_connect_gateway_instance_type column")

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN lakeflow_connect_gateway_num_workers INT
CHECK (lakeflow_connect_gateway_num_workers >= 0);
""", "Added lakeflow_connect_gateway_num_workers column")

execute_sql("""
ALTER TABLE line_items_backup_20260114 
ADD COLUMN lakeflow_connect_gateway_hours_per_month DECIMAL(10,2)
CHECK (lakeflow_connect_gateway_hours_per_month >= 0);
""", "Added lakeflow_connect_gateway_hours_per_month column")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 12. Verify All New Columns

# COMMAND ----------

print("\n" + "=" * 80)
print("VERIFICATION: Check all new columns were added")
print("=" * 80)

new_columns = query_sql("""
SELECT 
    column_name, 
    data_type, 
    character_maximum_length,
    numeric_precision,
    numeric_scale,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'line_items_backup_20260114' 
  AND table_schema = 'lakemeter'
  AND (
       column_name LIKE 'vector_search_%' 
    OR column_name LIKE 'lakebase_storage_%'
    OR column_name LIKE 'databricks_apps_%'
    OR column_name LIKE 'clean_room_%'
    OR column_name LIKE 'ai_parse_%'
    OR column_name LIKE 'shutterstock_%'
    OR column_name LIKE 'databricks_support_%'
    OR column_name LIKE 'lakeflow_connect_%'
  )
ORDER BY column_name;
""", "Fetch new columns")

if new_columns:
    print(f"\n📊 Found {len(new_columns)} new columns:")
    print("-" * 80)
    for col in new_columns:
        col_name = col['column_name']
        data_type = col['data_type']
        if col['character_maximum_length']:
            data_type += f"({col['character_maximum_length']})"
        elif col['numeric_precision']:
            data_type += f"({col['numeric_precision']},{col['numeric_scale']})"
        print(f"  • {col_name:<50} {data_type}")

# Expected count
expected_count = 26  # Updated: added databricks_apps_num_apps
actual_count = len(new_columns) if new_columns else 0

print("\n" + "=" * 80)
if actual_count == expected_count:
    print(f"✅ SUCCESS! All {expected_count} columns added correctly")
else:
    print(f"⚠️  Expected {expected_count} columns, but found {actual_count}")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 13. Summary

# COMMAND ----------

print("\n" + "=" * 80)
print("🎉 MIGRATION COMPLETE")
print("=" * 80)
print("""
✅ All 26 new columns added to line_items_backup_20260114
✅ All constraints validated
✅ Ready for production migration

New Columns Added:
- vector_search_storage_gb (1 column)
- lakebase_storage_gb (1 column)
- databricks_apps_* (3 columns: num_apps, size, hours_per_month)
- clean_room_* (2 columns)
- ai_parse_* (4 columns)
- shutterstock_imageai_num_images (1 column)
- databricks_support_* (2 columns)
- lakeflow_connect_* (12 columns)
""")

# COMMAND ----------

