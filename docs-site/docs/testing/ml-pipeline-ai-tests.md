---
sidebar_position: 13
---

# Sprint 11: ML Pipeline AI Tests (VECTOR_SEARCH + FMAPI + MODEL_SERVING)

Sprint 11 validates the AI assistant's ability to handle **ML/RAG pipeline conversations** — multi-workload scenarios targeting AI/ML workload types: Vector Search, Foundation Model API (Proprietary), and Model Serving.

## What's Tested

### Overview

| Scenario | File | Tests | AI Calls |
|----------|------|-------|----------|
| 3-workload type checks | `test_ml_pipeline_types.py` | 24 | Shared (1 session) |
| 3-workload confirm flow | `test_ml_pipeline_confirm.py` | 12 | Shared |
| 2-workload variant (VS + FMAPI) | `test_ml_pipeline_two.py` | 14 | 1 session |
| Negative: Model Serving only | `test_ml_pipeline_negative.py` | 7 | 1 session |
| **Sprint 11 AI total** | **4 files** | **57** | **3 sessions** |
| Non-AI regression guards | `test_regression_s10_bugs.py` | 8 | 0 |
| Model Serving combined | `test_ms_combined_validation.py` | 34 | 0 |
| Notes completeness | `test_notes_completeness.py` | 8 | 0 |
| **Sprint 11 non-AI total** | **3 files** | **50** | **0** |

### 3-Workload ML Pipeline (36 tests)

The primary scenario simulates a full RAG application setup:

> *"Set up a RAG application with vector search for embeddings, Claude for text generation, and a model serving endpoint for our custom reranker"*

The test suite verifies the AI proposes all three ML workload types across the conversation:

| Workload | Key Fields Asserted |
|----------|-------------------|
| **VECTOR_SEARCH** | `workload_type=VECTOR_SEARCH`, `endpoint_type` populated, `vector_capacity_millions` |
| **FMAPI_PROPRIETARY** | `workload_type=FMAPI_PROPRIETARY`, `fmapi_provider=anthropic`, `fmapi_model` contains `claude` |
| **MODEL_SERVING** | `workload_type=MODEL_SERVING`, `model_serving_type` populated |

![Calculator overview](/img/calculator-overview.png)
*The AI assistant proposes ML pipeline workloads — Vector Search, FMAPI Proprietary, and Model Serving for a complete RAG architecture.*

Each workload is checked for common metadata fields:
- `workload_name` — descriptive name
- `reason` — why this workload was proposed
- `notes` — additional context
- `proposal_id` — unique UUID

**Confirm flow** (12 tests):
- All 3 confirmations succeed
- Conversation state shows ≥ 3 confirmed workloads with correct types
- Each proposal has a distinct `proposal_id`

### 2-Workload Variant (14 tests)

A simpler RAG scenario with only Vector Search and FMAPI:

> *"I need vector search for embeddings and Claude for inference"*

Verifies:
- Both VS and FMAPI_PROPRIETARY workloads proposed
- Both confirmations succeed
- No unnecessary Model Serving workload proposed

### Negative Discrimination (7 tests)

Ensures the AI correctly identifies a **Model Serving-only** request without proposing VS or FMAPI:

> *"Deploy a custom PyTorch model on a GPU endpoint for real-time inference"*

Verifies:
- `workload_type` is `MODEL_SERVING`
- Does **not** propose `VECTOR_SEARCH` or `FMAPI_PROPRIETARY`

![Workload calculation detail](/img/workload-calculation-detail.png)
*Each ML workload in the pipeline has its own cost calculation — tests verify type-specific fields are correctly populated.*

:::note
The AI may use the `propose_genai_architecture` bundle tool instead of individual `propose_workload` calls. Both are valid — the tests check the resulting set of workload types regardless of which tool was used.
:::

## Acceptance Criteria

All 12 acceptance criteria pass:

| AC | Description | Status |
|----|-------------|--------|
| AC-1 | 3 proposals collected (VS, FMAPI_PROP, MS) | PASS |
| AC-2 | Types cover all three ML workloads | PASS |
| AC-3 | Common fields (name, reason, notes, proposal_id) | PASS |
| AC-4 | VS has `endpoint_type` populated | PASS |
| AC-5 | FMAPI_PROP has anthropic provider + claude model | PASS |
| AC-6 | MS has `model_serving_type` populated | PASS |
| AC-7 | All 3 confirmations succeed | PASS |
| AC-8 | State shows ≥ 3 confirmed with correct types | PASS |
| AC-9 | Distinct `proposal_id`s | PASS |
| AC-10 | 2-workload: VS + FMAPI_PROP only | PASS |
| AC-11 | Both 2-workload confirmations succeed | PASS |
| AC-12 | Negative: MS only, no VS/FMAPI | PASS |

## File Structure

```
tests/ai_assistant/sprint_11/
├── __init__.py
├── prompts.py                         # 119 lines — prompt constants for 3-wl, 2-wl, negative
├── conftest.py                        # 147 lines — module-scoped fixtures: sessions
├── test_ml_pipeline_types.py          # 138 lines — 24 tests: type checks, fields
├── test_ml_pipeline_confirm.py        # 90 lines — 12 tests: confirm flow, state
├── test_ml_pipeline_two.py            # 81 lines — 14 tests: 2-workload variant
└── test_ml_pipeline_negative.py       # 52 lines — 7 tests: MS-only discrimination

tests/sprint_11/
├── test_regression_s10_bugs.py        # 8 tests — Sprint 10 regression guards
├── test_ms_combined_validation.py     # 34 tests — Model Serving in combined Excel
└── test_notes_completeness.py         # 8 tests — Notes column completeness
```

## Running Sprint 11 Tests

```bash
cd "/path/to/lakemeter_app"
source .venv/bin/activate

# Default pytest (excludes AI tests, completes in ~9s)
pytest -v

# Sprint 11 non-AI tests only
pytest tests/sprint_11/ -v

# Sprint 11 AI tests (explicit, requires FMAPI access)
pytest tests/ai_assistant/sprint_11/ --no-header --timeout=300
```

Expected non-AI output:

```
tests/sprint_11/test_regression_s10_bugs.py::TestS10BugRegression::test_pyproject_ignores_ai PASSED
tests/sprint_11/test_ms_combined_validation.py::TestModelServingCombined::test_gpu_medium PASSED
...
tests/sprint_11/test_notes_completeness.py::TestNotesCompleteness::test_all_types_have_notes PASSED

50 passed in ~2.5s
```

## Test Results

| Suite | Tests | Runtime | AI Calls |
|-------|-------|---------|----------|
| Sprint 11 non-AI | 50 | ~2.5s | 0 |
| Sprint 11 AI (ML pipeline) | 57 | ~8 min | 3 sessions |
| Full non-AI regression | 1,409 | ~9.6s | 0 |

## Multi-Workload Test Comparison

| Sprint | Scenario | Workload Types | Tests |
|--------|----------|---------------|-------|
| Sprint 10 | Data Platform | JOBS + ALL_PURPOSE + DBSQL | ~40 AI |
| **Sprint 11** | **ML Pipeline** | **VECTOR_SEARCH + FMAPI_PROP + MODEL_SERVING** | **57 AI** |
| Sprint 12 (planned) | Complete Platform | 5+ workload types | TBD |

## Known Limitations

- AI tests are non-deterministic — auto-skip if FMAPI is unreachable
- The AI may propose workloads in different order than prompted — tests check the SET of types, not the order
- If the AI uses `propose_genai_architecture` (bundle tool) instead of individual proposals, the `extract_proposal` helper may need extension for edge cases

## Troubleshooting

| Issue | Resolution |
|-------|-----------|
| AI proposes wrong types | Check that the prompt clearly specifies "vector search", "Claude", and "model serving" |
| FMAPI provider not `anthropic` | Ensure the prompt says "Claude" — the AI may default to a different provider if prompt is ambiguous |
| Fewer than 3 proposals | The AI may bundle proposals or ask clarifying questions — escalation prompts handle this |
| AI tests skip | Check network access; tests auto-skip if FMAPI endpoint is unreachable |
| `extract_proposal` returns None | The AI may have used bundle tool — check `tool_results` for `propose_genai_architecture` |
