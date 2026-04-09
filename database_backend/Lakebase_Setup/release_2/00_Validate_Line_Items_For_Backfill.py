# Databricks notebook source
# MAGIC %md
# MAGIC # Validate Line Items for Cost Calculation Backfill
# MAGIC
# MAGIC **Purpose:** Validate that all line items can be properly mapped to API endpoints
# MAGIC
# MAGIC **What it checks:**
# MAGIC 1. ✅ Line items can be joined with estimates table (cloud, region, tier)
# MAGIC 2. ✅ Each workload type can be mapped to correct API endpoint
# MAGIC 3. ✅ Required fields are present for each workload type
# MAGIC 4. ✅ Summary of validation results
# MAGIC
# MAGIC **IMPORTANT:** This notebook does NOT modify any data or call APIs
# MAGIC
# MAGIC **Usage:**
# MAGIC - Set `TABLE_TO_VALIDATE` widget: "main" or "backup"
# MAGIC - Run to see validation report

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration Widgets

# COMMAND ----------

dbutils.widgets.dropdown("TABLE_TO_VALIDATE", "line_items_backup_20260114", 
                         ["line_items", "line_items_backup_20260114"], 
                         "1. Table to Validate")

# Get widget values
TABLE_NAME = dbutils.widgets.get("TABLE_TO_VALIDATE")

# Database and schema configuration
DB_NAME = "lakemeter_pricing"
SCHEMA_NAME = "lakemeter"
FULL_TABLE_NAME = f"{SCHEMA_NAME}.{TABLE_NAME}"

# Determine which estimates table to use
if TABLE_NAME == "line_items_backup_20260114":
    ESTIMATES_TABLE = f"{SCHEMA_NAME}.estimates_backup_20260119"
else:
    ESTIMATES_TABLE = f"{SCHEMA_NAME}.estimates"

print("=" * 80)
print("VALIDATION CONFIGURATION")
print("=" * 80)
print(f"Database: {DB_NAME}")
print(f"Schema: {SCHEMA_NAME}")
print(f"Line Items Table: {FULL_TABLE_NAME}")
print(f"Estimates Table: {ESTIMATES_TABLE}")
print("\n⚠️ NOTE: The following workload types will be EXCLUDED from backfill:")
print("   - VECTOR_SEARCH (schema needs migration)")
print("   - MODEL_SERVING (pending review)")
print("   - FMAPI_PROPRIETARY (schema needs migration)")
print("=" * 80)

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
from typing import Dict, Any, List, Optional

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
                return [dict(zip(columns, row)) for row in results]
            else:
                return True
    finally:
        conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 0: Check Available Columns in Tables

# COMMAND ----------

print("\n" + "=" * 80)
print("STEP 0: CHECKING AVAILABLE COLUMNS IN TABLES")
print("=" * 80)

# Check which columns exist in line_items table
columns_sql = f"""
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = '{SCHEMA_NAME}'
  AND table_name = '{TABLE_NAME}'
ORDER BY ordinal_position;
"""

available_columns = execute_query(columns_sql, fetch=True)
column_names = [col['column_name'] for col in available_columns]

print(f"\n📊 Line Items table has {len(column_names)} columns")
print("\nChecking for workload-specific columns:")

# Check for Vector Search columns
has_vector_capacity = 'vector_capacity_millions' in column_names
has_vector_mode = 'vector_search_mode' in column_names
print(f"  Vector Search: vector_capacity_millions={'✅' if has_vector_capacity else '❌'}, vector_search_mode={'✅' if has_vector_mode else '❌'}")

# Check for FMAPI columns  
has_fmapi_rate = 'fmapi_rate_type' in column_names
has_fmapi_quantity = 'fmapi_quantity' in column_names
has_fmapi_input = 'fmapi_input_tokens_per_month' in column_names
has_fmapi_output = 'fmapi_output_tokens_per_month' in column_names
print(f"  FMAPI (new): fmapi_rate_type={'✅' if has_fmapi_rate else '❌'}, fmapi_quantity={'✅' if has_fmapi_quantity else '❌'}")
print(f"  FMAPI (old): fmapi_input_tokens={'✅' if has_fmapi_input else '❌'}, fmapi_output_tokens={'✅' if has_fmapi_output else '❌'}")

print("\n⚠️ IMPORTANT NOTES:")
if not has_vector_capacity:
    print("  - VECTOR_SEARCH items will SKIP validation (missing vector_capacity_millions column)")
    print("    → These items need schema migration before backfill")
if not has_fmapi_rate:
    print("  - FMAPI items will SKIP validation (missing fmapi_rate_type/fmapi_quantity columns)")
    print("    → These items need schema migration before backfill")

print("\n" + "=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Check Line Items Can Join with Estimates

# COMMAND ----------

print("\n" + "=" * 80)
print("STEP 1: CHECKING JOIN WITH ESTIMATES TABLE")
print("=" * 80)

# Check if all line items have corresponding estimates
join_check_sql = f"""
SELECT 
    COUNT(*) as total_line_items,
    COUNT(e.estimate_id) as with_estimate,
    COUNT(*) - COUNT(e.estimate_id) as missing_estimate
FROM {FULL_TABLE_NAME} li
LEFT JOIN {ESTIMATES_TABLE} e ON li.estimate_id = e.estimate_id
"""

results = execute_query(join_check_sql, fetch=True)[0]
total = results['total_line_items']
with_estimate = results['with_estimate']
missing = results['missing_estimate']

print(f"\n📊 Total line items: {total}")
print(f"✅ With estimate: {with_estimate} ({with_estimate/total*100:.1f}%)" if total > 0 else "No line items found")
print(f"❌ Missing estimate: {missing} ({missing/total*100:.1f}%)" if missing > 0 else "✅ All line items have estimates")

if missing > 0:
    print("\n⚠️ WARNING: Some line items are missing estimate data!")
    missing_sql = f"""
    SELECT 
        li.line_item_id,
        li.workload_type,
        li.workload_name,
        li.estimate_id
    FROM {FULL_TABLE_NAME} li
    LEFT JOIN {ESTIMATES_TABLE} e ON li.estimate_id = e.estimate_id
    WHERE e.estimate_id IS NULL
    """
    missing_items = execute_query(missing_sql, fetch=True)
    print(f"\nALL {len(missing_items)} items missing estimate:")
    for idx, item in enumerate(missing_items, 1):
        print(f"{idx}. {item['workload_type']}: {item['workload_name']} (estimate_id: {item['estimate_id']})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Check API Endpoint Mapping

# COMMAND ----------

print("\n" + "=" * 80)
print("STEP 2: CHECKING API ENDPOINT MAPPING")
print("=" * 80)

# Define endpoint mapping logic
def get_endpoint_for_validation(workload_type: str, serverless_enabled: Optional[bool], 
                                 dbsql_warehouse_type: Optional[str], 
                                 fmapi_provider: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """
    Get endpoint and validation message for a workload
    Returns: (endpoint, error_message)
    """
    
    if workload_type == "JOBS":
        if serverless_enabled is None:
            return None, "serverless_enabled is NULL"
        endpoint = "/api/v1/calculate/jobs-serverless" if serverless_enabled else "/api/v1/calculate/jobs-classic"
        return endpoint, None
        
    elif workload_type == "ALL_PURPOSE":
        if serverless_enabled is None:
            return None, "serverless_enabled is NULL"
        endpoint = "/api/v1/calculate/all-purpose-serverless" if serverless_enabled else "/api/v1/calculate/all-purpose-classic"
        return endpoint, None
        
    elif workload_type == "DLT":
        if serverless_enabled is None:
            return None, "serverless_enabled is NULL"
        endpoint = "/api/v1/calculate/dlt-serverless" if serverless_enabled else "/api/v1/calculate/dlt-classic"
        return endpoint, None
        
    elif workload_type == "DBSQL":
        if not dbsql_warehouse_type:
            return None, "dbsql_warehouse_type is NULL"
        endpoint_map = {
            "classic": "/api/v1/calculate/dbsql-classic",
            "pro": "/api/v1/calculate/dbsql-pro",
            "serverless": "/api/v1/calculate/dbsql-serverless"
        }
        endpoint = endpoint_map.get(dbsql_warehouse_type.lower())
        if not endpoint:
            return None, f"Unknown dbsql_warehouse_type: {dbsql_warehouse_type}"
        return endpoint, None
        
    elif workload_type == "VECTOR_SEARCH":
        return "/api/v1/calculate/vector-search", None
        
    elif workload_type == "MODEL_SERVING":
        return "/api/v1/calculate/model-serving", None
        
    elif workload_type == "FMAPI":
        if not fmapi_provider:
            return None, "fmapi_provider is NULL"
        provider_upper = fmapi_provider.upper()
        if "DATABRICKS" in provider_upper or "DBRX" in provider_upper:
            return "/api/v1/calculate/fmapi-databricks", None
        else:
            return "/api/v1/calculate/fmapi-proprietary", None
    
    elif workload_type == "FMAPI_DATABRICKS":
        return "/api/v1/calculate/fmapi-databricks", None
    
    elif workload_type == "FMAPI_PROPRIETARY":
        return "/api/v1/calculate/fmapi-proprietary", None
            
    elif workload_type == "LAKEBASE":
        return "/api/v1/calculate/lakebase", None
    
    elif workload_type == "DATABRICKS_APPS":
        return "/api/v1/calculate/databricks-apps", None
    
    elif workload_type == "CLEAN_ROOM":
        return "/api/v1/calculate/clean-room", None
    
    elif workload_type == "AI_PARSE":
        return "/api/v1/calculate/ai-parse", None
        
    else:
        return None, f"Unknown workload_type: {workload_type}"

# Fetch all line items with their mapping info
mapping_sql = f"""
SELECT 
    li.line_item_id,
    li.workload_type,
    li.workload_name,
    li.serverless_enabled,
    li.dbsql_warehouse_type,
    li.fmapi_provider,
    e.cloud,
    e.region,
    e.tier
FROM {FULL_TABLE_NAME} li
LEFT JOIN {ESTIMATES_TABLE} e ON li.estimate_id = e.estimate_id
"""

line_items = execute_query(mapping_sql, fetch=True)

# Validate each line item
can_map = 0
cannot_map = 0
mapping_errors = []

for item in line_items:
    endpoint, error = get_endpoint_for_validation(
        item['workload_type'],
        item.get('serverless_enabled'),
        item.get('dbsql_warehouse_type'),
        item.get('fmapi_provider')
    )
    
    if endpoint:
        can_map += 1
    else:
        cannot_map += 1
        mapping_errors.append({
            'line_item_id': item['line_item_id'],
            'workload_type': item['workload_type'],
            'workload_name': item['workload_name'],
            'error': error
        })

print(f"\n📊 Total line items: {len(line_items)}")
print(f"✅ Can map to endpoint: {can_map} ({can_map/len(line_items)*100:.1f}%)" if len(line_items) > 0 else "No items")
print(f"❌ Cannot map to endpoint: {cannot_map} ({cannot_map/len(line_items)*100:.1f}%)" if cannot_map > 0 else "✅ All items can be mapped")

if cannot_map > 0:
    print("\n⚠️ WARNING: Some line items cannot be mapped to API endpoints!")
    print(f"\nALL {len(mapping_errors)} mapping errors:")
    for idx, err in enumerate(mapping_errors, 1):
        print(f"\n{idx}. {err['workload_type']}: {err['workload_name']}")
        print(f"   Error: {err['error']}")
        print(f"   Line Item ID: {err['line_item_id']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Check Required Fields by Workload Type

# COMMAND ----------

print("\n" + "=" * 80)
print("STEP 3: CHECKING REQUIRED FIELDS BY WORKLOAD TYPE")
print("=" * 80)

# Define required fields for each workload type
def get_required_fields(workload_type: str, serverless_enabled: Optional[bool], 
                       dbsql_warehouse_type: Optional[str],
                       available_columns: List[str]) -> List[str]:
    """Get list of required fields for a workload type, filtered by what columns exist"""
    
    required = []
    
    if workload_type in ["JOBS", "ALL_PURPOSE"]:
        if not serverless_enabled:
            required = ["driver_node_type", "worker_node_type", "num_workers"]
        else:
            required = []  # Serverless needs minimal fields
            
    elif workload_type == "DLT":
        if not serverless_enabled:
            required = ["driver_node_type", "worker_node_type", "num_workers", "dlt_edition"]
        else:
            required = []  # Serverless DLT doesn't require dlt_edition
            
    elif workload_type == "DBSQL":
        required = ["dbsql_warehouse_size"]
        if dbsql_warehouse_type in ["classic", "pro"]:
            required.append("dbsql_vm_pricing_tier")
        
    elif workload_type == "VECTOR_SEARCH":
        # Check which schema version we have
        if "vector_capacity_millions" in available_columns:
            required = ["vector_search_mode", "vector_capacity_millions"]
        else:
            # Old schema - skip validation (data needs migration)
            required = []
        
    elif workload_type == "MODEL_SERVING":
        required = ["model_serving_gpu_type"]
        
    elif workload_type == "FMAPI":
        # Check which schema version we have
        if "fmapi_rate_type" in available_columns and "fmapi_quantity" in available_columns:
            required = ["fmapi_provider", "fmapi_model", "fmapi_endpoint_type", 
                       "fmapi_rate_type", "fmapi_quantity"]
        else:
            # Old schema - skip validation (data needs migration)
            required = []
    
    elif workload_type in ["FMAPI_DATABRICKS", "FMAPI_PROPRIETARY"]:
        # Check which schema version we have
        if "fmapi_rate_type" in available_columns and "fmapi_quantity" in available_columns:
            required = ["fmapi_provider", "fmapi_model", "fmapi_endpoint_type", 
                       "fmapi_rate_type", "fmapi_quantity"]
        else:
            # Old schema - skip validation (data needs migration)
            required = []
        
    elif workload_type == "LAKEBASE":
        required = ["lakebase_cu"]  # lakebase_storage_gb is optional (defaults to 0)
    
    elif workload_type == "DATABRICKS_APPS":
        if "databricks_apps_size" in available_columns:
            required = ["databricks_apps_size"]
        else:
            required = []
    
    elif workload_type == "CLEAN_ROOM":
        if "clean_room_num_collaborators" in available_columns:
            required = ["clean_room_num_collaborators"]
        else:
            required = []
    
    elif workload_type == "AI_PARSE":
        # AI Parse can use either dbu_quantity OR (num_pages + complexity)
        # Skip validation - will check at runtime
        required = []
        
    # Filter required fields to only include those that exist in the table
    return [field for field in required if field in available_columns]

# Build SQL query with only columns that exist
validation_columns = [
    'line_item_id', 'workload_type', 'workload_name', 'serverless_enabled', 'dbsql_warehouse_type',
    'driver_node_type', 'worker_node_type', 'num_workers', 'dlt_edition',
    'dbsql_warehouse_size', 'dbsql_vm_pricing_tier',
    'vector_search_mode', 'vector_capacity_millions',
    'model_serving_gpu_type',
    'fmapi_provider', 'fmapi_model', 'fmapi_endpoint_type', 'fmapi_rate_type', 'fmapi_quantity',
    'lakebase_cu', 'lakebase_storage_gb',
    'databricks_apps_size', 'databricks_apps_hours_per_month',
    'clean_room_num_collaborators', 'clean_room_days_per_month',
    'ai_parse_calculation_method', 'ai_parse_dbu_quantity', 'ai_parse_num_pages', 'ai_parse_complexity'
]

# Filter to only columns that exist
existing_validation_columns = [col for col in validation_columns if col in column_names]

# Build SELECT clause
select_clause = ',\n    '.join([f'li.{col}' for col in existing_validation_columns])

# Check required fields for each workload type
field_validation_sql = f"""
SELECT 
    {select_clause},
    -- Estimate fields
    e.cloud,
    e.region,
    e.tier
FROM {FULL_TABLE_NAME} li
LEFT JOIN {ESTIMATES_TABLE} e ON li.estimate_id = e.estimate_id
"""

print(f"\n📊 Querying {len(existing_validation_columns)} columns for validation")

line_items = execute_query(field_validation_sql, fetch=True)

missing_fields_count = 0
missing_field_items = []

for item in line_items:
    required_fields = get_required_fields(
        item['workload_type'],
        item.get('serverless_enabled'),
        item.get('dbsql_warehouse_type'),
        column_names  # Pass available columns
    )
    
    # Check estimate fields (always required)
    required_fields.extend(['cloud', 'region', 'tier'])
    
    missing = []
    for field in required_fields:
        if item.get(field) is None:
            missing.append(field)
    
    if missing:
        missing_fields_count += 1
        missing_field_items.append({
            'line_item_id': item['line_item_id'],
            'workload_type': item['workload_type'],
            'workload_name': item['workload_name'],
            'missing_fields': missing
        })

print(f"\n📊 Total line items: {len(line_items)}")
print(f"✅ All required fields present: {len(line_items) - missing_fields_count} ({(len(line_items) - missing_fields_count)/len(line_items)*100:.1f}%)" if len(line_items) > 0 else "No items")
print(f"❌ Missing required fields: {missing_fields_count} ({missing_fields_count/len(line_items)*100:.1f}%)" if missing_fields_count > 0 else "✅ All items have required fields")

if missing_fields_count > 0:
    print("\n⚠️ WARNING: Some line items are missing required fields!")
    print(f"\nALL {len(missing_field_items)} items with missing fields:")
    for idx, item in enumerate(missing_field_items, 1):
        print(f"\n{idx}. {item['workload_type']}: {item['workload_name']}")
        print(f"   Missing: {', '.join(item['missing_fields'])}")
        print(f"   Line Item ID: {item['line_item_id']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Summary by Workload Type

# COMMAND ----------

print("\n" + "=" * 80)
print("STEP 4: VALIDATION SUMMARY BY WORKLOAD TYPE")
print("=" * 80)

summary_sql = f"""
SELECT 
    li.workload_type,
    COUNT(*) as total_count,
    COUNT(e.estimate_id) as has_estimate,
    COUNT(*) - COUNT(e.estimate_id) as missing_estimate
FROM {FULL_TABLE_NAME} li
LEFT JOIN {ESTIMATES_TABLE} e ON li.estimate_id = e.estimate_id
GROUP BY li.workload_type
ORDER BY total_count DESC
"""

summary = execute_query(summary_sql, fetch=True)

print("\n📊 Breakdown by Workload Type:")
print(f"\n{'Workload Type':<20} {'Total':>8} {'Has Estimate':>14} {'Missing':>10}")
print("-" * 60)

for row in summary:
    workload = row['workload_type'] or 'NULL'
    total = row['total_count']
    has_est = row['has_estimate']
    missing = row['missing_estimate']
    
    status = "✅" if missing == 0 else "⚠️"
    print(f"{status} {workload:<18} {total:>8} {has_est:>14} {missing:>10}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Final Validation Report

# COMMAND ----------

print("\n" + "=" * 80)
print("FINAL VALIDATION REPORT")
print("=" * 80)

# Calculate overall readiness
total_items = len(line_items)
ready_for_backfill = len(line_items) - missing - cannot_map - missing_fields_count

print(f"\n📊 Database: {DB_NAME}")
print(f"📊 Table: {FULL_TABLE_NAME}")
print(f"📊 Total line items: {total_items}")
print()
print(f"✅ Ready for backfill: {ready_for_backfill} ({ready_for_backfill/total_items*100:.1f}%)" if total_items > 0 else "No items")
print()
print("Issues found:")
print(f"   ❌ Missing estimate join: {missing}")
print(f"   ❌ Cannot map to endpoint: {cannot_map}")
print(f"   ❌ Missing required fields: {missing_fields_count}")
print()

if ready_for_backfill == total_items:
    print("🎉 ALL LINE ITEMS ARE READY FOR BACKFILL!")
    print("   You can proceed with 02_Backfill_Line_Item_Costs notebook")
else:
    print("⚠️ SOME LINE ITEMS NEED ATTENTION BEFORE BACKFILL")
    print("   Please fix the issues above before running backfill")

print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC
# MAGIC **If validation passed (100% ready):**
# MAGIC - ✅ Proceed to `02_Backfill_Line_Item_Costs` notebook
# MAGIC - Start with backup table and small limit (10) to test
# MAGIC
# MAGIC **If validation failed:**
# MAGIC - ❌ Review the errors above
# MAGIC - Fix missing estimates, unmappable workloads, or missing required fields
# MAGIC - Re-run this validation notebook
