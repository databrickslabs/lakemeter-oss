-- =============================================================================
-- Add Cost Calculation Response Columns to Line Items
-- =============================================================================
-- Purpose: Store full API calculation responses for each line item
-- Columns:
--   - cost_calculation_response: JSONB - Full API response (structure varies by workload)
--   - calculation_completed_at: TIMESTAMP - When calculation finished
-- =============================================================================

-- Add columns to main table
ALTER TABLE lakemeter.line_items 
ADD COLUMN IF NOT EXISTS cost_calculation_response JSONB DEFAULT NULL,
ADD COLUMN IF NOT EXISTS calculation_completed_at TIMESTAMP DEFAULT NULL;

-- Add columns to backup table
ALTER TABLE lakemeter.line_items_backup 
ADD COLUMN IF NOT EXISTS cost_calculation_response JSONB DEFAULT NULL,
ADD COLUMN IF NOT EXISTS calculation_completed_at TIMESTAMP DEFAULT NULL;

-- Add indexes to main table
CREATE INDEX IF NOT EXISTS idx_line_items_calculation_response 
ON lakemeter.line_items USING GIN (cost_calculation_response);

CREATE INDEX IF NOT EXISTS idx_line_items_calculation_completed_at 
ON lakemeter.line_items(calculation_completed_at);

-- Add indexes to backup table
CREATE INDEX IF NOT EXISTS idx_line_items_backup_calculation_response 
ON lakemeter.line_items_backup USING GIN (cost_calculation_response);

CREATE INDEX IF NOT EXISTS idx_line_items_backup_calculation_completed_at 
ON lakemeter.line_items_backup(calculation_completed_at);

-- Add comments
COMMENT ON COLUMN lakemeter.line_items.cost_calculation_response IS 
'Stores the full API response from calculate endpoints. Structure varies by workload_type. Contains detailed breakdown including DBU rates, VM costs, hours, SKU breakdown, discount details, etc. Check response.success field to determine if calculation succeeded.';

COMMENT ON COLUMN lakemeter.line_items.calculation_completed_at IS 
'Timestamp when the cost calculation was completed. Check cost_calculation_response.success field to determine if successful or error.';

COMMENT ON COLUMN lakemeter.line_items_backup.cost_calculation_response IS 
'Stores the full API response from calculate endpoints. Structure varies by workload_type. Contains detailed breakdown including DBU rates, VM costs, hours, SKU breakdown, discount details, etc. Check response.success field to determine if calculation succeeded.';

COMMENT ON COLUMN lakemeter.line_items_backup.calculation_completed_at IS 
'Timestamp when the cost calculation was completed. Check cost_calculation_response.success field to determine if successful or error.';

-- Verify columns added
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'lakemeter'
  AND table_name IN ('line_items', 'line_items_backup')
  AND column_name IN ('cost_calculation_response', 'calculation_completed_at')
ORDER BY table_name, ordinal_position;

-- Check indexes
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'lakemeter'
  AND tablename IN ('line_items', 'line_items_backup')
  AND indexname LIKE '%calculation%'
ORDER BY tablename, indexname;
