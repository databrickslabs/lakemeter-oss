-- ============================================================================
-- Add discount_config column to estimates table
-- ============================================================================
-- This column exists in estimates_backup_20260119 but missing in estimates
-- Column type: JSONB (nullable)

-- Add the column
ALTER TABLE lakemeter.estimates 
ADD COLUMN IF NOT EXISTS discount_config JSONB;

-- Verify the column was added
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'lakemeter' 
  AND table_name = 'estimates'
  AND column_name = 'discount_config';

-- Optional: Check if any data needs to be migrated from backup
SELECT 
    COUNT(*) as total_records,
    COUNT(discount_config) as records_with_discount_config,
    COUNT(*) - COUNT(discount_config) as records_without_discount_config
FROM lakemeter.estimates_backup_20260119;

-- ============================================================================
-- Optional: Migrate discount_config data from backup if needed
-- ============================================================================
-- Uncomment and run if you want to copy discount_config values from backup

/*
UPDATE lakemeter.estimates e
SET discount_config = b.discount_config
FROM lakemeter.estimates_backup_20260119 b
WHERE e.estimate_id = b.estimate_id
  AND b.discount_config IS NOT NULL;
*/
