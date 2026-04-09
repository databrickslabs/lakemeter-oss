"""
Backfill Line Item Cost Calculation Responses

This script:
1. Fetches all line items that need cost calculation
2. Calls the appropriate calculation API for each workload type
3. Stores the full API response in cost_calculation_response JSONB column
4. Tracks success/failure status

Usage:
    # Test on backup table first
    python backfill_line_item_costs.py pending --table backup --limit 10
    
    # Run on main table for all pending items
    python backfill_line_item_costs.py pending --table main
    
    # Re-calculate all items (including success/error)
    python backfill_line_item_costs.py all --table main
    
    # Fix only errors
    python backfill_line_item_costs.py error --table main
"""

import asyncio
import json
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = "postgresql+asyncpg://postgres:lakemeter2025!@localhost:5432/lakemeter"

# API base URL
API_BASE_URL = "http://localhost:8000"

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
    ("FMAPI_DATABRICKS", None, None): "/api/v1/calculate/fmapi-databricks",
    ("FMAPI_PROPRIETARY", None, None): "/api/v1/calculate/fmapi-proprietary",
    ("LAKEBASE", None, None): "/api/v1/calculate/lakebase",
}


def get_endpoint(workload_type: str, serverless_enabled: Optional[bool], 
                 dbsql_warehouse_type: Optional[str]) -> Optional[str]:
    """Get the appropriate API endpoint for a workload type"""
    # For FMAPI, check the provider
    if workload_type == "FMAPI":
        # This will be handled separately by checking fmapi_provider
        return None
    
    key = (workload_type, serverless_enabled, dbsql_warehouse_type)
    return ENDPOINT_MAPPING.get(key)


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
        # Classic compute fields
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
            # Serverless fields
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
            "dlt_edition": line_item.get("dlt_edition", "core"),
            "photon_enabled": line_item.get("photon_enabled", False),
        })
        
        if not line_item.get("serverless_enabled"):
            payload.update({
                "driver_node_type": line_item["driver_node_type"],
                "worker_node_type": line_item["worker_node_type"],
                "num_workers": line_item["num_workers"],
                "driver_pricing_tier": line_item.get("driver_pricing_tier", "on_demand"),
                "worker_pricing_tier": line_item.get("worker_pricing_tier", "on_demand"),
                "driver_payment_option": line_item.get("driver_payment_option", "NA"),
                "worker_payment_option": line_item.get("worker_payment_option", "NA"),
            })
        else:
            payload["serverless_mode"] = line_item.get("serverless_mode", "standard")
        
        # Usage
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
        
        # VM pricing only for classic/pro
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
    
    elif workload_type == "FMAPI":
        # Determine endpoint based on provider
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
            "storage_gb": line_item["lakebase_storage_gb"],
            "ha_nodes": line_item.get("lakebase_ha_nodes", 1),
            "backup_retention_days": line_item.get("lakebase_backup_retention_days", 7),
            "hours_per_month": float(line_item.get("hours_per_month", 730)),  # Default: 24/7
        })
    
    return payload


async def calculate_line_item_cost(
    client: httpx.AsyncClient,
    line_item: Dict[str, Any],
    estimate: Dict[str, Any]
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Calculate cost for a single line item
    
    Returns:
        (success, response_data, error_message)
    """
    try:
        # Get endpoint
        workload_type = line_item["workload_type"]
        
        # Special handling for FMAPI
        if workload_type == "FMAPI":
            provider = line_item.get("fmapi_provider", "").upper()
            if "DATABRICKS" in provider or "DBRX" in provider:
                endpoint = "/api/v1/calculate/fmapi-databricks"
            else:
                endpoint = "/api/v1/calculate/fmapi-proprietary"
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
        
        # Call API
        response = await client.post(
            f"{API_BASE_URL}{endpoint}",
            json=payload,
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return True, result, None
            else:
                error_msg = result.get("error", {}).get("message", "Unknown error")
                return False, None, error_msg
        else:
            return False, None, f"HTTP {response.status_code}: {response.text[:200]}"
            
    except Exception as e:
        return False, None, str(e)


async def update_line_item_costs(
    db: AsyncSession,
    table_name: str,
    line_item_id: str,
    success: bool,
    response_data: Optional[Dict[str, Any]],
    error_message: Optional[str]
):
    """Update line item with calculated costs"""
    
    if success:
        update_query = text(f"""
            UPDATE lakemeter.{table_name}
            SET 
                cost_calculation_response = :response_data::jsonb,
                calculation_completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE line_item_id = :line_item_id
        """)
        
        await db.execute(update_query, {
            "line_item_id": line_item_id,
            "response_data": json.dumps(response_data)
        })
    else:
        # Store error in same response structure
        error_response = {
            "success": False,
            "error": {
                "message": error_message,
                "failed_at": datetime.now().isoformat()
            }
        }
        
        update_query = text(f"""
            UPDATE lakemeter.{table_name}
            SET 
                cost_calculation_response = :response_data::jsonb,
                calculation_completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE line_item_id = :line_item_id
        """)
        
        await db.execute(update_query, {
            "line_item_id": line_item_id,
            "response_data": json.dumps(error_response)
        })
    
    await db.commit()


async def backfill_all_line_items(
    status_filter: str = "pending",
    limit: Optional[int] = None,
    table_suffix: str = ""
):
    """
    Backfill calculated costs for all line items
    
    Args:
        status_filter: Only process items with this status:
            - pending: Items that have never been calculated (cost_calculation_response IS NULL)
            - error: Items where calculation failed (success = false)
            - all: All items (recalculate everything)
        limit: Max number of items to process (None = all)
        table_suffix: Table to process ('backup' or '' for main table)
    """
    table_name = f"line_items_{table_suffix}" if table_suffix else "line_items"
    
    print("=" * 80)
    print("BACKFILL LINE ITEM COST CALCULATION RESPONSES")
    print("=" * 80)
    print(f"Table: lakemeter.{table_name}")
    print(f"Status filter: {status_filter}")
    print(f"Limit: {limit or 'None (process all)'}")
    print()
    
    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Build query based on filter
    where_clause = ""
    if status_filter == "pending":
        where_clause = "AND li.cost_calculation_response IS NULL"
    elif status_filter == "error":
        where_clause = "AND li.cost_calculation_response->>'success' = 'false'"
    # 'all' = no where clause
    
    limit_clause = f"LIMIT {limit}" if limit else ""
    
    query = text(f"""
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
        FROM lakemeter.{table_name} li
        JOIN lakemeter.estimates e ON li.estimate_id = e.estimate_id
        WHERE 1=1 {where_clause}
        ORDER BY li.created_at ASC
        {limit_clause}
    """)
    
    async with async_session() as db:
        result = await db.execute(query)
        line_items = result.fetchall()
    
    total = len(line_items)
    print(f"📊 Found {total} line items to process\n")
    
    if total == 0:
        print("✅ No line items to process")
        return
    
    # Process line items
    success_count = 0
    error_count = 0
    
    async with httpx.AsyncClient() as client:
        for idx, row in enumerate(line_items, 1):
            line_item = dict(row._mapping)
            line_item_id = line_item["line_item_id"]
            workload_type = line_item["workload_type"]
            workload_name = line_item["workload_name"] or "Unnamed"
            
            print(f"[{idx}/{total}] Processing: {workload_type} - {workload_name}")
            
            # Extract estimate data
            estimate = {
                "estimate_id": line_item["estimate_id"],
                "cloud": line_item["cloud"],
                "region": line_item["region"],
                "tier": line_item["tier"]
            }
            
            # Calculate costs
            success, response_data, error_message = await calculate_line_item_cost(
                client, line_item, estimate
            )
            
            # Update database
            async with async_session() as db:
                await update_line_item_costs(
                    db, table_name, line_item_id, success, response_data, error_message
                )
            
            if success:
                cost = response_data.get("data", {}).get("cost_per_month", 0)
                print(f"   ✅ Success: ${cost:,.2f}/month")
                success_count += 1
            else:
                print(f"   ❌ Error: {error_message}")
                error_count += 1
            
            print()
            
            # Small delay to avoid overwhelming API
            await asyncio.sleep(0.1)
    
    # Summary
    print("=" * 80)
    print("BACKFILL COMPLETE")
    print("=" * 80)
    print(f"Total processed: {total}")
    print(f"✅ Success: {success_count}")
    print(f"❌ Errors: {error_count}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backfill cost calculation responses for line items"
    )
    parser.add_argument(
        "status",
        choices=["pending", "error", "stale", "all"],
        default="pending",
        help="Which line items to process (default: pending)"
    )
    parser.add_argument(
        "--table",
        choices=["main", "backup"],
        default="main",
        help="Which table to process: main (line_items) or backup (line_items_backup)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of items to process (default: all)"
    )
    
    args = parser.parse_args()
    
    table_suffix = "backup" if args.table == "backup" else ""
    
    # Run backfill
    asyncio.run(backfill_all_line_items(args.status, args.limit, table_suffix))
