-- =============================================================================
-- CREATE LAKEBASE ROLE FOR DATA SYNC
-- =============================================================================
-- Run this SQL in Lakebase SQL Editor
-- This creates a dedicated role for syncing data and running tests
-- =============================================================================

-- 1. Create the sync role with password
CREATE ROLE lakemeter_sync_role LOGIN PASSWORD 'YOUR_SECURE_PASSWORD_HERE';

-- 2. Grant connect to database
GRANT CONNECT ON DATABASE lakemeter_pricing TO lakemeter_sync_role;

-- =============================================================================
-- GRANT ACCESS TO lakemeter SCHEMA
-- =============================================================================

-- 3. Grant usage on lakemeter schema
GRANT USAGE ON SCHEMA lakemeter TO lakemeter_sync_role;

-- 4. Grant CREATE on schema (to create new tables)
GRANT CREATE ON SCHEMA lakemeter TO lakemeter_sync_role;

-- 5. Grant ALL on all tables in lakemeter schema (existing + future)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA lakemeter TO lakemeter_sync_role;

-- 6. Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA lakemeter 
GRANT ALL PRIVILEGES ON TABLES TO lakemeter_sync_role;

-- 7. Grant sequence privileges (for auto-increment columns)
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA lakemeter TO lakemeter_sync_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA lakemeter 
GRANT ALL PRIVILEGES ON SEQUENCES TO lakemeter_sync_role;

-- =============================================================================
-- ALSO GRANT ACCESS TO public SCHEMA (optional, for temp tables)
-- =============================================================================

GRANT USAGE ON SCHEMA public TO lakemeter_sync_role;
GRANT CREATE ON SCHEMA public TO lakemeter_sync_role;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO lakemeter_sync_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT ALL PRIVILEGES ON TABLES TO lakemeter_sync_role;

-- =============================================================================
-- VERIFY ROLE
-- =============================================================================

-- Check role exists
SELECT rolname, rolcanlogin 
FROM pg_roles 
WHERE rolname = 'lakemeter_sync_role';

-- Check grants on lakemeter schema
SELECT grantee, privilege_type, table_schema, table_name
FROM information_schema.role_table_grants
WHERE grantee = 'lakemeter_sync_role'
  AND table_schema = 'lakemeter'
ORDER BY table_name;

-- Check schema privileges
SELECT nspname as schema_name, 
       has_schema_privilege('lakemeter_sync_role', nspname, 'USAGE') as has_usage,
       has_schema_privilege('lakemeter_sync_role', nspname, 'CREATE') as has_create
FROM pg_namespace 
WHERE nspname IN ('lakemeter', 'public');

-- =============================================================================
-- CONNECTION DETAILS
-- =============================================================================
-- 
-- Host:     instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com
-- Port:     5432
-- Database: lakemeter_pricing
-- Schema:   lakemeter
-- User:     lakemeter_sync_role
-- Password: YOUR_SECURE_PASSWORD_HERE
-- SSL:      require
--
-- JDBC URL:
-- jdbc:postgresql://instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com:5432/lakemeter_pricing?currentSchema=lakemeter&sslmode=require
--
-- Python psycopg2 Connection:
-- conn = psycopg2.connect(
--     host="instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com",
--     port=5432,
--     database="lakemeter_pricing",
--     user="lakemeter_sync_role",
--     password="YOUR_SECURE_PASSWORD_HERE",
--     options="-c search_path=lakemeter"
-- )
--
-- =============================================================================

