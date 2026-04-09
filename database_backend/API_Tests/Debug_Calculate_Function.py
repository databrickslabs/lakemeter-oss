# Databricks notebook source
# MAGIC %md
# MAGIC # Debug: Test calculate_line_item_costs Function
# MAGIC
# MAGIC **Purpose:** Test the database function directly to see the actual error

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup Database Connection

# COMMAND ----------

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import asyncio

# Get OAuth token from notebook context
token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()

# Database configuration
DATABRICKS_HOST = "https://fe-vm-lakemeter.cloud.databricks.com"
DATABRICKS_HTTP_PATH = "/sql/1.0/warehouses/fac2abc3f5e38a9f"

# Create connection URL
DATABASE_URL = f"databricks://token:{token}@{DATABRICKS_HOST.replace('https://', '')}?http_path={DATABRICKS_HTTP_PATH}&catalog=lakemeter_pricing&schema=lakemeter"

print(f"✅ Connection URL: {DATABASE_URL[:60]}...")
print(f"✅ OAuth Token: {token[:30]}...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Async Engine and Session

# COMMAND ----------

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debug
    future=True,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

# Create session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

print("✅ Async engine and session factory created")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 1: Simple Query (Verify Connection)

# COMMAND ----------

async def test_connection():
    """Test basic database connectivity"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 'Connection works!' as message"))
        row = result.fetchone()
        return row[0]

result = asyncio.run(test_connection())
print(f"✅ {result}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 2: Call Function with Named Parameters (Current Approach)

# COMMAND ----------

async def test_function_named_params():
    """Test the function using named parameters"""
    async with AsyncSessionLocal() as session:
        try:
            query = text("""
                SELECT 
                    dbu_per_hour,
                    hours_per_month,
                    dbu_per_month,
                    dbu_price,
                    dbu_cost_per_month,
                    driver_vm_cost_per_hour,
                    worker_vm_cost_per_hour,
                    total_vm_cost_per_hour,
                    driver_vm_cost_per_month,
                    total_worker_vm_cost_per_month,
                    vm_cost_per_month,
                    cost_per_month
                FROM lakemeter.calculate_line_item_costs(
                    :p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10,
                    :p11, :p12, :p13, :p14, :p15, :p16, :p17, :p18, :p19, :p20,
                    :p21, :p22, :p23, :p24, :p25, :p26, :p27, :p28, :p29, :p30,
                    :p31, :p32, :p33, :p34, :p35
                )
            """)
            
            result = await session.execute(query, {
                "p1": "JOBS",
                "p2": "AWS",
                "p3": "us-east-1",
                "p4": "PREMIUM",
                "p5": False,
                "p6": False,
                "p7": None,
                "p8": "m5.xlarge",
                "p9": "m5.xlarge",
                "p10": 1,
                "p11": "on_demand",
                "p12": "on_demand",
                "p13": 1,
                "p14": 60,
                "p15": 30,
                "p16": None,
                "p17": "standard",
                "p18": None,
                "p19": None,
                "p20": 1,
                "p21": "on_demand",
                "p22": None,
                "p23": 0,
                "p24": None,
                "p25": None,
                "p26": None,
                "p27": "global",
                "p28": "all",
                "p29": "input_token",
                "p30": 0,
                "p31": 0,
                "p32": 1,
                "p33": "NA",
                "p34": "NA",
                "p35": "NA"
            })
            
            row = result.fetchone()
            return {
                "success": True,
                "dbu_per_hour": float(row[0]),
                "hours_per_month": float(row[1]),
                "dbu_per_month": float(row[2]),
                "dbu_price": float(row[3]),
                "dbu_cost_per_month": float(row[4]),
                "driver_vm_cost_per_hour": float(row[5]),
                "worker_vm_cost_per_hour": float(row[6]),
                "total_vm_cost_per_hour": float(row[7]),
                "driver_vm_cost_per_month": float(row[8]),
                "total_worker_vm_cost_per_month": float(row[9]),
                "vm_cost_per_month": float(row[10]),
                "cost_per_month": float(row[11])
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }

result = asyncio.run(test_function_named_params())
print("\n" + "=" * 80)
print("TEST RESULT: Named Parameters (:p1, :p2...)")
print("=" * 80)

if result.get("success"):
    print("✅ SUCCESS!")
    print(f"\n💰 Results:")
    print(f"   DBU per hour: {result['dbu_per_hour']}")
    print(f"   Hours per month: {result['hours_per_month']}")
    print(f"   Total cost per month: ${result['cost_per_month']:.2f}")
    print(f"   - DBU cost: ${result['dbu_cost_per_month']:.2f}")
    print(f"   - VM cost: ${result['vm_cost_per_month']:.2f}")
else:
    print("❌ FAILED!")
    print(f"\nError Type: {result.get('error_type')}")
    print(f"Error Message: {result.get('error')}")
    print(f"\nFull Traceback:")
    print(result.get('traceback'))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 3: Call Function Directly (Raw SQL)

# COMMAND ----------

async def test_function_raw_sql():
    """Test the function using raw SQL"""
    async with AsyncSessionLocal() as session:
        try:
            query = text("""
                SELECT 
                    dbu_per_hour,
                    hours_per_month,
                    dbu_per_month,
                    dbu_price,
                    dbu_cost_per_month,
                    driver_vm_cost_per_hour,
                    worker_vm_cost_per_hour,
                    total_vm_cost_per_hour,
                    driver_vm_cost_per_month,
                    total_worker_vm_cost_per_month,
                    vm_cost_per_month,
                    cost_per_month
                FROM lakemeter.calculate_line_item_costs(
                    'JOBS', 'AWS', 'us-east-1', 'PREMIUM',
                    FALSE, FALSE, NULL, 'm5.xlarge', 'm5.xlarge', 1,
                    'on_demand', 'on_demand', 1, 60, 30, NULL, 'standard',
                    NULL, NULL, 1, 'on_demand', NULL, 0, NULL, NULL, NULL,
                    'global', 'all', 'input_token', 0, 0, 1, 'NA', 'NA', 'NA'
                )
            """)
            
            result = await session.execute(query)
            row = result.fetchone()
            
            return {
                "success": True,
                "dbu_per_hour": float(row[0]),
                "hours_per_month": float(row[1]),
                "dbu_per_month": float(row[2]),
                "dbu_price": float(row[3]),
                "dbu_cost_per_month": float(row[4]),
                "driver_vm_cost_per_hour": float(row[5]),
                "worker_vm_cost_per_hour": float(row[6]),
                "total_vm_cost_per_hour": float(row[7]),
                "driver_vm_cost_per_month": float(row[8]),
                "total_worker_vm_cost_per_month": float(row[9]),
                "vm_cost_per_month": float(row[10]),
                "cost_per_month": float(row[11])
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }

result = asyncio.run(test_function_raw_sql())
print("\n" + "=" * 80)
print("TEST RESULT: Raw SQL (Hardcoded Values)")
print("=" * 80)

if result.get("success"):
    print("✅ SUCCESS!")
    print(f"\n💰 Results:")
    print(f"   DBU per hour: {result['dbu_per_hour']}")
    print(f"   Hours per month: {result['hours_per_month']}")
    print(f"   Total cost per month: ${result['cost_per_month']:.2f}")
    print(f"   - DBU cost: ${result['dbu_cost_per_month']:.2f}")
    print(f"   - VM cost: ${result['vm_cost_per_month']:.2f}")
else:
    print("❌ FAILED!")
    print(f"\nError Type: {result.get('error_type')}")
    print(f"Error Message: {result.get('error')}")
    print(f"\nFull Traceback:")
    print(result.get('traceback'))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC Compare the results:
# MAGIC - **Test 2** (Named params): Shows if SQLAlchemy parameter binding works
# MAGIC - **Test 3** (Raw SQL): Shows if the function works with hardcoded values
# MAGIC
# MAGIC If Test 3 works but Test 2 fails, the issue is with parameter binding.

# COMMAND ----------



