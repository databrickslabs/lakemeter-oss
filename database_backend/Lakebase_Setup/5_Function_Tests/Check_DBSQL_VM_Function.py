# Databricks notebook source
# MAGIC %md
# MAGIC # 🔍 Check: calculate_dbsql_vm_costs Function Signature

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2

conn = psycopg2.connect(
    host=LAKEBASE_HOST,
    port=LAKEBASE_PORT,
    database=LAKEBASE_DATABASE,
    user=LAKEBASE_USER,
    password=LAKEBASE_PASSWORD,
    sslmode='require'
)

# COMMAND ----------

query = """
SELECT 
    p.proname as function_name,
    pg_get_function_arguments(p.oid) as arguments
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'lakemeter'
  AND p.proname = 'calculate_dbsql_vm_costs';
"""

cursor = conn.cursor()
cursor.execute(query)
result = cursor.fetchone()

if result:
    function_name, arguments = result
    print(f"Function: {function_name}")
    print(f"\n{'='*100}")
    print("ARGUMENTS:")
    print('='*100)
    
    args = arguments.split(', ')
    for i, arg in enumerate(args, 1):
        print(f"{i:2d}. {arg}")
    
    print(f"\n{'='*100}")
    print(f"Total parameters: {len(args)}")
    print('='*100)
    
    # Check for payment_option parameter
    has_payment_param = any('payment' in arg.lower() for arg in args)
    if has_payment_param:
        print("\n✅ HAS payment_option parameter!")
        payment_params = [arg for arg in args if 'payment' in arg.lower()]
        for param in payment_params:
            print(f"   • {param}")
    else:
        print("\n❌ NO payment_option parameter!")
else:
    print("❌ Function 'calculate_dbsql_vm_costs' NOT FOUND!")

cursor.close()
conn.close()




