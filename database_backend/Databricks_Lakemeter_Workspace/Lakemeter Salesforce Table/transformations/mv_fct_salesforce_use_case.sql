CREATE OR REFRESH MATERIALIZED VIEW users.steven_tan.mv_fct_salesforce_use_case
COMMENT "Salesforce use cases - distinct records"
AS
SELECT DISTINCT
  customer_id,
  salesforce_use_case_id,
  dim_canonical_customer_name,
  dim_salesforce_use_case_id,
  salesforce_use_case_name
FROM main.metric_store.fct_salesforce_use_case__core;