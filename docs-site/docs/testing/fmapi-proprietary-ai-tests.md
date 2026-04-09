---
sidebar_position: 10
---

# Sprint 8: FMAPI Proprietary Tests

Sprint 8 validates the AI assistant's ability to propose **Foundation Model API (Proprietary)** workloads for all three proprietary providers — Anthropic (Claude), OpenAI (GPT), and Google (Gemini) — plus negative discrimination against Databricks-hosted and GPU serving models.

## What's Tested

### Overview

| Variant | File | Tests | AI Calls | Provider |
|---------|------|-------|----------|----------|
| Claude Sonnet 4.5 (Anthropic) | `test_fmapi_prop_claude.py` | 9 | 1 | anthropic |
| GPT-5 Mini (OpenAI) | `test_fmapi_prop_openai.py` | 9 | 1 | openai |
| Gemini 2.5 Flash (Google) | `test_fmapi_prop_google.py` | 9 | 1 | google |
| Negative — Llama (DB-hosted) | `test_fmapi_prop_negative.py` | 4 | 1 | N/A |
| Negative — GPU Serving | `test_fmapi_prop_negative.py` | 3 | 1 | N/A |
| **Total** | **4 files** | **34** | **5** | |

### Claude — Anthropic (9 tests)

A single AI call simulates requesting Claude through Databricks Foundation Model APIs:

> *"Add Claude API usage, 5M input tokens and 1M output tokens per month"*

| Field | Assertion |
|-------|-----------|
| `workload_type` | Equals `"FMAPI_PROPRIETARY"` |
| `fmapi_provider` | Contains `"anthropic"` |
| `fmapi_model` | Contains `"claude"` |
| `fmapi_rate_type` | Valid token type (input_token, output_token) |
| `fmapi_quantity` | In range 1-100 |
| `fmapi_endpoint_type` | Valid endpoint type |
| `workload_name` | Non-empty |
| `reason` | Populated |
| `proposal_id` | Present |

![Calculator overview](/img/calculator-overview.png)
*The AI assistant proposes FMAPI Proprietary workloads — each provider (Anthropic, OpenAI, Google) has distinct pricing and model options.*

:::note
The AI may propose two separate workloads for input and output tokens, since each rate_type is a separate line item. Tests validate whichever workload is returned first.
:::

### GPT — OpenAI (9 tests)

Tests OpenAI model recognition and provider classification:

> *"I need GPT-5 mini for 20M input tokens per month"*

Verifies:
- `workload_type` equals `"FMAPI_PROPRIETARY"`
- `fmapi_provider` contains `"openai"`
- `fmapi_model` contains `"gpt"`
- `fmapi_quantity` > 0
- Standard metadata fields (name, reason, proposal_id)

### Gemini — Google (9 tests)

Tests Google model recognition:

> *"Add Gemini 2.5 Flash usage, 15M input tokens per month"*

Verifies:
- `workload_type` equals `"FMAPI_PROPRIETARY"`
- `fmapi_provider` contains `"google"`
- `fmapi_model` contains `"gemini"`
- `fmapi_quantity` > 0
- Standard metadata fields (name, reason, proposal_id)

### Negative Discrimination (7 tests)

Two scenarios ensure the AI doesn't propose FMAPI Proprietary for incorrect use cases:

**Llama (Databricks-Hosted) — AC-20**:
> *"I want to use Llama 3 for text generation"*
- Verifies: `workload_type` is **not** `"FMAPI_PROPRIETARY"` (should be `FMAPI_DATABRICKS`)

**GPU Model Serving — AC-21**:
> *"Deploy my custom PyTorch model on a GPU endpoint"*
- Verifies: `workload_type` is **not** `"FMAPI_PROPRIETARY"` (should be `MODEL_SERVING`)

## Iteration 2: Regression Fix

Sprint 8 iteration 2 also fixed a regression in Sprint 5's ETL negative tests:

**Bug**: `test_model_serving_negative.py::TestModelServingNegativeEtl` — 2 errors. The `non_serving_etl_proposal` fixture failed because the AI asked "Lakeflow Jobs (Procedural) or SDP (Declarative)?" instead of proposing a workload after 3 messages.

**Root Cause**: The ETL prompts were ambiguous — "batch ETL workload" doesn't specify JOBS vs DLT, so the AI asked for clarification.

**Fix**: Updated `tests/ai_assistant/sprint_5/prompts.py` to explicitly specify "Lakeflow Jobs" workload type and added "I want the JOBS workload type, not DLT" to the final escalation prompt.

:::tip Lesson Learned
When testing negative scenarios, prompts must be unambiguous about what workload type *should* be proposed. If the AI can reasonably ask a clarifying question, it will — and the fixture will fail.
:::

## File Structure

```
tests/ai_assistant/sprint_8/
├── __init__.py
├── prompts.py                        # 5 prompt sequences (3 providers + 2 negative)
├── conftest.py                       # 5 module-scoped fixtures (1 AI call each)
├── test_fmapi_prop_claude.py         # 9 tests — Anthropic Claude
├── test_fmapi_prop_openai.py         # 9 tests — OpenAI GPT
├── test_fmapi_prop_google.py         # 9 tests — Google Gemini
└── test_fmapi_prop_negative.py       # 7 tests — Llama + GPU discrimination
```

## Running Sprint 8 Tests

```bash
cd "/path/to/lakemeter_app"
source .venv/bin/activate

# Sprint 8 AI tests only (~5 minutes)
python -m pytest tests/ai_assistant/sprint_8/ -v

# Full regression (non-AI, ~6 seconds)
python -m pytest tests/ --ignore=tests/ai_assistant -v
```

Expected output:

```
tests/ai_assistant/sprint_8/test_fmapi_prop_claude.py::TestFmapiPropClaude::test_workload_type PASSED
tests/ai_assistant/sprint_8/test_fmapi_prop_claude.py::TestFmapiPropClaude::test_provider PASSED
tests/ai_assistant/sprint_8/test_fmapi_prop_claude.py::TestFmapiPropClaude::test_model PASSED
...
tests/ai_assistant/sprint_8/test_fmapi_prop_openai.py::TestFmapiPropOpenai::test_provider PASSED
...
tests/ai_assistant/sprint_8/test_fmapi_prop_google.py::TestFmapiPropGoogle::test_provider PASSED
...
tests/ai_assistant/sprint_8/test_fmapi_prop_negative.py::TestFmapiPropNegativeLlama::test_not_proprietary PASSED
tests/ai_assistant/sprint_8/test_fmapi_prop_negative.py::TestFmapiPropNegativeGpu::test_not_proprietary PASSED

34 passed in ~300s
```

## Provider Selection Logic

The AI must correctly map model names to the right provider and workload type:

| User Request | Expected Type | Expected Provider | Key Signals |
|-------------|--------------|-------------------|-------------|
| Claude, Anthropic models | **FMAPI_PROPRIETARY** | `anthropic` | "Claude", "Anthropic", "Sonnet", "Opus", "Haiku" |
| GPT, OpenAI models | **FMAPI_PROPRIETARY** | `openai` | "GPT", "OpenAI", "GPT-4", "GPT-5" |
| Gemini, Google models | **FMAPI_PROPRIETARY** | `google` | "Gemini", "Google", "Gemini Flash", "Gemini Pro" |
| Llama, DBRX, BGE | **FMAPI_DATABRICKS** | N/A | "Llama", "DBRX", "BGE", "open-source" |
| Custom model + GPU | **MODEL_SERVING** | N/A | "custom model", "PyTorch", "GPU endpoint" |

### Valid Providers

The AI must propose one of: `anthropic` | `openai` | `google`

## Acceptance Criteria

All 21 acceptance criteria pass:

| AC | Description | Status |
|----|-------------|--------|
| AC-1-9 | Claude -> FMAPI_PROPRIETARY + anthropic + claude + rate + quantity + endpoint + name + reason + proposal_id | PASS |
| AC-10-14 | GPT -> FMAPI_PROPRIETARY + openai + gpt + quantity + name + reason + proposal_id | PASS |
| AC-15-19 | Gemini -> FMAPI_PROPRIETARY + google + gemini + quantity + name + reason + proposal_id | PASS |
| AC-20 | Llama -> NOT FMAPI_PROPRIETARY (is FMAPI_DATABRICKS) | PASS |
| AC-21 | GPU serving -> NOT FMAPI_PROPRIETARY (is MODEL_SERVING) | PASS |

## Known Limitations

- AI responses are non-deterministic — model names use substring matching (e.g., `"claude"` not exact version string)
- AI may propose slightly different model names (e.g., `"claude-sonnet-4-5"` vs `"claude-4-5-sonnet"`)
- Quantity ranges are generous to accommodate AI's interpretation of token volume
- AI may propose 2 separate workloads (input + output) when a user specifies both — tests validate the first proposal

## Troubleshooting

| Issue | Resolution |
|-------|-----------|
| `fmapi_provider` doesn't match expected | The AI may use a different provider string format. Check if it's a valid alias (e.g., "openai" vs "open_ai"). |
| AI proposes FMAPI_DATABRICKS for Claude | Ensure the prompt clearly says "Claude" or specifies "Anthropic" as the provider. |
| Negative Llama test returns FMAPI_PROPRIETARY | The AI may misclassify open-source models. Ensure the prompt says "Llama" and mentions "Databricks-hosted" or "open-source." |
| Fixture fails with clarifying question | Check that the prompt sequence has 3 progressively specific messages. The final message should be explicit about the workload type. |
