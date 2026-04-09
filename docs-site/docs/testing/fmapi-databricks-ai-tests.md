---
sidebar_position: 9
---

# Sprint 7: FMAPI Databricks Tests

Sprint 7 validates the AI assistant's ability to propose **Foundation Model API (Databricks)** workloads for open-source models hosted on Databricks, plus backend pricing calculation correctness. It covers Llama input tokens, output tokens, BGE embeddings, negative discrimination, and 36 backend pricing unit tests.

## What's Tested

### AI Assistant Proposal Tests

| Variant | File | Tests | AI Calls | Model Category |
|---------|------|-------|----------|----------------|
| Llama Input Tokens (10M) | `test_fmapi_db_llama_input.py` | 8 | 1 | LLM (input) |
| Llama Output Tokens (5M) | `test_fmapi_db_output_tokens.py` | 8 | 1 | LLM (output) |
| BGE Embeddings (20M) | `test_fmapi_db_embeddings.py` | 7 | 1 | Embedding |
| Negative — Claude (Proprietary) | `test_fmapi_db_negative.py` | 4 | 1 | N/A |
| Negative — GPU Serving | `test_fmapi_db_negative.py` | 3 | 1 | N/A |
| **Total AI** | **4 files** | **30** | **5** | |

### Backend Pricing Tests

| Category | File | Tests |
|----------|------|-------|
| SKU mapping, rate lookup, calc formulas | `test_fmapi_db_pricing.py` | 36 |
| Edge cases (unknown provider, Google cache) | `test_fmapi_prop_edge_cases.py` | 10 |
| **Total Backend** | **2 files** | **46** |

**Combined Sprint 7 Total: 76 tests (30 AI + 46 backend)**

### Llama Input Tokens — 10M/month (8 tests)

A single AI call simulates requesting Databricks-hosted Llama for input token processing:

> *"I want to use Llama 4 via Foundation Model API, expecting 10M input tokens per month"*

| Field | Assertion |
|-------|-----------|
| `workload_type` | Equals `"FMAPI_DATABRICKS"` |
| `fmapi_model` | Contains `"llama"` |
| `fmapi_rate_type` | Valid token type (input_token, output_token) |
| `fmapi_quantity` | In range 1-100 |
| `fmapi_endpoint_type` | In `[global, regional]` |
| `workload_name` | Non-empty, descriptive |
| `reason` | Populated |
| `proposal_id` | Present |

![Calculator overview](/img/calculator-overview.png)
*The AI assistant proposes FMAPI Databricks workloads from natural language descriptions of model usage needs.*

### Llama Output Tokens — 5M/month (8 tests)

Tests output token rate type recognition:

> *"Add DBRX usage with 5M output tokens per month"*

Verifies:
- `workload_type` equals `"FMAPI_DATABRICKS"`
- `fmapi_rate_type` equals `"output_token"`
- `fmapi_quantity` in range 1-100
- `fmapi_model` populated
- `fmapi_endpoint_type` valid
- Standard metadata fields (name, reason, proposal_id)

### BGE Embeddings — 20M Tokens (7 tests)

Tests embedding model recognition:

> *"I need BGE-Large embeddings for 20M tokens per month via Databricks Foundation Models"*

Verifies:
- `workload_type` equals `"FMAPI_DATABRICKS"`
- `fmapi_model` contains substring matching `bge`, `gte`, or `embed`
- `fmapi_quantity` > 0
- `fmapi_endpoint_type` valid
- Standard metadata fields (name, reason)

### Negative Discrimination (7 tests)

Two scenarios ensure the AI doesn't propose FMAPI Databricks for incorrect use cases:

**Claude (Proprietary Model) — AC-18**:
> *"I want to use Claude Sonnet for my chat application"*
- Verifies: `workload_type` is **not** `"FMAPI_DATABRICKS"` (should be `FMAPI_PROPRIETARY`)
- Also asserts: `fmapi_provider` contains `"anthropic"`, `fmapi_model` contains `"claude"`

**GPU Model Serving — AC-19**:
> *"I need a GPU endpoint for serving my custom PyTorch model"*
- Verifies: `workload_type` is **not** `"FMAPI_DATABRICKS"` (should be `MODEL_SERVING`)
- Also asserts: GPU type present

### Backend Pricing Tests (36 tests)

The `test_fmapi_db_pricing.py` file tests calculation correctness without AI calls:

| Category | What's Verified | Tests |
|----------|----------------|-------|
| **SKU Mapping** | All DB models -> `SERVERLESS_REAL_TIME_INFERENCE` | 4 |
| **Unknown Fallback** | Unknown/empty model returns valid fallback | 2 |
| **Rate Lookup** | Llama, BGE, GTE rates across rate types | 6 |
| **Output > Input** | Output token rate exceeds input for all models | 2 |
| **Embeddings Input-Only** | Embedding models only have input_token rates | 2 |
| **Hourly Classification** | Provisioned = hourly, token = not hourly | 3 |
| **calc_item_values** | Token-based and provisioned calculation paths | 6 |
| **Formula Verification** | Calculations match pricing JSON data | 4 |
| **Data Integrity** | Required fields, positive rates, hourly flags | 7 |

### Edge Case Tests (10 tests)

| Case | What's Verified |
|------|----------------|
| Unknown provider fallback | `_get_fmapi_sku` returns `OPENAI_MODEL_SERVING`, rate returns not-found |
| Empty provider / None model | Graceful handling, no exceptions |
| Google `cache_read` / `cache_write` | Rate lookup returns not-found, SKU still resolves |

## File Structure

```
tests/ai_assistant/sprint_7/          # AI proposal tests
├── __init__.py
├── prompts.py                         # 5 prompt sequences
├── conftest.py                        # 5 module-scoped fixtures
├── test_fmapi_db_llama_input.py       # 8 tests — Llama input tokens
├── test_fmapi_db_output_tokens.py     # 8 tests — Output tokens
├── test_fmapi_db_embeddings.py        # 7 tests — BGE embeddings
└── test_fmapi_db_negative.py          # 7 tests — proprietary + GPU discrimination

tests/sprint_7/                        # Backend pricing tests
├── test_fmapi_db_pricing.py           # 36 tests — SKU, rates, calculations
└── test_fmapi_prop_edge_cases.py      # 10 tests — fallback edge cases
```

## Running Sprint 7 Tests

```bash
cd "/path/to/lakemeter_app"
source .venv/bin/activate

# Backend pricing only (fast, ~1 second)
python -m pytest tests/sprint_7/ -v

# AI assistant only (~4 minutes)
python -m pytest tests/ai_assistant/sprint_7/ -v

# All Sprint 7 tests
python -m pytest tests/sprint_7/ tests/ai_assistant/sprint_7/ -v
```

## Acceptance Criteria

All acceptance criteria pass:

| AC | Description | Status |
|----|-------------|--------|
| AC-1 | Llama -> `workload_type=FMAPI_DATABRICKS` | PASS |
| AC-2 | Llama -> `fmapi_model` contains "llama" | PASS |
| AC-3 | Llama -> `fmapi_rate_type` is valid token type | PASS |
| AC-4 | Llama -> `fmapi_quantity` in range 1-100 | PASS |
| AC-5 | Llama -> `fmapi_endpoint_type` in [global, regional] | PASS |
| AC-6-8 | Llama -> name, reason, proposal_id populated | PASS |
| AC-9-13 | Output -> FMAPI_DATABRICKS + output_token + quantity + model + name + reason | PASS |
| AC-14-17 | Embeddings -> FMAPI_DATABRICKS + model + quantity + endpoint + name + reason | PASS |
| AC-18 | Claude -> NOT FMAPI_DATABRICKS (is FMAPI_PROPRIETARY) | PASS |
| AC-19 | GPU serving -> NOT FMAPI_DATABRICKS (is MODEL_SERVING) | PASS |

## Known Limitations

- AI responses are non-deterministic — model name assertions use substring matching (e.g., `"llama"` not exact version)
- Embedding model assertion accepts `bge`, `gte`, or `embed` to handle AI's model name variations
- Backend pricing tests depend on the pricing JSON bundle being present in the test environment

## Troubleshooting

| Issue | Resolution |
|-------|-----------|
| `fmapi_model` doesn't contain expected substring | The AI may use a different model variant. Check if the proposed model is still a Databricks-hosted model. |
| `fmapi_rate_type` is `provisioned_scaling` | The AI may interpret high token volume as needing provisioned throughput. Adjust the prompt to specify "pay-per-token." |
| Backend pricing test fails on rate lookup | Verify the pricing JSON bundle exists and contains the expected model entries. |
| Negative Claude test returns FMAPI_DATABRICKS | The AI may not distinguish proprietary vs Databricks models. Ensure the prompt clearly says "Claude" or "Anthropic." |
