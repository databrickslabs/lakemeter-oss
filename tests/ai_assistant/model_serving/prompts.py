"""Prompt constants for MODEL_SERVING workload proposal tests.

Three compute type variants: GPU_MEDIUM, CPU, GPU_SMALL.
Two negative discrimination variants: interactive compute, batch ETL.
"""

# Valid model_serving_type enum values
VALID_SERVING_TYPES = ["cpu", "gpu_small", "gpu_medium", "gpu_large"]

# Variant 1: GPU Medium A10G, 200 hours/month
GPU_MEDIUM_PRIMARY = (
    "I need to deploy a model serving endpoint with GPU medium A10G "
    "for real-time ML inference on AWS us-east-1. "
    "Expecting around 200 hours of usage per month."
)
GPU_MEDIUM_FOLLOWUP = (
    "This is a Databricks Model Serving endpoint — GPU medium (A10G). "
    "200 hours per month, scale-to-zero disabled for low latency. "
    "Please propose the Model Serving workload configuration now."
)
GPU_MEDIUM_FINAL = (
    "Yes, please go ahead and propose the Model Serving workload with "
    "gpu_medium compute type, 200 hours per month, scale-to-zero disabled."
)

# Variant 2: CPU only, 500 hours/month, lightweight inference
CPU_PRIMARY = (
    "I need a CPU-only model serving endpoint for lightweight "
    "scikit-learn model inference on AWS us-east-1. "
    "Running about 500 hours per month."
)
CPU_FOLLOWUP = (
    "This is a Databricks Model Serving endpoint — CPU compute only "
    "(no GPU needed). 500 hours per month, scale-to-zero enabled. "
    "Please propose the Model Serving workload configuration now."
)
CPU_FINAL = (
    "Please propose the Model Serving workload with "
    "cpu compute type, 500 hours per month, scale-to-zero enabled."
)

# Variant 3: GPU Small T4, 300 hours/month, real-time embeddings
GPU_SMALL_PRIMARY = (
    "I need a GPU small T4 model serving endpoint for "
    "real-time embedding generation on AWS us-east-1. "
    "About 300 hours per month."
)
GPU_SMALL_FOLLOWUP = (
    "This is a Databricks Model Serving endpoint — GPU small (T4). "
    "300 hours per month for embedding inference. "
    "Please propose the Model Serving workload configuration now."
)
GPU_SMALL_FINAL = (
    "Go ahead and propose the Model Serving workload with "
    "gpu_small compute type, 300 hours per month."
)

# Variant 4: Negative — interactive compute (should NOT be MODEL_SERVING)
NON_SERVING_INTERACTIVE_PRIMARY = (
    "I need an interactive notebook cluster for data exploration "
    "with 4 workers on AWS us-east-1."
)
NON_SERVING_INTERACTIVE_FOLLOWUP = (
    "This is an All-Purpose Compute cluster for interactive Jupyter notebooks. "
    "4 workers, i3.xlarge, running 8 hours per day, 22 days/month. "
    "Please propose the workload configuration now."
)
NON_SERVING_INTERACTIVE_FINAL = (
    "Go ahead and propose an All-Purpose Compute workload — "
    "4 workers, i3.xlarge, 176 hours/month, interactive use."
)

# Variant 5: Negative — batch ETL (should NOT be MODEL_SERVING)
NON_SERVING_ETL_PRIMARY = (
    "I need a Lakeflow Jobs workload for a daily batch ETL pipeline "
    "to transform raw CSV files into curated Delta tables on AWS us-east-1."
)
NON_SERVING_ETL_FOLLOWUP = (
    "This is a Lakeflow Jobs (procedural) ETL job — processes 200GB, "
    "4 workers, runs once a day for 30 minutes, 22 days/month. "
    "Please propose the Lakeflow Jobs workload configuration now."
)
NON_SERVING_ETL_FINAL = (
    "Go ahead and propose a Lakeflow Jobs workload — "
    "daily ETL job, 4 workers, 30 minutes per run, 22 days/month. "
    "I want the JOBS workload type, not DLT."
)
