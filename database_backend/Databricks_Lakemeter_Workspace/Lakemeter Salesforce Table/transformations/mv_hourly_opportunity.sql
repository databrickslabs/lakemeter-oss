CREATE OR REFRESH MATERIALIZED VIEW users.steven_tan.mv_hourly_opportunity
COMMENT "Hourly opportunities - distinct records"
AS
SELECT DISTINCT
  id,
  name,
  accountid
FROM main.sfdc_bronze.hourly_opportunity;