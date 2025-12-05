-- =============================================================================
-- CREATE LAKEBASE ROLE FOR SALESFORCE SYNC
-- =============================================================================
-- Run this SQL in Lakebase (lakemeter-db) SQL Editor
-- This creates a dedicated role for syncing Salesforce data
-- =============================================================================

-- 1. Create the sync role with password
CREATE ROLE lakemeter_sync_role LOGIN PASSWORD 'Lak3m3t3r_Sync_2024!';

-- 2. Grant connect to database
GRANT CONNECT ON DATABASE databricks_postgres TO lakemeter_sync_role;

-- =============================================================================
-- GRANT ACCESS TO lakemeter_pricing SCHEMA
-- =============================================================================

-- 3. Grant usage on lakemeter_pricing schema
GRANT USAGE ON SCHEMA lakemeter_pricing TO lakemeter_sync_role;

-- 4. Grant CREATE on schema (to create new tables)
GRANT CREATE ON SCHEMA lakemeter_pricing TO lakemeter_sync_role;

-- 5. Grant ALL on all tables in lakemeter_pricing schema (existing + future)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA lakemeter_pricing TO lakemeter_sync_role;

-- 6. Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA lakemeter_pricing 
GRANT ALL PRIVILEGES ON TABLES TO lakemeter_sync_role;

-- 7. Grant sequence privileges (for auto-increment columns)
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA lakemeter_pricing TO lakemeter_sync_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA lakemeter_pricing 
GRANT ALL PRIVILEGES ON SEQUENCES TO lakemeter_sync_role;

-- =============================================================================
-- ALSO GRANT ACCESS TO public SCHEMA (optional)
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

-- Check grants
SELECT grantee, privilege_type, table_schema
FROM information_schema.role_table_grants
WHERE grantee = 'lakemeter_sync_role';

-- =============================================================================
-- CONNECTION DETAILS
-- =============================================================================
-- 
-- Host:     instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com
-- Port:     5432
-- Database: databricks_postgres
-- User:     lakemeter_sync_role
-- Password: Lak3m3t3r_Sync_2024!
-- SSL:      require
--
-- JDBC URL:
-- jdbc:postgresql://instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com:5432/databricks_postgres?sslmode=require
--
-- =============================================================================

