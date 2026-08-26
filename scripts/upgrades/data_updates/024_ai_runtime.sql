INSERT INTO lakemeter.ref_workload_types (
    workload_type,
    display_name,
    description,
    sku_product_type_standard,
    display_order
)
VALUES (
    'AI_RUNTIME',
    'AI Runtime',
    'Serverless GPU model training',
    'MODEL_TRAINING',
    17
)
ON CONFLICT (workload_type) DO UPDATE
SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    sku_product_type_standard = EXCLUDED.sku_product_type_standard,
    display_order = EXCLUDED.display_order;
