# Databricks notebook source
# MAGIC %md
# MAGIC # Backfill Line Item Cost Calculation Responses
# MAGIC
# MAGIC **Purpose:** Calculate costs for existing line items by calling calculation APIs
# MAGIC
# MAGIC **What it does:**
# MAGIC 1. Fetches line items that need calculation
# MAGIC 2. Calls appropriate API endpoint based on workload type
# MAGIC 3. Stores full response in `cost_calculation_response` JSONB column
# MAGIC
# MAGIC **Usage:**
# MAGIC - Set `TABLE_TO_PROCESS` widget: "main" or "backup"
# MAGIC - Set `STATUS_FILTER` widget: "pending", "error", or "all"
# MAGIC - Set `LIMIT` widget: number of items to process (0 = all)
# MAGIC
# MAGIC **Recommendation:** Test on backup table first with small limit!

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration Widgets

# COMMAND ----------

dbutils.widgets.dropdown("TABLE_TO_PROCESS", "line_items_backup_20260114", 
                        ["line_items", "line_items_backup_20260114"], 
                        "1. Table to Process")
dbutils.widgets.dropdown("STATUS_FILTER", "all", ["pending", "error", "all"], "2. Status Filter")
dbutils.widgets.text("LIMIT", "0", "3. Limit (0 = all)")
dbutils.widgets.text("API_BASE_URL", "https://lakemeter-api-335310294452632.aws.databricksapps.com", "4. API Base URL")
dbutils.widgets.text("DATABRICKS_HOST", "https://fe-vm-lakemeter.cloud.databricks.com", "5. Databricks Host")
dbutils.widgets.text("SERVICE_PRINCIPAL_CLIENT_ID", "", "6. Service Principal Client ID")
dbutils.widgets.text("SERVICE_PRINCIPAL_SECRET", "", "7. Service Principal Secret")

# Get widget values
TABLE_NAME = dbutils.widgets.get("TABLE_TO_PROCESS")
STATUS_FILTER = dbutils.widgets.get("STATUS_FILTER")
LIMIT_STR = dbutils.widgets.get("LIMIT")
API_BASE_URL = dbutils.widgets.get("API_BASE_URL")

# Service Principal Configuration (M2M Authentication)
DATABRICKS_HOST = dbutils.widgets.get("DATABRICKS_HOST")
SERVICE_PRINCIPAL_CLIENT_ID = dbutils.widgets.get("SERVICE_PRINCIPAL_CLIENT_ID")
SERVICE_PRINCIPAL_SECRET = dbutils.widgets.get("SERVICE_PRINCIPAL_SECRET")

print("=" * 80)
print("CONFIGURATION")
print("=" * 80)
print(f"API Base URL: {API_BASE_URL}")
print(f"Databricks Host: {DATABRICKS_HOST}")
print(f"Service Principal: {'Configured' if SERVICE_PRINCIPAL_CLIENT_ID else 'NOT configured'}")
print("=" * 80)

# Database and schema configuration
DB_NAME = "lakemeter_pricing"
SCHEMA_NAME = "lakemeter"
FULL_TABLE_NAME = f"{SCHEMA_NAME}.{TABLE_NAME}"

# Determine which estimates table to use
if TABLE_NAME == "line_items_backup_20260114":
    ESTIMATES_TABLE = f"{SCHEMA_NAME}.estimates_backup_20260119"
else:
    ESTIMATES_TABLE = f"{SCHEMA_NAME}.estimates"

# Workload types to EXCLUDE from backfill
EXCLUDED_WORKLOAD_TYPES = ['VECTOR_SEARCH', 'MODEL_SERVING', 'FMAPI_PROPRIETARY']

LIMIT = int(LIMIT_STR) if LIMIT_STR and LIMIT_STR != "0" else None

# COMMAND ----------

# MAGIC %md
# MAGIC ## Authentication Setup (M2M)

# COMMAND ----------

# Install databricks-sdk if needed
try:
    from databricks.sdk import WorkspaceClient
except ImportError:
    print("Installing databricks-sdk...")
    import subprocess
    subprocess.check_call(["pip", "install", "-q", "databricks-sdk"])
    from databricks.sdk import WorkspaceClient

import requests

print("=" * 80)
print("AUTHENTICATION (M2M)")
print("=" * 80)
print("🔐 Authenticating with Service Principal...")

# Create workspace client with service principal
wc = WorkspaceClient(
    host=DATABRICKS_HOST,
    client_id=SERVICE_PRINCIPAL_CLIENT_ID,
    client_secret=SERVICE_PRINCIPAL_SECRET
)

# Get authentication headers (OAuth2 token)
AUTH_HEADERS = wc.config.authenticate()

print("✅ Authentication successful")
print(f"   Headers: {list(AUTH_HEADERS.keys())}")
print("=" * 80)

print("\n" + "=" * 80)
print("BACKFILL CONFIGURATION")
print("=" * 80)
print(f"Database: {DB_NAME}")
print(f"Schema: {SCHEMA_NAME}")
print(f"Line Items Table: {FULL_TABLE_NAME}")
print(f"Estimates Table: {ESTIMATES_TABLE}")
print(f"Status Filter: {STATUS_FILTER}")
print(f"Limit: {LIMIT or 'None (process all)'}")
print(f"API Base URL: {API_BASE_URL}")
print(f"Authentication: ✅ Service Principal (M2M)")
print("\n⚠️ EXCLUDED from backfill:")
print(f"   {', '.join(EXCLUDED_WORKLOAD_TYPES)}")
print("   Reason: Schema migration required / pending review")
print("=" * 80)

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

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
# MAGIC ## Test API Authentication

# COMMAND ----------

print("\n" + "=" * 80)
print("TESTING API AUTHENTICATION")
print("=" * 80)

# Test API connection
print("1. Testing API reachability (GET /docs)...")
test_response = requests.get(
    f"{API_BASE_URL}/docs",
    headers=AUTH_HEADERS,
    timeout=10
)
print(f"   ✅ API reachable: HTTP {test_response.status_code}")

print("\n2. Testing authentication with calculation endpoint...")
test_payload = {
    "cloud": "AWS",
    "region": "us-east-1", 
    "tier": "PREMIUM",
    "cu_per_node": 2,
    "storage_gb": 0,
    "hours_per_month": 730
}

test_calc_response = requests.post(
    f"{API_BASE_URL}/api/v1/calculate/lakebase",
    json=test_payload,
    headers=AUTH_HEADERS,
    timeout=10
)

if test_calc_response.status_code == 200:
    result = test_calc_response.json()
    print(f"   ✅ Authentication successful!")
    print(f"   Test calculation: {result.get('success')}")
    if result.get('data'):
        print(f"   Sample cost: ${result['data'].get('cost_per_month', 0):,.2f}/month")
elif test_calc_response.status_code == 401:
    print(f"   ❌ Authentication FAILED (401)")
    print(f"   Response: {test_calc_response.text}")
    print("\n⚠️ Check service principal has 'CAN USE' permission on app")
else:
    print(f"   ⚠️ Unexpected status: {test_calc_response.status_code}")
    print(f"   Response: {test_calc_response.text[:300]}")

print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Workload Type to API Endpoint Mapping

# COMMAND ----------

# Workload type to API endpoint mapping
ENDPOINT_MAPPING = {
    # Format: (workload_type, serverless_enabled, dbsql_warehouse_type) -> endpoint
    ("JOBS", False, None): "/api/v1/calculate/jobs-classic",
    ("JOBS", True, None): "/api/v1/calculate/jobs-serverless",
    ("ALL_PURPOSE", False, None): "/api/v1/calculate/all-purpose-classic",
    ("ALL_PURPOSE", True, None): "/api/v1/calculate/all-purpose-serverless",
    ("DLT", False, None): "/api/v1/calculate/dlt-classic",
    ("DLT", True, None): "/api/v1/calculate/dlt-serverless",
    ("DBSQL", None, "classic"): "/api/v1/calculate/dbsql-classic",
    ("DBSQL", None, "pro"): "/api/v1/calculate/dbsql-pro",
    ("DBSQL", None, "serverless"): "/api/v1/calculate/dbsql-serverless",
    ("VECTOR_SEARCH", None, None): "/api/v1/calculate/vector-search",
    ("MODEL_SERVING", None, None): "/api/v1/calculate/model-serving",
    ("FMAPI", None, None): None,  # Will be handled by provider check
    ("FMAPI_DATABRICKS", None, None): "/api/v1/calculate/fmapi-databricks",
    ("FMAPI_PROPRIETARY", None, None): "/api/v1/calculate/fmapi-proprietary",
    ("LAKEBASE", None, None): "/api/v1/calculate/lakebase",
    ("DATABRICKS_APPS", None, None): "/api/v1/calculate/databricks-apps",
    ("CLEAN_ROOM", None, None): "/api/v1/calculate/clean-room",
    ("AI_PARSE", None, None): "/api/v1/calculate/ai-parse",
}

def get_endpoint(workload_type: str, serverless_enabled: Optional[bool], 
                 dbsql_warehouse_type: Optional[str]) -> Optional[str]:
    """Get the appropriate API endpoint for a workload type"""
    if workload_type == "FMAPI":
        return None  # Will be handled separately
    
    key = (workload_type, serverless_enabled, dbsql_warehouse_type)
    return ENDPOINT_MAPPING.get(key)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Build API Request Payload

# COMMAND ----------

def build_payload(line_item: Dict[str, Any], estimate: Dict[str, Any]) -> Dict[str, Any]:
    """Build API request payload from line item data"""
    
    workload_type = line_item["workload_type"]
    
    # Base payload (common fields)
    payload = {
        "cloud": estimate["cloud"],
        "region": estimate["region"],
        "tier": estimate["tier"],
    }
    
    # Add workload-specific fields
    if workload_type in ["JOBS", "ALL_PURPOSE"]:
        if not line_item.get("serverless_enabled"):
            payload.update({
                "driver_node_type": line_item["driver_node_type"],
                "worker_node_type": line_item["worker_node_type"],
                "num_workers": line_item["num_workers"],
                "photon_enabled": line_item.get("photon_enabled", False),
                "driver_pricing_tier": line_item.get("driver_pricing_tier", "on_demand"),
                "worker_pricing_tier": line_item.get("worker_pricing_tier", "on_demand"),
                "driver_payment_option": line_item.get("driver_payment_option", "NA"),
                "worker_payment_option": line_item.get("worker_payment_option", "NA"),
            })
        else:
            payload.update({
                "serverless_mode": line_item.get("serverless_mode", "standard"),
            })
            if workload_type == "JOBS":
                payload["photon_enabled"] = line_item.get("photon_enabled", False)
        
        # Usage parameters
        if line_item.get("hours_per_month"):
            payload["hours_per_month"] = float(line_item["hours_per_month"])
        else:
            payload.update({
                "runs_per_day": line_item.get("runs_per_day", 0),
                "avg_runtime_minutes": line_item.get("avg_runtime_minutes", 0),
                "days_per_month": line_item.get("days_per_month", 30),
            })
    
    elif workload_type == "DLT":
        payload.update({
            "photon_enabled": line_item.get("photon_enabled", False),
        })
        
        if not line_item.get("serverless_enabled"):
            # Classic DLT requires dlt_edition
            payload.update({
                "dlt_edition": line_item.get("dlt_edition", "core"),
                "driver_node_type": line_item["driver_node_type"],
                "worker_node_type": line_item["worker_node_type"],
                "num_workers": line_item["num_workers"],
                "driver_pricing_tier": line_item.get("driver_pricing_tier", "on_demand"),
                "worker_pricing_tier": line_item.get("worker_pricing_tier", "on_demand"),
                "driver_payment_option": line_item.get("driver_payment_option", "NA"),
                "worker_payment_option": line_item.get("worker_payment_option", "NA"),
            })
        else:
            # Serverless DLT - dlt_edition is optional (API will default)
            payload["serverless_mode"] = line_item.get("serverless_mode", "standard")
            if line_item.get("dlt_edition"):
                payload["dlt_edition"] = line_item["dlt_edition"]
        
        if line_item.get("hours_per_month"):
            payload["hours_per_month"] = float(line_item["hours_per_month"])
        else:
            payload.update({
                "runs_per_day": line_item.get("runs_per_day", 0),
                "avg_runtime_minutes": line_item.get("avg_runtime_minutes", 0),
                "days_per_month": line_item.get("days_per_month", 30),
            })
    
    elif workload_type == "DBSQL":
        payload.update({
            "warehouse_type": line_item["dbsql_warehouse_type"],
            "warehouse_size": line_item["dbsql_warehouse_size"],
            "num_clusters": line_item.get("dbsql_num_clusters", 1),
            "hours_per_month": float(line_item.get("hours_per_month", 0)),
        })
        
        if line_item["dbsql_warehouse_type"] in ["classic", "pro"]:
            payload.update({
                "vm_pricing_tier": line_item.get("dbsql_vm_pricing_tier", "on_demand"),
                "vm_payment_option": line_item.get("dbsql_vm_payment_option", "NA"),
            })
    
    elif workload_type == "VECTOR_SEARCH":
        payload.update({
            "vector_search_mode": line_item["vector_search_mode"],
            "capacity_millions": float(line_item["vector_capacity_millions"]),
        })
    
    elif workload_type == "MODEL_SERVING":
        payload.update({
            "gpu_type": line_item["model_serving_gpu_type"],
            "hours_per_month": float(line_item.get("hours_per_month", 0)),
        })
    
    elif workload_type in ["FMAPI", "FMAPI_DATABRICKS", "FMAPI_PROPRIETARY"]:
        provider = line_item["fmapi_provider"]
        payload.update({
            "provider": provider,
            "model": line_item["fmapi_model"],
            "endpoint_type": line_item["fmapi_endpoint_type"],
            "context_length": line_item["fmapi_context_length"],
            "rate_type": line_item["fmapi_rate_type"],
            "quantity": line_item["fmapi_quantity"],
        })
    
    elif workload_type == "LAKEBASE":
        payload.update({
            "cu_per_node": line_item["lakebase_cu"],
            "storage_gb": float(line_item.get("lakebase_storage_gb", 0)),  # Optional, defaults to 0
            "ha_nodes": line_item.get("lakebase_ha_nodes", 1),
            "backup_retention_days": line_item.get("lakebase_backup_retention_days", 7),
            "hours_per_month": float(line_item.get("hours_per_month", 730)),
        })
    
    elif workload_type == "DATABRICKS_APPS":
        payload.update({
            "size": line_item["databricks_apps_size"],
            "hours_per_month": float(line_item.get("databricks_apps_hours_per_month", line_item.get("hours_per_month", 730))),
        })
    
    elif workload_type == "CLEAN_ROOM":
        payload.update({
            "num_collaborators": line_item["clean_room_num_collaborators"],
            "days_per_month": line_item.get("clean_room_days_per_month", line_item.get("days_per_month", 30)),
        })
    
    elif workload_type == "AI_PARSE":
        # AI Parse can use either dbu_quantity OR (num_pages + complexity)
        if line_item.get("ai_parse_dbu_quantity"):
            payload.update({
                "dbu_quantity": float(line_item["ai_parse_dbu_quantity"]),
            })
        elif line_item.get("ai_parse_num_pages") and line_item.get("ai_parse_complexity"):
            payload.update({
                "num_pages": int(line_item["ai_parse_num_pages"]),
                "complexity": line_item["ai_parse_complexity"],
            })
    
    return payload

# COMMAND ----------

# MAGIC %md
# MAGIC ## Calculate Cost for Single Line Item

# COMMAND ----------

def calculate_line_item_cost(
    line_item: Dict[str, Any],
    estimate: Dict[str, Any]
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Calculate cost for a single line item
    
    Returns:
        (success, response_data, error_message)
    """
    try:
        workload_type = line_item["workload_type"]
        
        # Special handling for FMAPI (if stored as generic type)
        if workload_type == "FMAPI":
            provider = line_item.get("fmapi_provider", "").upper()
            if "DATABRICKS" in provider or "DBRX" in provider:
                endpoint = "/api/v1/calculate/fmapi-databricks"
            else:
                endpoint = "/api/v1/calculate/fmapi-proprietary"
        # Direct handling for split FMAPI workload types
        elif workload_type == "FMAPI_DATABRICKS":
            endpoint = "/api/v1/calculate/fmapi-databricks"
        elif workload_type == "FMAPI_PROPRIETARY":
            endpoint = "/api/v1/calculate/fmapi-proprietary"
        # Direct handling for other new workload types
        elif workload_type == "DATABRICKS_APPS":
            endpoint = "/api/v1/calculate/databricks-apps"
        elif workload_type == "CLEAN_ROOM":
            endpoint = "/api/v1/calculate/clean-room"
        elif workload_type == "AI_PARSE":
            endpoint = "/api/v1/calculate/ai-parse"
        # Direct handling for LAKEBASE
        elif workload_type == "LAKEBASE":
            endpoint = "/api/v1/calculate/lakebase"
        # Direct handling for DBSQL based on warehouse type
        elif workload_type == "DBSQL":
            warehouse_type = line_item.get("dbsql_warehouse_type", "").lower()
            if warehouse_type == "classic":
                endpoint = "/api/v1/calculate/dbsql-classic"
            elif warehouse_type == "pro":
                endpoint = "/api/v1/calculate/dbsql-pro"
            elif warehouse_type == "serverless":
                endpoint = "/api/v1/calculate/dbsql-serverless"
            else:
                endpoint = None  # Will trigger "No endpoint mapping" error
        else:
            endpoint = get_endpoint(
                workload_type,
                line_item.get("serverless_enabled"),
                line_item.get("dbsql_warehouse_type")
            )
        
        if not endpoint:
            return False, None, f"No endpoint mapping for {workload_type}"
        
        # Build payload
        payload = build_payload(line_item, estimate)
        
        # Call API with authentication headers
        url = f"{API_BASE_URL}{endpoint}"
        
        # Debug: Print request details for first item
        if workload_type not in getattr(calculate_line_item_cost, '_logged_types', set()):
            if not hasattr(calculate_line_item_cost, '_logged_types'):
                calculate_line_item_cost._logged_types = set()
            calculate_line_item_cost._logged_types.add(workload_type)
            print(f"\n🔍 DEBUG - First {workload_type} request:")
            print(f"   URL: {url}")
            print(f"   Headers: {list(AUTH_HEADERS.keys())}")
            print(f"   Payload keys: {list(payload.keys())}")
        
        response = requests.post(
            url,
            json=payload,
            headers=AUTH_HEADERS,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return True, result, None
            else:
                error_msg = result.get("error", {}).get("message", "Unknown error")
                return False, None, error_msg
        else:
            # Enhanced error message with more details
            error_detail = f"HTTP {response.status_code}: {response.text[:200]}"
            if response.status_code == 401:
                error_detail += "\n   ⚠️ Authentication failed. Token may be invalid or API requires different auth method."
            return False, None, error_detail
            
    except Exception as e:
        return False, None, str(e)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Update Line Item with Results

# COMMAND ----------

def update_line_item_costs(
    full_table_name: str,
    line_item_id: str,
    success: bool,
    response_data: Optional[Dict[str, Any]],
    error_message: Optional[str]
):
    """Update line item with calculated costs"""
    
    if success:
        update_sql = f"""
            UPDATE {full_table_name}
            SET 
                cost_calculation_response = %s::jsonb,
                calculation_completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE line_item_id = %s
        """
        execute_query(update_sql, (json.dumps(response_data), line_item_id))
    else:
        # Store error in same response structure
        error_response = {
            "success": False,
            "error": {
                "message": error_message,
                "failed_at": datetime.now().isoformat()
            }
        }
        
        update_sql = f"""
            UPDATE {full_table_name}
            SET 
                cost_calculation_response = %s::jsonb,
                calculation_completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE line_item_id = %s
        """
        execute_query(update_sql, (json.dumps(error_response), line_item_id))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Fetch Line Items to Process

# COMMAND ----------

print("=" * 80)
print("FETCHING LINE ITEMS TO PROCESS")
print("=" * 80)

# Build WHERE clause based on status filter
if STATUS_FILTER == "pending":
    where_clause = "AND li.cost_calculation_response IS NULL"
elif STATUS_FILTER == "error":
    where_clause = "AND li.cost_calculation_response->>'success' = 'false'"
else:  # all
    where_clause = ""

# Add exclusion filter for certain workload types
excluded_list = "'" + "','".join(EXCLUDED_WORKLOAD_TYPES) + "'"
where_clause += f" AND li.workload_type NOT IN ({excluded_list})"

limit_clause = f"LIMIT {LIMIT}" if LIMIT else ""

fetch_sql = f"""
    SELECT 
        li.line_item_id,
        li.workload_type,
        li.workload_name,
        li.serverless_enabled,
        li.photon_enabled,
        li.driver_node_type,
        li.worker_node_type,
        li.num_workers,
        li.dlt_edition,
        li.dbsql_warehouse_type,
        li.dbsql_warehouse_size,
        li.dbsql_num_clusters,
        li.dbsql_vm_pricing_tier,
        li.dbsql_vm_payment_option,
        li.vector_search_mode,
        li.vector_capacity_millions,
        li.model_serving_gpu_type,
        li.fmapi_provider,
        li.fmapi_model,
        li.fmapi_endpoint_type,
        li.fmapi_context_length,
        li.fmapi_rate_type,
        li.fmapi_quantity,
        li.lakebase_cu,
        li.lakebase_storage_gb,
        li.lakebase_ha_nodes,
        li.lakebase_backup_retention_days,
        li.databricks_apps_size,
        li.databricks_apps_hours_per_month,
        li.clean_room_num_collaborators,
        li.clean_room_days_per_month,
        li.ai_parse_calculation_method,
        li.ai_parse_dbu_quantity,
        li.ai_parse_num_pages,
        li.ai_parse_complexity,
        li.runs_per_day,
        li.avg_runtime_minutes,
        li.days_per_month,
        li.hours_per_month,
        li.driver_pricing_tier,
        li.worker_pricing_tier,
        li.driver_payment_option,
        li.worker_payment_option,
        li.serverless_mode,
        e.estimate_id,
        e.cloud,
        e.region,
        e.tier
    FROM {FULL_TABLE_NAME} li
    JOIN {ESTIMATES_TABLE} e ON li.estimate_id = e.estimate_id
    WHERE 1=1 {where_clause}
    ORDER BY li.created_at ASC
    {limit_clause}
"""

line_items = execute_query(fetch_sql, fetch=True)
total = len(line_items)

print(f"\n📊 Found {total} line items to process")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Process Line Items

# COMMAND ----------

if total == 0:
    print("\n✅ No line items to process")
    dbutils.notebook.exit("No line items to process")

print("\n" + "=" * 80)
print("PROCESSING LINE ITEMS")
print("=" * 80)

success_count = 0
error_count = 0

for idx, line_item in enumerate(line_items, 1):
    line_item_id = line_item["line_item_id"]
    workload_type = line_item["workload_type"]
    workload_name = line_item["workload_name"] or "Unnamed"
    
    print(f"\n[{idx}/{total}] Processing: {workload_type} - {workload_name}")
    print(f"   Line Item ID: {line_item_id}")
    
    # Extract estimate data
    estimate = {
        "estimate_id": line_item["estimate_id"],
        "cloud": line_item["cloud"],
        "region": line_item["region"],
        "tier": line_item["tier"]
    }
    
    # Calculate costs
    success, response_data, error_message = calculate_line_item_cost(
        line_item, estimate
    )
    
    # Update database
    update_line_item_costs(
        FULL_TABLE_NAME, line_item_id, success, response_data, error_message
    )
    
    if success:
        cost = response_data.get("data", {}).get("cost_per_month", 0)
        print(f"   ✅ Success: ${cost:,.2f}/month")
        success_count += 1
    else:
        print(f"   ❌ Error: {error_message}")
        error_count += 1

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("\n" + "=" * 80)
print("BACKFILL COMPLETE")
print("=" * 80)
print(f"Database: {DB_NAME}")
print(f"Table: {FULL_TABLE_NAME}")
print(f"Total processed: {total}")
print(f"✅ Success: {success_count}")
print(f"❌ Errors: {error_count}")
print(f"Success rate: {success_count/total*100:.1f}%" if total > 0 else "N/A")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Results

# COMMAND ----------

print("\n" + "=" * 80)
print("VERIFICATION QUERIES")
print("=" * 80)

# Count by status
print("\n📊 Count by calculation status:")
count_sql = f"""
SELECT 
    CASE 
        WHEN cost_calculation_response IS NULL THEN 'pending'
        WHEN cost_calculation_response->>'success' = 'true' THEN 'success'
        WHEN cost_calculation_response->>'success' = 'false' THEN 'error'
        ELSE 'unknown'
    END as status,
    COUNT(*) as count
FROM {FULL_TABLE_NAME}
GROUP BY 1
ORDER BY 2 DESC;
"""

results = execute_query(count_sql, fetch=True)
for row in results:
    print(f"   {row['status']}: {row['count']}")

# Show sample successful calculations
print("\n📊 Sample successful calculations:")
sample_sql = f"""
SELECT 
    workload_type,
    workload_name,
    (cost_calculation_response->'data'->>'cost_per_month')::numeric as monthly_cost
FROM {FULL_TABLE_NAME}
WHERE cost_calculation_response->>'success' = 'true'
ORDER BY monthly_cost DESC
LIMIT 5;
"""

results = execute_query(sample_sql, fetch=True)
for row in results:
    print(f"   {row['workload_type']} - {row['workload_name']}: ${row['monthly_cost']:,.2f}/mo")

# Show errors
print("\n❌ Recent errors (if any):")
error_sql = f"""
SELECT 
    workload_type,
    workload_name,
    cost_calculation_response->'error'->>'message' as error_message
FROM {FULL_TABLE_NAME}
WHERE cost_calculation_response->>'success' = 'false'
ORDER BY calculation_completed_at DESC
LIMIT 5;
"""

results = execute_query(error_sql, fetch=True)
if results:
    for row in results:
        print(f"   {row['workload_type']} - {row['workload_name']}")
        print(f"      Error: {row['error_message']}")
else:
    print("   (No errors)")

print("\n" + "=" * 80)
