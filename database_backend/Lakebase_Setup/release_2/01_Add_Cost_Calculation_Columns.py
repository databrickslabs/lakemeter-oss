# Databricks notebook source
# MAGIC %md
# MAGIC # Add Cost Calculation Response Columns to Line Items
# MAGIC
# MAGIC **Purpose:** Store full API calculation responses for each line item
# MAGIC
# MAGIC **New Columns:**
# MAGIC - `cost_calculation_response` (JSONB): Full API response with cost breakdown
# MAGIC - `calculation_completed_at` (TIMESTAMP): When calculation finished
# MAGIC
# MAGIC **Tables Updated:**
# MAGIC - `lakemeter.line_items` (main table)
# MAGIC - `lakemeter.line_items_backup` (backup table)
# MAGIC - `lakemeter.estimates_backup` (if exists - no changes needed)
# MAGIC
# MAGIC **Response Structure:**
# MAGIC ```json
# MAGIC {
# MAGIC   "success": true/false,
# MAGIC   "data": {
# MAGIC     "cost_per_month": 5000.00,
# MAGIC     "dbu_per_month": 1000,
# MAGIC     "vm_costs": {...},
# MAGIC     "sku_breakdown": [...],
# MAGIC     "discount_summary": {...}
# MAGIC   },
# MAGIC   "error": {  // Only if success=false
# MAGIC     "message": "...",
# MAGIC     "code": "..."
# MAGIC   }
# MAGIC }
# MAGIC ```

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
        print(f"Error: {e}")
        raise
    finally:
        conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Check Existing Columns

# COMMAND ----------

print("=" * 80)
print("CHECKING EXISTING COLUMNS")
print("=" * 80)

check_sql = """
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'lakemeter'
  AND table_name IN ('line_items', 'line_items_backup')
  AND column_name IN ('cost_calculation_response', 'calculation_completed_at')
ORDER BY table_name, ordinal_position;
"""

try:
    results = execute_query(check_sql, fetch=True)
    if results:
        print(f"\n✅ Found {len(results)} existing columns:")
        for row in results:
            print(f"   {row[0]}.{row[1]} ({row[2]}) - nullable: {row[3]}")
    else:
        print("\n📝 No existing columns found - will create new ones")
except Exception as e:
    print(f"\n⚠️  Could not check: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Add Columns to Main Table

# COMMAND ----------

print("\n" + "=" * 80)
print("ADDING COLUMNS TO line_items")
print("=" * 80)

add_columns_main = """
-- Add columns to main table
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS cost_calculation_response JSONB DEFAULT NULL,
ADD COLUMN IF NOT EXISTS calculation_completed_at TIMESTAMP DEFAULT NULL;
"""

try:
    execute_query(add_columns_main)
    print("✅ Columns added to lakemeter.line_items")
except Exception as e:
    print(f"❌ Error: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Add Columns to Backup Table

# COMMAND ----------

print("\n" + "=" * 80)
print("ADDING COLUMNS TO line_items_backup")
print("=" * 80)

add_columns_backup = """
-- Add columns to backup table
ALTER TABLE lakemeter.line_items_backup 
ADD COLUMN IF NOT EXISTS cost_calculation_response JSONB DEFAULT NULL,
ADD COLUMN IF NOT EXISTS calculation_completed_at TIMESTAMP DEFAULT NULL;
"""

try:
    execute_query(add_columns_backup)
    print("✅ Columns added to lakemeter.line_items_backup")
except Exception as e:
    print(f"❌ Error: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Create Indexes for Performance

# COMMAND ----------

print("\n" + "=" * 80)
print("CREATING INDEXES")
print("=" * 80)

create_indexes = """
-- Add indexes to main table
CREATE INDEX IF NOT EXISTS idx_line_items_calculation_response 
ON lakemeter.line_items USING GIN (cost_calculation_response);

CREATE INDEX IF NOT EXISTS idx_line_items_calculation_completed_at 
ON lakemeter.line_items(calculation_completed_at);

-- Add indexes to backup table
CREATE INDEX IF NOT EXISTS idx_line_items_backup_calculation_response 
ON lakemeter.line_items_backup USING GIN (cost_calculation_response);

CREATE INDEX IF NOT EXISTS idx_line_items_backup_calculation_completed_at 
ON lakemeter.line_items_backup(calculation_completed_at);
"""

try:
    execute_query(create_indexes)
    print("✅ Indexes created")
except Exception as e:
    print(f"❌ Error: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Add Column Comments

# COMMAND ----------

print("\n" + "=" * 80)
print("ADDING COLUMN COMMENTS")
print("=" * 80)

add_comments = """
-- Add comments
COMMENT ON COLUMN lakemeter.line_items.cost_calculation_response IS 
'Stores the full API response from calculate endpoints. Structure varies by workload_type. Contains detailed breakdown including DBU rates, VM costs, hours, SKU breakdown, discount details, etc. Check response.success field to determine if calculation succeeded.';

COMMENT ON COLUMN lakemeter.line_items.calculation_completed_at IS 
'Timestamp when the cost calculation was completed. Check cost_calculation_response.success field to determine if successful or error.';

COMMENT ON COLUMN lakemeter.line_items_backup.cost_calculation_response IS 
'Stores the full API response from calculate endpoints. Structure varies by workload_type. Contains detailed breakdown including DBU rates, VM costs, hours, SKU breakdown, discount details, etc. Check response.success field to determine if calculation succeeded.';

COMMENT ON COLUMN lakemeter.line_items_backup.calculation_completed_at IS 
'Timestamp when the cost calculation was completed. Check cost_calculation_response.success field to determine if successful or error.';
"""

try:
    execute_query(add_comments)
    print("✅ Comments added")
except Exception as e:
    print(f"❌ Error: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Verify Installation

# COMMAND ----------

print("\n" + "=" * 80)
print("VERIFYING INSTALLATION")
print("=" * 80)

# Check columns
print("\n📊 Checking columns...")
verify_columns = """
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'lakemeter'
  AND table_name IN ('line_items', 'line_items_backup')
  AND column_name IN ('cost_calculation_response', 'calculation_completed_at')
ORDER BY table_name, ordinal_position;
"""

results = execute_query(verify_columns, fetch=True)
if results:
    print(f"✅ Found {len(results)} columns:")
    for row in results:
        print(f"   • {row[0]}.{row[1]} ({row[2]})")
else:
    print("❌ No columns found!")

# Check indexes
print("\n📊 Checking indexes...")
verify_indexes = """
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'lakemeter'
  AND tablename IN ('line_items', 'line_items_backup')
  AND indexname LIKE '%calculation%'
ORDER BY tablename, indexname;
"""

results = execute_query(verify_indexes, fetch=True)
if results:
    print(f"✅ Found {len(results)} indexes:")
    for row in results:
        print(f"   • {row[2]} on {row[1]}")
else:
    print("⚠️  No indexes found")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("\n" + "=" * 80)
print("✅ INSTALLATION COMPLETE")
print("=" * 80)

print("\n📋 Columns added:")
print("   • cost_calculation_response (JSONB)")
print("   • calculation_completed_at (TIMESTAMP)")

print("\n🗂️  Tables updated:")
print("   • lakemeter.line_items")
print("   • lakemeter.line_items_backup")

print("\n📇 Indexes created:")
print("   • GIN index on cost_calculation_response (for JSONB queries)")
print("   • B-tree index on calculation_completed_at")

print("\n🎯 Next steps:")
print("   1. Run backfill script to calculate costs for existing line items")
print("   2. Use release_2/02_Backfill_Line_Item_Costs.py notebook")
print("   3. Test on line_items_backup first with --limit flag")

print("\n💡 Query examples:")
print("""
-- Get successful calculations
SELECT 
    line_item_id,
    workload_name,
    (cost_calculation_response->'data'->>'cost_per_month')::numeric as monthly_cost
FROM lakemeter.line_items
WHERE cost_calculation_response->>'success' = 'true'
ORDER BY monthly_cost DESC;

-- Check for errors
SELECT 
    line_item_id,
    workload_name,
    cost_calculation_response->'error'->>'message' as error_message
FROM lakemeter.line_items
WHERE cost_calculation_response->>'success' = 'false';

-- Sum costs by estimate
SELECT 
    e.estimate_name,
    SUM((li.cost_calculation_response->'data'->>'cost_per_month')::numeric) as total_cost
FROM lakemeter.estimates e
JOIN lakemeter.line_items li ON e.estimate_id = li.estimate_id
WHERE li.cost_calculation_response->>'success' = 'true'
GROUP BY e.estimate_id, e.estimate_name;
""")

print("\n" + "=" * 80)
