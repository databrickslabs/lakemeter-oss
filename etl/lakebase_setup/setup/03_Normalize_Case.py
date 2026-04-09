# Databricks notebook source
# MAGIC %md
# MAGIC # Normalize Case Sensitivity in Lakemeter Tables
# MAGIC
# MAGIC One-time migration to fix existing lowercase values in enum fields.
# MAGIC Also creates DB-level triggers to prevent future case mismatches.

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2

conn = get_lakebase_connection()
conn.autocommit = True
cur = conn.cursor()

# ============================================================
# PART 1: Fix existing data
# ============================================================
migration_statements = [
    # UPPERCASE fields on line_items
    ("line_items.dbsql_warehouse_type", """
        UPDATE lakemeter.line_items SET dbsql_warehouse_type = UPPER(dbsql_warehouse_type)
        WHERE dbsql_warehouse_type IS NOT NULL AND dbsql_warehouse_type != UPPER(dbsql_warehouse_type)
    """),
    ("line_items.dlt_edition", """
        UPDATE lakemeter.line_items SET dlt_edition = UPPER(dlt_edition)
        WHERE dlt_edition IS NOT NULL AND dlt_edition != UPPER(dlt_edition)
    """),
    ("line_items.workload_type", """
        UPDATE lakemeter.line_items SET workload_type = UPPER(workload_type)
        WHERE workload_type IS NOT NULL AND workload_type != UPPER(workload_type)
    """),
    ("line_items.cloud", """
        UPDATE lakemeter.line_items SET cloud = UPPER(cloud)
        WHERE cloud IS NOT NULL AND cloud != UPPER(cloud)
    """),
    # UPPERCASE fields on estimates
    ("estimates.cloud", """
        UPDATE lakemeter.estimates SET cloud = UPPER(cloud)
        WHERE cloud IS NOT NULL AND cloud != UPPER(cloud)
    """),
    ("estimates.tier", """
        UPDATE lakemeter.estimates SET tier = UPPER(tier)
        WHERE tier IS NOT NULL AND tier != UPPER(tier)
    """),
    # LOWERCASE fields on line_items
    ("line_items.serverless_mode", """
        UPDATE lakemeter.line_items SET serverless_mode = LOWER(serverless_mode)
        WHERE serverless_mode IS NOT NULL AND serverless_mode != LOWER(serverless_mode)
    """),
    ("line_items.vector_search_mode", """
        UPDATE lakemeter.line_items SET vector_search_mode = LOWER(vector_search_mode)
        WHERE vector_search_mode IS NOT NULL AND vector_search_mode != LOWER(vector_search_mode)
    """),
    ("line_items.fmapi_provider", """
        UPDATE lakemeter.line_items SET fmapi_provider = LOWER(fmapi_provider)
        WHERE fmapi_provider IS NOT NULL AND fmapi_provider != LOWER(fmapi_provider)
    """),
    ("line_items.fmapi_rate_type", """
        UPDATE lakemeter.line_items SET fmapi_rate_type = LOWER(fmapi_rate_type)
        WHERE fmapi_rate_type IS NOT NULL AND fmapi_rate_type != LOWER(fmapi_rate_type)
    """),
    ("line_items.model_serving_gpu_type", """
        UPDATE lakemeter.line_items SET model_serving_gpu_type = LOWER(model_serving_gpu_type)
        WHERE model_serving_gpu_type IS NOT NULL AND model_serving_gpu_type != LOWER(model_serving_gpu_type)
    """),
]

print("=" * 60)
print("PART 1: Normalizing existing data")
print("=" * 60)
for field, sql in migration_statements:
    cur.execute(sql.strip())
    print(f"  {field}: {cur.rowcount} rows updated")

# COMMAND ----------

# ============================================================
# PART 2: Create DB-level normalization triggers
# ============================================================
print("=" * 60)
print("PART 2: Creating normalization triggers")
print("=" * 60)

# Trigger function for estimates
cur.execute("""
    CREATE OR REPLACE FUNCTION lakemeter.normalize_estimates_case()
    RETURNS TRIGGER AS $$
    BEGIN
        IF NEW.cloud IS NOT NULL THEN NEW.cloud = UPPER(NEW.cloud); END IF;
        IF NEW.tier IS NOT NULL THEN NEW.tier = UPPER(NEW.tier); END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
""")
print("  Created function: normalize_estimates_case()")

# Trigger function for line_items
cur.execute("""
    CREATE OR REPLACE FUNCTION lakemeter.normalize_line_items_case()
    RETURNS TRIGGER AS $$
    BEGIN
        -- UPPERCASE fields
        IF NEW.cloud IS NOT NULL THEN NEW.cloud = UPPER(NEW.cloud); END IF;
        IF NEW.workload_type IS NOT NULL THEN NEW.workload_type = UPPER(NEW.workload_type); END IF;
        IF NEW.dbsql_warehouse_type IS NOT NULL THEN NEW.dbsql_warehouse_type = UPPER(NEW.dbsql_warehouse_type); END IF;
        IF NEW.dlt_edition IS NOT NULL THEN NEW.dlt_edition = UPPER(NEW.dlt_edition); END IF;
        -- LOWERCASE fields
        IF NEW.serverless_mode IS NOT NULL THEN NEW.serverless_mode = LOWER(NEW.serverless_mode); END IF;
        IF NEW.vector_search_mode IS NOT NULL THEN NEW.vector_search_mode = LOWER(NEW.vector_search_mode); END IF;
        IF NEW.fmapi_provider IS NOT NULL THEN NEW.fmapi_provider = LOWER(NEW.fmapi_provider); END IF;
        IF NEW.fmapi_rate_type IS NOT NULL THEN NEW.fmapi_rate_type = LOWER(NEW.fmapi_rate_type); END IF;
        IF NEW.fmapi_endpoint_type IS NOT NULL THEN NEW.fmapi_endpoint_type = LOWER(NEW.fmapi_endpoint_type); END IF;
        IF NEW.fmapi_context_length IS NOT NULL THEN NEW.fmapi_context_length = LOWER(NEW.fmapi_context_length); END IF;
        IF NEW.model_serving_gpu_type IS NOT NULL THEN NEW.model_serving_gpu_type = LOWER(NEW.model_serving_gpu_type); END IF;
        IF NEW.driver_pricing_tier IS NOT NULL THEN NEW.driver_pricing_tier = LOWER(NEW.driver_pricing_tier); END IF;
        IF NEW.worker_pricing_tier IS NOT NULL THEN NEW.worker_pricing_tier = LOWER(NEW.worker_pricing_tier); END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
""")
print("  Created function: normalize_line_items_case()")

# Drop existing triggers if they exist, then create
for table, func in [("estimates", "normalize_estimates_case"), ("line_items", "normalize_line_items_case")]:
    cur.execute(f"DROP TRIGGER IF EXISTS trg_{func} ON lakemeter.{table};")
    cur.execute(f"""
        CREATE TRIGGER trg_{func}
        BEFORE INSERT OR UPDATE ON lakemeter.{table}
        FOR EACH ROW EXECUTE FUNCTION lakemeter.{func}();
    """)
    print(f"  Created trigger: trg_{func} on {table}")

# COMMAND ----------

# Verify
cur.execute("SELECT COUNT(*) FROM lakemeter.line_items WHERE dbsql_warehouse_type IS NOT NULL AND dbsql_warehouse_type != UPPER(dbsql_warehouse_type)")
remaining = cur.fetchone()[0]
print(f"\nVerification: {remaining} rows still have non-uppercase dbsql_warehouse_type (should be 0)")

cur.execute("SELECT COUNT(*) FROM lakemeter.estimates WHERE cloud IS NOT NULL AND cloud != UPPER(cloud)")
remaining = cur.fetchone()[0]
print(f"Verification: {remaining} rows still have non-uppercase cloud on estimates (should be 0)")

cur.close()
conn.close()
print("\nMigration complete!")
