INSERT INTO lakemeter.ref_workload_types (
    workload_type,
    display_name,
    description,
    sku_product_type_standard,
    sku_product_type_serverless,
    display_order
)
VALUES (
    'VECTOR_SEARCH',
    'AI Search',
    'AI Search endpoints and optional reranking',
    'SERVERLESS_REAL_TIME_INFERENCE',
    'SERVERLESS_REAL_TIME_INFERENCE',
    5
)
ON CONFLICT (workload_type) DO UPDATE
SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    sku_product_type_standard = EXCLUDED.sku_product_type_standard,
    sku_product_type_serverless = EXCLUDED.sku_product_type_serverless,
    display_order = EXCLUDED.display_order;
