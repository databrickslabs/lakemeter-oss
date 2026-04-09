# Databricks notebook source
# MAGIC %md
# MAGIC # 🔍 Check Main Orchestrator Function Status

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
import pandas as pd

def get_connection():
    """Create and return a PostgreSQL connection"""
    return psycopg2.connect(
        host=LAKEBASE_HOST,
        port=LAKEBASE_PORT,
        database=LAKEBASE_DB,
        user=LAKEBASE_USER,
        password=LAKEBASE_PASSWORD
    )

def execute_query(query, params=None, fetch=True):
    """Execute a query and optionally fetch results"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch:
                columns = [desc[0] for desc in cur.description] if cur.description else []
                results = cur.fetchall()
                conn.commit()
                return pd.DataFrame(results, columns=columns) if results else pd.DataFrame()
            else:
                conn.commit()
                return None
    finally:
        conn.close()

# COMMAND ----------

print("=" * 100)
print("CHECKING: calculate_line_item_costs() FUNCTION")
print("=" * 100)

# Check if function exists at all
check_exists_sql = """
SELECT 
    p.proname as function_name,
    pg_get_function_identity_arguments(p.oid) as arguments,
    p.pronargs as num_params
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'lakemeter' 
  AND p.proname = 'calculate_line_item_costs';
"""

print("\n1️⃣  Does function exist?")
print("─" * 100)

try:
    result = execute_query(check_exists_sql)
    if result.empty:
        print("❌ Function does NOT exist in the database!")
        print("\n🔍 Possible reasons:")
        print("   1. 09_Main_Orchestrator notebook threw an error during execution")
        print("   2. Function creation SQL has syntax errors")
        print("   3. Permissions issue preventing function creation")
        print("\n🎯 ACTION: Re-run 09_Main_Orchestrator and look for error messages!")
    else:
        print(f"✅ Function EXISTS with {result.iloc[0]['num_params']} parameters")
        print(f"\n📋 Function signature:")
        print(f"   calculate_line_item_costs({result.iloc[0]['arguments'][:200]}...)")
        
        # Show parameter details
        print("\n2️⃣  Parameter details:")
        print("─" * 100)
        
        param_details_sql = """
        SELECT 
            p.proname as function_name,
            p.pronargs as total_params,
            pg_get_function_arguments(p.oid) as param_details
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'lakemeter' 
          AND p.proname = 'calculate_line_item_costs';
        """
        
        param_result = execute_query(param_details_sql)
        if not param_result.empty:
            total = param_result.iloc[0]['total_params']
            details = param_result.iloc[0]['param_details']
            
            print(f"Total parameters: {total}")
            print(f"\nParameter list:")
            
            # Split and show first 10 parameters
            params = details.split(',')
            for i, param in enumerate(params[:10], 1):
                print(f"  {i:2}. {param.strip()}")
            
            if len(params) > 10:
                print(f"  ... and {len(params) - 10} more parameters")
        
        # Test with explicit casts
        print("\n3️⃣  Testing function call with explicit type casts:")
        print("─" * 100)
        
        test_call_sql = """
        SELECT * FROM lakemeter.calculate_line_item_costs(
            'DBSQL'::VARCHAR,
            'AWS'::VARCHAR,
            'us-east-1'::VARCHAR,
            'PREMIUM'::VARCHAR,
            NULL::VARCHAR,
            NULL::VARCHAR,
            0::INT,
            FALSE::BOOLEAN,
            'standard'::VARCHAR,
            NULL::VARCHAR,
            FALSE::BOOLEAN,
            FALSE::BOOLEAN,
            'light'::VARCHAR,
            8::INT,
            60::INT,
            30::INT,
            'standard'::VARCHAR,
            'PRO'::VARCHAR,
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
        )
        LIMIT 1;
        """
        
        try:
            test_result = execute_query(test_call_sql)
            print("✅ Function call SUCCEEDED!")
            
            if not test_result.empty:
                print(f"\n💰 Results:")
                if 'dbu_cost_per_month' in test_result.columns:
                    dbu_cost = test_result.iloc[0]['dbu_cost_per_month']
                    print(f"   DBU cost: ${dbu_cost:,.2f}")
                
                if 'vm_cost_per_month' in test_result.columns:
                    vm_cost = test_result.iloc[0]['vm_cost_per_month']
                    print(f"   VM cost:  ${vm_cost:,.2f}")
                    
                    if vm_cost == 0:
                        print("   ❌ VM cost is STILL $0!")
                    else:
                        print("   ✅ VM cost is calculated!")
                
                if 'cost_per_month' in test_result.columns:
                    total = test_result.iloc[0]['cost_per_month']
                    print(f"   Total:    ${total:,.2f}")
        except Exception as e:
            print(f"❌ Function call FAILED: {e}")
            print("\n🔍 This might be a parameter mismatch issue")
            
except Exception as e:
    print(f"❌ Error checking function: {e}")

# COMMAND ----------

# Check all lakemeter functions
print("\n" + "=" * 100)
print("ALL LAKEMETER FUNCTIONS")
print("=" * 100)

all_functions_sql = """
SELECT 
    p.proname as function_name,
    p.pronargs as num_params
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'lakemeter'
ORDER BY p.proname;
"""

try:
    all_funcs = execute_query(all_functions_sql)
    if all_funcs.empty:
        print("❌ NO functions found in lakemeter schema!")
    else:
        print(f"✅ Found {len(all_funcs)} function(s):")
        display(all_funcs)
except Exception as e:
    print(f"❌ Error: {e}")

# COMMAND ----------

print("\n" + "=" * 100)
print("🎯 SUMMARY")
print("=" * 100)

print("\nIf calculate_line_item_costs does NOT exist:")
print("  → Re-run 09_Main_Orchestrator")
print("  → Look for error messages during execution")
print("  → Check the output for 'Function created' message")
print("")
print("If calculate_line_item_costs EXISTS but test fails:")
print("  → Parameter count mismatch")
print("  → Need to re-create with correct signature")
print("")
print("If VM cost is STILL $0:")
print("  → Main function might not be calling the VM cost sub-function")
print("  → Or passing wrong parameters to it")




