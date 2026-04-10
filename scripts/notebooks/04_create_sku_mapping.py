# Databricks notebook source
# MAGIC %md
# MAGIC # Step 4: Create SKU Discount Mapping
# MAGIC Creates the sku_discount_mapping table, auto-populates from DBU rates,
# MAGIC and marks non-cross-service-eligible SKUs.

# COMMAND ----------

dbutils.widgets.text("instance_name", "lakemeter-customer")
dbutils.widgets.text("db_name", "lakemeter_pricing")

instance_name = dbutils.widgets.get("instance_name")
db_name = dbutils.widgets.get("db_name")

print(f"Instance: {instance_name}")
print(f"Database: {db_name}")

# COMMAND ----------

import psycopg2
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Get Lakebase connection via owner credentials (OAuth)
instance = w.database.get_database_instance(instance_name)
instance_host = instance.read_write_dns
import uuid
cred = w.database.generate_database_credential(request_id=str(uuid.uuid4()), instance_names=[instance_name])
owner_user = w.current_user.me().user_name

conn = psycopg2.connect(
    host=instance_host,
    port=5432,
    database=db_name,
    user=owner_user,
    password=cred.token,
    sslmode="require",
)
conn.autocommit = True
cur = conn.cursor()
print(f"Connected to Lakebase: {db_name}@{instance_host}")

# COMMAND ----------

# Create SKU discount mapping table
cur.execute("""
    CREATE TABLE IF NOT EXISTS lakemeter.sku_discount_mapping (
        sku TEXT PRIMARY KEY,
        sku_display_name TEXT,
        discount_category TEXT NOT NULL
            CHECK (discount_category IN ('dbu', 'storage', 'support', 'network', 'excluded')),
        cross_service_eligible BOOLEAN NOT NULL DEFAULT TRUE,
        notes TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_sku_discount_category
        ON lakemeter.sku_discount_mapping(discount_category);
""")
print("SKU discount mapping table ready")

# COMMAND ----------

# Auto-populate from sync_pricing_dbu_rates if empty
cur.execute("SELECT COUNT(*) FROM lakemeter.sku_discount_mapping")
count = cur.fetchone()[0]

if count == 0:
    print("Populating SKU discount mapping from DBU rates...")
    cur.execute("""
        INSERT INTO lakemeter.sku_discount_mapping (sku, sku_display_name, discount_category)
        SELECT DISTINCT sku_name, sku_name, 'dbu'
        FROM lakemeter.sync_pricing_dbu_rates
        WHERE sku_name IS NOT NULL AND sku_name != ''
        ON CONFLICT DO NOTHING
    """)
    print(f"  Inserted {cur.rowcount} SKU mappings")
else:
    print(f"SKU discount mapping already populated ({count} rows)")

# COMMAND ----------

# Mark non-cross-service-eligible SKUs
non_eligible_patterns = [
    "Model Serving%",
    "Model Training%",
    "%Proprietary%",
]
for pattern in non_eligible_patterns:
    cur.execute(
        "UPDATE lakemeter.sku_discount_mapping SET cross_service_eligible = FALSE WHERE sku LIKE %s",
        (pattern,)
    )

# Verify
cur.execute("SELECT COUNT(*) FROM lakemeter.sku_discount_mapping")
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM lakemeter.sku_discount_mapping WHERE cross_service_eligible = FALSE")
non_eligible = cur.fetchone()[0]
print(f"SKU discount mapping: {total} total, {non_eligible} non-cross-service-eligible")

cur.close()
conn.close()
print("SKU discount mapping complete.")
