# Databricks notebook source
# MAGIC %md
# MAGIC # Check FMAPI Databricks Models in Pricing Table
# MAGIC 
# MAGIC This checks which models exist in `sync_product_fmapi_databricks` table.

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
import pandas as pd
from tabulate import tabulate

conn = get_lakebase_connection()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check Available Models

# COMMAND ----------

print("=" * 80)
print("AVAILABLE MODELS IN sync_product_fmapi_databricks")
print("=" * 80)

query = """
SELECT DISTINCT 
    cloud,
    model,
    rate_type,
    dbu_rate,
    input_divisor,
    is_hourly,
    sku_product_type
FROM lakemeter.sync_product_fmapi_databricks
ORDER BY cloud, model, rate_type;
"""

cur = conn.cursor()
cur.execute(query)
columns = [desc[0] for desc in cur.description]
results = cur.fetchall()

df = pd.DataFrame(results, columns=columns)
print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))

print(f"\n✅ Total rows: {len(df)}")
print(f"✅ Unique models: {df['model'].nunique()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check What Test Is Looking For

# COMMAND ----------

print("\n" + "=" * 80)
print("TEST IS LOOKING FOR THESE MODELS:")
print("=" * 80)

test_models = [
    'llama-3.1-8b-instruct',
    'dbrx-instruct',
    'bge-large-en-v1.5',
    'gte',
    'llama-3.1-70b-instruct',
    'gemma-3-12b',
    'gpt-oss-120b'
]

for model in test_models:
    exists = model in df['model'].values
    status = "✅ EXISTS" if exists else "❌ NOT FOUND"
    print(f"  • {model:<30} {status}")
    
    if exists:
        model_rates = df[df['model'] == model]
        print(f"    Rate types: {', '.join(model_rates['rate_type'].unique())}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Recommendations

# COMMAND ----------

print("\n" + "=" * 80)
print("RECOMMENDATIONS:")
print("=" * 80)

missing_models = [m for m in test_models if m not in df['model'].values]

if missing_models:
    print(f"\n❌ {len(missing_models)} models are missing from pricing table:")
    for m in missing_models:
        print(f"   • {m}")
    
    print("\n💡 Solutions:")
    print("   1. Update Test_12_FMAPI_Databricks to use models that exist in pricing table")
    print("   2. OR add these models to sync_product_fmapi_databricks table")
    print("\n   Available models you can use:")
    available_models = df['model'].unique()[:10]  # Show first 10
    for m in available_models:
        print(f"   • {m}")
else:
    print("✅ All test models exist in pricing table!")

conn.close()

