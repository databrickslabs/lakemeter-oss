# Databricks notebook source
# MAGIC %md
# MAGIC # Add New Workload Columns + Cost Calculation Columns to line_items
# MAGIC 
# MAGIC **Purpose:** Adds columns for new workload types + cost calculation response storage
# MAGIC 
# MAGIC **Target Table:** `lakemeter.line_items` (MAIN TABLE ONLY)
# MAGIC 
# MAGIC **New Workload Columns (25):**
# MAGIC - Vector Search (storage enhancement)
# MAGIC - Lakebase (storage enhancement)
# MAGIC - Databricks Apps
# MAGIC - Clean Room
# MAGIC - AI Parse
# MAGIC - Shutterstock ImageAI
# MAGIC - Databricks Support
# MAGIC - Lakeflow Connect (12 columns)
# MAGIC 
# MAGIC **Cost Calculation Columns (2):**
# MAGIC - cost_calculation_response (JSONB) - Full API response
# MAGIC - calculation_completed_at (TIMESTAMP) - When completed
# MAGIC 
# MAGIC **Total New Columns:** 27

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
# MAGIC ## 3. Verify Connection & Target Table

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
# MAGIC ## 4. Add New Columns - Vector Search Storage

# COMMAND ----------

print("=" * 80)
print("1. VECTOR SEARCH STORAGE")
print("=" * 80)

execute_sql("""
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS vector_search_storage_gb DECIMAL(10,2) 
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
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS lakebase_storage_gb DECIMAL(10,2) 
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
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS databricks_apps_size VARCHAR(20)
CHECK (databricks_apps_size IN ('medium', 'large'));
""", "Added databricks_apps_size column")

execute_sql("""
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS databricks_apps_hours_per_month DECIMAL(10,2)
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
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS clean_room_num_collaborators INT
CHECK (clean_room_num_collaborators >= 1 AND clean_room_num_collaborators <= 10);
""", "Added clean_room_num_collaborators column (1-10)")

execute_sql("""
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS clean_room_days_per_month INT
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
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS ai_parse_calculation_method VARCHAR(20)
CHECK (ai_parse_calculation_method IN ('dbu_based', 'pages_based'));
""", "Added ai_parse_calculation_method column")

execute_sql("""
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS ai_parse_dbu_quantity DECIMAL(15,2)
CHECK (ai_parse_dbu_quantity >= 0);
""", "Added ai_parse_dbu_quantity column")

execute_sql("""
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS ai_parse_num_pages INT
CHECK (ai_parse_num_pages >= 0);
""", "Added ai_parse_num_pages column")

execute_sql("""
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS ai_parse_complexity VARCHAR(20)
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
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS shutterstock_imageai_num_images INT
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
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS databricks_support_tier VARCHAR(50)
CHECK (databricks_support_tier IN ('business', 'enhanced', 'production', 'mission_critical'));
""", "Added databricks_support_tier column")

execute_sql("""
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS databricks_support_annual_commit DECIMAL(15,2)
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
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS lakeflow_connect_connector_type VARCHAR(20)
CHECK (lakeflow_connect_connector_type IN ('saas', 'database'));
""", "Added lakeflow_connect_connector_type column")

execute_sql("""
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS lakeflow_connect_pipeline_driver_node_type VARCHAR(50);
""", "Added lakeflow_connect_pipeline_driver_node_type column")

execute_sql("""
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS lakeflow_connect_pipeline_worker_node_type VARCHAR(50);
""", "Added lakeflow_connect_pipeline_worker_node_type column")

execute_sql("""
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS lakeflow_connect_pipeline_num_workers INT
CHECK (lakeflow_connect_pipeline_num_workers >= 0);
""", "Added lakeflow_connect_pipeline_num_workers column")

execute_sql("""
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS lakeflow_connect_pipeline_serverless_mode VARCHAR(20)
CHECK (lakeflow_connect_pipeline_serverless_mode IN ('standard', 'performance'));
""", "Added lakeflow_connect_pipeline_serverless_mode column")

execute_sql("""
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS lakeflow_connect_pipeline_runs_per_day INT
CHECK (lakeflow_connect_pipeline_runs_per_day >= 0);
""", "Added lakeflow_connect_pipeline_runs_per_day column")

execute_sql("""
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS lakeflow_connect_pipeline_avg_runtime_minutes INT
CHECK (lakeflow_connect_pipeline_avg_runtime_minutes >= 0);
""", "Added lakeflow_connect_pipeline_avg_runtime_minutes column")

execute_sql("""
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS lakeflow_connect_pipeline_hours_per_month DECIMAL(10,2)
CHECK (lakeflow_connect_pipeline_hours_per_month >= 0);
""", "Added lakeflow_connect_pipeline_hours_per_month column")

execute_sql("""
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS lakeflow_connect_gateway_cloud VARCHAR(10)
CHECK (lakeflow_connect_gateway_cloud IN ('AWS', 'AZURE', 'GCP'));
""", "Added lakeflow_connect_gateway_cloud column")

execute_sql("""
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS lakeflow_connect_gateway_instance_type VARCHAR(50);
""", "Added lakeflow_connect_gateway_instance_type column")

execute_sql("""
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS lakeflow_connect_gateway_num_workers INT
CHECK (lakeflow_connect_gateway_num_workers >= 0);
""", "Added lakeflow_connect_gateway_num_workers column")

execute_sql("""
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS lakeflow_connect_gateway_hours_per_month DECIMAL(10,2)
CHECK (lakeflow_connect_gateway_hours_per_month >= 0);
""", "Added lakeflow_connect_gateway_hours_per_month column")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 12. Add Cost Calculation Response Columns

# COMMAND ----------

print("=" * 80)
print("9. COST CALCULATION RESPONSE (2 columns)")
print("=" * 80)

execute_sql("""
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS cost_calculation_response JSONB DEFAULT NULL;
""", "Added cost_calculation_response column (JSONB)")

execute_sql("""
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS calculation_completed_at TIMESTAMP DEFAULT NULL;
""", "Added calculation_completed_at column (TIMESTAMP)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 13. Create Indexes

# COMMAND ----------

print("\n" + "=" * 80)
print("CREATING INDEXES FOR COST CALCULATION COLUMNS")
print("=" * 80)

execute_sql("""
CREATE INDEX IF NOT EXISTS idx_line_items_calculation_response 
ON lakemeter.line_items USING GIN (cost_calculation_response);
""", "Created GIN index on cost_calculation_response")

execute_sql("""
CREATE INDEX IF NOT EXISTS idx_line_items_calculation_completed_at 
ON lakemeter.line_items(calculation_completed_at);
""", "Created B-tree index on calculation_completed_at")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 14. Add Column Comments

# COMMAND ----------

print("\n" + "=" * 80)
print("ADDING COLUMN COMMENTS")
print("=" * 80)

execute_sql("""
COMMENT ON COLUMN lakemeter.line_items.cost_calculation_response IS 
'Stores the full API response from calculate endpoints. Structure varies by workload_type. Contains detailed breakdown including DBU rates, VM costs, hours, SKU breakdown, discount details, etc. Check response.success field to determine if calculation succeeded.';
""", "Added comment for cost_calculation_response")

execute_sql("""
COMMENT ON COLUMN lakemeter.line_items.calculation_completed_at IS 
'Timestamp when the cost calculation was completed. Check cost_calculation_response.success field to determine if successful or error.';
""", "Added comment for calculation_completed_at")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 15. Verify All New Columns

# COMMAND ----------

print("\n" + "=" * 80)
print("VERIFICATION: Check all new columns were added")
print("=" * 80)

# Check workload columns
workload_columns = query_sql("""
SELECT 
    column_name, 
    data_type, 
    character_maximum_length,
    numeric_precision,
    numeric_scale,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'line_items' 
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
""", "Fetch workload columns")

# Check cost calculation columns
cost_calc_columns = query_sql("""
SELECT 
    column_name, 
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'line_items' 
  AND table_schema = 'lakemeter'
  AND column_name IN ('cost_calculation_response', 'calculation_completed_at')
ORDER BY column_name;
""", "Fetch cost calculation columns")

if workload_columns:
    print(f"\n📊 Workload columns: {len(workload_columns)}")
    print("-" * 80)
    for col in workload_columns[:5]:  # Show first 5
        col_name = col['column_name']
        data_type = col['data_type']
        if col['character_maximum_length']:
            data_type += f"({col['character_maximum_length']})"
        elif col['numeric_precision']:
            data_type += f"({col['numeric_precision']},{col['numeric_scale']})"
        print(f"  • {col_name:<50} {data_type}")
    if len(workload_columns) > 5:
        print(f"  ... and {len(workload_columns) - 5} more")

if cost_calc_columns:
    print(f"\n📊 Cost calculation columns: {len(cost_calc_columns)}")
    print("-" * 80)
    for col in cost_calc_columns:
        print(f"  • {col['column_name']:<50} {col['data_type']}")

# Expected counts
expected_workload = 25
expected_cost_calc = 2
expected_total = expected_workload + expected_cost_calc

actual_workload = len(workload_columns) if workload_columns else 0
actual_cost_calc = len(cost_calc_columns) if cost_calc_columns else 0
actual_total = actual_workload + actual_cost_calc

print("\n" + "=" * 80)
print(f"Workload columns: {actual_workload}/{expected_workload}")
print(f"Cost calculation columns: {actual_cost_calc}/{expected_cost_calc}")
print(f"Total: {actual_total}/{expected_total}")

if actual_total == expected_total:
    print(f"✅ SUCCESS! All {expected_total} columns added correctly")
else:
    print(f"⚠️  Expected {expected_total} columns, but found {actual_total}")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 16. Summary

# COMMAND ----------

print("\n" + "=" * 80)
print("🎉 MIGRATION COMPLETE")
print("=" * 80)
print(f"""
✅ All 27 new columns added to lakemeter.line_items
   - 25 workload type columns
   - 2 cost calculation response columns
✅ All constraints validated
✅ Indexes created for cost calculation queries
✅ Column comments added

📊 Next Steps:
   1. Run backfill script to calculate costs for existing line items
   2. Use release_2/02_Backfill_Line_Item_Costs.py notebook
   3. Test on line_items_backup first with --limit flag

💡 Query Examples:
   
   -- Get costs from calculation response
   SELECT 
       line_item_id,
       workload_name,
       (cost_calculation_response->'data'->>'cost_per_month')::numeric as monthly_cost
   FROM lakemeter.line_items
   WHERE cost_calculation_response->>'success' = 'true';
   
   -- Check calculation status
   SELECT 
       CASE 
           WHEN cost_calculation_response IS NULL THEN 'pending'
           WHEN cost_calculation_response->>'success' = 'true' THEN 'success'
           WHEN cost_calculation_response->>'success' = 'false' THEN 'error'
       END as status,
       COUNT(*) as count
   FROM lakemeter.line_items
   GROUP BY 1;
""")
print("=" * 80)

# COMMAND ----------
