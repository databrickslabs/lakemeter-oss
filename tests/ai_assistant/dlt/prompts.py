"""Prompt constants for DLT/SDP workload proposal tests.

Extracted from test_dlt_proposal.py to keep test file under 200-line guideline.
Three prompt sequences: PRO serverless, CORE basic, ADVANCED with monitoring.
"""

# Variant 1: CDC pipeline, Pro edition, serverless
DLT_PRO_PRIMARY = (
    "I need to set up a CDC pipeline using Spark Declarative Pipelines (SDP) "
    "with Pro edition and serverless compute on AWS us-east-1."
)
DLT_PRO_FOLLOWUP = (
    "This is a DLT/SDP workload (not Lakeflow Jobs). Use Pro edition for CDC "
    "and SCD type 2 support. Serverless compute, standard mode, Photon enabled. "
    "Running 4 times a day for 30 minutes each, 30 days/month. "
    "Please propose the SDP workload configuration now."
)
DLT_PRO_FINAL = (
    "Yes, please go ahead and propose the Spark Declarative Pipelines (DLT) "
    "workload with Pro edition, serverless, 4 runs/day, 30 min each."
)

# Variant 2: Basic pipeline, Core edition
DLT_CORE_PRIMARY = (
    "I need a basic DLT pipeline for simple batch ETL — just reading from S3, "
    "transforming, and writing to Delta tables. Nothing fancy, on AWS us-east-1."
)
DLT_CORE_FOLLOWUP = (
    "This should be an SDP (Spark Declarative Pipelines) workload with Core "
    "edition — no CDC or SCD needed. Classic compute, 4 workers, i3.xlarge, "
    "Photon enabled. 2 runs per day, 45 minutes each, 22 days/month. "
    "Please propose the DLT workload now."
)
DLT_CORE_FINAL = (
    "Please propose the DLT/SDP workload with Core edition, classic compute, "
    "4 workers, i3.xlarge, 2 runs/day, 45 min each, 22 days/month."
)

# Variant 3: Advanced pipeline with full monitoring
DLT_ADVANCED_PRIMARY = (
    "I need an advanced DLT pipeline with full data quality expectations, "
    "monitoring, and enhanced autoscaling on AWS us-east-1."
)
DLT_ADVANCED_FOLLOWUP = (
    "Use SDP (Spark Declarative Pipelines) with Advanced edition — we need "
    "data quality expectations and enhanced monitoring. Serverless compute, "
    "performance mode. 6 runs per day, 20 minutes each, 30 days/month. "
    "Please propose the DLT workload configuration now."
)
DLT_ADVANCED_FINAL = (
    "Go ahead and propose the DLT/SDP workload with Advanced edition, "
    "serverless performance mode, Photon enabled, 6 runs/day, 20 min each, "
    "30 days/month. Base table size is medium (~100GB). "
    "Use sensible defaults for anything I haven't specified — "
    "just propose the workload now, don't ask more questions."
)

# Variant 4: Negative test — non-DLT request (should NOT produce DLT)
NON_DLT_PRIMARY = (
    "I need an interactive cluster for ad-hoc data exploration "
    "with 4 workers on AWS us-east-1."
)
NON_DLT_FOLLOWUP = (
    "This is an All-Purpose Compute cluster for interactive notebooks. "
    "4 workers, i3.xlarge, running 8 hours per day, 22 days/month. "
    "Please propose the workload configuration now."
)
NON_DLT_FINAL = (
    "Go ahead and propose an All-Purpose Compute workload — "
    "4 workers, i3.xlarge, 8 hours/day, 22 days/month."
)
