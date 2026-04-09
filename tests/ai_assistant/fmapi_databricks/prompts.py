"""Prompt constants for FMAPI_DATABRICKS workload proposal tests.

Three positive variants: Llama input tokens, Llama output tokens, BGE embeddings.
Two negative discrimination variants: Claude (proprietary), GPU model serving.
"""

# Valid fmapi_endpoint_type enum values
VALID_ENDPOINT_TYPES = ["global", "regional"]

# Valid fmapi_rate_types
VALID_RATE_TYPES = [
    "input_token", "output_token", "cache_read", "cache_write",
    "batch_inference",
]

# ── Variant 1: Llama 4 Maverick, 10M input tokens ──────────────

LLAMA_INPUT_PRIMARY = (
    "I want to use Llama 4 Maverick via the Databricks Foundation Model API "
    "for a chatbot application. Expecting about 10 million input tokens "
    "per month on AWS us-east-1."
)
LLAMA_INPUT_FOLLOWUP = (
    "This is a Databricks-hosted open model — Llama 4 Maverick via FMAPI. "
    "10 million input tokens per month, global endpoint. "
    "Please propose the Foundation Model API workload configuration now."
)
LLAMA_INPUT_FINAL = (
    "Go ahead and propose an FMAPI Databricks workload for Llama 4 Maverick, "
    "10 million input tokens per month, global endpoint."
)

# ── Variant 2: Output tokens, 5M ───────────────────────────────

OUTPUT_TOKEN_PRIMARY = (
    "I need to estimate Foundation Model API output token costs for a "
    "Databricks-hosted Llama model generating about 5 million output tokens "
    "per month on AWS us-east-1."
)
OUTPUT_TOKEN_FOLLOWUP = (
    "This is FMAPI Databricks — a Llama model for text generation. "
    "5 million output tokens per month. "
    "Please propose the Foundation Model API workload configuration now."
)
OUTPUT_TOKEN_FINAL = (
    "Go ahead and propose an FMAPI Databricks workload for Llama "
    "output tokens — 5 million output tokens per month."
)

# ── Variant 3: BGE-Large embeddings, 20M tokens ────────────────

EMBEDDINGS_PRIMARY = (
    "I need to run BGE-Large embeddings through the Databricks Foundation "
    "Model API for a vector search pipeline. About 20 million input tokens "
    "per month on AWS us-east-1."
)
EMBEDDINGS_FOLLOWUP = (
    "This is a Databricks-hosted embeddings model — BGE-Large via FMAPI. "
    "20 million input tokens per month for generating embeddings. "
    "Please propose the Foundation Model API workload configuration now."
)
EMBEDDINGS_FINAL = (
    "Go ahead and propose an FMAPI Databricks workload for BGE-Large "
    "embeddings — 20 million input tokens per month."
)

# ── Variant 4: Negative — Claude API (should be FMAPI_PROPRIETARY) ──

NON_DB_CLAUDE_PRIMARY = (
    "I need to use Claude Sonnet 4.5 through the Databricks Foundation "
    "Model API for 8 million input tokens per month on AWS us-east-1."
)
NON_DB_CLAUDE_FOLLOWUP = (
    "This is the Anthropic Claude model — Claude Sonnet 4.5 via FMAPI. "
    "A proprietary model, not open-source. 8 million input tokens. "
    "Please propose the workload configuration now."
)
NON_DB_CLAUDE_FINAL = (
    "Go ahead and propose an FMAPI workload for Claude Sonnet 4.5 — "
    "Anthropic proprietary model, 8 million input tokens per month."
)

# ── Variant 5: Negative — GPU model serving (should be MODEL_SERVING) ──

NON_DB_GPU_PRIMARY = (
    "I need to deploy a custom fine-tuned model on a GPU medium A10G "
    "endpoint for real-time inference on AWS us-east-1."
)
NON_DB_GPU_FOLLOWUP = (
    "This is a Databricks Model Serving endpoint — GPU medium (A10G). "
    "A custom model deployment, not FMAPI. 200 hours per month. "
    "Please propose the workload configuration now."
)
NON_DB_GPU_FINAL = (
    "Go ahead and propose a Model Serving workload — GPU medium, "
    "200 hours per month for custom model inference."
)
