CREATE OR REFRESH MATERIALIZED VIEW mv_dim_salesforce_account
COMMENT "Salesforce accounts - deduplicated by account name, keeping latest ds, only accounts with use cases"
AS
WITH accounts_with_use_cases AS (
  SELECT DISTINCT
    a.salesforce_account_id,
    a.salesforce_account_name,
    a.ds
  FROM main.metric_store.dim_salesforce_account a
  INNER JOIN main.metric_store.fct_salesforce_use_case__core uc
    ON a.salesforce_account_id = uc.customer_id
),
ranked_accounts AS (
  SELECT 
    salesforce_account_id,
    salesforce_account_name,
    ROW_NUMBER() OVER (
      PARTITION BY salesforce_account_name 
      ORDER BY ds DESC
    ) AS rn
  FROM accounts_with_use_cases
)
SELECT 
  salesforce_account_id,
  salesforce_account_name
FROM ranked_accounts
WHERE rn = 1;