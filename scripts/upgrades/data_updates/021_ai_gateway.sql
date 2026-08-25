INSERT INTO lakemeter.ref_workload_types (
    workload_type,
    display_name,
    description,
    sku_product_type_standard,
    display_order
)
VALUES (
    'AI_GATEWAY',
    'Unity AI Gateway',
    'Additive AI Gateway inference tables and usage tracking',
    'SERVERLESS_REAL_TIME_INFERENCE',
    15
)
ON CONFLICT (workload_type) DO UPDATE
SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    sku_product_type_standard = EXCLUDED.sku_product_type_standard,
    display_order = EXCLUDED.display_order;
