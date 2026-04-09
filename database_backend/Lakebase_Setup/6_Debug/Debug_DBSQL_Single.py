# Databricks notebook source
# MAGIC %md
# MAGIC # 🐛 DEBUG: Single DBSQL Classic Scenario
# MAGIC
# MAGIC Test just ONE scenario to see the **FULL** error message

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import pandas as pd
import psycopg2

def get_connection():
    return psycopg2.connect(
        host=LAKEBASE_HOST,
        port=LAKEBASE_PORT,
        database=LAKEBASE_DATABASE,
        user=LAKEBASE_USER,
        password=LAKEBASE_PASSWORD,
        sslmode='require'
    )

conn = get_connection()
print(f"✅ Connected to Lakebase: {LAKEBASE_HOST}:{LAKEBASE_PORT}/{LAKEBASE_DATABASE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🧪 Test: AWS us-east-1 STANDARD 2X-Large 1cl on_demand

# COMMAND ----------

test_sql = """
SELECT 
    'TEST: AWS us-east-1 STANDARD 2X-Large'::VARCHAR as label,
    *
FROM lakemeter.calculate_line_item_costs(
    'DBSQL'::VARCHAR,
    'AWS'::VARCHAR,
    'us-east-1'::VARCHAR,
    'STANDARD'::VARCHAR,
    FALSE::BOOLEAN,
    FALSE::BOOLEAN,
    NULL::VARCHAR,
    NULL::VARCHAR,
    NULL::VARCHAR,
    0::INT,
    'NA'::VARCHAR,
    'NA'::VARCHAR,
    8::INT,
    60::INT,
    30::INT,
    'standard'::VARCHAR,
    'classic'::VARCHAR,
    '2X-Large'::VARCHAR,
    1::INT,
    'on_demand'::VARCHAR,
    NULL::VARCHAR,
    0::DECIMAL,
    NULL::VARCHAR,
    NULL::VARCHAR,
    NULL::VARCHAR,
    'global'::VARCHAR,
    'standard'::VARCHAR,
    'pay_per_token'::VARCHAR,
    0::BIGINT,
    0::BIGINT,
    0::INT,
    1::INT,
    'NA'::VARCHAR,
    'NA'::VARCHAR,
    'NA'::VARCHAR
);
"""

print("🔍 Running test...")
print("=" * 100)

try:
    result = pd.read_sql_query(test_sql, conn)
    print("✅ SUCCESS!")
    print(f"\nColumns returned: {list(result.columns)}")
    print(f"\nFirst row:")
    display(result)
    
    # Check costs
    dbu_cost = float(result['dbu_cost_per_month'].iloc[0])
    vm_cost = float(result['vm_cost_per_month'].iloc[0]) if 'vm_cost_per_month' in result.columns else 0
    total_cost = float(result['cost_per_month'].iloc[0])
    
    print(f"\n💰 Costs:")
    print(f"   DBU: ${dbu_cost:,.2f}/month")
    if 'vm_cost_per_month' in result.columns:
        print(f"   VM:  ${vm_cost:,.2f}/month")
    print(f"   Total: ${total_cost:,.2f}/month")
    
    if total_cost == 0:
        print("\n⚠️  WARNING: Total cost is $0 - something is wrong!")
    
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}")
    print("=" * 100)
    print("FULL ERROR MESSAGE:")
    print("=" * 100)
    print(str(e))
    print("\n" + "=" * 100)
    print("STACK TRACE:")
    print("=" * 100)
    import traceback
    traceback.print_exc()

finally:
    conn.close()

