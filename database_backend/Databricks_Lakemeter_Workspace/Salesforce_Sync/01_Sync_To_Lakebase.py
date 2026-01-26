# Databricks notebook source
# MAGIC %md
# MAGIC # Sync Salesforce Tables to Lakebase
# MAGIC 
# MAGIC **Run this notebook in the LOGFOOD workspace** (`adb-2548836972759138`)
# MAGIC 
# MAGIC This notebook:
# MAGIC 1. Reads Salesforce tables from Unity Catalog
# MAGIC 2. Writes directly to Lakebase (lakemeter-db)
# MAGIC 
# MAGIC **Source Tables:**
# MAGIC - `main.metric_store.dim_salesforce_account`
# MAGIC - `main.metric_store.fct_salesforce_use_case__core`
# MAGIC - `main.sfdc_bronze.hourly_opportunity`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install PostgreSQL Driver

# COMMAND ----------

# MAGIC %pip install psycopg2-binary

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

# Lakebase Connection Details (using dedicated sync role)
LAKEBASE_CONFIG = {
    "host": "instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com",
    "port": 5432,
    "database": "lakemeter_pricing",
    "user": "lakemeter_sync_role",
    "password": "Lak3m3t3r_Sync_2024!",
    "sslmode": "require"
}

# Tables to sync (writing to lakemeter schema)
TABLES_TO_SYNC = [
    {
        "source": "main.metric_store.dim_salesforce_account",
        "target": "sync_dim_salesforce_account",
        "schema": "lakemeter"
    },
    {
        "source": "main.metric_store.fct_salesforce_use_case__core",
        "target": "sync_fct_salesforce_use_case",
        "schema": "lakemeter"
    },
    {
        "source": "main.sfdc_bronze.hourly_opportunity",
        "target": "sync_hourly_opportunity",
        "schema": "lakemeter"
    }
]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Lakebase Credentials
# MAGIC 
# MAGIC Using dedicated `lakemeter_sync_role` with password authentication.
# MAGIC 
# MAGIC **To create this role, run `00_Create_Lakebase_Role.sql` in Lakebase SQL Editor first!**

# COMMAND ----------

print(f"✅ Using role: {LAKEBASE_CONFIG['user']}")
print(f"   Host: {LAKEBASE_CONFIG['host']}")
print(f"   Database: {LAKEBASE_CONFIG['database']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Connect to Lakebase

# COMMAND ----------

import psycopg2
from psycopg2 import sql as psql

def get_lakebase_connection():
    """Create connection to Lakebase"""
    return psycopg2.connect(
        host=LAKEBASE_CONFIG["host"],
        port=LAKEBASE_CONFIG["port"],
        database=LAKEBASE_CONFIG["database"],
        user=LAKEBASE_CONFIG["user"],
        password=LAKEBASE_CONFIG["password"],
        sslmode=LAKEBASE_CONFIG["sslmode"]
    )

# Test connection
try:
    conn = get_lakebase_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT version()")
    version = cursor.fetchone()[0]
    print(f"✅ Connected to Lakebase!")
    print(f"   PostgreSQL: {version[:50]}...")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Sync Functions

# COMMAND ----------

def get_spark_to_pg_type(spark_type):
    """Map Spark types to PostgreSQL types"""
    type_map = {
        "string": "TEXT",
        "long": "BIGINT",
        "integer": "INTEGER",
        "int": "INTEGER",
        "double": "DOUBLE PRECISION",
        "float": "REAL",
        "boolean": "BOOLEAN",
        "timestamp": "TIMESTAMP",
        "date": "DATE",
        "decimal": "DECIMAL",
        "binary": "BYTEA"
    }
    
    spark_type_lower = spark_type.lower()
    
    # Handle decimal with precision
    if spark_type_lower.startswith("decimal"):
        return spark_type.upper().replace("DECIMAL", "DECIMAL")
    
    return type_map.get(spark_type_lower, "TEXT")

def create_table_from_spark_schema(conn, table_name, schema_name, spark_df):
    """Create PostgreSQL table from Spark DataFrame schema"""
    
    columns = []
    for field in spark_df.schema.fields:
        pg_type = get_spark_to_pg_type(field.dataType.simpleString())
        null_constraint = "" if field.nullable else " NOT NULL"
        columns.append(f'"{field.name}" {pg_type}{null_constraint}')
    
    create_sql = f"""
    DROP TABLE IF EXISTS {schema_name}.{table_name} CASCADE;
    CREATE TABLE {schema_name}.{table_name} (
        {', '.join(columns)}
    );
    """
    
    cursor = conn.cursor()
    cursor.execute(create_sql)
    conn.commit()
    cursor.close()
    
    print(f"   ✅ Created table: {schema_name}.{table_name}")

def insert_data_batch(conn, table_name, schema_name, df, batch_size=1000):
    """Insert data in batches"""
    
    columns = df.columns
    placeholders = ", ".join(["%s"] * len(columns))
    column_names = ", ".join([f'"{c}"' for c in columns])
    
    insert_sql = f"""
    INSERT INTO {schema_name}.{table_name} ({column_names})
    VALUES ({placeholders})
    """
    
    cursor = conn.cursor()
    
    # Convert to list of tuples
    rows = df.collect()
    total = len(rows)
    
    for i in range(0, total, batch_size):
        batch = rows[i:i+batch_size]
        data = [tuple(row.asDict().values()) for row in batch]
        cursor.executemany(insert_sql, data)
        conn.commit()
        print(f"   Inserted {min(i+batch_size, total)}/{total} rows...")
    
    cursor.close()
    print(f"   ✅ Inserted {total} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Sync Tables

# COMMAND ----------

def sync_table(table_config):
    """Sync a single table from Unity Catalog to Lakebase"""
    
    source = table_config["source"]
    target = table_config["target"]
    schema = table_config["schema"]
    
    print(f"\n📥 Syncing: {source} → {schema}.{target}")
    
    # Read from Unity Catalog
    print(f"   Reading from Unity Catalog...")
    df = spark.table(source)
    row_count = df.count()
    print(f"   Found {row_count:,} rows")
    
    # Connect to Lakebase
    conn = get_lakebase_connection()
    
    try:
        # Create table
        create_table_from_spark_schema(conn, target, schema, df)
        
        # Insert data
        if row_count > 0:
            insert_data_batch(conn, target, schema, df)
        
        print(f"✅ Synced: {source} → {schema}.{target} ({row_count:,} rows)")
        return {"table": target, "status": "✅ Success", "rows": row_count}
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"table": target, "status": f"❌ {str(e)[:50]}", "rows": 0}
        
    finally:
        conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run Sync

# COMMAND ----------

results = []
for table_config in TABLES_TO_SYNC:
    result = sync_table(table_config)
    results.append(result)

# Display results
display(spark.createDataFrame(results))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify in Lakebase

# COMMAND ----------

conn = get_lakebase_connection()
cursor = conn.cursor()

print("📋 Tables in Lakebase:")
for table_config in TABLES_TO_SYNC:
    target = table_config["target"]
    schema = table_config["schema"]
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {schema}.{target}")
        count = cursor.fetchone()[0]
        print(f"   ✅ {schema}.{target}: {count:,} rows")
    except Exception as e:
        print(f"   ❌ {schema}.{target}: {e}")

cursor.close()
conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Done!
# MAGIC 
# MAGIC Tables synced to Lakebase (`lakemeter` schema in `lakemeter_pricing` database):
# MAGIC - `lakemeter.sync_dim_salesforce_account`
# MAGIC - `lakemeter.sync_fct_salesforce_use_case`
# MAGIC - `lakemeter.sync_hourly_opportunity`
# MAGIC 
# MAGIC You can now query these from the Lakemeter workspace!

