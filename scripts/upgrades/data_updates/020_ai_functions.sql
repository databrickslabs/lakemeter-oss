INSERT INTO lakemeter.ref_workload_types (
    workload_type,
    display_name,
    description,
    sku_product_type_standard,
    display_order
)
VALUES
    (
        'AI_EXTRACT',
        'AI Extract',
        'Structured extraction from raw text or parsed document input',
        'SERVERLESS_REAL_TIME_INFERENCE',
        13
    ),
    (
        'AI_CLASSIFY',
        'AI Classify',
        'Classification of raw text or parsed document input',
        'SERVERLESS_REAL_TIME_INFERENCE',
        14
    )
ON CONFLICT (workload_type) DO UPDATE
SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    sku_product_type_standard = EXCLUDED.sku_product_type_standard,
    display_order = EXCLUDED.display_order;
