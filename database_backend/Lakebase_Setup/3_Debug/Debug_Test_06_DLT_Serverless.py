# Databricks notebook source
# MAGIC %md
# MAGIC # Debug Test_06 DLT Serverless - Why All Costs Are $0?
# MAGIC 
# MAGIC This notebook diagnoses why Test_06_DLT_Serverless.py shows $0 for all costs.
# MAGIC 
# MAGIC **Likely Issues:**
# MAGIC 1. Product type mismatch (like Test_04)
# MAGIC 2. Missing pricing data for DLT Serverless
# MAGIC 3. Join issue in view
# MAGIC 4. Missing DBU rates for instance types

# COMMAND ----------

import psycopg2
import pandas as pd
from datetime import datetime
import uuid

# Connection details
DB_HOST = "instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com"
DB_PORT = 5432
DB_NAME = "lakemeter_pricing"
DB_USER = "lakemeter_sync_role"
DB_PASSWORD = dbutils.secrets.get(scope="lakemeter-credentials", key="lakebase-password")

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        sslmode='require'
    )

def query_sql(sql, params=None):
    """Execute a SELECT query and return results as DataFrame"""
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        
        if cursor.description is None:
            return pd.DataFrame()
        
        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()
        
        df = pd.DataFrame(results, columns=columns)
        return df
    except Exception as e:
        print(f"❌ SQL Error: {str(e)}")
        print(f"   Query: {sql[:100]}...")
        if params:
            print(f"   Params: {params}")
        return pd.DataFrame()
    finally:
        if cursor:
            cursor.close()
        conn.close()

def execute_query(sql, params=None, fetch=True):
    """Execute a query (INSERT/UPDATE/SELECT) with optional result fetching"""
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        
        conn.commit()
        
        if fetch and cursor.description:
            columns = [desc[0] for desc in cursor.description]
            results = cursor.fetchall()
            return pd.DataFrame(results, columns=columns)
        return None
    except Exception as e:
        conn.rollback()
        print(f"❌ Execute Error: {str(e)}")
        print(f"   Query: {sql[:100]}...")
        if params:
            print(f"   Params: {params}")
        return None
    finally:
        if cursor:
            cursor.close()
        conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Check DLT Serverless Line Items

# COMMAND ----------

print("=" * 100)
print("🔍 CHECKING DLT SERVERLESS LINE ITEMS")
print("=" * 100)

line_items_sql = """
SELECT 
    li.line_item_id,
    li.workload_type,
    li.serverless_enabled,
    li.serverless_mode,
    li.dlt_edition,
    li.dlt_pipeline_mode,
    li.photon_enabled,
    li.driver_node_type,
    li.worker_node_type,
    li.num_workers,
    li.runs_per_day,
    li.avg_runtime_minutes,
    li.days_per_month,
    li.cloud,
    e.region,
    e.tier
FROM lakemeter.line_items li
JOIN lakemeter.estimates e ON li.estimate_id = e.estimate_id
WHERE li.workload_type = 'DLT' 
  AND li.serverless_enabled = TRUE
ORDER BY e.cloud, e.region, e.tier, li.serverless_mode, li.dlt_pipeline_mode
LIMIT 20;
"""

line_items_df = query_sql(line_items_sql)
print(f"\n📋 Found {len(line_items_df)} DLT Serverless line items:")
if len(line_items_df) > 0:
    print(line_items_df.to_string())
else:
    print("❌ NO DLT SERVERLESS LINE ITEMS FOUND!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Check Instance DBU Rates

# COMMAND ----------

print("\n" + "=" * 100)
print("🔍 CHECKING INSTANCE DBU RATES")
print("=" * 100)

if len(line_items_df) > 0:
    first_item = line_items_df.iloc[0]
    
    instance_rates_sql = """
    SELECT 
        cloud,
        instance_type,
        dbu_rate
    FROM lakemeter.sync_ref_instance_dbu_rates
    WHERE cloud = %s
      AND instance_type IN (%s, %s)
    ORDER BY instance_type;
    """
    
    instance_rates_df = query_sql(
        instance_rates_sql,
        (first_item['cloud'], first_item['driver_node_type'], first_item['worker_node_type'])
    )
    
    print(f"\n📋 Instance DBU Rates for {first_item['cloud']} - {first_item['driver_node_type']}, {first_item['worker_node_type']}:")
    if len(instance_rates_df) > 0:
        print(instance_rates_df.to_string())
    else:
        print(f"❌ NO INSTANCE DBU RATES FOUND for these instance types!")
        print(f"   Cloud: {first_item['cloud']}")
        print(f"   Driver: {first_item['driver_node_type']}")
        print(f"   Worker: {first_item['worker_node_type']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Check DLT Photon Multipliers

# COMMAND ----------

print("\n" + "=" * 100)
print("🔍 CHECKING DLT PHOTON MULTIPLIERS")
print("=" * 100)

if len(line_items_df) > 0:
    first_item = line_items_df.iloc[0]
    
    # DLT editions
    for edition in ['CORE', 'PRO', 'ADVANCED']:
        multiplier_sql = """
        SELECT 
            cloud,
            sku_type,
            feature,
            multiplier
        FROM lakemeter.sync_ref_dbu_multipliers
        WHERE cloud = %s
          AND sku_type LIKE %s
          AND feature IN ('photon', 'standard')
        ORDER BY sku_type, feature;
        """
        
        multiplier_df = query_sql(multiplier_sql, (first_item['cloud'], f'DLT_{edition}%'))
        
        print(f"\n📋 Multipliers for {first_item['cloud']} DLT_{edition}:")
        if len(multiplier_df) > 0:
            print(multiplier_df.to_string())
        else:
            print(f"⚠️  No multipliers found for DLT_{edition}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Check DLT Serverless Pricing (CRITICAL!)

# COMMAND ----------

print("\n" + "=" * 100)
print("🔍 CHECKING DLT SERVERLESS PRICING - MOST CRITICAL!")
print("=" * 100)

if len(line_items_df) > 0:
    # Check for each cloud/region/tier combination
    for idx, row in line_items_df.head(6).iterrows():
        print(f"\n{'─' * 80}")
        print(f"Line Item: {row['cloud']} / {row['region']} / {row['tier']}")
        print(f"  DLT Edition: {row['dlt_edition']}")
        print(f"  Serverless Mode: {row['serverless_mode']}")
        print(f"  Pipeline Mode: {row['dlt_pipeline_mode']}")
        print(f"{'─' * 80}")
        
        # Expected product_type for DLT Serverless
        product_type = 'JOBS_SERVERLESS_COMPUTE'
        
        dbu_pricing_sql = """
        SELECT 
            cloud,
            region,
            tier,
            product_type,
            price_per_dbu
        FROM lakemeter.sync_pricing_dbu_rates
        WHERE cloud = %s
          AND region = %s
          AND tier = %s
          AND product_type = %s;
        """
        
        dbu_pricing_df = query_sql(
            dbu_pricing_sql,
            (row['cloud'], row['region'], row['tier'], product_type)
        )
        
        print(f"Looking for: cloud={row['cloud']}, region={row['region']}, tier={row['tier']}, product_type={product_type}")
        
        if len(dbu_pricing_df) > 0:
            print(f"✅ FOUND DBU Pricing:")
            print(dbu_pricing_df.to_string())
        else:
            print(f"❌ NO DBU PRICING FOUND!")
            print("\n🔍 Let's check what's available for this cloud/region/tier:")
            
            available_sql = """
            SELECT DISTINCT
                product_type,
                price_per_dbu
            FROM lakemeter.sync_pricing_dbu_rates
            WHERE cloud = %s
              AND region = %s
              AND tier = %s
              AND product_type LIKE 'DLT%' OR product_type LIKE 'DELTA%'
            ORDER BY product_type;
            """
            
            available_df = query_sql(available_sql, (row['cloud'], row['region'], row['tier']))
            
            if len(available_df) > 0:
                print(f"Available DLT product_types for {row['cloud']} / {row['region']} / {row['tier']}:")
                print(available_df.to_string())
            else:
                print(f"❌ NO DLT PRICING DATA AT ALL for {row['cloud']} / {row['region']} / {row['tier']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Manual Cost Calculation

# COMMAND ----------

print("\n" + "=" * 100)
print("🧮 MANUAL COST CALCULATION")
print("=" * 100)

if len(line_items_df) > 0:
    first_item = line_items_df.iloc[0]
    
    print(f"\nTesting calculation for first line item:")
    print(f"  Cloud: {first_item['cloud']}")
    print(f"  Region: {first_item['region']}")
    print(f"  Tier: {first_item['tier']}")
    print(f"  Workload: {first_item['workload_type']}")
    print(f"  DLT Edition: {first_item['dlt_edition']}")
    print(f"  Serverless: {first_item['serverless_enabled']}")
    print(f"  Serverless Mode: {first_item['serverless_mode']}")
    print(f"  Pipeline Mode: {first_item['dlt_pipeline_mode']}")
    print(f"  Driver: {first_item['driver_node_type']}")
    print(f"  Worker: {first_item['worker_node_type']}")
    print(f"  Num Workers: {first_item['num_workers']}")
    print(f"  Usage: {first_item['runs_per_day']} runs/day × {first_item['avg_runtime_minutes']} min × {first_item['days_per_month']} days/month")
    
    # Get instance DBU rates
    instance_sql = """
    SELECT instance_type, dbu_rate
    FROM lakemeter.sync_ref_instance_dbu_rates
    WHERE cloud = %s AND instance_type IN (%s, %s);
    """
    instances = query_sql(instance_sql, (first_item['cloud'], first_item['driver_node_type'], first_item['worker_node_type']))
    
    driver_dbu = 0
    worker_dbu = 0
    if len(instances) > 0:
        for idx, inst in instances.iterrows():
            if inst['instance_type'] == first_item['driver_node_type']:
                driver_dbu = inst['dbu_rate']
            elif inst['instance_type'] == first_item['worker_node_type']:
                worker_dbu = inst['dbu_rate']
    
    print(f"\n📊 DBU Rates:")
    print(f"  Driver DBU Rate: {driver_dbu}")
    print(f"  Worker DBU Rate: {worker_dbu}")
    
    # Calculate DBU per hour
    # For DLT serverless: (driver_dbu + worker_dbu * num_workers) * serverless_mode_multiplier
    # Photon is always enabled for serverless (multiplier = 1.0)
    dbu_per_hour = (driver_dbu + (worker_dbu * first_item['num_workers'])) * 1.0  # Photon multiplier = 1.0
    
    if first_item['serverless_mode'] == 'performance':
        dbu_per_hour *= 2
    
    print(f"\n🔢 DBU Calculation:")
    print(f"  Base DBU/hour: ({driver_dbu} + {worker_dbu} × {first_item['num_workers']}) = {driver_dbu + (worker_dbu * first_item['num_workers'])}")
    print(f"  Serverless Mode: {first_item['serverless_mode']} (multiplier: {'2.0' if first_item['serverless_mode'] == 'performance' else '1.0'})")
    print(f"  Final DBU/hour: {dbu_per_hour}")
    
    # Calculate hours per month
    hours_per_month = first_item['runs_per_day'] * (first_item['avg_runtime_minutes'] / 60.0) * first_item['days_per_month']
    print(f"  Hours/month: {first_item['runs_per_day']} × ({first_item['avg_runtime_minutes']} / 60) × {first_item['days_per_month']} = {hours_per_month}")
    
    # Calculate DBU per month
    dbu_per_month = dbu_per_hour * hours_per_month
    print(f"  DBU/month: {dbu_per_hour} × {hours_per_month} = {dbu_per_month}")
    
    # Get DBU price
    dbu_price_sql = """
    SELECT price_per_dbu
    FROM lakemeter.sync_pricing_dbu_rates
    WHERE cloud = %s AND region = %s AND tier = %s AND product_type = 'JOBS_SERVERLESS_COMPUTE';
    """
    price_result = query_sql(dbu_price_sql, (first_item['cloud'], first_item['region'], first_item['tier']))
    
    if len(price_result) > 0:
        price_per_dbu = price_result.iloc[0]['price_per_dbu']
        print(f"\n💰 DBU Pricing:")
        print(f"  Price per DBU: ${price_per_dbu}")
        
        total_cost = dbu_per_month * float(price_per_dbu)
        print(f"  Total Cost: {dbu_per_month} × ${price_per_dbu} = ${total_cost:.2f}")
    else:
        print(f"\n❌ NO PRICING FOUND!")
        print(f"  This is why cost_per_month = 0!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Check View Calculation

# COMMAND ----------

print("\n" + "=" * 100)
print("🔍 CHECKING VIEW CALCULATION")
print("=" * 100)

if len(line_items_df) > 0:
    first_item = line_items_df.iloc[0]
    
    view_sql = """
    SELECT 
        line_item_id,
        cloud,
        region,
        tier,
        workload_type,
        serverless_enabled,
        serverless_mode,
        dlt_edition,
        dlt_pipeline_mode,
        hours_per_month,
        driver_dbu_rate,
        worker_dbu_rate,
        photon_multiplier,
        dbu_per_hour,
        dbu_per_month,
        price_per_dbu,
        product_type_for_pricing,
        dbu_cost_per_month,
        vm_cost_per_month,
        cost_per_month
    FROM lakemeter.v_line_items_with_costs
    WHERE line_item_id = %s;
    """
    
    view_result = query_sql(view_sql, (first_item['line_item_id'],))
    
    if len(view_result) > 0:
        print("\n📋 View Calculation Result:")
        for col in view_result.columns:
            print(f"  {col}: {view_result.iloc[0][col]}")
        
        print("\n🔍 Analysis:")
        result = view_result.iloc[0]
        
        if result['driver_dbu_rate'] == 0 or result['worker_dbu_rate'] == 0:
            print("  ❌ Instance DBU rates are 0! Check sync_ref_instance_dbu_rates.")
        
        if result['dbu_per_hour'] == 0:
            print("  ❌ dbu_per_hour is 0! Issue in DBU calculation logic.")
        
        if result['price_per_dbu'] == 0:
            print("  ❌ price_per_dbu is 0! Check sync_pricing_dbu_rates for product_type_for_pricing.")
            print(f"     Looking for: {result['product_type_for_pricing']}")
        
        if result['hours_per_month'] == 0:
            print("  ❌ hours_per_month is 0! Check runs_per_day, avg_runtime_minutes, days_per_month.")
    else:
        print(f"❌ Line item not found in view!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Check All DLT Product Types Available

# COMMAND ----------

print("\n" + "=" * 100)
print("🔍 ALL DLT PRODUCT TYPES AVAILABLE IN PRICING")
print("=" * 100)

if len(line_items_df) > 0:
    first_item = line_items_df.iloc[0]
    
    all_dlt_sql = """
    SELECT DISTINCT
        product_type,
        COUNT(*) as region_tier_count,
        MIN(price_per_dbu) as min_price,
        MAX(price_per_dbu) as max_price
    FROM lakemeter.sync_pricing_dbu_rates
    WHERE cloud = %s
      AND (product_type LIKE 'DLT%' OR product_type LIKE 'DELTA%')
    GROUP BY product_type
    ORDER BY product_type;
    """
    
    all_dlt_df = query_sql(all_dlt_sql, (first_item['cloud'],))
    
    print(f"\nAll DLT product types for {first_item['cloud']}:")
    if len(all_dlt_df) > 0:
        print(all_dlt_df.to_string())
    else:
        print("❌ NO DLT PRODUCT TYPES FOUND!")

# COMMAND ----------

print("\n" + "=" * 100)
print("✅ DIAGNOSTIC COMPLETE")
print("=" * 100)
print("\nLook for ❌ errors above to identify the root cause.")
print("\nMost likely issues:")
print("  1. price_per_dbu = 0 (pricing data missing or product_type mismatch)")
print("  2. dbu_per_hour = 0 (instance DBU rates missing)")
print("  3. hours_per_month = 0 (usage parameters missing)")

