-- =============================================================================
-- Update Lakebase CU Constraint to Match Current Docs
-- =============================================================================
-- Reference: https://docs.databricks.com/aws/en/oltp/projects/manage-computes#available-compute-sizes
--
-- Autoscaling-compatible: 0.5, 1-32 CU
-- Fixed-size only: 36, 40, 44, 48, 52, 56, 60, 64, 72, 80, 88, 96, 104, 112 CU
-- Each CU = ~2 GB RAM
-- =============================================================================

-- Step 1: Drop old constraint (was limited to 1, 2, 4, 8)
ALTER TABLE lakemeter.line_items DROP CONSTRAINT IF EXISTS chk_lakebase_cu;

-- Step 2: Change column from INTEGER to NUMERIC(5,1) to support 0.5 CU
ALTER TABLE lakemeter.line_items ALTER COLUMN lakebase_cu TYPE NUMERIC(5,1);

-- Step 3: Add new constraint with all valid Lakebase Autoscaling compute sizes
ALTER TABLE lakemeter.line_items
ADD CONSTRAINT chk_lakebase_cu
CHECK (lakebase_cu IS NULL OR lakebase_cu IN (
    0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
    17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32,
    36, 40, 44, 48, 52, 56, 60, 64, 72, 80, 88, 96, 104, 112
));

-- Verify
SELECT constraint_name FROM information_schema.table_constraints
WHERE table_name = 'line_items' AND constraint_name = 'chk_lakebase_cu';
