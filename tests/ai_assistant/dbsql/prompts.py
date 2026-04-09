"""Prompt constants for DBSQL workload proposal tests.

Three warehouse type variants: SERVERLESS, PRO, CLASSIC.
Two negative discrimination variants: interactive compute, batch ETL.
"""

# Valid DBSQL warehouse sizes for assertions
VALID_WAREHOUSE_SIZES = [
    "2X-Small", "X-Small", "Small", "Medium",
    "Large", "X-Large", "2X-Large", "3X-Large", "4X-Large",
]

# Variant 1: Serverless SQL warehouse, medium size, BI dashboards
DBSQL_SERVERLESS_PRIMARY = (
    "I need a serverless SQL warehouse for BI dashboards on AWS us-east-1. "
    "Medium size, expecting about 50 concurrent queries at peak."
)
DBSQL_SERVERLESS_FOLLOWUP = (
    "This is a Databricks SQL (DBSQL) warehouse — serverless type, Medium size, "
    "1 cluster. We run dashboards 12 hours a day, 22 days/month (~264 hours/month). "
    "Please propose the DBSQL workload configuration now."
)
DBSQL_SERVERLESS_FINAL = (
    "Yes, please go ahead and propose the Databricks SQL workload with "
    "serverless warehouse type, Medium size, 1 cluster, 264 hours per month."
)

# Variant 2: Pro SQL warehouse, large size, analytics
DBSQL_PRO_PRIMARY = (
    "I need a Databricks SQL Pro warehouse for analytics queries on AWS us-east-1. "
    "Large size with 2 clusters for scaling."
)
DBSQL_PRO_FOLLOWUP = (
    "This is a DBSQL warehouse — Pro type (not serverless, not classic). "
    "Large size, 2 clusters. Running about 200 hours per month. "
    "Please propose the DBSQL workload configuration now."
)
DBSQL_PRO_FINAL = (
    "Please propose the Databricks SQL workload with Pro warehouse type, "
    "Large size, 2 clusters, 200 hours per month."
)

# Variant 3: Classic SQL warehouse (legacy, explicit request)
DBSQL_CLASSIC_PRIMARY = (
    "I need a classic legacy Databricks SQL warehouse on AWS us-east-1. "
    "Small size, single cluster. We have a legacy integration that requires it."
)
DBSQL_CLASSIC_FOLLOWUP = (
    "This must be a Classic DBSQL warehouse — not Pro, not Serverless. "
    "Small size, 1 cluster, running 150 hours per month. "
    "Please propose the classic DBSQL workload now."
)
DBSQL_CLASSIC_FINAL = (
    "Go ahead and propose the Databricks SQL workload with Classic warehouse type, "
    "Small size, 1 cluster, 150 hours per month. This is a legacy classic warehouse."
)

# Variant 4: Negative test — interactive compute (should NOT be DBSQL)
NON_DBSQL_PRIMARY = (
    "I need an interactive notebook cluster for data science work "
    "with 4 workers on AWS us-east-1."
)
NON_DBSQL_FOLLOWUP = (
    "This is an All-Purpose Compute cluster for interactive Jupyter notebooks. "
    "4 workers, i3.xlarge, running 8 hours per day, 22 days/month. "
    "Please propose the workload configuration now."
)
NON_DBSQL_FINAL = (
    "Go ahead and propose an All-Purpose Compute workload — "
    "4 workers, i3.xlarge, 176 hours/month, interactive use."
)

# Variant 5: Negative test — batch ETL (should NOT be DBSQL)
NON_DBSQL_ETL_PRIMARY = (
    "I need a batch ETL pipeline that runs daily to process raw data "
    "into curated Delta tables on AWS us-east-1."
)
NON_DBSQL_ETL_FOLLOWUP = (
    "This is a daily batch ETL job — processes 500GB, "
    "4 workers, runs once a day for 45 minutes, 22 days/month. "
    "Please propose the workload configuration now."
)
NON_DBSQL_ETL_FINAL = (
    "Go ahead and propose a batch ETL workload — "
    "daily job, 4 workers, 45 minutes per run, 22 days/month."
)
