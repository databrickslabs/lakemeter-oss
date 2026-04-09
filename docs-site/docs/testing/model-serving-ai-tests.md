---
sidebar_position: 7
---

# Sprint 5: Model Serving Tests

Sprint 5 validates the AI assistant's ability to propose **Model Serving** endpoint workloads across three GPU/CPU variants and correctly reject non-serving requests.

## What's Tested

### Overview

| Variant | File | Tests | AI Calls | Compute Type |
|---------|------|-------|----------|--------------|
| GPU Medium (A10G) | `test_model_serving_gpu_medium.py` | 8 | 1 | gpu_medium |
| CPU Only | `test_model_serving_cpu.py` | 8 | 1 | cpu |
| GPU Small (T4) | `test_model_serving_gpu_small.py` | 8 | 1 | gpu_small |
| Negative (Interactive) | `test_model_serving_negative.py` | 2 | 1 | N/A |
| Negative (Batch ETL) | `test_model_serving_negative.py` | 2 | 1 | N/A |
| **Total** | **4 files** | **28** | **5** | |

### GPU Medium — A10G Real-Time Inference (8 tests)

A single AI call simulates deploying a GPU-accelerated serving endpoint:

> *"I need to deploy a model serving endpoint with GPU medium A10G for real-time ML inference on AWS us-east-1. Expecting around 200 hours of usage per month."*

| Field | Assertion |
|-------|-----------|
| `workload_type` | Equals `"MODEL_SERVING"` |
| `model_serving_type` | Contains `"gpu_medium"` |
| `hours_per_month` | In range 100–744 (tolerant of AI interpretation) |
| `workload_name` | Non-empty, at least 3 characters |
| `reason` | Populated, at least 10 characters |
| `notes` | Populated |
| `proposal_id` | Present |

![Workload Configuration](/img/workload-expanded-config.png)
*A Model Serving workload configuration — the AI assistant generates these configurations from natural language descriptions of ML deployment needs.*

### CPU Only — Lightweight Inference (8 tests)

Tests a CPU-only endpoint for scikit-learn models:

> *"I need a CPU-only model serving endpoint for lightweight scikit-learn model inference on AWS us-east-1. Running about 500 hours per month."*

Verifies:
- `model_serving_type` contains `"cpu"`
- `hours_per_month` is present and > 0
- `model_serving_scale_to_zero` is a boolean when present (conditional check — AI may omit this field)
- Standard metadata fields populated

### GPU Small — T4 Embedding Generation (8 tests)

Tests a smaller GPU endpoint for embeddings:

> *"I need a GPU small T4 model serving endpoint for real-time embedding generation on AWS us-east-1. About 300 hours per month."*

Verifies:
- `model_serving_type` contains `"gpu_small"`
- `hours_per_month` is present and > 0
- Standard metadata fields populated

### Negative Discrimination (4 tests)

Two scenarios ensure the AI doesn't propose Model Serving for unrelated workloads:

**Interactive Compute (AC-15)**:
> *"I need an interactive notebook cluster for data exploration with 4 workers."*
- Verifies: `workload_type` is **not** `"MODEL_SERVING"`

**Batch ETL (AC-16)**:
> *"I need a daily batch ETL pipeline to transform raw CSV files into curated Delta tables."*
- Verifies: `workload_type` is **not** `"MODEL_SERVING"`

## File Structure

```
tests/ai_assistant/sprint_5/
├── __init__.py
├── prompts.py                         # 5 prompt sequences (3 GPU/CPU + 2 negative)
├── conftest.py                        # 5 module-scoped fixtures (1 AI call each)
├── test_model_serving_gpu_medium.py   # 8 tests — GPU Medium A10G
├── test_model_serving_cpu.py          # 8 tests — CPU only
├── test_model_serving_gpu_small.py    # 8 tests — GPU Small T4
└── test_model_serving_negative.py     # 4 tests — interactive + ETL discrimination
```

## Running Sprint 5 Tests

```bash
cd "/path/to/lakemeter_app"
source .venv/bin/activate
python -m pytest tests/ai_assistant/sprint_5/ -v
```

Expected output:

```
tests/ai_assistant/sprint_5/test_model_serving_gpu_medium.py::TestModelServingGpuMedium::test_workload_type PASSED
tests/ai_assistant/sprint_5/test_model_serving_gpu_medium.py::TestModelServingGpuMedium::test_serving_type PASSED
tests/ai_assistant/sprint_5/test_model_serving_gpu_medium.py::TestModelServingGpuMedium::test_hours_per_month PASSED
...
tests/ai_assistant/sprint_5/test_model_serving_cpu.py::TestModelServingCpu::test_serving_type_cpu PASSED
tests/ai_assistant/sprint_5/test_model_serving_cpu.py::TestModelServingCpu::test_scale_to_zero_boolean PASSED
...
tests/ai_assistant/sprint_5/test_model_serving_gpu_small.py::TestModelServingGpuSmall::test_serving_type PASSED
...
tests/ai_assistant/sprint_5/test_model_serving_negative.py::TestServingNegativeInteractive::test_not_serving PASSED
tests/ai_assistant/sprint_5/test_model_serving_negative.py::TestServingNegativeEtl::test_not_serving PASSED

28 passed in ~250s
```

![Calculator Overview](/img/calculator-overview.png)
*The calculator with Model Serving workloads — tests verify the AI correctly proposes these configurations for ML inference use cases.*

## Compute Type Selection Logic

The AI must correctly map hardware requirements to serving compute types:

| User Intent | Expected Type | Key Signals |
|-------------|--------------|-------------|
| GPU-intensive inference, A10G | **gpu_medium** | "GPU medium", "A10G", "real-time inference" |
| Lightweight inference, no GPU | **cpu** | "CPU-only", "scikit-learn", "lightweight" |
| Smaller GPU, embeddings | **gpu_small** | "GPU small", "T4", "embeddings" |
| Large models, A100 | **gpu_large** | "GPU large", "A100", "large models" |

### Valid Serving Types

The AI must propose one of: `cpu` | `gpu_small` | `gpu_medium` | `gpu_large`

## Acceptance Criteria

All 16 acceptance criteria pass:

| AC | Description | Status |
|----|-------------|--------|
| AC-1 | GPU Medium → `workload_type=MODEL_SERVING` | PASS |
| AC-2 | GPU Medium → `model_serving_type` contains `gpu_medium` | PASS |
| AC-3 | GPU Medium → `hours_per_month` ~ 200 | PASS |
| AC-4–7 | GPU Medium → name, reason, notes, proposal_id | PASS |
| AC-8–9 | CPU → MODEL_SERVING + cpu type | PASS |
| AC-10 | CPU → `hours_per_month > 0` | PASS |
| AC-11 | CPU → `scale_to_zero` is boolean when present | PASS |
| AC-12–14 | GPU Small → MODEL_SERVING + gpu_small + hours | PASS |
| AC-15 | Interactive compute ≠ MODEL_SERVING | PASS |
| AC-16 | Batch ETL ≠ MODEL_SERVING | PASS |

## Known Limitations

- AI responses are non-deterministic — `hours_per_month` uses a tolerant range (100–744) instead of asserting the exact requested value
- `model_serving_scale_to_zero` is checked conditionally — the AI may not always include this optional field
- Each negative variant makes its own AI call (~30–60s each)

## Troubleshooting

| Issue | Resolution |
|-------|-----------|
| `hours_per_month` out of range | The AI may interpret "200 hours" differently. Widen the assertion range if the value is reasonable. |
| CPU test returns gpu_small | The AI may think any inference needs a GPU. Ensure the prompt explicitly says "CPU-only, no GPU." |
| `scale_to_zero` assertion fails | This field is optional. The test only checks it when present — if the assertion is running, the AI included it but with a non-boolean value. |
| Negative test returns MODEL_SERVING | Check that the prompt doesn't mention "model", "inference", or "serving." |
