-- One-time migration: normalize existing data to canonical case
-- UPPERCASE fields: cloud, workload_type, dbsql_warehouse_type, dlt_edition
-- Run this against the lakemeter Lakebase database

-- Fix dbsql_warehouse_type (most impactful — caused DBSQL Pro pricing bug)
UPDATE lakemeter.line_items
SET dbsql_warehouse_type = UPPER(dbsql_warehouse_type)
WHERE dbsql_warehouse_type IS NOT NULL
  AND dbsql_warehouse_type != UPPER(dbsql_warehouse_type);

-- Fix dlt_edition
UPDATE lakemeter.line_items
SET dlt_edition = UPPER(dlt_edition)
WHERE dlt_edition IS NOT NULL
  AND dlt_edition != UPPER(dlt_edition);

-- Fix workload_type
UPDATE lakemeter.line_items
SET workload_type = UPPER(workload_type)
WHERE workload_type IS NOT NULL
  AND workload_type != UPPER(workload_type);

-- Fix cloud on line_items
UPDATE lakemeter.line_items
SET cloud = UPPER(cloud)
WHERE cloud IS NOT NULL
  AND cloud != UPPER(cloud);

-- Fix cloud and tier on estimates
UPDATE lakemeter.estimates
SET cloud = UPPER(cloud)
WHERE cloud IS NOT NULL
  AND cloud != UPPER(cloud);

UPDATE lakemeter.estimates
SET tier = UPPER(tier)
WHERE tier IS NOT NULL
  AND tier != UPPER(tier);
