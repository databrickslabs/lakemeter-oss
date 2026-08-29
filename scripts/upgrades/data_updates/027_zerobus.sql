INSERT INTO lakemeter.ref_workload_types (
    workload_type,
    display_name,
    description,
    sku_product_type_standard,
    display_order
)
VALUES (
    'ZEROBUS',
    'Zerobus Ingest',
    'Direct standard or OpenTelemetry ingestion into Delta tables',
    'JOBS_SERVERLESS_COMPUTE',
    19
)
ON CONFLICT (workload_type) DO UPDATE
SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    sku_product_type_standard = EXCLUDED.sku_product_type_standard,
    display_order = EXCLUDED.display_order;
