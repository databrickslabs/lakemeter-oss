# Databricks notebook source
# MAGIC %md
# MAGIC # Add FMAPI Model Validation Constraints (Optional)
# MAGIC 
# MAGIC **Purpose:** Add database-level validation for FMAPI model names.
# MAGIC 
# MAGIC **What it does:**
# MAGIC - Creates reference tables for valid Databricks and Proprietary model names
# MAGIC - Adds triggers to validate model names on INSERT/UPDATE
# MAGIC - Prevents typos and ensures models exist in pricing tables
# MAGIC 
# MAGIC **Note:** This is OPTIONAL. You can rely on application-level validation instead.

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2

def execute_sql(sql, description, show_error=True):
    """Execute SQL and return True if successful"""
    conn = get_lakebase_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            conn.commit()
            print(f"✅ {description}")
            return True
    except Exception as e:
        conn.rollback()
        if show_error:
            print(f"❌ {description}: {e}")
        return False
    finally:
        conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Create Reference Tables

# COMMAND ----------

print("=" * 80)
print("CREATING REFERENCE TABLES FOR FMAPI MODELS")
print("=" * 80)

# Create ref table for Databricks models
create_databricks_ref_sql = """
CREATE TABLE IF NOT EXISTS lakemeter.ref_fmapi_databricks_models (
    model_name VARCHAR(100) PRIMARY KEY,
    description TEXT,
    is_active BOOLEAN DEFAULT true
);
"""

execute_sql(create_databricks_ref_sql, "Created ref_fmapi_databricks_models table")

# COMMAND ----------

# Populate with available models
populate_databricks_sql = """
INSERT INTO lakemeter.ref_fmapi_databricks_models (model_name, description, is_active)
SELECT DISTINCT model, 'Databricks-hosted model', true
FROM lakemeter.sync_product_fmapi_databricks
ON CONFLICT (model_name) DO NOTHING;
"""

execute_sql(populate_databricks_sql, "Populated ref_fmapi_databricks_models from sync table")

# COMMAND ----------

# Create ref table for Proprietary models
create_proprietary_ref_sql = """
CREATE TABLE IF NOT EXISTS lakemeter.ref_fmapi_proprietary_models (
    provider VARCHAR(50),
    model_name VARCHAR(100),
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    PRIMARY KEY (provider, model_name)
);
"""

execute_sql(create_proprietary_ref_sql, "Created ref_fmapi_proprietary_models table")

# COMMAND ----------

# Populate with available proprietary models
populate_proprietary_sql = """
INSERT INTO lakemeter.ref_fmapi_proprietary_models (provider, model_name, description, is_active)
SELECT DISTINCT provider, model, 'Proprietary model served by Databricks', true
FROM lakemeter.sync_product_fmapi_proprietary
ON CONFLICT (provider, model_name) DO NOTHING;
"""

execute_sql(populate_proprietary_sql, "Populated ref_fmapi_proprietary_models from sync table")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Create Validation Triggers

# COMMAND ----------

print("\n" + "=" * 80)
print("CREATING VALIDATION TRIGGERS")
print("=" * 80)

# COMMAND ----------

create_trigger_sql = """
-- Function to validate FMAPI model names
CREATE OR REPLACE FUNCTION lakemeter.validate_fmapi_model()
RETURNS TRIGGER AS $$
BEGIN
    -- Validate FMAPI_DATABRICKS models
    IF NEW.workload_type = 'FMAPI_DATABRICKS' THEN
        IF NOT EXISTS (
            SELECT 1 FROM lakemeter.ref_fmapi_databricks_models
            WHERE model_name = NEW.fmapi_model
            AND is_active = true
        ) THEN
            RAISE EXCEPTION 'Invalid Databricks model "%". Valid models can be found in ref_fmapi_databricks_models table.', NEW.fmapi_model;
        END IF;
    END IF;
    
    -- Validate FMAPI_PROPRIETARY models
    IF NEW.workload_type = 'FMAPI_PROPRIETARY' THEN
        IF NOT EXISTS (
            SELECT 1 FROM lakemeter.ref_fmapi_proprietary_models
            WHERE provider = NEW.fmapi_provider
            AND model_name = NEW.fmapi_model
            AND is_active = true
        ) THEN
            RAISE EXCEPTION 'Invalid proprietary model "%" for provider "%". Valid models can be found in ref_fmapi_proprietary_models table.', NEW.fmapi_model, NEW.fmapi_provider;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists
DROP TRIGGER IF EXISTS trg_validate_fmapi_model ON lakemeter.line_items;

-- Create trigger
CREATE TRIGGER trg_validate_fmapi_model
    BEFORE INSERT OR UPDATE ON lakemeter.line_items
    FOR EACH ROW
    EXECUTE FUNCTION lakemeter.validate_fmapi_model();
"""

result = execute_sql(create_trigger_sql, "Created FMAPI model validation trigger")

if result:
    print("\n✅ Trigger added successfully!")
    print("   • Validates FMAPI_DATABRICKS model names")
    print("   • Validates FMAPI_PROPRIETARY model/provider combinations")
    print("   • Prevents typos and ensures models exist in pricing tables")
else:
    print("\n⚠️  Trigger could not be added.")
    print("   This is optional - you can rely on application-level validation.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Test the Trigger

# COMMAND ----------

print("\n" + "=" * 80)
print("TESTING FMAPI MODEL VALIDATION TRIGGER")
print("=" * 80)

# Create test user
TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
execute_sql(
    f"INSERT INTO lakemeter.users (user_id, email, full_name, role, is_active, created_at) VALUES ('{TEST_USER_ID}', 'fmapi_trigger_test@databricks.com', 'FMAPI Trigger Test', 'admin', TRUE, NOW()) ON CONFLICT (user_id) DO NOTHING;",
    "Created test user"
)

# Create test estimate
TEST_ESTIMATE_ID = "00000000-0000-0000-0000-000000000002"
execute_sql(
    f"INSERT INTO lakemeter.estimates (estimate_id, owner_user_id, estimate_name, cloud, region, tier, created_at, updated_at) VALUES ('{TEST_ESTIMATE_ID}', '{TEST_USER_ID}', 'FMAPI Trigger Test', 'AWS', 'us-east-1', 'PREMIUM', NOW(), NOW()) ON CONFLICT (estimate_id) DO NOTHING;",
    "Created test estimate"
)

# COMMAND ----------

# Test 1: Invalid Databricks model (should fail)
print("\n📋 Test 1: Invalid Databricks Model (should be rejected)")
print("-" * 80)

invalid_databricks_sql = f"""
INSERT INTO lakemeter.line_items (
    line_item_id, estimate_id, display_order, workload_name, workload_type,
    serverless_enabled, photon_enabled, fmapi_model, fmapi_provisioned_type,
    fmapi_input_tokens_per_month, fmapi_output_tokens_per_month,
    runs_per_day, avg_runtime_minutes, days_per_month, created_at, updated_at
) VALUES (
    gen_random_uuid(), '{TEST_ESTIMATE_ID}', 1, 'Test Invalid Databricks Model', 'FMAPI_DATABRICKS',
    TRUE, TRUE, 'invalid-model-name', 'pay_per_token',
    1000000, 500000, 24, 60, 30, NOW(), NOW()
);
"""

result = execute_sql(invalid_databricks_sql, "Insert invalid Databricks model", show_error=True)
if not result:
    print("✅ PASS: Invalid Databricks model was correctly rejected!")
else:
    print("❌ FAIL: Invalid model was accepted (trigger not working)")

# COMMAND ----------

# Test 2: Valid Databricks model (should succeed)
print("\n📋 Test 2: Valid Databricks Model (should be accepted)")
print("-" * 80)

valid_databricks_sql = f"""
INSERT INTO lakemeter.line_items (
    line_item_id, estimate_id, display_order, workload_name, workload_type,
    serverless_enabled, photon_enabled, fmapi_model, fmapi_provisioned_type,
    fmapi_input_tokens_per_month, fmapi_output_tokens_per_month,
    runs_per_day, avg_runtime_minutes, days_per_month, created_at, updated_at
) VALUES (
    gen_random_uuid(), '{TEST_ESTIMATE_ID}', 2, 'Test Valid Databricks Model', 'FMAPI_DATABRICKS',
    TRUE, TRUE, 'gte', 'pay_per_token',
    1000000, 0, 24, 60, 30, NOW(), NOW()
);
"""

result = execute_sql(valid_databricks_sql, "Insert valid Databricks model", show_error=True)
if result:
    print("✅ PASS: Valid Databricks model was accepted!")
else:
    print("❌ FAIL: Valid model was rejected (trigger too strict)")

# COMMAND ----------

# Cleanup
print("\n🧹 Cleaning up test data...")
execute_sql(
    f"DELETE FROM lakemeter.line_items WHERE estimate_id = '{TEST_ESTIMATE_ID}';",
    "Deleted test line items"
)
execute_sql(
    f"DELETE FROM lakemeter.estimates WHERE estimate_id = '{TEST_ESTIMATE_ID}';",
    "Deleted test estimate"
)
execute_sql(
    f"DELETE FROM lakemeter.users WHERE user_id = '{TEST_USER_ID}';",
    "Deleted test user"
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC 
# MAGIC ✅ **What was created:**
# MAGIC - `ref_fmapi_databricks_models` - Valid Databricks model names
# MAGIC - `ref_fmapi_proprietary_models` - Valid proprietary model/provider combinations
# MAGIC - Validation trigger on `line_items`
# MAGIC 
# MAGIC 🔒 **Trigger behavior:**
# MAGIC - Validates `FMAPI_DATABRICKS` model names
# MAGIC - Validates `FMAPI_PROPRIETARY` model/provider combinations
# MAGIC - Prevents typos and invalid model names
# MAGIC - Only affects FMAPI workloads (other workloads unaffected)
# MAGIC 
# MAGIC 📋 **Application layer responsibility:**
# MAGIC - Show only valid models in dropdowns (query ref tables)
# MAGIC - Filter by cloud/tier if pricing varies
# MAGIC - Provide better UX than database error messages
# MAGIC 
# MAGIC ⚠️  **Note:** This is optional. You can disable the trigger and rely on application-level validation only.

