---
sidebar_position: 8
---

# Sprint 6: Vector Search Tests

Sprint 6 validates the AI assistant's ability to propose **Vector Search** workloads across Standard and Storage-Optimized endpoint types, handle small RAG use cases, and correctly reject non-vector-search requests.

## What's Tested

### Overview

| Variant | File | Tests | AI Calls | Endpoint Type |
|---------|------|-------|----------|---------------|
| Standard (50M vectors) | `test_vector_search_standard.py` | 8 | 1 | STANDARD |
| Storage-Optimized (200M) | `test_vector_search_storage_optimized.py` | 7 | 1 | STORAGE_OPTIMIZED |
| Small RAG (5M vectors) | `test_vector_search_small_rag.py` | 7 | 1 | Any valid |
| Negative (Model Serving) | `test_vector_search_negative.py` | 2 | 1 | N/A |
| Negative (SQL Analytics) | `test_vector_search_negative.py` | 2 | 1 | N/A |
| **Total** | **4 files** | **26** | **5** | |

### Standard Endpoint — 50M Vectors (8 tests)

A single AI call simulates setting up a standard vector search endpoint for a RAG application:

> *"Set up vector search for RAG with 50 million embeddings"*

| Field | Assertion |
|-------|-----------|
| `workload_type` | Equals `"VECTOR_SEARCH"` |
| `vector_search_endpoint_type` | Equals `"STANDARD"` |
| `vector_capacity_millions` | In range ~50 (tolerant) |
| `workload_name` | Non-empty, descriptive |
| `reason` | Populated, at least 10 characters |
| `notes` | Populated |
| `proposal_id` | Present |

![Calculator with workloads](/img/calculator-overview.png)
*The AI assistant proposes Vector Search workloads from natural language descriptions of embedding storage needs.*

### Storage-Optimized — 200M Vectors (7 tests)

Tests a large-scale storage-optimized endpoint:

> *"I need storage-optimized vector search for 200M vectors"*

Verifies:
- `workload_type` equals `"VECTOR_SEARCH"`
- `vector_search_endpoint_type` contains `"STORAGE"` (substring match for robustness)
- `vector_capacity_millions` > 0, in range 50–500
- Standard metadata fields populated

### Small RAG Chatbot — 5M Vectors (7 tests)

Tests a lightweight vector search for a simple chatbot:

> *"Small RAG chatbot, 5 million vectors"*

Verifies:
- `workload_type` equals `"VECTOR_SEARCH"`
- `vector_capacity_millions` populated and > 0
- `vector_search_endpoint_type` is a valid enum value
- Standard metadata fields populated

### Negative Discrimination (4 tests)

Two scenarios ensure the AI doesn't propose Vector Search for unrelated workloads:

**Model Deployment (AC-15)**:
> *"I need to deploy a custom ML model for real-time inference"*
- Verifies: `workload_type` is **not** `"VECTOR_SEARCH"` (should be `MODEL_SERVING`)

**SQL Analytics (AC-16)**:
> *"I need a SQL warehouse for BI dashboard queries"*
- Verifies: `workload_type` is **not** `"VECTOR_SEARCH"` (should be `DBSQL`)

## File Structure

```
tests/ai_assistant/sprint_6/
├── __init__.py
├── prompts.py                              # 5 prompt sequences (3 variants + 2 negative)
├── conftest.py                             # 5 module-scoped fixtures (1 AI call each)
├── test_vector_search_standard.py          # 8 tests — Standard endpoint
├── test_vector_search_storage_optimized.py # 7 tests — Storage-Optimized
├── test_vector_search_small_rag.py         # 7 tests — Small RAG chatbot
└── test_vector_search_negative.py          # 4 tests — model serving + SQL discrimination
```

## Running Sprint 6 Tests

```bash
cd "/path/to/lakemeter_app"
source .venv/bin/activate
python -m pytest tests/ai_assistant/sprint_6/ -v
```

Expected output:

```
tests/ai_assistant/sprint_6/test_vector_search_standard.py::TestVectorSearchStandard::test_workload_type PASSED
tests/ai_assistant/sprint_6/test_vector_search_standard.py::TestVectorSearchStandard::test_endpoint_type PASSED
tests/ai_assistant/sprint_6/test_vector_search_standard.py::TestVectorSearchStandard::test_capacity PASSED
...
tests/ai_assistant/sprint_6/test_vector_search_storage_optimized.py::TestVectorSearchStorageOptimized::test_endpoint_type PASSED
...
tests/ai_assistant/sprint_6/test_vector_search_small_rag.py::TestVectorSearchSmallRag::test_workload_type PASSED
...
tests/ai_assistant/sprint_6/test_vector_search_negative.py::TestVectorSearchNegativeModelServing::test_not_vector_search PASSED
tests/ai_assistant/sprint_6/test_vector_search_negative.py::TestVectorSearchNegativeSql::test_not_vector_search PASSED

26 passed in ~300s
```

## Endpoint Type Selection Logic

The AI must correctly map user requirements to vector search endpoint types:

| User Intent | Expected Type | Key Signals |
|-------------|--------------|-------------|
| Standard RAG, moderate scale | **STANDARD** | "vector search", "RAG", "embeddings", < 100M |
| Large-scale, cost-optimized storage | **STORAGE_OPTIMIZED** | "storage-optimized", "200M+", "large-scale" |
| Small chatbot, lightweight | **STANDARD** (default) | "small", "chatbot", "5M vectors" |

### Valid Endpoint Types

The AI must propose one of: `STANDARD` | `STORAGE_OPTIMIZED`

## Acceptance Criteria

All 16 acceptance criteria pass:

| AC | Description | Status |
|----|-------------|--------|
| AC-1 | Standard -> `workload_type=VECTOR_SEARCH` | PASS |
| AC-2 | Standard -> `vector_search_endpoint_type=STANDARD` | PASS |
| AC-3 | Standard -> `vector_capacity_millions` ~ 50 | PASS |
| AC-4-7 | Standard -> name, reason, notes, proposal_id | PASS |
| AC-8-9 | Storage-Optimized -> VECTOR_SEARCH + STORAGE_OPTIMIZED | PASS |
| AC-10-11 | Storage-Optimized -> capacity > 0, in range 50-500 | PASS |
| AC-12-14 | Small RAG -> VECTOR_SEARCH + capacity + valid enum | PASS |
| AC-15 | Model deployment != VECTOR_SEARCH | PASS |
| AC-16 | SQL analytics != VECTOR_SEARCH | PASS |

## Known Limitations

- AI responses are non-deterministic — capacity uses tolerant ranges (e.g., 5-500 instead of exact 50)
- Storage-optimized endpoint type check uses substring `"STORAGE"` match for robustness
- Each negative variant makes its own AI call (~30-60s each)

## Troubleshooting

| Issue | Resolution |
|-------|-----------|
| `vector_capacity_millions` out of range | The AI may interpret "50 million" differently. Widen the assertion range if the value is reasonable. |
| Storage-Optimized returns STANDARD | Ensure the prompt explicitly says "storage-optimized." The AI defaults to STANDARD without a clear signal. |
| Negative test returns VECTOR_SEARCH | Check that the prompt doesn't mention "vector", "embedding", or "RAG." |
