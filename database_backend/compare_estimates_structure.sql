-- ============================================================================
-- Compare structure of estimates and estimates_backup_20260119
-- ============================================================================

-- Method 1: Compare column names, types, and order
WITH estimates_cols AS (
    SELECT 
        column_name,
        data_type,
        character_maximum_length,
        is_nullable,
        column_default,
        ordinal_position
    FROM information_schema.columns
    WHERE table_schema = 'lakemeter' 
      AND table_name = 'estimates'
    ORDER BY ordinal_position
),
backup_cols AS (
    SELECT 
        column_name,
        data_type,
        character_maximum_length,
        is_nullable,
        column_default,
        ordinal_position
    FROM information_schema.columns
    WHERE table_schema = 'lakemeter' 
      AND table_name = 'estimates_backup_20260119'
    ORDER BY ordinal_position
)
SELECT 
    COALESCE(e.column_name, b.column_name) as column_name,
    e.ordinal_position as estimates_position,
    b.ordinal_position as backup_position,
    e.data_type as estimates_type,
    b.data_type as backup_type,
    e.is_nullable as estimates_nullable,
    b.is_nullable as backup_nullable,
    CASE 
        WHEN e.column_name IS NULL THEN '❌ Missing in estimates'
        WHEN b.column_name IS NULL THEN '❌ Missing in backup'
        WHEN e.data_type <> b.data_type THEN '⚠️ Type mismatch'
        WHEN e.is_nullable <> b.is_nullable THEN '⚠️ Nullable mismatch'
        ELSE '✅ Match'
    END as status
FROM estimates_cols e
FULL OUTER JOIN backup_cols b ON e.column_name = b.column_name
ORDER BY COALESCE(e.ordinal_position, b.ordinal_position);

-- ============================================================================
-- Method 2: Quick column count comparison
-- ============================================================================

SELECT 
    'estimates' as table_name,
    COUNT(*) as column_count
FROM information_schema.columns
WHERE table_schema = 'lakemeter' AND table_name = 'estimates'

UNION ALL

SELECT 
    'estimates_backup_20260119' as table_name,
    COUNT(*) as column_count
FROM information_schema.columns
WHERE table_schema = 'lakemeter' AND table_name = 'estimates_backup_20260119';

-- ============================================================================
-- Method 3: List all columns side by side
-- ============================================================================

SELECT 
    e.ordinal_position,
    e.column_name as estimates_column,
    e.data_type as estimates_type,
    b.column_name as backup_column,
    b.data_type as backup_type
FROM (
    SELECT column_name, data_type, ordinal_position
    FROM information_schema.columns
    WHERE table_schema = 'lakemeter' AND table_name = 'estimates'
) e
FULL OUTER JOIN (
    SELECT column_name, data_type, ordinal_position
    FROM information_schema.columns
    WHERE table_schema = 'lakemeter' AND table_name = 'estimates_backup_20260119'
) b ON e.ordinal_position = b.ordinal_position
ORDER BY COALESCE(e.ordinal_position, b.ordinal_position);
