INSERT INTO lakemeter.ref_workload_types (
    workload_type,
    display_name,
    description,
    sku_product_type_standard,
    display_order
)
VALUES (
    'GENERAL_STORAGE',
    'Databricks Default Storage',
    'Managed storage for Unity Catalog data and workspace assets',
    'DATABRICKS_STORAGE',
    18
)
ON CONFLICT (workload_type) DO UPDATE
SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    sku_product_type_standard = EXCLUDED.sku_product_type_standard,
    display_order = EXCLUDED.display_order;
