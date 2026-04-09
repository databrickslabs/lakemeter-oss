-- ============================================================================
-- Add Missing Columns for API Compatibility
-- ============================================================================
-- 
-- Purpose: Add columns that are required by the new API design but missing
--          from the backup table schema
--
-- Target Tables: line_items_backup_20260114 (and line_items if needed)
--
-- Missing Columns:
-- 1. VECTOR_SEARCH: vector_capacity_millions
-- 2. FMAPI: fmapi_rate_type, fmapi_quantity
--
-- ============================================================================

-- ===========================================
-- 1. Add Vector Search Capacity Column
-- ===========================================

-- Add vector_capacity_millions for VECTOR_SEARCH workload type
ALTER TABLE lakemeter.line_items_backup_20260114 
ADD COLUMN IF NOT EXISTS vector_capacity_millions DECIMAL(15,2)
CHECK (vector_capacity_millions >= 0);

COMMENT ON COLUMN lakemeter.line_items_backup_20260114.vector_capacity_millions IS 
'Vector capacity in millions (e.g., 2 for 2M vectors). Replaces old serverless_size field for Vector Search.';

-- Also add to main table if needed
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS vector_capacity_millions DECIMAL(15,2)
CHECK (vector_capacity_millions >= 0);

COMMENT ON COLUMN lakemeter.line_items.vector_capacity_millions IS 
'Vector capacity in millions (e.g., 2 for 2M vectors). Replaces old serverless_size field for Vector Search.';

-- ===========================================
-- 2. Add FMAPI Rate Type and Quantity Columns
-- ===========================================

-- Add fmapi_rate_type (replaces separate input/output token columns)
ALTER TABLE lakemeter.line_items_backup_20260114 
ADD COLUMN IF NOT EXISTS fmapi_rate_type VARCHAR(50)
CHECK (fmapi_rate_type IN (
    'input_token', 
    'output_token', 
    'provisioned_scaling', 
    'provisioned_entry',
    'cache_read',
    'cache_write'
));

COMMENT ON COLUMN lakemeter.line_items_backup_20260114.fmapi_rate_type IS 
'FMAPI rate type: input_token, output_token, provisioned_scaling, provisioned_entry, cache_read, cache_write';

-- Add fmapi_quantity (unified quantity field)
ALTER TABLE lakemeter.line_items_backup_20260114 
ADD COLUMN IF NOT EXISTS fmapi_quantity BIGINT
CHECK (fmapi_quantity >= 0);

COMMENT ON COLUMN lakemeter.line_items_backup_20260114.fmapi_quantity IS 
'FMAPI quantity: number of tokens or hours depending on rate_type. Replaces separate input/output token columns.';

-- Also add to main table if needed
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS fmapi_rate_type VARCHAR(50)
CHECK (fmapi_rate_type IN (
    'input_token', 
    'output_token', 
    'provisioned_scaling', 
    'provisioned_entry',
    'cache_read',
    'cache_write'
));

COMMENT ON COLUMN lakemeter.line_items.fmapi_rate_type IS 
'FMAPI rate type: input_token, output_token, provisioned_scaling, provisioned_entry, cache_read, cache_write';

ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS fmapi_quantity BIGINT
CHECK (fmapi_quantity >= 0);

COMMENT ON COLUMN lakemeter.line_items.fmapi_quantity IS 
'FMAPI quantity: number of tokens or hours depending on rate_type. Replaces separate input/output token columns.';

-- ===========================================
-- 3. Verification
-- ===========================================

-- Check if columns were added successfully
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_schema = 'lakemeter'
  AND table_name IN ('line_items', 'line_items_backup_20260114')
  AND column_name IN ('vector_capacity_millions', 'fmapi_rate_type', 'fmapi_quantity')
ORDER BY table_name, column_name;

-- ===========================================
-- 4. Data Migration (Optional)
-- ===========================================

-- TODO: Migrate data from old columns to new columns if needed
-- 
-- For FMAPI: 
--   - Create 2 rows from each old row (one for input, one for output)
--   - OR decide which rate_type to use for existing rows
--
-- For Vector Search:
--   - Map serverless_size to vector_capacity_millions
--   - Need to determine the mapping logic

PRINT 'Migration complete! New columns added for API compatibility.';
PRINT 'NOTE: Existing rows will have NULL values for new columns.';
PRINT 'You may need to update existing data before backfill.';
