# Databricks notebook source
# MAGIC %md
# MAGIC # SKU Discount Category Mapping
# MAGIC
# MAGIC **Purpose:** Create and populate the `sku_discount_mapping` table that maps product_type SKUs to discount categories.
# MAGIC
# MAGIC **Target Database:** Lakebase (PostgreSQL) - `lakemeter` schema
# MAGIC
# MAGIC **Discount Categories:**
# MAGIC - `dbu` - All compute/DBU-based workloads (eligible for EA discounts)
# MAGIC - `storage` - Storage and DSU-based workloads (rarely discounted)
# MAGIC - `support` - Support and compliance products (rarely discounted)
# MAGIC - `network` - Network egress/connectivity (typically NOT discounted)
# MAGIC - `excluded` - Internal/RnD usage (NOT discounted)
# MAGIC
# MAGIC **Author:** Steven Tan  
# MAGIC **Date:** 2026-01-20

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Install Dependencies & Connect to Lakebase

# COMMAND ----------

# Install required packages
%pip install psycopg2-binary --quiet
dbutils.library.restartPython()

# COMMAND ----------

import psycopg2
from datetime import datetime

# Lakebase connection details
LAKEBASE_HOST = "instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com"
LAKEBASE_PORT = 5432
LAKEBASE_DATABASE = "lakemeter_pricing"
LAKEBASE_USER = "lakemeter_sync_role"
LAKEBASE_PASSWORD = dbutils.secrets.get(scope="lakemeter-credentials", key="lakebase-password")

print("✅ Lakebase connection details loaded")
print(f"   Host: {LAKEBASE_HOST}")
print(f"   Database: {LAKEBASE_DATABASE}")
print(f"   User: {LAKEBASE_USER}")

# COMMAND ----------

# Connect to Lakebase
conn = psycopg2.connect(
    host=LAKEBASE_HOST,
    port=LAKEBASE_PORT,
    database=LAKEBASE_DATABASE,
    user=LAKEBASE_USER,
    password=LAKEBASE_PASSWORD
)
cursor = conn.cursor()

print("✅ Connected to Lakebase successfully")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Create SKU Discount Mapping Table

# COMMAND ----------

# DBTITLE 1,Create sku_discount_mapping table
create_table_sql = """
CREATE TABLE IF NOT EXISTS lakemeter.sku_discount_mapping (
    sku VARCHAR(100) PRIMARY KEY,
    discount_category VARCHAR(50) NOT NULL,
    description VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_discount_category 
    CHECK (discount_category IN ('dbu', 'storage', 'support', 'network', 'excluded'))
);

COMMENT ON TABLE lakemeter.sku_discount_mapping IS 'Maps SKU product_types to discount categories for pricing calculations';
"""

try:
    cursor.execute(create_table_sql)
    conn.commit()
    print("✅ Table 'lakemeter.sku_discount_mapping' created successfully")
except Exception as e:
    conn.rollback()
    print(f"❌ Error creating table: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Verify Existing Product Types

# COMMAND ----------

# DBTITLE 1,Query all distinct product_types from pricing table
query_product_types = """
SELECT DISTINCT product_type 
FROM lakemeter.sync_pricing_dbu_rates
ORDER BY product_type;
"""

try:
    cursor.execute(query_product_types)
    product_types = cursor.fetchall()
    print(f"📊 Found {len(product_types)} distinct product_types in sync_pricing_dbu_rates:")
    for pt in product_types:
        print(f"   - {pt[0]}")
except Exception as e:
    print(f"❌ Error querying product types: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Insert SKU Mappings by Category

# COMMAND ----------

# DBTITLE 1,DBU Category - All Compute/Workload SKUs
dbu_mappings_sql = """
INSERT INTO lakemeter.sku_discount_mapping (sku, discount_category, description) VALUES
-- All-Purpose Compute
('ALL_PURPOSE_COMPUTE', 'dbu', 'Classic all-purpose compute'),
('ALL_PURPOSE_COMPUTE_(DLT)', 'dbu', 'All-purpose compute for DLT'),
('ALL_PURPOSE_COMPUTE_(PHOTON)', 'dbu', 'All-purpose compute with Photon'),
('ALL_PURPOSE_SERVERLESS_COMPUTE', 'dbu', 'Serverless all-purpose compute'),

-- Jobs Compute
('JOBS_COMPUTE', 'dbu', 'Classic jobs compute'),
('JOBS_COMPUTE_(PHOTON)', 'dbu', 'Jobs compute with Photon'),
('JOBS_LIGHT_COMPUTE', 'dbu', 'Jobs light compute'),
('JOBS_SERVERLESS_COMPUTE', 'dbu', 'Serverless jobs compute'),

-- SQL Compute
('SQL_COMPUTE', 'dbu', 'Classic SQL compute'),
('SQL_PRO_COMPUTE', 'dbu', 'SQL Pro compute'),
('SERVERLESS_SQL_COMPUTE', 'dbu', 'Serverless SQL compute'),
('DATABASE_SERVERLESS_COMPUTE', 'dbu', 'Database serverless compute'),

-- DLT (Delta Live Tables)
('DLT_CORE_COMPUTE', 'dbu', 'DLT Core edition'),
('DLT_CORE_COMPUTE_(PHOTON)', 'dbu', 'DLT Core with Photon'),
('DLT_PRO_COMPUTE', 'dbu', 'DLT Pro edition'),
('DLT_PRO_COMPUTE_(PHOTON)', 'dbu', 'DLT Pro with Photon'),
('DLT_ADVANCED_COMPUTE', 'dbu', 'DLT Advanced edition'),
('DLT_ADVANCED_COMPUTE_(PHOTON)', 'dbu', 'DLT Advanced with Photon'),

-- Model Training
('MODEL_TRAINING', 'dbu', 'Model training compute'),
('MODEL_TRAINING_ON_DEMAND', 'dbu', 'Model training on-demand'),
('MODEL_TRAINING_RESERVATION', 'dbu', 'Model training reserved capacity'),
('MODEL_TRAINING_HERO_RESERVATION', 'dbu', 'Model training hero reservation'),
('MODEL_TRAINING_IN_CUSTOMER_TENANCY', 'dbu', 'Model training in customer tenancy'),
('MODEL_TRAINING_SERVERLESS_GPU_COMPUTE_PROVISIONED_CAPACITY', 'dbu', 'Serverless GPU provisioned capacity'),

-- Model Serving (FMAPI)
('SERVERLESS_REAL_TIME_INFERENCE', 'dbu', 'Serverless real-time inference'),
('SERVERLESS_REAL_TIME_INFERENCE_LAUNCH', 'dbu', 'Serverless real-time inference launch'),
('ANTHROPIC_MODEL_SERVING', 'dbu', 'Anthropic model serving (FMAPI)'),
('OPENAI_MODEL_SERVING', 'dbu', 'OpenAI model serving (FMAPI)'),
('GEMINI_MODEL_SERVING', 'dbu', 'Gemini model serving (FMAPI)'),

-- Clean Rooms
('CLEAN_ROOMS_COLLABORATOR', 'dbu', 'Clean Rooms collaborator compute')
ON CONFLICT (sku) DO NOTHING;
"""

try:
    cursor.execute(dbu_mappings_sql)
    conn.commit()
    print(f"✅ DBU category mappings inserted ({cursor.rowcount} rows)")
except Exception as e:
    conn.rollback()
    print(f"❌ Error inserting DBU mappings: {e}")
    raise

# COMMAND ----------

# DBTITLE 1,Storage Category - DSU and Storage SKUs
storage_mappings_sql = """
INSERT INTO lakemeter.sku_discount_mapping (sku, discount_category, description) VALUES
('DATABRICKS_STORAGE', 'storage', 'Databricks storage (DSU)'),
('DATABRICKS_STORAGE_GB', 'storage', 'Databricks storage per GB'),
('DATABRICKS_STORAGE_TIER1REQUESTS', 'storage', 'Storage Tier 1 requests'),
('DATABRICKS_STORAGE_TIER2REQUESTS', 'storage', 'Storage Tier 2 requests')
ON CONFLICT (sku) DO NOTHING;
"""

try:
    cursor.execute(storage_mappings_sql)
    conn.commit()
    print(f"✅ Storage category mappings inserted ({cursor.rowcount} rows)")
except Exception as e:
    conn.rollback()
    print(f"❌ Error inserting storage mappings: {e}")
    raise

# COMMAND ----------

# DBTITLE 1,Support Category - Enhanced Security & Compliance
support_mappings_sql = """
INSERT INTO lakemeter.sku_discount_mapping (sku, discount_category, description) VALUES
('ENHANCED_SECURITY_AND_COMPLIANCE_FOR_WORKSPACES', 'support', 'Enhanced security and compliance add-on')
ON CONFLICT (sku) DO NOTHING;
"""

try:
    cursor.execute(support_mappings_sql)
    conn.commit()
    print(f"✅ Support category mappings inserted ({cursor.rowcount} rows)")
except Exception as e:
    conn.rollback()
    print(f"❌ Error inserting support mappings: {e}")
    raise

# COMMAND ----------

# DBTITLE 1,Network Category - Egress and Connectivity (NOT Discounted)
network_mappings_sql = """
INSERT INTO lakemeter.sku_discount_mapping (sku, discount_category, description) VALUES
-- Databricks-specific egress
('DATABRICKS_INTERNET_EGRESS_ASIA', 'network', 'Databricks internet egress - Asia'),
('DATABRICKS_INTERNET_EGRESS_EUROPE', 'network', 'Databricks internet egress - Europe'),
('DATABRICKS_INTERNET_EGRESS_NORTH_AMERICA', 'network', 'Databricks internet egress - North America'),
('DATABRICKS_INTERNET_EGRESS_SOUTH_AMERICA', 'network', 'Databricks internet egress - South America'),
('DATABRICKS_INTER_AZ_EGRESS', 'network', 'Databricks inter-AZ egress'),

-- Databricks inter-continental egress
('DATABRICKS_INTER_CONTINENTAL_EGRESS_AFRICA', 'network', 'Databricks inter-continental egress - Africa'),
('DATABRICKS_INTER_CONTINENTAL_EGRESS_ASIA', 'network', 'Databricks inter-continental egress - Asia'),
('DATABRICKS_INTER_CONTINENTAL_EGRESS_EUROPE', 'network', 'Databricks inter-continental egress - Europe'),
('DATABRICKS_INTER_CONTINENTAL_EGRESS_MIDDLE_EAST', 'network', 'Databricks inter-continental egress - Middle East'),
('DATABRICKS_INTER_CONTINENTAL_EGRESS_NORTH_AMERICA', 'network', 'Databricks inter-continental egress - North America'),
('DATABRICKS_INTER_CONTINENTAL_EGRESS_OCEANIA', 'network', 'Databricks inter-continental egress - Oceania'),
('DATABRICKS_INTER_CONTINENTAL_EGRESS_SOUTH_AMERICA', 'network', 'Databricks inter-continental egress - South America'),

-- Databricks inter-region egress
('DATABRICKS_INTER_REGION_EGRESS_ASIA', 'network', 'Databricks inter-region egress - Asia'),
('DATABRICKS_INTER_REGION_EGRESS_EUROPE', 'network', 'Databricks inter-region egress - Europe'),
('DATABRICKS_INTER_REGION_EGRESS_NORTH_AMERICA', 'network', 'Databricks inter-region egress - North America'),
('DATABRICKS_INTER_REGION_EGRESS_SOUTH_AMERICA', 'network', 'Databricks inter-region egress - South America'),

-- Generic egress (cloud provider)
('INTERNET_EGRESS_AFRICA', 'network', 'Internet egress - Africa'),
('INTERNET_EGRESS_ASIA', 'network', 'Internet egress - Asia'),
('INTERNET_EGRESS_EUROPE', 'network', 'Internet egress - Europe'),
('INTERNET_EGRESS_FROM', 'network', 'Internet egress from region'),
('INTERNET_EGRESS_MIDDLE_EAST', 'network', 'Internet egress - Middle East'),
('INTERNET_EGRESS_NORTH_AMERICA', 'network', 'Internet egress - North America'),
('INTERNET_EGRESS_OCEANIA', 'network', 'Internet egress - Oceania'),
('INTERNET_EGRESS_SOUTH_AMERICA', 'network', 'Internet egress - South America'),
('INTER_AVAILABILITY_ZONE_EGRESS', 'network', 'Inter-availability zone egress'),
('INTER_REGION_EGRESS', 'network', 'Inter-region egress'),
('INTER_REGION_EGRESS_FROM', 'network', 'Inter-region egress from region'),

-- Private and Public Connectivity
('PRIVATE_CONNECTIVITY_DATA_PROCESSED', 'network', 'Private connectivity data processed'),
('PRIVATE_CONNECTIVITY_ENDPOINT', 'network', 'Private connectivity endpoint'),
('PRIVATE_CONNECTIVITY_INBOUND_DATA_PROCESSED', 'network', 'Private connectivity inbound data'),
('PRIVATE_CONNECTIVITY_OUTBOUND_DATA_PROCESSED', 'network', 'Private connectivity outbound data'),
('PUBLIC_CONNECTIVITY_DATA_PROCESSED', 'network', 'Public connectivity data processed'),
('PUBLIC_CONNECTIVITY_DATA_PROCESSED_US_GOV', 'network', 'Public connectivity data processed (US Gov)')
ON CONFLICT (sku) DO NOTHING;
"""

try:
    cursor.execute(network_mappings_sql)
    conn.commit()
    print(f"✅ Network category mappings inserted ({cursor.rowcount} rows)")
except Exception as e:
    conn.rollback()
    print(f"❌ Error inserting network mappings: {e}")
    raise

# COMMAND ----------

# DBTITLE 1,Excluded Category - Internal/RnD
excluded_mappings_sql = """
INSERT INTO lakemeter.sku_discount_mapping (sku, discount_category, description) VALUES
('INTERNAL_RND_USAGE', 'excluded', 'Internal R&D usage - not for customer discounts')
ON CONFLICT (sku) DO NOTHING;
"""

try:
    cursor.execute(excluded_mappings_sql)
    conn.commit()
    print(f"✅ Excluded category mappings inserted ({cursor.rowcount} rows)")
except Exception as e:
    conn.rollback()
    print(f"❌ Error inserting excluded mappings: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Verify Mappings

# COMMAND ----------

# DBTITLE 1,Count by discount category
category_counts_query = """
SELECT 
    discount_category,
    COUNT(*) as sku_count
FROM lakemeter.sku_discount_mapping
GROUP BY discount_category
ORDER BY discount_category;
"""

try:
    cursor.execute(category_counts_query)
    category_counts = cursor.fetchall()
    print("📊 SKU Count by Discount Category:")
    print(f"{'Category':<15} {'Count':<10}")
    print("-" * 25)
    for cat, count in category_counts:
        print(f"{cat:<15} {count:<10}")
except Exception as e:
    print(f"❌ Error querying category counts: {e}")

# COMMAND ----------

# DBTITLE 1,Show all mappings
all_mappings_query = """
SELECT 
    sku,
    discount_category,
    description
FROM lakemeter.sku_discount_mapping
ORDER BY discount_category, sku;
"""

try:
    cursor.execute(all_mappings_query)
    all_mappings = cursor.fetchall()
    print(f"📋 All SKU Discount Mappings ({len(all_mappings)} total):\n")
    
    current_category = None
    for sku, category, description in all_mappings:
        if category != current_category:
            current_category = category
            print(f"\n{'='*80}")
            print(f"Category: {category.upper()}")
            print(f"{'='*80}")
        print(f"  {sku:<50} | {description}")
except Exception as e:
    print(f"❌ Error querying mappings: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Validate: Check for Missing SKUs

# COMMAND ----------

# DBTITLE 1,Find product_types not yet mapped
missing_skus_query = """
SELECT DISTINCT p.product_type
FROM lakemeter.sync_pricing_dbu_rates p
LEFT JOIN lakemeter.sku_discount_mapping m
    ON p.product_type = m.sku
WHERE m.sku IS NULL
ORDER BY p.product_type;
"""

try:
    cursor.execute(missing_skus_query)
    missing_skus = cursor.fetchall()
    
    if missing_skus:
        print(f"⚠️ WARNING: {len(missing_skus)} product_types are NOT yet mapped:")
        for sku in missing_skus:
            print(f"   - {sku[0]}")
    else:
        print("✅ All product_types from sync_pricing_dbu_rates are mapped!")
except Exception as e:
    print(f"❌ Error checking for missing SKUs: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Create Index for Performance

# COMMAND ----------

# DBTITLE 1,Create index on discount_category
create_index_sql = """
CREATE INDEX IF NOT EXISTS idx_sku_discount_category 
ON lakemeter.sku_discount_mapping(discount_category);
"""

try:
    cursor.execute(create_index_sql)
    conn.commit()
    print("✅ Index created on discount_category")
except Exception as e:
    conn.rollback()
    print(f"❌ Error creating index: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Summary

# COMMAND ----------

# DBTITLE 1,Final Summary
summary_query = """
SELECT 
    'Total SKUs Mapped' as metric,
    COUNT(*)::TEXT as count
FROM lakemeter.sku_discount_mapping

UNION ALL

SELECT 
    'DBU Category' as metric,
    COUNT(*)::TEXT as count
FROM lakemeter.sku_discount_mapping
WHERE discount_category = 'dbu'

UNION ALL

SELECT 
    'Storage Category' as metric,
    COUNT(*)::TEXT as count
FROM lakemeter.sku_discount_mapping
WHERE discount_category = 'storage'

UNION ALL

SELECT 
    'Support Category' as metric,
    COUNT(*)::TEXT as count
FROM lakemeter.sku_discount_mapping
WHERE discount_category = 'support'

UNION ALL

SELECT 
    'Network Category (NOT Discounted)' as metric,
    COUNT(*)::TEXT as count
FROM lakemeter.sku_discount_mapping
WHERE discount_category = 'network'

UNION ALL

SELECT 
    'Excluded Category' as metric,
    COUNT(*)::TEXT as count
FROM lakemeter.sku_discount_mapping
WHERE discount_category = 'excluded';
"""

try:
    cursor.execute(summary_query)
    summary = cursor.fetchall()
    
    print("=" * 60)
    print("✅ SKU DISCOUNT MAPPING SETUP COMPLETE")
    print("=" * 60)
    print(f"{'Metric':<40} {'Count':<10}")
    print("-" * 60)
    for metric, count in summary:
        print(f"{metric:<40} {count:<10}")
    print("=" * 60)
except Exception as e:
    print(f"❌ Error generating summary: {e}")

# COMMAND ----------

# Close connection
cursor.close()
conn.close()
print("\n✅ Database connection closed")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Notes
# MAGIC
# MAGIC **Discount Categories:**
# MAGIC - ✅ **dbu**: All compute/workload SKUs - eligible for EA DBU discounts (typically 15-30%)
# MAGIC - ✅ **storage**: Storage/DSU SKUs - rarely discounted (usually 0%), but option available
# MAGIC - ✅ **support**: Enhanced security/compliance - rarely discounted, but option available
# MAGIC - ❌ **network**: Network egress/connectivity - typically NEVER discounted (infrastructure cost)
# MAGIC - ❌ **excluded**: Internal usage - not applicable for customer discounts
# MAGIC
# MAGIC **Next Steps:**
# MAGIC 1. Update API to query this table for discount category lookup
# MAGIC 2. Add `discount_config` parameter to calculation endpoints
# MAGIC 3. Apply discounts based on category + SKU-specific overrides
