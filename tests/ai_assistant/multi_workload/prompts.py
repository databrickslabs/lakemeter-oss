"""Prompt constants for multi-workload proposal tests.

Sprint 10: conversations requesting multiple workloads in a single session.
Variant 1: 3-workload platform (JOBS + ALL_PURPOSE + DBSQL).
Variant 2: 2-workload (JOBS + DBSQL only).
Negative: single-workload should not produce extras.
"""

# ── Variant 1: Full data platform — JOBS + ALL_PURPOSE + DBSQL ────────

PLATFORM_PRIMARY = (
    "I need to set up a data platform on AWS us-east-1. "
    "It needs three things: (1) daily ETL jobs to process data from S3 "
    "into Delta Lake, (2) interactive notebooks for data science and "
    "exploration, and (3) a SQL warehouse for BI dashboards and reporting."
)

PLATFORM_FOLLOWUP = (
    "Let's start with the first workload. I need a Lakeflow Jobs workload "
    "for the daily ETL pipeline — serverless, running 5 times per day, "
    "about 30 minutes each run, 22 days per month. "
    "Please propose this Jobs workload now."
)

PLATFORM_FINAL = (
    "Go ahead and propose a Lakeflow Jobs workload — serverless, "
    "5 runs/day, 30 minutes each, 22 days/month for ETL processing."
)

# After confirming JOBS, ask for ALL_PURPOSE
PLATFORM_NEXT_INTERACTIVE_PRIMARY = (
    "Great, the Jobs workload is confirmed. Now I need an interactive "
    "All-Purpose cluster for data science. 4 workers, running about "
    "8 hours per day, 22 days per month. Classic compute."
)

PLATFORM_NEXT_INTERACTIVE_FOLLOWUP = (
    "This is a Databricks All-Purpose Compute cluster for interactive "
    "data science work. 4 workers, approximately 176 hours per month "
    "(8 hrs × 22 days). Please propose the All-Purpose workload now."
)

PLATFORM_NEXT_INTERACTIVE_FINAL = (
    "Go ahead and propose an All-Purpose Compute workload — "
    "4 workers, 176 hours per month, interactive data science."
)

# After confirming ALL_PURPOSE, ask for DBSQL
PLATFORM_NEXT_DBSQL_PRIMARY = (
    "Perfect. Now I need a Databricks SQL warehouse for BI dashboards. "
    "Serverless, medium size, running about 500 hours per month."
)

PLATFORM_NEXT_DBSQL_FOLLOWUP = (
    "This is a Databricks SQL Serverless warehouse — medium size, "
    "1 cluster, 500 hours per month for BI reporting. "
    "Please propose the SQL warehouse workload now."
)

PLATFORM_NEXT_DBSQL_FINAL = (
    "Go ahead and propose a Databricks SQL workload — "
    "serverless, medium, 500 hours/month for BI dashboards."
)

# ── Variant 2: 2-workload — JOBS + DBSQL (no ALL_PURPOSE) ────────────

TWO_WL_PRIMARY = (
    "I need two workloads for our data pipeline on AWS us-east-1: "
    "(1) an ETL pipeline using Lakeflow Jobs to process daily data, "
    "and (2) a Databricks SQL warehouse for analytics queries."
)

TWO_WL_JOBS_FOLLOWUP = (
    "Start with the ETL pipeline. Lakeflow Jobs, serverless, "
    "running 3 times per day, 20 minutes each, 22 days/month. "
    "Please propose the Jobs workload now."
)

TWO_WL_JOBS_FINAL = (
    "Go ahead and propose a Lakeflow Jobs workload — serverless, "
    "3 runs/day, 20 minutes each, 22 days/month."
)

TWO_WL_DBSQL_PRIMARY = (
    "Now the SQL warehouse — serverless, small size, "
    "about 200 hours per month for analytics."
)

TWO_WL_DBSQL_FOLLOWUP = (
    "Databricks SQL Serverless warehouse, small size, "
    "200 hours per month. Please propose this workload now."
)

TWO_WL_DBSQL_FINAL = (
    "Go ahead and propose a Databricks SQL workload — "
    "serverless, small, 200 hours/month."
)

# ── Negative: single-workload — data science only ─────────────────────

NEG_DS_ONLY_PRIMARY = (
    "I just need an interactive cluster for data science exploration. "
    "4 workers, running 8 hours a day on AWS us-east-1. "
    "No ETL jobs or SQL warehouses needed."
)

NEG_DS_ONLY_FOLLOWUP = (
    "This is an All-Purpose Compute cluster for interactive notebooks. "
    "4 workers, about 176 hours per month. "
    "Please propose the All-Purpose workload now."
)

NEG_DS_ONLY_FINAL = (
    "Go ahead and propose an All-Purpose Compute workload — "
    "4 workers, 176 hours/month, interactive data science only."
)
