"""Prompt constants for LAKEBASE workload proposal tests.

Two positive variants: HA production database (4 CU), small dev/test (0.5 CU, 10GB).
Two negative discrimination variants: ETL pipeline (JOBS), SQL analytics (DBSQL).
"""

# ── Variant 1: HA Production Database, 4 CU, 500GB storage ──────────

HA_PROD_PRIMARY = (
    "I need a Lakebase PostgreSQL database for a production application. "
    "It should have 4 compute units with high availability enabled, "
    "500GB of storage, and 1 read replica for read scaling on AWS us-east-1."
)
HA_PROD_FOLLOWUP = (
    "This is a Databricks Lakebase instance — a managed PostgreSQL database. "
    "4 CU, high availability with a standby replica, 1 read replica, "
    "500GB storage. Please propose the Lakebase workload configuration now."
)
HA_PROD_FINAL = (
    "Go ahead and propose a Lakebase workload — 4 CU, HA enabled, "
    "1 read replica, 500GB storage, production PostgreSQL database."
)

# ── Variant 2: Small dev/test instance, 0.5 CU, 10GB, no HA ────────

SMALL_DEV_PRIMARY = (
    "I need a small Lakebase PostgreSQL database for development and testing. "
    "Just 0.5 compute units, 10GB storage, no high availability needed. "
    "AWS us-east-1."
)
SMALL_DEV_FOLLOWUP = (
    "This is a Databricks Lakebase instance — small dev/test setup. "
    "0.5 CU, 10GB storage, no HA, no read replicas. "
    "Please propose the Lakebase workload configuration now."
)
SMALL_DEV_FINAL = (
    "Go ahead and propose a Lakebase workload — 0.5 CU, 10GB storage, "
    "no high availability, no replicas, for development use."
)

# ── Variant 3: Negative — ETL pipeline (should be JOBS, not LAKEBASE) ─

NON_LB_ETL_PRIMARY = (
    "I need a daily ETL pipeline that processes 500GB of data "
    "from S3 into Delta Lake tables on AWS us-east-1."
)
NON_LB_ETL_FOLLOWUP = (
    "This is a Databricks Lakeflow Jobs workload — batch ETL processing. "
    "Runs daily, processes 500GB, writes to Delta tables. "
    "Please propose the workload configuration now."
)
NON_LB_ETL_FINAL = (
    "Go ahead and propose a Jobs workload for daily ETL — "
    "batch data processing pipeline, 500GB per run."
)

# ── Variant 4: Negative — SQL analytics (should be DBSQL, not LAKEBASE)

NON_LB_SQL_PRIMARY = (
    "I need a SQL warehouse for BI dashboards and ad-hoc analytics "
    "queries, serverless, medium size on AWS us-east-1."
)
NON_LB_SQL_FOLLOWUP = (
    "This is a Databricks SQL Serverless warehouse — medium size "
    "for BI reporting and analytics. 200 hours per month. "
    "Please propose the workload configuration now."
)
NON_LB_SQL_FINAL = (
    "Go ahead and propose a Databricks SQL workload — "
    "serverless, medium size, for BI dashboards and analytics."
)
