# Databricks notebook source
# MAGIC %md
# MAGIC # 🔍 Comprehensive Case Sensitivity Audit
# MAGIC
# MAGIC Check ALL functions for case-sensitive string comparisons

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
import pandas as pd
import re

def get_connection():
    return psycopg2.connect(
        host=LAKEBASE_HOST,
        port=LAKEBASE_PORT,
        database=LAKEBASE_DB,
        user=LAKEBASE_USER,
        password=LAKEBASE_PASSWORD
    )

def execute_query(query):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            columns = [desc[0] for desc in cur.description] if cur.description else []
            results = cur.fetchall()
            conn.commit()
            return pd.DataFrame(results, columns=columns) if results else pd.DataFrame()
    finally:
        conn.close()

# COMMAND ----------

print("=" * 100)
print("AUDIT: All lakemeter Functions")
print("=" * 100)

# Get all functions
get_functions = """
SELECT 
    p.proname as function_name,
    pg_get_functiondef(p.oid) as function_definition
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'lakemeter'
ORDER BY p.proname;
"""

functions = execute_query(get_functions)
print(f"\n✅ Found {len(functions)} functions to audit\n")

# COMMAND ----------

print("=" * 100)
print("CHECKING: String Parameters and WHERE Clauses")
print("=" * 100)

issues_found = []

for idx, row in functions.iterrows():
    func_name = row['function_name']
    func_def = row['function_definition']
    
    # Skip trigger functions
    if 'TRIGGER' in func_def or func_name.startswith('validate_') or func_name.startswith('sync_'):
        continue
    
    print(f"\n{'='*80}")
    print(f"Function: {func_name}")
    print(f"{'='*80}")
    
    # Check for string parameters (VARCHAR, TEXT)
    param_pattern = r'p_(\w+)\s+(VARCHAR|TEXT|CHAR)'
    params = re.findall(param_pattern, func_def, re.IGNORECASE)
    
    if params:
        print(f"\n📝 String parameters found: {len(params)}")
        for param_name, param_type in params:
            print(f"   • p_{param_name} ({param_type})")
            
            # Check if parameter is normalized (converted to UPPER/LOWER)
            if f'v_{param_name} := UPPER(p_{param_name})' in func_def:
                print(f"     ✅ Normalized to UPPER")
            elif f'v_{param_name} := LOWER(p_{param_name})' in func_def:
                print(f"     ✅ Normalized to LOWER")
            elif f'UPPER(p_{param_name})' in func_def or f'LOWER(p_{param_name})' in func_def:
                print(f"     ✅ Used with UPPER/LOWER in query")
            else:
                # Check if used in WHERE/JOIN without UPPER/LOWER
                if f'= p_{param_name}' in func_def or f'IN (p_{param_name}' in func_def:
                    print(f"     ⚠️  Used directly in comparison (might be case-sensitive)")
                    issues_found.append({
                        'function': func_name,
                        'parameter': f'p_{param_name}',
                        'issue': 'Used in comparison without UPPER/LOWER'
                    })
    
    # Check for WHERE clauses with string literals
    where_literals = re.findall(r"WHERE.*?=\s*['\"](\w+)['\"]", func_def, re.IGNORECASE | re.DOTALL)
    if where_literals:
        print(f"\n🔍 WHERE clauses with string literals:")
        for literal in set(where_literals):
            print(f"   • '{literal}'")
    
    # Check for IN clauses with string literals
    in_clauses = re.findall(r"IN\s*\(['\"](\w+)['\"]", func_def, re.IGNORECASE)
    if in_clauses:
        print(f"\n🔍 IN clauses with string literals:")
        for literal in set(in_clauses):
            print(f"   • IN ('{literal}'...)")
    
    # Check for CASE WHEN with string comparisons
    case_when = re.findall(r"WHEN\s+['\"](\w+)['\"]", func_def, re.IGNORECASE)
    if case_when:
        print(f"\n🔍 CASE WHEN with string literals:")
        for literal in set(case_when):
            print(f"   • WHEN '{literal}'")

# COMMAND ----------

print("\n" + "=" * 100)
print("SPECIFIC CHECKS: Known String Columns")
print("=" * 100)

# Check specific functions for known string column comparisons
specific_checks = [
    {
        'function': 'calculate_dbsql_dbu',
        'checks': [
            ('warehouse_type', 'Should use LOWER() on both sides'),
            ('warehouse_size', 'Should use UPPER() on both sides'),
        ]
    },
    {
        'function': 'calculate_dbsql_vm_costs',
        'checks': [
            ('warehouse_type', 'Should use LOWER() on both sides'),
            ('warehouse_size', 'Should use UPPER() on both sides'),
        ]
    },
    {
        'function': 'calculate_classic_vm_costs',
        'checks': [
            ('instance_type', 'Should match exactly or use UPPER()'),
            ('pricing_tier', 'Should match exactly'),
        ]
    },
    {
        'function': 'get_product_type_for_pricing',
        'checks': [
            ('p_workload_type', 'Should normalize to UPPER'),
            ('p_dbsql_warehouse_type', 'Should normalize to UPPER'),
            ('p_dlt_edition', 'Should normalize to UPPER'),
        ]
    },
    {
        'function': 'calculate_line_item_costs',
        'checks': [
            ('p_dbsql_warehouse_type in IF statement', 'Should use LOWER()'),
        ]
    },
]

for check in specific_checks:
    func_name = check['function']
    print(f"\n{'='*80}")
    print(f"Checking: {func_name}")
    print(f"{'='*80}")
    
    func_row = functions[functions['function_name'] == func_name]
    if func_row.empty:
        print(f"❌ Function not found in database!")
        continue
    
    func_def = func_row.iloc[0]['function_definition']
    
    for column, recommendation in check['checks']:
        print(f"\n🔎 Checking: {column}")
        print(f"   Recommendation: {recommendation}")
        
        # Check if UPPER/LOWER is used
        if f'UPPER({column})' in func_def or f'UPPER(p_{column})' in func_def:
            print(f"   ✅ Uses UPPER()")
        elif f'LOWER({column})' in func_def or f'LOWER(p_{column})' in func_def:
            print(f"   ✅ Uses LOWER()")
        elif f'v_{column} := UPPER' in func_def:
            print(f"   ✅ Normalized to UPPER")
        elif f'v_{column} := LOWER' in func_def:
            print(f"   ✅ Normalized to LOWER")
        else:
            print(f"   ⚠️  No UPPER/LOWER found - might be case-sensitive")

# COMMAND ----------

print("\n" + "=" * 100)
print("🎯 SUMMARY OF POTENTIAL ISSUES")
print("=" * 100)

if issues_found:
    print(f"\n⚠️  Found {len(issues_found)} potential case-sensitivity issues:\n")
    issues_df = pd.DataFrame(issues_found)
    display(issues_df)
    
    print("\n💡 RECOMMENDATIONS:")
    print("   1. Add normalization (UPPER/LOWER) at function start")
    print("   2. Use normalized variables in WHERE/JOIN clauses")
    print("   3. Use UPPER() on both sides for table column comparisons")
else:
    print("\n✅ No obvious case-sensitivity issues found!")
    print("   All string parameters appear to be normalized or used with UPPER/LOWER")

# COMMAND ----------

print("\n" + "=" * 100)
print("🔧 RECOMMENDED PATTERN")
print("=" * 100)

print("""
For any function with string parameters:

1. DECLARE normalized variables:
   DECLARE
       v_workload_type VARCHAR;
       v_warehouse_type VARCHAR;
   BEGIN
   
2. NORMALIZE at function start:
   v_workload_type := UPPER(p_workload_type);
   v_warehouse_type := LOWER(p_warehouse_type);
   
3. USE normalized variables in queries:
   WHERE workload_type = v_workload_type
   
4. For table column comparisons, use UPPER() on BOTH sides:
   WHERE UPPER(warehouse_size) = UPPER(p_warehouse_size)
   
This ensures:
  ✅ Function accepts any case input ('pro', 'PRO', 'Pro')
  ✅ Matches any case in table ('pro', 'PRO', 'Pro')
  ✅ Consistent behavior across all functions
""")

# COMMAND ----------

print("\n" + "=" * 100)
print("📋 CHECKLIST FOR EACH FUNCTION")
print("=" * 100)

print("""
For each function with string parameters:

□ Input normalization (UPPER/LOWER at start)
□ WHERE clauses use normalized variables
□ JOIN conditions use UPPER() on both sides if needed
□ IF statements use LOWER() for lowercase comparisons
□ CASE WHEN uses normalized variables
□ IN clauses use normalized variables

Functions already checked:
  ✅ get_product_type_for_pricing - UPPER normalization
  ✅ calculate_dbsql_vm_costs - LOWER for warehouse_type
  ✅ calculate_dbsql_dbu - LOWER for warehouse_type, UPPER for warehouse_size
  ✅ calculate_line_item_costs - LOWER in DBSQL IF statement
  
Functions to check:
  ⚠️  calculate_classic_vm_costs - instance_type, pricing_tier
  ⚠️  calculate_classic_compute_dbu - node_type
  ⚠️  calculate_vector_search_dbu - vector_search_mode
  ⚠️  calculate_model_serving_dbu - serverless_size
  ⚠️  calculate_fmapi_databricks_dbu - fmapi_model
  ⚠️  calculate_fmapi_proprietary_dbu - fmapi_model, fmapi_provider
""")




