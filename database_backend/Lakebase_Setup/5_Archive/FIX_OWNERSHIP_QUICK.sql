-- =============================================================================
-- QUICK FIX: Drop Functions (Ownership Issue)
-- =============================================================================
-- Run this in Lakebase SQL Editor if you get "must be owner" errors
-- This will drop the functions that are blocking the notebook
-- =============================================================================

-- Step 1: Check who owns the functions
SELECT 
    '🔍 Current ownership:' as info;

SELECT 
    p.proname as function_name,
    pg_get_userbyid(p.proowner) as owner,
    current_user as you_are_logged_in_as,
    CASE 
        WHEN pg_get_userbyid(p.proowner) = current_user THEN '✅ YOU OWN THIS'
        ELSE '❌ OWNED BY: ' || pg_get_userbyid(p.proowner)
    END as ownership_status
FROM pg_proc p 
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'lakemeter' 
AND p.proname LIKE 'sync_%'
ORDER BY p.proname;

-- =============================================================================
-- Step 2: If you see "✅ YOU OWN THIS", run these DROP commands:
-- =============================================================================

DROP FUNCTION IF EXISTS lakemeter.sync_line_item_cloud() CASCADE;
DROP FUNCTION IF EXISTS lakemeter.sync_estimate_cloud_to_line_items() CASCADE;

-- Verify they're gone
SELECT 
    '✅ Functions dropped!' as status,
    COUNT(*) as remaining_functions
FROM pg_proc p 
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'lakemeter' 
AND p.proname LIKE 'sync_%';

-- Expected: remaining_functions = 0

-- =============================================================================
-- Step 3: Go back to Databricks and re-run 01_Create_Tables.py
-- =============================================================================

-- =============================================================================
-- IF YOU SEE "❌ OWNED BY: [someone_else]":
-- =============================================================================
-- You need to either:
--   Option A: Log out and log back in as that user
--   Option B: Ask that user to run this script
--   Option C: Use a superuser account to drop them
--
-- To check who has superuser privileges:
-- SELECT rolname, rolsuper FROM pg_roles WHERE rolsuper = true;
-- =============================================================================

