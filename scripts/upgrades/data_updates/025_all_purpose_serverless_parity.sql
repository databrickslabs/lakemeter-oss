UPDATE lakemeter.ref_workload_types
SET sku_product_type_serverless = 'ALL_PURPOSE_SERVERLESS_COMPUTE'
WHERE workload_type = 'ALL_PURPOSE';

CREATE OR REPLACE FUNCTION lakemeter.calculate_serverless_compute_dbu(
    p_cloud VARCHAR,
    p_driver_node_type VARCHAR,
    p_worker_node_type VARCHAR,
    p_num_workers INT,
    p_workload_type VARCHAR DEFAULT 'JOBS',
    p_serverless_mode VARCHAR DEFAULT 'standard'
)
RETURNS DECIMAL(18,4)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_driver_dbu DECIMAL(18,4);
    v_worker_dbu DECIMAL(18,4);
    v_photon_multiplier DECIMAL(10,4);
    v_mode_multiplier DECIMAL(10,4);
    v_total_dbu DECIMAL(18,4);
BEGIN
    SELECT dbu_rate INTO v_driver_dbu
    FROM lakemeter.sync_ref_instance_dbu_rates
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(instance_type) = UPPER(p_driver_node_type)
    LIMIT 1;

    SELECT dbu_rate INTO v_worker_dbu
    FROM lakemeter.sync_ref_instance_dbu_rates
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(instance_type) = UPPER(p_worker_node_type)
    LIMIT 1;

    v_photon_multiplier := lakemeter.get_photon_multiplier(
        p_cloud,
        p_workload_type,
        NULL,
        TRUE,
        TRUE
    );

    v_mode_multiplier := CASE
        WHEN UPPER(COALESCE(p_workload_type, '')) = 'ALL_PURPOSE' THEN 2.0
        WHEN LOWER(COALESCE(p_serverless_mode, 'standard')) = 'performance' THEN 2.0
        ELSE 1.0
    END;

    v_total_dbu := (
        COALESCE(v_driver_dbu, 0)
        + (COALESCE(v_worker_dbu, 0) * COALESCE(p_num_workers, 0))
    ) * v_photon_multiplier * v_mode_multiplier;

    RETURN v_total_dbu;
END;
$$;

COMMENT ON FUNCTION lakemeter.calculate_serverless_compute_dbu IS
'Calculate DBU per hour for serverless compute workloads. All-Purpose always
uses Performance Optimized mode; Jobs and DLT honor the selected mode.';
