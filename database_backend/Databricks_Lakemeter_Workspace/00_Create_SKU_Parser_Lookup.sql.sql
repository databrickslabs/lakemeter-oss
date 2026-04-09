-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Create SKU Parser Lookup Table
-- MAGIC
-- MAGIC **Workspace:** Logfood (`adb-2548836972759138.18.azuredatabricks.net`)
-- MAGIC
-- MAGIC This notebook creates a lookup table for parsing SKU names into:
-- MAGIC - `tier` (PREMIUM, ENTERPRISE, STANDARD, MCT, or NULL)
-- MAGIC - `product_type` (JOBS_COMPUTE, DLT_CORE, etc.)
-- MAGIC - `sku_region` (US_EAST_N_VIRGINIA, etc.)
-- MAGIC - `region_code` (us-east-1, eastus, us-central1)
-- MAGIC
-- MAGIC **Source:** `main.fin_live_gold.paid_usage_metering.sku`
-- MAGIC **Target:** `main.metric_store.sku_parser_lookup`

-- COMMAND ----------

-- MAGIC %python
-- MAGIC # Configuration
-- MAGIC SOURCE_TABLE = "main.fin_live_gold.paid_usage_metering"
-- MAGIC TARGET_TABLE = "users.steven_tan.sku_parser_lookup"
-- MAGIC
-- MAGIC print(f"✅ Source: {SOURCE_TABLE}")
-- MAGIC print(f"✅ Target: {TARGET_TABLE}")

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 1: Check Table Schema & Get All Unique SKUs

-- COMMAND ----------

-- MAGIC %python
-- MAGIC # First, check the table schema to find the correct SKU column name
-- MAGIC print("📋 Checking table schema...")
-- MAGIC df_schema = spark.sql(f"DESCRIBE {SOURCE_TABLE}")
-- MAGIC display(df_schema)

-- COMMAND ----------

-- MAGIC %python
-- MAGIC # Get all unique SKUs from the usage table
-- MAGIC # Note: Naming as sku_name for consistency with Lakebase tables
-- MAGIC df_skus = spark.sql(f"""
-- MAGIC     SELECT DISTINCT 
-- MAGIC         sku as sku_name,
-- MAGIC         cloud
-- MAGIC     FROM {SOURCE_TABLE}
-- MAGIC     WHERE sku IS NOT NULL
-- MAGIC     ORDER BY cloud, sku_name
-- MAGIC """)
-- MAGIC
-- MAGIC print(f"✅ Found {df_skus.count()} unique SKUs")
-- MAGIC display(df_skus.limit(20))

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 2: Parse SKUs Using Python Logic

-- COMMAND ----------

-- MAGIC %python
-- MAGIC import re
-- MAGIC from pyspark.sql.functions import udf
-- MAGIC from pyspark.sql.types import StructType, StructField, StringType
-- MAGIC
-- MAGIC # Known regions (order matters - longest first for matching)
-- MAGIC KNOWN_REGIONS = [
-- MAGIC     # AWS regions
-- MAGIC     "US_EAST_N_VIRGINIA", "US_EAST_OHIO", "US_WEST_OREGON", "US_WEST_CALIFORNIA",
-- MAGIC     "US_SOUTH_CAROLINA", "US_IOWA", "US_NEVADA", "US_VIRGINIA", "US_OREGON",
-- MAGIC     "AP_MUMBAI", "AP_SINGAPORE", "AP_SYDNEY", "AP_TOKYO", "AP_SEOUL", "AP_JAKARTA",
-- MAGIC     "EUROPE_IRELAND", "EUROPE_FRANKFURT", "EUROPE_LONDON", "EUROPE_FRANCE", 
-- MAGIC     "EUROPE_BELGIUM", "EUROPE_ENGLAND", "EUROPE_STOCKHOLM",
-- MAGIC     "CANADA", "CANADA_QUEBEC", "SA_BRAZIL", "ME_DAMMAM", "INDIA_MUMBAI",
-- MAGIC     
-- MAGIC     # Azure regions
-- MAGIC     "US_EAST", "US_EAST_2", "US_WEST", "US_WEST_2", "US_WEST_3", 
-- MAGIC     "US_CENTRAL", "US_NORTH_CENTRAL", "US_SOUTH_CENTRAL", "US_WEST_CENTRAL",
-- MAGIC     "EU_WEST", "EU_NORTH", "UK_SOUTH", "UK_WEST",
-- MAGIC     "FRANCE_CENTRAL", "GERMANY_WEST_CENTRAL", "SWITZERLAND_NORTH", "SWITZERLAND_WEST",
-- MAGIC     "SWEDEN_CENTRAL", "NORWAY_EAST", "QATAR_CENTRAL", "UAE_NORTH",
-- MAGIC     "ASIA_EAST", "ASIA_SOUTHEAST", "ASIA_SINGAPORE", "ASIA_TOKYO",
-- MAGIC     "AUSTRALIA_EAST", "AUSTRALIA_SOUTHEAST", "AUSTRALIA_CENTRAL", "AUSTRALIA_CENTRAL_2",
-- MAGIC     "AUSTRALIA_SYDNEY",
-- MAGIC     "JAPAN_EAST", "JAPAN_WEST", "KOREA_CENTRAL",
-- MAGIC     "INDIA_CENTRAL", "INDIA_SOUTH", "INDIA_WEST",
-- MAGIC     "BRAZIL_SOUTH", "SOUTH_AFRICA_NORTH", "MEXICO_CENTRAL",
-- MAGIC     "CANADA_CENTRAL", "CANADA_EAST",
-- MAGIC     
-- MAGIC     # GCP regions  
-- MAGIC     "ASIA_SINGAPORE", "ASIA_TOKYO", "AUSTRALIA_SYDNEY", 
-- MAGIC     "EUROPE_BELGIUM", "EUROPE_ENGLAND",
-- MAGIC     "US_IOWA", "US_NEVADA", "US_SOUTH_CAROLINA", "US_VIRGINIA",
-- MAGIC ]
-- MAGIC
-- MAGIC # Tiers
-- MAGIC TIERS = ["ENTERPRISE", "PREMIUM", "STANDARD", "MCT"]
-- MAGIC
-- MAGIC def parse_sku_name(sku_name):
-- MAGIC     """Parse SKU name into tier, product_type, and region."""
-- MAGIC     
-- MAGIC     if not sku_name:
-- MAGIC         return (None, None, None)
-- MAGIC     
-- MAGIC     # Extract tier
-- MAGIC     tier = None
-- MAGIC     remaining = sku_name
-- MAGIC     for t in TIERS:
-- MAGIC         if sku_name.startswith(t + "_"):
-- MAGIC             tier = t
-- MAGIC             remaining = sku_name[len(t) + 1:]
-- MAGIC             break
-- MAGIC     
-- MAGIC     # Extract region (check from end)
-- MAGIC     region = None
-- MAGIC     for r in sorted(KNOWN_REGIONS, key=len, reverse=True):  # Longest first
-- MAGIC         if remaining.endswith("_" + r):
-- MAGIC             region = r
-- MAGIC             remaining = remaining[:-(len(r) + 1)]
-- MAGIC             break
-- MAGIC     
-- MAGIC     # Remaining is the product type
-- MAGIC     product_type = remaining if remaining else None
-- MAGIC     
-- MAGIC     return (tier, product_type, region)
-- MAGIC
-- MAGIC # Create UDF
-- MAGIC schema = StructType([
-- MAGIC     StructField("tier", StringType(), True),
-- MAGIC     StructField("product_type", StringType(), True),
-- MAGIC     StructField("sku_region", StringType(), True)
-- MAGIC ])
-- MAGIC
-- MAGIC parse_sku_udf = udf(parse_sku_name, schema)
-- MAGIC
-- MAGIC print("✅ Defined SKU parsing UDF")

-- COMMAND ----------

-- MAGIC %python
-- MAGIC # Apply parsing to all SKUs
-- MAGIC from pyspark.sql.functions import col
-- MAGIC
-- MAGIC df_parsed = df_skus.withColumn("parsed", parse_sku_udf(col("sku_name")))
-- MAGIC df_parsed = df_parsed.select(
-- MAGIC     col("sku_name"),
-- MAGIC     col("cloud"),
-- MAGIC     col("parsed.tier").alias("tier"),
-- MAGIC     col("parsed.product_type").alias("product_type"),
-- MAGIC     col("parsed.sku_region").alias("sku_region")
-- MAGIC )
-- MAGIC
-- MAGIC print(f"✅ Parsed {df_parsed.count()} SKUs")
-- MAGIC display(df_parsed.limit(30))

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 3: Add Region Code Mapping

-- COMMAND ----------

-- MAGIC %python
-- MAGIC # Region mappings by cloud
-- MAGIC AWS_REGION_MAPPING = {
-- MAGIC     "US_EAST_N_VIRGINIA": "us-east-1",
-- MAGIC     "US_EAST_OHIO": "us-east-2", 
-- MAGIC     "US_WEST_OREGON": "us-west-2",
-- MAGIC     "US_WEST_CALIFORNIA": "us-west-1",
-- MAGIC     "AP_MUMBAI": "ap-south-1",
-- MAGIC     "AP_SINGAPORE": "ap-southeast-1",
-- MAGIC     "AP_SYDNEY": "ap-southeast-2",
-- MAGIC     "AP_TOKYO": "ap-northeast-1",
-- MAGIC     "AP_SEOUL": "ap-northeast-2",
-- MAGIC     "AP_JAKARTA": "ap-southeast-3",
-- MAGIC     "EUROPE_IRELAND": "eu-west-1",
-- MAGIC     "EUROPE_FRANKFURT": "eu-central-1",
-- MAGIC     "EUROPE_LONDON": "eu-west-2",
-- MAGIC     "EUROPE_FRANCE": "eu-west-3",
-- MAGIC     "EUROPE_STOCKHOLM": "eu-north-1",
-- MAGIC     "CANADA": "ca-central-1",
-- MAGIC     "SA_BRAZIL": "sa-east-1",
-- MAGIC }
-- MAGIC
-- MAGIC AZURE_REGION_MAPPING = {
-- MAGIC     "US_EAST": "eastus",
-- MAGIC     "US_EAST_2": "eastus2",
-- MAGIC     "US_WEST": "westus",
-- MAGIC     "US_WEST_2": "westus2",
-- MAGIC     "US_WEST_3": "westus3",
-- MAGIC     "US_CENTRAL": "centralus",
-- MAGIC     "US_NORTH_CENTRAL": "northcentralus",
-- MAGIC     "US_SOUTH_CENTRAL": "southcentralus",
-- MAGIC     "US_WEST_CENTRAL": "westcentralus",
-- MAGIC     "EU_WEST": "westeurope",
-- MAGIC     "EU_NORTH": "northeurope",
-- MAGIC     "UK_SOUTH": "uksouth",
-- MAGIC     "UK_WEST": "ukwest",
-- MAGIC     "FRANCE_CENTRAL": "francecentral",
-- MAGIC     "GERMANY_WEST_CENTRAL": "germanywestcentral",
-- MAGIC     "SWITZERLAND_NORTH": "switzerlandnorth",
-- MAGIC     "SWITZERLAND_WEST": "switzerlandwest",
-- MAGIC     "SWEDEN_CENTRAL": "swedencentral",
-- MAGIC     "NORWAY_EAST": "norwayeast",
-- MAGIC     "QATAR_CENTRAL": "qatarcentral",
-- MAGIC     "UAE_NORTH": "uaenorth",
-- MAGIC     "ASIA_EAST": "eastasia",
-- MAGIC     "ASIA_SOUTHEAST": "southeastasia",
-- MAGIC     "AUSTRALIA_EAST": "australiaeast",
-- MAGIC     "AUSTRALIA_SOUTHEAST": "australiasoutheast",
-- MAGIC     "AUSTRALIA_CENTRAL": "australiacentral",
-- MAGIC     "AUSTRALIA_CENTRAL_2": "australiacentral2",
-- MAGIC     "JAPAN_EAST": "japaneast",
-- MAGIC     "JAPAN_WEST": "japanwest",
-- MAGIC     "KOREA_CENTRAL": "koreacentral",
-- MAGIC     "INDIA_CENTRAL": "centralindia",
-- MAGIC     "INDIA_SOUTH": "southindia",
-- MAGIC     "INDIA_WEST": "westindia",
-- MAGIC     "BRAZIL_SOUTH": "brazilsouth",
-- MAGIC     "SOUTH_AFRICA_NORTH": "southafricanorth",
-- MAGIC     "MEXICO_CENTRAL": "mexicocentral",
-- MAGIC     "CANADA_CENTRAL": "canadacentral",
-- MAGIC     "CANADA_EAST": "canadaeast",
-- MAGIC }
-- MAGIC
-- MAGIC GCP_REGION_MAPPING = {
-- MAGIC     "US_IOWA": "us-central1",
-- MAGIC     "US_NEVADA": "us-west4",
-- MAGIC     "US_SOUTH_CAROLINA": "us-east1",
-- MAGIC     "US_OREGON": "us-west1",
-- MAGIC     "US_VIRGINIA": "us-east4",
-- MAGIC     "US_WEST_CALIFORNIA": "us-west2",
-- MAGIC     "EUROPE_BELGIUM": "europe-west1",
-- MAGIC     "EUROPE_ENGLAND": "europe-west2",
-- MAGIC     "EUROPE_FRANKFURT": "europe-west3",
-- MAGIC     "EUROPE_FRANCE": "europe-west9",
-- MAGIC     "CANADA_QUEBEC": "northamerica-northeast1",
-- MAGIC     "ASIA_SINGAPORE": "asia-southeast1",
-- MAGIC     "ASIA_TOKYO": "asia-northeast1",
-- MAGIC     "AUSTRALIA_SYDNEY": "australia-southeast1",
-- MAGIC     "INDIA_MUMBAI": "asia-south1",
-- MAGIC     "SA_BRAZIL": "southamerica-east1",
-- MAGIC     "ME_DAMMAM": "me-central2",
-- MAGIC }
-- MAGIC
-- MAGIC def get_region_code(cloud, sku_region):
-- MAGIC     """Map sku_region to region_code based on cloud."""
-- MAGIC     if not sku_region or not cloud:
-- MAGIC         return None
-- MAGIC     
-- MAGIC     cloud_upper = cloud.upper()
-- MAGIC     if cloud_upper == "AWS":
-- MAGIC         return AWS_REGION_MAPPING.get(sku_region)
-- MAGIC     elif cloud_upper == "AZURE":
-- MAGIC         return AZURE_REGION_MAPPING.get(sku_region)
-- MAGIC     elif cloud_upper == "GCP":
-- MAGIC         return GCP_REGION_MAPPING.get(sku_region)
-- MAGIC     else:
-- MAGIC         return None
-- MAGIC
-- MAGIC # Create UDF for region mapping
-- MAGIC region_code_udf = udf(get_region_code, StringType())
-- MAGIC
-- MAGIC print("✅ Defined region code mapping UDF")

-- COMMAND ----------

-- MAGIC %python
-- MAGIC # Add region column (cloud region code)
-- MAGIC from pyspark.sql.functions import col
-- MAGIC
-- MAGIC df_with_region = df_parsed.withColumn(
-- MAGIC     "region",
-- MAGIC     region_code_udf(col("cloud"), col("sku_region"))
-- MAGIC )
-- MAGIC
-- MAGIC print(f"✅ Added region mapping")
-- MAGIC display(df_with_region.limit(30))

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 4: Validation & Statistics (OPTIONAL - Skip for large tables)

-- COMMAND ----------

-- MAGIC %python
-- MAGIC # COMMENTED OUT: Expensive operations for large tables
-- MAGIC # Uncomment if you want to see statistics (will take time)
-- MAGIC
-- MAGIC # total = df_with_region.count()
-- MAGIC # with_tier = df_with_region.filter(col("tier").isNotNull()).count()
-- MAGIC # with_sku_region = df_with_region.filter(col("sku_region").isNotNull()).count()
-- MAGIC # with_region = df_with_region.filter(col("region").isNotNull()).count()
-- MAGIC
-- MAGIC # print(f"📊 SKU Parsing Statistics:")
-- MAGIC # print(f"   Total SKUs: {total}")
-- MAGIC # print(f"   With Tier: {with_tier} ({with_tier/total*100:.1f}%)")
-- MAGIC # print(f"   With SKU Region: {with_sku_region} ({with_sku_region/total*100:.1f}%)")
-- MAGIC # print(f"   With Region: {with_region} ({with_region/total*100:.1f}%)")
-- MAGIC
-- MAGIC # print(f"\n📊 By Tier:")
-- MAGIC # df_with_region.groupBy("tier").count().orderBy("tier").show()
-- MAGIC
-- MAGIC # print(f"\n📊 Sample SKUs without region (if any):")
-- MAGIC # df_with_region.filter(
-- MAGIC #     col("sku_region").isNotNull() & col("region").isNull()
-- MAGIC # ).select("sku_name", "cloud", "sku_region").show(20, False)
-- MAGIC
-- MAGIC print("⏭️  Skipped validation (large table optimization)")
-- MAGIC print("✅ Proceeding to save table...")

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 5: Save to Table

-- COMMAND ----------

-- MAGIC %python
-- MAGIC from pyspark.sql.functions import current_timestamp
-- MAGIC
-- MAGIC # Add metadata
-- MAGIC df_final = df_with_region.withColumn("updated_at", current_timestamp())
-- MAGIC
-- MAGIC # Save to table
-- MAGIC df_final.write \
-- MAGIC     .mode("overwrite") \
-- MAGIC     .option("overwriteSchema", "true") \
-- MAGIC     .saveAsTable(TARGET_TABLE)
-- MAGIC
-- MAGIC print(f"✅ Saved {df_final.count()} SKU mappings to {TARGET_TABLE}")

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 6: Verify Table

-- COMMAND ----------

SELECT * FROM users.steven_tan.sku_parser_lookup
ORDER BY cloud, sku_name
LIMIT 50;

-- COMMAND ----------

-- Show summary by cloud and tier
SELECT 
  cloud,
  tier,
  COUNT(*) as sku_count,
  COUNT(DISTINCT product_type) as unique_products
FROM users.steven_tan.sku_parser_lookup
GROUP BY cloud, tier
ORDER BY cloud, tier;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Done!
-- MAGIC
-- MAGIC Table created: `users.steven_tan.sku_parser_lookup`
-- MAGIC
-- MAGIC **Columns:**
-- MAGIC - `sku_name` - Original SKU from usage data (for consistency with Lakebase)
-- MAGIC - `cloud` - AWS, AZURE, GCP
-- MAGIC - `tier` - PREMIUM, ENTERPRISE, STANDARD, MCT, or NULL
-- MAGIC - `product_type` - Parsed product type (SKU after removing tier and region)
-- MAGIC - `sku_region` - SKU region name (US_EAST_N_VIRGINIA, AP_MUMBAI, etc.)
-- MAGIC - `region` - Cloud region code (us-east-1, eastus, asia-south1, etc.)
-- MAGIC - `updated_at` - Timestamp
-- MAGIC
-- MAGIC **Usage in LDP:**
-- MAGIC ```sql
-- MAGIC SELECT 
-- MAGIC   p.*,
-- MAGIC   s.tier,
-- MAGIC   s.product_type,
-- MAGIC   s.region
-- MAGIC FROM paid_usage_metering p
-- MAGIC LEFT JOIN users.steven_tan.sku_parser_lookup s
-- MAGIC   ON p.sku = s.sku_name AND p.cloud = s.cloud
-- MAGIC ```

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Done!
-- MAGIC
-- MAGIC Table created: `main.metric_store.sku_parser_lookup`
-- MAGIC
-- MAGIC **Columns:**
-- MAGIC - `raw_sku` - Original SKU from usage data
-- MAGIC - `cloud` - AWS, AZURE, GCP
-- MAGIC - `tier` - PREMIUM, ENTERPRISE, STANDARD, MCT, or NULL
-- MAGIC - `product_type` - Parsed product type
-- MAGIC - `sku_region` - SKU region name (US_EAST_N_VIRGINIA, etc.)
-- MAGIC - `region_code` - Cloud region code (us-east-1, eastus, etc.)
-- MAGIC - `updated_at` - Timestamp
-- MAGIC
-- MAGIC **Usage in LDP:**
-- MAGIC ```sql
-- MAGIC SELECT 
-- MAGIC   p.*,
-- MAGIC   s.tier,
-- MAGIC   s.product_type,
-- MAGIC   s.region_code
-- MAGIC FROM paid_usage_metering p
-- MAGIC LEFT JOIN sku_parser_lookup s
-- MAGIC   ON p.sku = s.raw_sku AND p.cloud = s.cloud
-- MAGIC ```