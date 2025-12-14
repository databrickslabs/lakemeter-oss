# Databricks notebook source
# MAGIC %md
# MAGIC # Lakebase Connection Configuration
# MAGIC 
# MAGIC **Purpose:** Centralized configuration for Lakebase (PostgreSQL) connections
# MAGIC 
# MAGIC **Usage:** Include this notebook in other notebooks using:
# MAGIC ```python
# MAGIC %run ./00_Lakebase_Config
# MAGIC ```
# MAGIC 
# MAGIC **Note:** This notebook is imported by all test notebooks and setup scripts

# COMMAND ----------

# ============================================================================
# LAKEBASE CONNECTION CONFIGURATION
# ============================================================================
# PostgreSQL connection details for Lakemeter application database

LAKEBASE_HOST = "instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com"
LAKEBASE_PORT = 5432
LAKEBASE_DB = "lakemeter_pricing"
LAKEBASE_DATABASE = "lakemeter_pricing"  # Alias for compatibility
LAKEBASE_USER = "lakemeter_sync_role"
LAKEBASE_PASSWORD = "Lak3m3t3r_Sync_2024!"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_lakebase_connection():
    """
    Returns a psycopg2 connection to Lakebase.
    
    Returns:
        psycopg2.connection: Active database connection
    
    Example:
        conn = get_lakebase_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM lakemeter.estimates")
    """
    import psycopg2
    return psycopg2.connect(
        host=LAKEBASE_HOST,
        port=LAKEBASE_PORT,
        database=LAKEBASE_DB,
        user=LAKEBASE_USER,
        password=LAKEBASE_PASSWORD
    )

def get_connection_string():
    """
    Returns a PostgreSQL connection string.
    
    Returns:
        str: PostgreSQL connection string
    
    Example:
        conn_str = get_connection_string()
        # postgresql://user:pass@host:port/database
    """
    return f"postgresql://{LAKEBASE_USER}:{LAKEBASE_PASSWORD}@{LAKEBASE_HOST}:{LAKEBASE_PORT}/{LAKEBASE_DB}"

# ============================================================================
# VERIFICATION
# ============================================================================

print("✅ Lakebase Configuration Loaded")
print(f"   Host: {LAKEBASE_HOST}")
print(f"   Port: {LAKEBASE_PORT}")
print(f"   Database: {LAKEBASE_DB}")
print(f"   User: {LAKEBASE_USER}")
print(f"   Password: {'*' * len(LAKEBASE_PASSWORD)}")

