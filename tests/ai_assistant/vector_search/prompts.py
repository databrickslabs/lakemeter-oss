"""Prompt constants for VECTOR_SEARCH workload proposal tests.

Three endpoint variants: STANDARD (50M), STORAGE_OPTIMIZED (200M), small RAG (5M).
Two negative discrimination variants: model deployment, SQL analytics.
"""

# Valid vector_search_endpoint_type enum values
VALID_ENDPOINT_TYPES = ["STANDARD", "STORAGE_OPTIMIZED"]

# Variant 1: Standard endpoint, 50 million embeddings for RAG
STANDARD_PRIMARY = (
    "I need to set up vector search for a RAG application with "
    "50 million embeddings on AWS us-east-1. "
    "Low latency is important for real-time retrieval."
)
STANDARD_FOLLOWUP = (
    "This is a Databricks Vector Search endpoint — standard type "
    "optimized for speed. 50 million vectors for semantic search. "
    "Please propose the Vector Search workload configuration now."
)
STANDARD_FINAL = (
    "Yes, please go ahead and propose the Vector Search workload with "
    "standard endpoint type, 50 million vector capacity."
)

# Variant 2: Storage-optimized endpoint, 200 million vectors
STORAGE_OPT_PRIMARY = (
    "I need a storage-optimized vector search endpoint for a large "
    "document corpus with 200 million vectors on AWS us-east-1. "
    "Cost efficiency matters more than latency."
)
STORAGE_OPT_FOLLOWUP = (
    "This is a Databricks Vector Search endpoint — storage-optimized type "
    "for cost-efficient large-scale vector storage. 200 million vectors. "
    "Please propose the Vector Search workload configuration now."
)
STORAGE_OPT_FINAL = (
    "Go ahead and propose the Vector Search workload with "
    "storage-optimized endpoint type, 200 million vector capacity."
)

# Variant 3: Small RAG chatbot, 5 million document embeddings
SMALL_RAG_PRIMARY = (
    "I need a small vector search endpoint for a RAG chatbot with "
    "about 5 million document embeddings on AWS us-east-1."
)
SMALL_RAG_FOLLOWUP = (
    "This is a Databricks Vector Search endpoint for a small RAG use case. "
    "5 million vectors for chatbot retrieval. "
    "Please propose the Vector Search workload configuration now."
)
SMALL_RAG_FINAL = (
    "Please propose the Vector Search workload with "
    "5 million vector capacity for the RAG chatbot."
)

# Variant 4: Negative — model deployment (should NOT be VECTOR_SEARCH)
NON_VS_MODEL_PRIMARY = (
    "I need to deploy a real-time ML model serving endpoint "
    "with GPU medium for inference on AWS us-east-1."
)
NON_VS_MODEL_FOLLOWUP = (
    "This is a Databricks Model Serving endpoint — GPU medium (A10G). "
    "200 hours per month for ML inference. "
    "Please propose the workload configuration now."
)
NON_VS_MODEL_FINAL = (
    "Go ahead and propose a Model Serving workload — "
    "GPU medium, 200 hours per month, real-time inference."
)

# Variant 5: Negative — SQL analytics (should NOT be VECTOR_SEARCH)
NON_VS_SQL_PRIMARY = (
    "I need a serverless SQL warehouse for BI dashboards "
    "and ad-hoc analytics queries on AWS us-east-1."
)
NON_VS_SQL_FOLLOWUP = (
    "This is a Databricks SQL Serverless warehouse — medium size "
    "for BI reporting. Running about 200 hours per month. "
    "Please propose the workload configuration now."
)
NON_VS_SQL_FINAL = (
    "Go ahead and propose a Databricks SQL workload — "
    "serverless, medium size, for BI dashboards."
)
