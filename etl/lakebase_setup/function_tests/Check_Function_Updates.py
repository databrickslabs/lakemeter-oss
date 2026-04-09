# Databricks notebook source
# MAGIC %md
# MAGIC # 🔍 Check Which Functions Have Been Updated
# MAGIC
# MAGIC Verify if the case-insensitive logic has been applied to the database functions.

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import pandas as pd

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check Function Definitions

# COMMAND ----------

print("=" * 100)
print("CHECKING IF FUNCTIONS HAVE CASE-INSENSITIVE LOGIC")
print("=" * 100)

# Check get_product_type_for_pricing
print("\n1️⃣  get_product_type_for_pricing()")
print("─" * 100)

check_utility_sql = """
SELECT 
    p.proname as function_name,
    pg_get_functiondef(p.oid) as function_definition
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'lakemeter' 
  AND p.proname = 'get_product_type_for_pricing';
"""

try:
    result = execute_query(check_utility_sql)
    if not result.empty:
        func_def = result.iloc[0]['function_definition']
        
        # Check for case-insensitive logic
        if 'v_workload_type := UPPER' in func_def or 'UPPER(p_workload_type)' in func_def:
            print("✅ UPDATED: Function has case-insensitive logic (UPPER conversion found)")
        else:
            print("❌ OLD VERSION: Function does NOT have case-insensitive logic")
            print("   → You need to RUN: 4_Functions/01_Utility_Functions")
    else:
        print("❌ Function does NOT exist!")
except Exception as e:
    print(f"❌ Error: {e}")

# Check calculate_dbsql_vm_costs
print("\n2️⃣  calculate_dbsql_vm_costs()")
print("─" * 100)

check_vm_sql = """
SELECT 
    p.proname as function_name,
    pg_get_functiondef(p.oid) as function_definition
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'lakemeter' 
  AND p.proname = 'calculate_dbsql_vm_costs';
"""

try:
    result = execute_query(check_vm_sql)
    if not result.empty:
        func_def = result.iloc[0]['function_definition']
        
        # Check for case-insensitive logic
        if 'v_warehouse_type := LOWER' in func_def or 'LOWER(p_dbsql_warehouse_type)' in func_def:
            print("✅ UPDATED: Function has case-insensitive logic (LOWER conversion found)")
        else:
            print("❌ OLD VERSION: Function does NOT have case-insensitive logic")
            print("   → You need to RUN: 4_Functions/08_VM_Cost_Calculators")
    else:
        print("❌ Function does NOT exist!")
except Exception as e:
    print(f"❌ Error: {e}")

# Check calculate_line_item_costs
print("\n3️⃣  calculate_line_item_costs()")
print("─" * 100)

check_main_sql = """
SELECT 
    p.proname as function_name,
    pg_get_function_identity_arguments(p.oid) as arguments
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'lakemeter' 
  AND p.proname = 'calculate_line_item_costs';
"""

try:
    result = execute_query(check_main_sql)
    if not result.empty:
        print("✅ EXISTS: Function found")
        print(f"   Parameters: {result.iloc[0]['arguments'][:100]}...")
    else:
        print("❌ Function does NOT exist!")
        print("   → You need to RUN: 4_Functions/09_Main_Orchestrator")
except Exception as e:
    print(f"❌ Error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("\n" + "=" * 100)
print("🎯 ACTION REQUIRED")
print("=" * 100)

print("\nTo fix the VM cost issue, you need to RUN these notebooks in Databricks:\n")
print("1. 4_Functions/01_Utility_Functions")
print("   → Updates get_product_type_for_pricing() with case-insensitive logic")
print("")
print("2. 4_Functions/08_VM_Cost_Calculators")
print("   → Updates calculate_dbsql_vm_costs() with case-insensitive logic")
print("")
print("3. 4_Functions/09_Main_Orchestrator")
print("   → Updates calculate_line_item_costs() (depends on functions above)")
print("")
print("Then re-run Test_Func_08_DBSQL_Pro with 'Clear state and outputs'")
print("=" * 100)




