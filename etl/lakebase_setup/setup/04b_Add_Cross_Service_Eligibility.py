# Databricks notebook source
# MAGIC %md
# MAGIC # Add Cross-Service Eligibility to SKU Discount Mapping
# MAGIC
# MAGIC **Purpose:** Add `cross_service_eligible` column to `sku_discount_mapping` table.
# MAGIC
# MAGIC Per https://www.databricks.com/product/sku-groups#exclusions, the cross-service
# MAGIC (EA) discount does NOT apply to all DBU SKUs. Excluded SKUs include:
# MAGIC - Serverless Real-Time Inference (Model Serving)
# MAGIC - Model Training (all variants)
# MAGIC - FMAPI Proprietary (OpenAI, Anthropic, Gemini)
# MAGIC - Data Transfer / Egress (all variants)
# MAGIC - Databricks Storage
# MAGIC
# MAGIC **Behavior in API:**
# MAGIC - `cross_service_eligible = TRUE` → `dbu_discount` applies
# MAGIC - `cross_service_eligible = FALSE` → `dbu_discount` is SKIPPED, response shows
# MAGIC   `source = "global:dbu:excluded_from_cross_service"`
# MAGIC - `sku_specific` overrides ALWAYS apply regardless of eligibility
# MAGIC
# MAGIC **Azure:** Applied to all SKUs (no published exclusion list).
# MAGIC
# MAGIC **Author:** Steven Tan
# MAGIC **Date:** 2026-01-25

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Connect to Lakebase

# COMMAND ----------

%pip install psycopg2-binary --quiet
dbutils.library.restartPython()

# COMMAND ----------

import psycopg2

LAKEBASE_HOST = "instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com"
LAKEBASE_PORT = 5432
LAKEBASE_DATABASE = "lakemeter_pricing"
LAKEBASE_USER = "lakemeter_sync_role"
LAKEBASE_PASSWORD = dbutils.secrets.get(scope="lakemeter-credentials", key="lakebase-password")

conn = psycopg2.connect(
    host=LAKEBASE_HOST,
    port=LAKEBASE_PORT,
    database=LAKEBASE_DATABASE,
    user=LAKEBASE_USER,
    password=LAKEBASE_PASSWORD
)
cursor = conn.cursor()
print("Connected to Lakebase")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Add cross_service_eligible Column

# COMMAND ----------

alter_sql = """
ALTER TABLE lakemeter.sku_discount_mapping
ADD COLUMN IF NOT EXISTS cross_service_eligible BOOLEAN NOT NULL DEFAULT TRUE;

COMMENT ON COLUMN lakemeter.sku_discount_mapping.cross_service_eligible IS
    'TRUE = dbu_discount (cross-service) applies. FALSE = excluded per databricks.com/product/sku-groups#exclusions. sku_specific overrides always apply.';
"""

try:
    cursor.execute(alter_sql)
    conn.commit()
    print("Column cross_service_eligible added (default TRUE)")
except Exception as e:
    conn.rollback()
    print(f"Error: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Mark Excluded SKUs
# MAGIC
# MAGIC These SKUs are explicitly excluded from cross-service SKU groups
# MAGIC per https://www.databricks.com/product/sku-groups#exclusions

# COMMAND ----------

excluded_skus = [
    # Serverless Real-Time Inference (Model Serving)
    "SERVERLESS_REAL_TIME_INFERENCE",
    "SERVERLESS_REAL_TIME_INFERENCE_LAUNCH",

    # Model Training (all variants)
    "MODEL_TRAINING",
    "MODEL_TRAINING_ON_DEMAND",
    "MODEL_TRAINING_RESERVATION",
    "MODEL_TRAINING_HERO_RESERVATION",
    "MODEL_TRAINING_IN_CUSTOMER_TENANCY",
    "MODEL_TRAINING_SERVERLESS_GPU_COMPUTE_PROVISIONED_CAPACITY",

    # FMAPI Proprietary (third-party model serving)
    "OPENAI_MODEL_SERVING",
    "ANTHROPIC_MODEL_SERVING",
    "GEMINI_MODEL_SERVING",
]

placeholders = ", ".join(["%s"] * len(excluded_skus))
update_sql = f"""
UPDATE lakemeter.sku_discount_mapping
SET cross_service_eligible = FALSE
WHERE sku IN ({placeholders});
"""

try:
    cursor.execute(update_sql, excluded_skus)
    conn.commit()
    print(f"Marked {cursor.rowcount} SKUs as cross_service_eligible = FALSE")
except Exception as e:
    conn.rollback()
    print(f"Error: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Verify

# COMMAND ----------

verify_sql = """
SELECT 
    sku,
    discount_category,
    cross_service_eligible
FROM lakemeter.sku_discount_mapping
WHERE discount_category = 'dbu'
ORDER BY cross_service_eligible, sku;
"""

cursor.execute(verify_sql)
rows = cursor.fetchall()

print(f"{'SKU':<65} {'Category':<10} {'Cross-Service Eligible'}")
print("-" * 100)
for sku, cat, eligible in rows:
    marker = "YES" if eligible else "NO  <-- EXCLUDED"
    print(f"{sku:<65} {cat:<10} {marker}")

# COMMAND ----------

summary_sql = """
SELECT 
    cross_service_eligible,
    COUNT(*) as count
FROM lakemeter.sku_discount_mapping
WHERE discount_category = 'dbu'
GROUP BY cross_service_eligible
ORDER BY cross_service_eligible DESC;
"""

cursor.execute(summary_sql)
rows = cursor.fetchall()

print("\nSummary (DBU category only):")
for eligible, count in rows:
    label = "Eligible (dbu_discount applies)" if eligible else "Excluded (dbu_discount skipped)"
    print(f"  {label}: {count} SKUs")

# COMMAND ----------

cursor.close()
conn.close()
print("\nDone. Connection closed.")
