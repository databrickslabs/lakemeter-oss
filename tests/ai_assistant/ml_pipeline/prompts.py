"""Prompt constants for ML pipeline multi-workload proposal tests.

Sprint 11: conversations requesting an ML/RAG pipeline with
VECTOR_SEARCH + FMAPI_PROPRIETARY + MODEL_SERVING.
Variant 1: 3-workload full RAG pipeline.
Variant 2: 2-workload (Vector Search + FMAPI only, no Model Serving).
Negative: single-workload model serving only.
"""

# -- Variant 1: Full RAG pipeline — VECTOR_SEARCH + FMAPI_PROPRIETARY + MODEL_SERVING --

RAG_PRIMARY = (
    "I'm building a RAG application on AWS us-east-1. I need three "
    "components: (1) vector search for storing and querying embeddings, "
    "(2) Claude via Foundation Model API for text generation, and "
    "(3) a model serving endpoint for our custom reranker model."
)

RAG_VS_FOLLOWUP = (
    "Let's start with vector search. I need a Databricks Vector Search "
    "endpoint to store about 50 million embedding vectors for our "
    "document corpus. Standard endpoint type. "
    "Please propose the Vector Search workload now."
)

RAG_VS_FINAL = (
    "Go ahead and propose a Vector Search workload — standard endpoint, "
    "50 million vectors for RAG document retrieval."
)

# After confirming VECTOR_SEARCH, ask for FMAPI_PROPRIETARY (Claude)
RAG_FMAPI_PRIMARY = (
    "Great, vector search is confirmed. Now I need Claude for text "
    "generation. We'll use Anthropic's Claude via the Foundation Model "
    "API — about 10 million input tokens and 2 million output tokens "
    "per month."
)

RAG_FMAPI_FOLLOWUP = (
    "This is a Databricks Foundation Model API workload for Anthropic "
    "Claude. Proprietary model serving. 10 million input tokens per "
    "month. Please propose the FMAPI Proprietary workload now."
)

RAG_FMAPI_FINAL = (
    "Go ahead and propose an FMAPI Proprietary workload — Anthropic "
    "Claude, 10M input tokens per month for RAG text generation."
)

# After confirming FMAPI_PROPRIETARY, ask for MODEL_SERVING
RAG_MS_PRIMARY = (
    "Perfect. Now I need a model serving endpoint for our custom "
    "reranker model. GPU small instance, running about 200 hours "
    "per month with scale-to-zero enabled."
)

RAG_MS_FOLLOWUP = (
    "This is a Databricks Model Serving endpoint for a custom "
    "reranker — GPU small, 200 hours per month, scale-to-zero "
    "enabled. Please propose the Model Serving workload now."
)

RAG_MS_FINAL = (
    "Go ahead and propose a Model Serving workload — GPU small, "
    "200 hours/month, scale-to-zero for our custom reranker."
)

# -- Variant 2: 2-workload — VECTOR_SEARCH + FMAPI_PROPRIETARY only --

TWO_WL_PRIMARY = (
    "I need two workloads for a RAG system on AWS us-east-1: "
    "(1) vector search for embeddings and (2) Claude via FMAPI "
    "for text generation. No custom model serving needed."
)

TWO_WL_VS_FOLLOWUP = (
    "Start with vector search. Standard endpoint, 20 million "
    "vectors for document retrieval. "
    "Please propose the Vector Search workload now."
)

TWO_WL_VS_FINAL = (
    "Go ahead and propose a Vector Search workload — standard "
    "endpoint, 20 million vectors."
)

TWO_WL_FMAPI_PRIMARY = (
    "Now the Claude FMAPI workload — Anthropic Claude, 5 million "
    "input tokens per month for text generation."
)

TWO_WL_FMAPI_FOLLOWUP = (
    "FMAPI Proprietary workload — Anthropic Claude, 5M input "
    "tokens per month. Please propose this workload now."
)

TWO_WL_FMAPI_FINAL = (
    "Go ahead and propose an FMAPI Proprietary workload — "
    "Anthropic Claude, 5M input tokens/month."
)

# -- Negative: single-workload — model serving only --

NEG_MS_ONLY_PRIMARY = (
    "I just need a model serving endpoint for deploying our ML model "
    "on AWS us-east-1. GPU medium, about 300 hours per month. "
    "No vector search or FMAPI needed."
)

NEG_MS_ONLY_FOLLOWUP = (
    "This is a Databricks Model Serving endpoint — GPU medium, "
    "300 hours per month. Please propose the Model Serving "
    "workload now."
)

NEG_MS_ONLY_FINAL = (
    "Go ahead and propose a Model Serving workload — GPU medium, "
    "300 hours/month for ML model inference only."
)
