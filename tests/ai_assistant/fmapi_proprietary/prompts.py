"""Prompt constants for FMAPI_PROPRIETARY workload proposal tests.

Three positive variants: Claude (Anthropic), GPT (OpenAI), Gemini (Google).
Two negative discrimination variants: Llama (FMAPI_DATABRICKS), GPU serving (MODEL_SERVING).
"""

# Valid fmapi_endpoint_type enum values
VALID_ENDPOINT_TYPES = ["global", "in_geo"]

# Valid fmapi_rate_types
VALID_RATE_TYPES = [
    "input_token", "output_token", "cache_read", "cache_write",
    "batch_inference",
]

# ── Variant 1: Claude Sonnet 4.5, 5M input tokens (Anthropic) ─────

CLAUDE_INPUT_PRIMARY = (
    "I need to use Claude Sonnet 4.5 through the Databricks Foundation "
    "Model API for a text generation application. Expecting about 5 million "
    "input tokens per month on AWS us-east-1."
)
CLAUDE_INPUT_FOLLOWUP = (
    "This is a proprietary Anthropic model — Claude Sonnet 4.5 via FMAPI. "
    "5 million input tokens per month, global endpoint. "
    "Please propose the Foundation Model API workload configuration now."
)
CLAUDE_INPUT_FINAL = (
    "Go ahead and propose an FMAPI Proprietary workload for Claude Sonnet 4.5 — "
    "Anthropic proprietary model, 5 million input tokens per month, global endpoint."
)

# ── Variant 2: GPT-5 mini, 20M input tokens (OpenAI) ──────────────

GPT_INPUT_PRIMARY = (
    "I want to use GPT-5 mini through the Databricks Foundation Model API "
    "for a customer support chatbot. We expect about 20 million input tokens "
    "per month on AWS us-east-1."
)
GPT_INPUT_FOLLOWUP = (
    "This is a proprietary OpenAI model — GPT-5 mini via FMAPI. "
    "20 million input tokens per month, global endpoint. "
    "Please propose the Foundation Model API workload configuration now."
)
GPT_INPUT_FINAL = (
    "Go ahead and propose an FMAPI Proprietary workload for GPT-5 mini — "
    "OpenAI proprietary model, 20 million input tokens per month, global endpoint."
)

# ── Variant 3: Gemini 2.5 Flash, 15M input tokens (Google) ────────

GEMINI_INPUT_PRIMARY = (
    "I need to use Gemini 2.5 Flash through the Databricks Foundation "
    "Model API for document summarization. About 15 million input tokens "
    "per month on AWS us-east-1."
)
GEMINI_INPUT_FOLLOWUP = (
    "This is a proprietary Google model — Gemini 2.5 Flash via FMAPI. "
    "15 million input tokens per month, global endpoint. "
    "Please propose the Foundation Model API workload configuration now."
)
GEMINI_INPUT_FINAL = (
    "Go ahead and propose an FMAPI Proprietary workload for Gemini 2.5 Flash — "
    "Google proprietary model, 15 million input tokens per month, global endpoint."
)

# ── Variant 4: Negative — Llama (should be FMAPI_DATABRICKS) ──────

NON_PROP_LLAMA_PRIMARY = (
    "I want to use Llama 4 Maverick through the Databricks Foundation "
    "Model API for 10 million input tokens per month on AWS us-east-1."
)
NON_PROP_LLAMA_FOLLOWUP = (
    "This is a Databricks-hosted open model — Llama 4 Maverick via FMAPI. "
    "Not a proprietary model. 10 million input tokens per month. "
    "Please propose the Foundation Model API workload configuration now."
)
NON_PROP_LLAMA_FINAL = (
    "Go ahead and propose an FMAPI Databricks workload for Llama 4 Maverick, "
    "10 million input tokens per month, global endpoint."
)

# ── Variant 5: Negative — GPU model serving (should be MODEL_SERVING)

NON_PROP_GPU_PRIMARY = (
    "I need to deploy a custom fine-tuned model on a GPU medium A10G "
    "endpoint for real-time inference on AWS us-east-1."
)
NON_PROP_GPU_FOLLOWUP = (
    "This is a Databricks Model Serving endpoint — GPU medium (A10G). "
    "A custom model deployment, not FMAPI. 200 hours per month. "
    "Please propose the workload configuration now."
)
NON_PROP_GPU_FINAL = (
    "Go ahead and propose a Model Serving workload — GPU medium, "
    "200 hours per month for custom model inference."
)
