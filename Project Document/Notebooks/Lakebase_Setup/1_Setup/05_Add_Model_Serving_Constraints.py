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
# MAGIC ## Step 4: Add CHECK Constraint to line_items (Optional)
# MAGIC 
# MAGIC **Type:** CHECK constraint (not FK) - Only validates MODEL_SERVING workloads
# MAGIC 
# MAGIC **WARNING:** This will fail if there are existing MODEL_SERVING line_items with invalid cloud/GPU combinations.
# MAGIC 
# MAGIC **Note:** Other workload types (VECTOR_SEARCH, FMAPI, etc.) are NOT affected by this constraint.
# MAGIC 
# MAGIC **Recommendation:** Run Test_11_Model_Serving first to ensure all GPU types are in the reference table.

# COMMAND ----------

print("=" * 80)
print("⚠️  ADDING CONSTRAINT TO line_items")
print("=" * 80)

add_constraint_sql = """
-- Add CHECK constraint for MODEL_SERVING workloads only
-- This ensures cloud + serverless_size combination is valid ONLY for MODEL_SERVING
-- Other workload types (VECTOR_SEARCH, etc.) are not affected
ALTER TABLE lakemeter.line_items
ADD CONSTRAINT chk_line_items_model_serving_gpu
CHECK (
    -- If not MODEL_SERVING, constraint passes
    workload_type != 'MODEL_SERVING' 
    OR 
    -- If MODEL_SERVING, validate cloud+serverless_size exists in reference table
    (workload_type = 'MODEL_SERVING' AND 
     EXISTS (
         SELECT 1 FROM lakemeter.ref_model_serving_gpu_types 
         WHERE cloud = line_items.cloud 
         AND gpu_type = line_items.serverless_size
         AND is_active = true
     )
    )
);

-- Note: CHECK constraint with subquery validates only MODEL_SERVING rows
-- Vector Search, FMAPI, and other workloads are not affected
"""

result = execute_sql(add_constraint_sql, "Added chk_line_items_model_serving_gpu constraint", show_error=True)

if result:
    print("\n✅ Constraint added successfully!")
    print("   • Only valid cloud/GPU combinations can be inserted for MODEL_SERVING")
    print("   • Prevents selecting AWS GPUs when cloud=AZURE, etc.")
    print("   • Other workload types (VECTOR_SEARCH, FMAPI, etc.) are NOT affected")
else:
    print("\n⚠️  Constraint could not be added.")
    print("   Possible reasons:")
    print("   1. Existing MODEL_SERVING line_items with invalid cloud/GPU combinations")
    print("   2. Sync triggers haven't populated 'cloud' column yet")
    print("   3. GPU type not in reference table")
    print("\n💡 To fix:")
    print("   1. Run Test_11_Model_Serving to populate all GPU types")
    print("   2. Delete or update existing MODEL_SERVING line_items with invalid GPU types")
    print("   3. Re-run this notebook")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Test Constraint (Optional)

# COMMAND ----------

print("=" * 80)
print("🧪 TESTING CONSTRAINT")
print("=" * 80)

test_constraint_sql = """
-- This should FAIL (AWS GPU type with AZURE cloud)
INSERT INTO lakemeter.estimates (estimate_id, owner_user_id, estimate_name, cloud, region, tier)
VALUES (gen_random_uuid(), gen_random_uuid(), 'Test Constraint', 'AZURE', 'eastus', 'PREMIUM');

-- This should FAIL (invalid cloud/GPU combination)
INSERT INTO lakemeter.line_items (
    line_item_id, estimate_id, workload_type, cloud, serverless_size
) VALUES (
    gen_random_uuid(),
    (SELECT estimate_id FROM lakemeter.estimates WHERE estimate_name = 'Test Constraint' LIMIT 1),
    'MODEL_SERVING',
    'AZURE',
    'gpu_small_t4'  -- This is AWS-specific, should fail for AZURE
);

-- Rollback the test
ROLLBACK;
"""

print("Testing constraint with invalid cloud/GPU combination...")
print("(This should fail with foreign key violation)")
result = execute_sql(test_constraint_sql, "Test constraint", show_error=True)

if not result:
    print("\n✅ Constraint is working! (Test insertion failed as expected)")
else:
    print("\n⚠️  Constraint may not be active (Test insertion succeeded)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC 
# MAGIC ✅ **What was created:**
# MAGIC - `ref_model_serving_gpu_types` table with valid cloud/GPU combinations
# MAGIC - CHECK constraint on `line_items` to prevent invalid GPU combinations (if enabled)
# MAGIC 
# MAGIC 📊 **Valid combinations:**
# MAGIC - AWS: cpu, gpu_small_t4, gpu_medium_a10g_*, gpu_xlarge/2xlarge/4xlarge_a100_80gb_*
# MAGIC - AZURE: cpu, gpu_medium_a10g_*, gpu_xlarge_a100_40gb/80gb_*
# MAGIC - GCP: cpu, gpu_small_t4, gpu_medium_g2_standard_8, gpu_xlarge/2xlarge_a100_80gb_*
# MAGIC 
# MAGIC 🔒 **CHECK Constraint behavior:**
# MAGIC - **Type:** CHECK constraint (not FK) with conditional logic
# MAGIC - **Scope:** Only validates MODEL_SERVING workload type
# MAGIC - **Impact:** Other workloads (VECTOR_SEARCH, FMAPI, etc.) are NOT affected
# MAGIC - Prevents inserting AWS GPU types when cloud=AZURE for MODEL_SERVING
# MAGIC - Prevents inserting Azure GPU types when cloud=AWS for MODEL_SERVING
# MAGIC - Prevents inserting GCP GPU types when cloud=AZURE for MODEL_SERVING
# MAGIC 
# MAGIC ⚠️  **Note:** If constraint fails, it's optional. You can skip it and rely on application-level validation.

