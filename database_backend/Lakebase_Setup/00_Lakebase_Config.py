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

# Parameterized config — set via notebook widgets or defaults
try:
    dbutils.widgets.text("lakebase_host", "ep-silent-fire-d1kv74l0.database.us-west-2.cloud.databricks.com", "Lakebase Host")
    dbutils.widgets.text("lakebase_db", "lakemeter_pricing", "Database Name")
    dbutils.widgets.text("lakebase_user", "lakemeter_sync_role", "Database User")
    LAKEBASE_HOST = dbutils.widgets.get("lakebase_host")
    LAKEBASE_DB = dbutils.widgets.get("lakebase_db")
    LAKEBASE_USER = dbutils.widgets.get("lakebase_user")
except Exception:
    # Fallback defaults for non-interactive execution
    LAKEBASE_HOST = "ep-silent-fire-d1kv74l0.database.us-west-2.cloud.databricks.com"
    LAKEBASE_DB = "lakemeter_pricing"
    LAKEBASE_USER = "lakemeter_sync_role"

LAKEBASE_PORT = 5432
LAKEBASE_DATABASE = LAKEBASE_DB  # Alias for compatibility
LAKEBASE_PASSWORD = dbutils.secrets.get(scope="lakemeter-credentials", key="lakebase-password")

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

def execute_query(query):
    """
    Execute a SQL query and return results as a list of tuples.
    
    Args:
        query (str): SQL query to execute
    
    Returns:
        list: List of tuples containing query results
    
    Example:
        results = execute_query("SELECT * FROM lakemeter.estimates LIMIT 5")
        for row in results:
            print(row)
    """
    import psycopg2
    conn = None
    cursor = None
    try:
        conn = get_lakebase_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        
        # If it's a SELECT query, fetch results
        if query.strip().upper().startswith('SELECT'):
            results = cursor.fetchall()
            return results
        else:
            # For INSERT, UPDATE, DELETE, commit and return affected rows
            conn.commit()
            return cursor.rowcount
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ============================================================================
# VERIFICATION
# ============================================================================

print("✅ Lakebase Configuration Loaded")
print(f"   Host: {LAKEBASE_HOST}")
print(f"   Port: {LAKEBASE_PORT}")
print(f"   Database: {LAKEBASE_DB}")
print(f"   User: {LAKEBASE_USER}")
print(f"   Password: {'*' * len(LAKEBASE_PASSWORD)}")

