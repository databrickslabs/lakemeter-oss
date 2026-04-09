-- =============================================================================
-- GRANT SUPERUSER TO lakemeter_sync_role
-- =============================================================================
-- ⚠️  WARNING: This gives lakemeter_sync_role unlimited privileges!
-- Run this with an ADMIN user (not lakemeter_sync_role)
-- =============================================================================

-- Check current role attributes
SELECT 
    rolname,
    rolsuper as is_superuser,
    rolcreaterole as can_create_roles,
    rolcreatedb as can_create_databases,
    rolcanlogin as can_login
FROM pg_roles
WHERE rolname = 'lakemeter_sync_role';

-- Grant superuser privilege
ALTER ROLE lakemeter_sync_role WITH SUPERUSER;

-- Verify
SELECT 
    rolname,
    rolsuper as is_superuser,
    CASE WHEN rolsuper THEN '✅ SUPERUSER' ELSE '❌ NOT SUPERUSER' END as status
FROM pg_roles
WHERE rolname = 'lakemeter_sync_role';

-- =============================================================================
-- EXPECTED OUTPUT:
-- rolname              | is_superuser | status
-- ---------------------+--------------+----------------
-- lakemeter_sync_role  | t            | ✅ SUPERUSER
-- =============================================================================

-- =============================================================================
-- ⚠️  SECURITY CONSIDERATIONS:
-- =============================================================================
-- Superuser can:
--   ✅ Drop any table/view/database
--   ✅ Create/modify any user
--   ✅ Bypass all permission checks
--   ✅ Access any data
--   ✅ Modify system catalogs
--
-- Recommendation:
--   - Use this ONLY for development/testing
--   - For production, use Option 1 (Transfer Ownership) instead
--   - Or use Option 3 (create objects with correct owner from start)
-- =============================================================================

-- To REVOKE superuser later (if needed):
-- ALTER ROLE lakemeter_sync_role WITH NOSUPERUSER;

