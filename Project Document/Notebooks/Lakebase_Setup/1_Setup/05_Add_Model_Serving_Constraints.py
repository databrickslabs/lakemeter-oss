# Databricks notebook source
# MAGIC %md
# MAGIC # Add Model Serving GPU Type Constraints
# MAGIC 
# MAGIC **Purpose:** Add constraints to prevent invalid cloud/GPU combinations for Model Serving.
# MAGIC 
# MAGIC **Why needed:**
# MAGIC - AWS, Azure, and GCP have different GPU types available
# MAGIC - Users should not be able to select AWS-specific GPUs when cloud=AZURE
# MAGIC - Prevents data integrity issues
# MAGIC 
# MAGIC **Approach:**
# MAGIC - Create a reference table with valid cloud/GPU combinations
# MAGIC - Add a foreign key constraint linking (cloud, serverless_size) to this table
# MAGIC - Only applies when workload_type = 'MODEL_SERVING'
# MAGIC 
# MAGIC **Note:** This is optional - you can skip if you want to allow any GPU type.

# COMMAND ----------

# Load Lakebase configuration (from same folder)
%run ./00_Lakebase_Config

# COMMAND ----------

import psycopg2

def execute_sql(sql, description="", show_error=True):
    """Execute SQL with error handling"""
    try:
        conn = get_lakebase_connection()
        with conn.cursor() as cur:
            cur.execute(sql)
            conn.commit()
        conn.close()
        print(f"✅ {description}")
        return True
    except Exception as e:
        if show_error:
            print(f"❌ {description}: {str(e)}")
        return False

print("✅ Setup complete!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Create Reference Table for Valid Cloud/GPU Combinations

# COMMAND ----------

print("=" * 80)
print("📋 CREATING MODEL SERVING GPU REFERENCE TABLE")
print("=" * 80)

create_ref_table_sql = """
-- Drop existing table if exists
DROP TABLE IF EXISTS lakemeter.ref_model_serving_gpu_types CASCADE;

-- Create reference table for valid cloud/GPU combinations
CREATE TABLE lakemeter.ref_model_serving_gpu_types (
    cloud VARCHAR(20) NOT NULL,
    gpu_type VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    PRIMARY KEY (cloud, gpu_type)
);

-- Add comment
COMMENT ON TABLE lakemeter.ref_model_serving_gpu_types IS 
'Reference table for valid Model Serving GPU types per cloud. Used to constrain line_items.serverless_size.';
"""

execute_sql(create_ref_table_sql, "Created ref_model_serving_gpu_types table")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Populate with Valid Cloud/GPU Combinations from Pricing Table

# COMMAND ----------

print("=" * 80)
print("📊 POPULATING FROM PRICING TABLE")
print("=" * 80)

populate_sql = """
-- Populate from pricing table (only active GPU types)
INSERT INTO lakemeter.ref_model_serving_gpu_types (cloud, gpu_type, description)
SELECT DISTINCT 
    cloud,
    size_or_model as gpu_type,
    'Model Serving: ' || size_or_model || ' (' || dbu_rate || ' DBU/hour)' as description
FROM lakemeter.sync_product_serverless_rates
WHERE product = 'model_serving'
ORDER BY cloud, size_or_model;
"""

execute_sql(populate_sql, "Populated ref_model_serving_gpu_types from pricing table")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Query and Display Valid Combinations

# COMMAND ----------

print("=" * 80)
print("📋 VALID CLOUD/GPU COMBINATIONS")
print("=" * 80)

query_sql = """
SELECT cloud, COUNT(*) as gpu_types, STRING_AGG(gpu_type, ', ' ORDER BY gpu_type) as available_gpus
FROM lakemeter.ref_model_serving_gpu_types
WHERE is_active = true
GROUP BY cloud
ORDER BY cloud;
"""

conn = get_lakebase_connection()
with conn.cursor() as cur:
    cur.execute(query_sql)
    results = cur.fetchall()
    
print("\n{:<10} {:<15} {}".format("Cloud", "GPU Types", "Available GPUs"))
print("-" * 100)
for row in results:
    print(f"{row[0]:<10} {row[1]:<15} {row[2]}")
conn.close()

print("\n✅ Reference table populated!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Add Validation Trigger to line_items (Optional)
# MAGIC 
# MAGIC **Type:** Trigger (not constraint) - Only validates MODEL_SERVING workloads
# MAGIC 
# MAGIC **Validation approach (Simplified):**
# MAGIC - Checks if GPU type exists in reference table (any cloud)
# MAGIC - Does NOT validate cloud-specific GPU types
# MAGIC - Application layer should handle cloud-specific validation
# MAGIC 
# MAGIC **Why simplified?**
# MAGIC - Prevents typos (e.g., "gpu_small" instead of "gpu_small_t4")
# MAGIC - Ensures GPU type exists in pricing table
# MAGIC - Simpler and more reliable than cloud-specific validation
# MAGIC - Cloud-specific validation is better handled by application/UI
# MAGIC 
# MAGIC **Note:** 
# MAGIC - Only validates NEW inserts and updates (existing data is NOT checked)
# MAGIC - Other workload types (VECTOR_SEARCH, FMAPI, etc.) are NOT affected
# MAGIC 
# MAGIC **Recommendation:** Run Test_11_Model_Serving first to ensure all GPU types are in the reference table.

# COMMAND ----------

print("=" * 80)
print("⚠️  ADDING CONSTRAINT TO line_items")
print("=" * 80)

add_constraint_sql = """
-- Create trigger function to validate MODEL_SERVING GPU types
-- Simplified: Just check if GPU type exists (any cloud), not cloud-specific
CREATE OR REPLACE FUNCTION lakemeter.validate_model_serving_gpu_type()
RETURNS TRIGGER AS $$
BEGIN
    -- Only validate if workload_type is MODEL_SERVING
    IF NEW.workload_type = 'MODEL_SERVING' THEN
        -- Check if serverless_size exists in reference table (any cloud)
        IF NOT EXISTS (
            SELECT 1 FROM lakemeter.ref_model_serving_gpu_types
            WHERE gpu_type = NEW.serverless_size
            AND is_active = true
        ) THEN
            RAISE EXCEPTION 'Invalid GPU type "%". Must be one of the valid GPU types in ref_model_serving_gpu_types table. Common types: cpu, gpu_small_t4, gpu_medium_a10g_1x, gpu_xlarge_a100_80gb_8x, etc.',
                NEW.serverless_size;
        END IF;
    END IF;
    
    -- If not MODEL_SERVING or validation passed, allow the operation
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists
DROP TRIGGER IF EXISTS trg_validate_model_serving_gpu ON lakemeter.line_items;

-- Create trigger on INSERT and UPDATE
CREATE TRIGGER trg_validate_model_serving_gpu
    BEFORE INSERT OR UPDATE ON lakemeter.line_items
    FOR EACH ROW
    EXECUTE FUNCTION lakemeter.validate_model_serving_gpu_type();

-- Note: 
-- - Trigger validates MODEL_SERVING workload type only
-- - Checks if GPU type exists in reference table (ANY cloud)
-- - Does NOT validate cloud-specific GPU types (application layer handles that)
-- - Prevents typos and ensures GPU type exists
-- - Vector Search, FMAPI, and other workloads are not affected
"""

result = execute_sql(add_constraint_sql, "Created trigger validate_model_serving_gpu_type", show_error=True)

if result:
    print("\n✅ Trigger added successfully!")
    print("   • Validates GPU types for MODEL_SERVING workloads")
    print("   • Prevents typos (e.g., 'gpu_small' instead of 'gpu_small_t4')")
    print("   • Ensures GPU type exists in reference table (any cloud)")
    print("   • Other workload types (VECTOR_SEARCH, FMAPI, etc.) are NOT affected")
    print("   • Trigger validates on INSERT and UPDATE operations")
    print("\n⚠️  Note: Trigger does NOT validate cloud-specific GPU availability")
    print("   (e.g., doesn't prevent AWS-only GPUs on Azure)")
    print("   → Application/UI layer should handle cloud-specific filtering")
else:
    print("\n⚠️  Trigger could not be added.")
    print("   Possible reasons:")
    print("   1. Permission issues creating functions/triggers")
    print("   2. Syntax errors in trigger definition")
    print("\n💡 To fix:")
    print("   1. Check if lakemeter_sync_role has CREATE FUNCTION permission")
    print("   2. Re-run this notebook")
    print("\n⚠️  Note: Existing line_items will NOT be validated.")
    print("   The trigger only validates NEW inserts and updates.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Test Constraint (Optional)

# COMMAND ----------

print("=" * 80)
print("🧪 TESTING TRIGGER (Simplified Validation)")
print("=" * 80)

print("Testing trigger with invalid GPU type (not in reference table)...")
print("(This should fail with trigger exception)")

# Test the trigger with proper setup
test_trigger_sql = """
-- Step 1: Create a test user
INSERT INTO lakemeter.users (user_id, full_name, email, role, is_active, created_at, updated_at)
VALUES ('00000000-0000-0000-0000-000000000001', 'Test User', 'test_trigger@example.com', 'admin', true, NOW(), NOW())
ON CONFLICT (user_id) DO NOTHING;

-- Step 2: Create a test estimate
INSERT INTO lakemeter.estimates (estimate_id, owner_user_id, estimate_name, cloud, region, tier, created_at, updated_at)
VALUES ('00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001', 'Test GPU Trigger', 'AWS', 'us-east-1', 'PREMIUM', NOW(), NOW())
ON CONFLICT (estimate_id) DO NOTHING;

-- Step 3: Try to insert COMPLETELY INVALID GPU type (typo/doesn't exist)
-- This should FAIL with trigger exception: "Invalid GPU type gpu_invalid_typo"
INSERT INTO lakemeter.line_items (
    line_item_id, estimate_id, display_order, workload_name, workload_type, 
    serverless_enabled, photon_enabled, serverless_product, serverless_size,
    runs_per_day, avg_runtime_minutes, days_per_month, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    '00000000-0000-0000-0000-000000000002',
    1, 'Test Invalid GPU', 'MODEL_SERVING',
    TRUE, TRUE, 'model_serving', 'gpu_invalid_typo',  -- Doesn't exist in table ❌
    24, 60, 30, NOW(), NOW()
);
"""

result = execute_sql(test_trigger_sql, "Test trigger with invalid GPU", show_error=True)

if not result:
    print("\n✅ Trigger is working! (Invalid GPU insertion failed as expected)")
    print("   • GPU type 'gpu_invalid_typo' was correctly rejected (not in reference table)")
else:
    print("\n⚠️  Trigger may not be active (Invalid GPU insertion succeeded)")
    
# Test with valid GPU to confirm trigger allows valid data
print("\n   Testing with VALID GPU to confirm trigger allows valid data...")
test_valid_sql = """
INSERT INTO lakemeter.line_items (
    line_item_id, estimate_id, display_order, workload_name, workload_type, 
    serverless_enabled, photon_enabled, serverless_product, serverless_size,
    runs_per_day, avg_runtime_minutes, days_per_month, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    '00000000-0000-0000-0000-000000000002',
    2, 'Test Valid GPU', 'MODEL_SERVING',
    TRUE, TRUE, 'model_serving', 'cpu',  -- Valid (exists in table) ✅
    24, 60, 30, NOW(), NOW()
);
"""
valid_result = execute_sql(test_valid_sql, "Test with valid GPU (cpu)", show_error=True)
if valid_result:
    print("   ✅ Valid GPU 'cpu' was accepted (trigger allows valid data)")
else:
    print("   ❌ Valid GPU 'cpu' was rejected (trigger may be too strict)")
    
# Cleanup test data
print("\n🧹 Cleaning up test data...")
cleanup_sql = """
DELETE FROM lakemeter.line_items WHERE estimate_id = '00000000-0000-0000-0000-000000000002';
DELETE FROM lakemeter.estimates WHERE estimate_id = '00000000-0000-0000-0000-000000000002';
DELETE FROM lakemeter.users WHERE user_id = '00000000-0000-0000-0000-000000000001';
"""
execute_sql(cleanup_sql, "Cleanup test data", show_error=False)
print("✅ Test data cleaned up")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC 
# MAGIC ✅ **What was created:**
# MAGIC - `ref_model_serving_gpu_types` table with all valid GPU types
# MAGIC - Validation trigger on `line_items` to prevent typos and invalid GPU types (if enabled)
# MAGIC 
# MAGIC 📊 **Valid GPU types (all clouds combined):**
# MAGIC - **cpu** (all clouds)
# MAGIC - **gpu_small_t4** (AWS, GCP)
# MAGIC - **gpu_medium_a10g_1x/4x/8x** (AWS, Azure)
# MAGIC - **gpu_medium_g2_standard_8** (GCP)
# MAGIC - **gpu_xlarge_a100_40gb_8x** (Azure)
# MAGIC - **gpu_xlarge/2xlarge/4xlarge_a100_80gb_*** (AWS, GCP)
# MAGIC 
# MAGIC 🔒 **Trigger behavior (Simplified):**
# MAGIC - **Type:** BEFORE INSERT OR UPDATE trigger
# MAGIC - **Scope:** Only validates MODEL_SERVING workload type
# MAGIC - **Validation:** Checks if GPU type exists in reference table (ANY cloud)
# MAGIC - **Does NOT validate:** Cloud-specific GPU availability
# MAGIC - **Impact:** Other workloads (VECTOR_SEARCH, FMAPI, etc.) are NOT affected
# MAGIC - **Benefits:**
# MAGIC   - Prevents typos (e.g., "gpu_small" instead of "gpu_small_t4")
# MAGIC   - Ensures GPU type exists in pricing table
# MAGIC   - Simple and reliable validation
# MAGIC - **Application layer responsibility:**
# MAGIC   - Validate cloud-specific GPU availability (e.g., don't show AWS-only GPUs for Azure)
# MAGIC   - This is better handled by UI/frontend logic
# MAGIC 
# MAGIC ⚠️  **Note:** If trigger creation fails, it's optional. You can skip it and rely on application-level validation.

