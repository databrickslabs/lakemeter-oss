# Databricks notebook source
# MAGIC %md
# MAGIC # Debug: Check Product Types for FMAPI in DBU Pricing Table

# COMMAND ----------

%run ../00_Lakebase_Config

# COMMAND ----------

import pandas as pd

# Check what product types exist in the DBU pricing table
query = """
SELECT DISTINCT 
    product_type,
    COUNT(*) as count_regions
FROM lakemeter.sync_pricing_dbu_rates
GROUP BY product_type
ORDER BY product_type;
"""

results = execute_query(query)

if results:
    df = pd.DataFrame(results, columns=['product_type', 'count_regions'])
    print(f"✅ Found {len(df)} distinct product types in sync_pricing_dbu_rates")
    display(df)
    
    # Check for FMAPI-related types
    print("\n🔍 FMAPI-related product types:")
    fmapi_types = [row[0] for row in results if 'FMAPI' in row[0].upper() or 'MODEL' in row[0].upper() or 'ANTHROPIC' in row[0].upper() or 'OPENAI' in row[0].upper() or 'GEMINI' in row[0].upper()]
    
    if fmapi_types:
        for ptype in fmapi_types:
            print(f"   • {ptype}")
    else:
        print("   ❌ No FMAPI-related product types found!")
        print("\n   Looking for SERVERLESS types:")
        serverless_types = [row[0] for row in results if 'SERVERLESS' in row[0].upper()]
        for ptype in serverless_types:
            print(f"   • {ptype}")
else:
    print("❌ No pricing data found!")

# COMMAND ----------

# Check what product type the function is returning for FMAPI
print("\n" + "=" * 100)
print("TESTING get_product_type_for_pricing() for FMAPI")
print("=" * 100)

test_cases = [
    ('FMAPI_DATABRICKS', None),
    ('FMAPI_PROPRIETARY', 'anthropic'),
    ('FMAPI_PROPRIETARY', 'openai'),
    ('FMAPI_PROPRIETARY', 'google'),
]

for workload, provider in test_cases:
    if provider:
        query = f"""
        SELECT lakemeter.get_product_type_for_pricing(
            '{workload}'::VARCHAR,
            FALSE::BOOLEAN,
            FALSE::BOOLEAN,
            NULL::VARCHAR,
            NULL::VARCHAR,
            '{provider}'::VARCHAR
        ) as product_type;
        """
        label = f"{workload} ({provider})"
    else:
        query = f"""
        SELECT lakemeter.get_product_type_for_pricing(
            '{workload}'::VARCHAR,
            FALSE::BOOLEAN,
            FALSE::BOOLEAN,
            NULL::VARCHAR,
            NULL::VARCHAR,
            NULL::VARCHAR
        ) as product_type;
        """
        label = workload
    
    result = execute_query(query)
    if result:
        product_type = result[0][0]
        print(f"\n{label}:")
        print(f"   → Product type: {product_type}")
        
        # Check if this product type exists in pricing table
        check_query = f"""
        SELECT COUNT(*) as count
        FROM lakemeter.sync_pricing_dbu_rates
        WHERE UPPER(product_type) = UPPER('{product_type}');
        """
        check_result = execute_query(check_query)
        if check_result and check_result[0][0] > 0:
            print(f"   ✅ EXISTS in pricing table ({check_result[0][0]} records)")
        else:
            print(f"   ❌ NOT FOUND in pricing table!")


