# Databricks notebook source
# MAGIC %md
# MAGIC # Debug: Why FMAPI DBU Price is $0
# MAGIC
# MAGIC Check if product types exist for specific cloud/region/tier combinations

# COMMAND ----------

%run ../00_Lakebase_Config

# COMMAND ----------

import pandas as pd

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Scenarios from Test_Func_13

# COMMAND ----------

test_scenarios = [
    {'line': 'Claude Sonnet - Input', 'cloud': 'AWS', 'region': 'us-east-1', 'tier': 'PREMIUM', 'provider': 'anthropic'},
    {'line': 'Claude Haiku - Cache Read', 'cloud': 'AWS', 'region': 'us-east-1', 'tier': 'ENTERPRISE', 'provider': 'anthropic'},
    {'line': 'GPT-5 - Input', 'cloud': 'AZURE', 'region': 'eastus', 'tier': 'PREMIUM', 'provider': 'openai'},
    {'line': 'Gemini Pro - Input', 'cloud': 'GCP', 'region': 'us-central1', 'tier': 'ENTERPRISE', 'provider': 'google'},
]

print("=" * 100)
print("CHECKING DBU PRICE AVAILABILITY FOR TEST SCENARIOS")
print("=" * 100)

for scenario in test_scenarios:
    cloud = scenario['cloud']
    region = scenario['region']
    tier = scenario['tier']
    provider = scenario['provider']
    
    # Determine product type based on provider
    if provider == 'google':
        product_type = 'GEMINI_MODEL_SERVING'
    else:
        product_type = f"{provider.upper()}_MODEL_SERVING"
    
    print(f"\n{scenario['line']}")
    print(f"  Cloud: {cloud}, Region: {region}, Tier: {tier}")
    print(f"  Product Type: {product_type}")
    
    # Check if pricing exists
    query = f"""
    SELECT 
        cloud,
        region,
        tier,
        product_type,
        price_per_dbu
    FROM lakemeter.sync_pricing_dbu_rates
    WHERE UPPER(cloud) = UPPER('{cloud}')
      AND UPPER(region) = UPPER('{region}')
      AND UPPER(tier) = UPPER('{tier}')
      AND UPPER(product_type) = UPPER('{product_type}');
    """
    
    result = execute_query(query)
    
    if result and len(result) > 0:
        price = result[0][4]
        print(f"  ✅ FOUND: ${price} per DBU")
    else:
        print(f"  ❌ NOT FOUND!")
        
        # Check what IS available for this product type
        alt_query = f"""
        SELECT DISTINCT
            cloud,
            region,
            tier,
            price_per_dbu
        FROM lakemeter.sync_pricing_dbu_rates
        WHERE UPPER(product_type) = UPPER('{product_type}')
        ORDER BY cloud, region, tier
        LIMIT 10;
        """
        
        alt_result = execute_query(alt_query)
        if alt_result and len(alt_result) > 0:
            print(f"  📋 But {product_type} IS available in these combinations:")
            for row in alt_result:
                print(f"     • {row[0]} / {row[1]} / {row[2]} → ${row[3]} per DBU")
        else:
            print(f"  ❌ Product type '{product_type}' not found AT ALL in pricing table!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check All Available FMAPI Product Types

# COMMAND ----------

print("\n" + "=" * 100)
print("ALL FMAPI-RELATED PRODUCT TYPES IN PRICING TABLE")
print("=" * 100)

query = """
SELECT 
    product_type,
    COUNT(DISTINCT cloud) as clouds,
    COUNT(DISTINCT region) as regions,
    COUNT(DISTINCT tier) as tiers,
    COUNT(*) as total_records,
    MIN(price_per_dbu) as min_price,
    MAX(price_per_dbu) as max_price
FROM lakemeter.sync_pricing_dbu_rates
WHERE UPPER(product_type) LIKE '%MODEL%' 
   OR UPPER(product_type) LIKE '%FMAPI%'
   OR UPPER(product_type) LIKE '%ANTHROPIC%'
   OR UPPER(product_type) LIKE '%OPENAI%'
   OR UPPER(product_type) LIKE '%GEMINI%'
GROUP BY product_type
ORDER BY product_type;
"""

results = execute_query(query)

if results:
    df = pd.DataFrame(results, columns=['product_type', 'clouds', 'regions', 'tiers', 'total_records', 'min_price', 'max_price'])
    print(f"\n✅ Found {len(df)} FMAPI-related product types")
    display(df)
else:
    print("\n❌ No FMAPI-related product types found!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test get_dbu_price() Function Directly

# COMMAND ----------

print("\n" + "=" * 100)
print("TESTING get_dbu_price() FUNCTION CALLS")
print("=" * 100)

for scenario in test_scenarios:
    cloud = scenario['cloud']
    region = scenario['region']
    tier = scenario['tier']
    provider = scenario['provider']
    
    if provider == 'google':
        product_type = 'GEMINI_MODEL_SERVING'
    else:
        product_type = f"{provider.upper()}_MODEL_SERVING"
    
    query = f"""
    SELECT lakemeter.get_dbu_price(
        '{cloud}'::VARCHAR,
        '{region}'::VARCHAR,
        '{tier}'::VARCHAR,
        '{product_type}'::VARCHAR
    ) as dbu_price;
    """
    
    result = execute_query(query)
    
    if result:
        price = result[0][0]
        print(f"\n{scenario['line']}")
        print(f"  get_dbu_price('{cloud}', '{region}', '{tier}', '{product_type}')")
        print(f"  → ${price} per DBU")
        
        if price and price > 0:
            print(f"  ✅ Function returns positive price")
        else:
            print(f"  ❌ Function returns $0!")


