# Databricks notebook source
# MAGIC %md
# MAGIC # Update Lakebase CU Constraint
# MAGIC
# MAGIC **Purpose:** Update lakebase_cu column and constraint to match current Databricks docs
# MAGIC
# MAGIC **Reference:** https://docs.databricks.com/aws/en/oltp/projects/manage-computes#available-compute-sizes
# MAGIC
# MAGIC **Changes:**
# MAGIC - Column type: INTEGER -> NUMERIC(5,1) (to support 0.5 CU)
# MAGIC - Valid CU sizes: 0.5, 1-32 (autoscaling), 36-112 (fixed-size)
# MAGIC - Each CU = ~2 GB RAM (Autoscaling model)

# COMMAND ----------

import psycopg2

# Self-contained Lakebase connection (no %run dependency)
LAKEBASE_HOST = "instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com"
LAKEBASE_PORT = 5432
LAKEBASE_DB = "lakemeter_pricing"
LAKEBASE_USER = "lakemeter_sync_role"
LAKEBASE_PASSWORD = dbutils.secrets.get(scope="lakemeter-credentials", key="lakebase-password")

conn = psycopg2.connect(
    host=LAKEBASE_HOST,
    port=LAKEBASE_PORT,
    dbname=LAKEBASE_DB,
    user=LAKEBASE_USER,
    password=LAKEBASE_PASSWORD,
    sslmode="require"
)
conn.autocommit = True
cur = conn.cursor()
print("Connected to Lakebase")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Drop old constraint

# COMMAND ----------

try:
    cur.execute("ALTER TABLE lakemeter.line_items DROP CONSTRAINT IF EXISTS chk_lakebase_cu")
    print("Dropped old chk_lakebase_cu constraint")
except Exception as e:
    print(f"Drop error (may not exist): {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Alter column type to NUMERIC(5,1)

# COMMAND ----------

try:
    cur.execute("ALTER TABLE lakemeter.line_items ALTER COLUMN lakebase_cu TYPE NUMERIC(5,1)")
    print("Changed lakebase_cu column to NUMERIC(5,1)")
except Exception as e:
    print(f"Alter error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Add new constraint with all valid CU sizes

# COMMAND ----------

try:
    cur.execute("""
        ALTER TABLE lakemeter.line_items
        ADD CONSTRAINT chk_lakebase_cu
        CHECK (lakebase_cu IS NULL OR lakebase_cu IN (
            0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
            17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32,
            36, 40, 44, 48, 52, 56, 60, 64, 72, 80, 88, 96, 104, 112
        ))
    """)
    print("Added new chk_lakebase_cu constraint with all valid Autoscaling sizes")
except Exception as e:
    print(f"Constraint error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify

# COMMAND ----------

cur.execute("""
    SELECT constraint_name, check_clause
    FROM information_schema.check_constraints
    WHERE constraint_name = 'chk_lakebase_cu'
""")
row = cur.fetchone()
if row:
    print(f"Verified: {row[0]}")
    print(f"Clause: {row[1][:200]}...")
else:
    print("WARNING: constraint not found!")

# COMMAND ----------

# Check column type
cur.execute("""
    SELECT column_name, data_type, numeric_precision, numeric_scale
    FROM information_schema.columns
    WHERE table_schema = 'lakemeter' AND table_name = 'line_items' AND column_name = 'lakebase_cu'
""")
row = cur.fetchone()
if row:
    print(f"Column: {row[0]}, Type: {row[1]}, Precision: {row[2]}, Scale: {row[3]}")

# COMMAND ----------

cur.close()
conn.close()
print("Migration complete!")
