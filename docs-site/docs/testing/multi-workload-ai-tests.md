---
sidebar_position: 12
---

# Sprint 10: Multi-Workload AI Tests (JOBS + ALL_PURPOSE + DBSQL)

Sprint 10 validates the AI assistant's ability to handle **multi-workload conversations** — a single session where the user requests multiple workload types and the AI proposes, confirms, and tracks each one across conversation turns.

## What's Tested

### Overview

| Area | File | Tests | AI Calls |
|------|------|-------|----------|
| JOBS type & fields | `test_data_platform_types.py` | ~8 | Shared |
| ALL_PURPOSE type & fields | `test_data_platform_types.py` | ~8 | Shared |
| DBSQL type & fields | `test_data_platform_types.py` | ~8 | Shared |
| Confirm flow (3 workloads) | `test_data_platform_confirm.py` | ~12 | Shared |
| Conversation state | `test_data_platform_confirm.py` | ~4 | Shared |
| **Non-AI regression** | `test_regression_s10.py` | 123 | 0 |

### Multi-Turn Conversation Flow

The AI handles a complex data platform request across multiple conversation turns:

> *"I need a data platform with daily ETL jobs, interactive notebooks for data science, and a SQL warehouse for BI"*

The test suite verifies the full lifecycle:

1. **Initial prompt** → AI proposes the first workload (e.g., JOBS)
2. **Confirmation** → Test confirms the proposal via `/confirm-workload`
3. **Continue conversation** → AI proposes the second workload (ALL_PURPOSE)
4. **Confirmation** → Second workload confirmed
5. **Continue** → AI proposes the third workload (DBSQL)
6. **Final confirmation** → All three workloads confirmed
7. **State verification** → `/state` endpoint shows 3 confirmed workloads

![Calculator overview](/img/calculator-overview.png)
*The AI assistant manages multi-workload conversations — proposing JOBS, ALL_PURPOSE, and DBSQL workloads across turns.*

### Type Verification

For each of the three workloads proposed, the tests verify:

| Workload | Key Fields Asserted |
|----------|-------------------|
| **JOBS** | `workload_type=JOBS`, `serverless_enabled`, `num_workers`, `runs_per_day`, `avg_runtime_minutes`, `days_per_month` |
| **ALL_PURPOSE** | `workload_type=ALL_PURPOSE`, `num_workers`, `hours_per_month`, `driver_node_type`, `worker_node_type` |
| **DBSQL** | `workload_type=DBSQL`, `dbsql_warehouse_type`, `dbsql_warehouse_size`, `dbsql_num_clusters` |

Each proposed workload must also include common metadata:
- `workload_name` — descriptive, non-empty
- `reason` — explanation of why this workload was proposed
- `notes` — additional context
- `proposal_id` — unique UUID for confirmation

### Confirm Flow & State Management

The confirm tests validate that:
- All 3 confirmations succeed (HTTP 200)
- Conversation state shows ≥ 3 confirmed workloads with correct types
- Each proposal has a distinct `proposal_id`
- The AI does not duplicate previously confirmed workloads

### Test Suite Timeout Fix (BUG-S10-005)

Sprint 10 also fixed a critical infrastructure bug: the default `pytest` run was timing out at 1800s because AI assistant tests (which make live FMAPI calls) were being collected.

**Root cause**: `pyproject.toml` had `testpaths = ["tests"]` without excluding `tests/ai_assistant/`.

**Fixes applied**:
1. Added `addopts = "--ignore=tests/ai_assistant"` to `pyproject.toml`
2. Added `_fmapi_reachable()` check + autouse skip fixture to `tests/ai_assistant/conftest.py`
3. Split `conftest.py` (227 lines) into `conftest.py` (106 lines) + `chat_helpers.py` (129 lines)

![Workload calculation detail](/img/workload-calculation-detail.png)
*Each confirmed workload appears in the estimate with full cost breakdown — tests verify the end-to-end confirm flow.*

**Regression tests** (4 tests in `test_regression_s10.py`):

| Test | Verifies |
|------|----------|
| `test_ai_conftest_under_200_lines` | File size compliance after split |
| `test_pyproject_ignores_ai_tests` | `addopts` excludes AI directory |
| `test_ai_conftest_has_fmapi_skip` | FMAPI skip fixture exists |
| `test_default_pytest_collects_no_ai_tests` | Default run excludes AI tests |

:::warning Important
After Sprint 10, the default `pytest` command excludes AI tests. To run AI tests explicitly:
```bash
pytest tests/ai_assistant/ --no-header --timeout=300
```
:::

## File Structure

```
tests/ai_assistant/sprint_10/
├── __init__.py
├── prompts.py                         # Multi-workload conversation prompts
├── conftest.py                        # Module-scoped fixtures, multi-turn session
├── test_data_platform_types.py        # Type + field assertions for all 3 workloads
└── test_data_platform_confirm.py      # Confirm flow + state verification

tests/ai_assistant/
├── conftest.py                        # Shared fixtures + FMAPI skip logic (106 lines)
└── chat_helpers.py                    # Extracted chat helper functions (129 lines)

tests/sprint_10/
└── test_regression_s10.py             # 123 tests — regression guards + timeout fix
```

## Running Sprint 10 Tests

```bash
cd "/path/to/lakemeter_app"
source .venv/bin/activate

# Default pytest (excludes AI tests, completes in ~9s)
pytest -v

# Sprint 10 non-AI regression tests
pytest tests/sprint_10/ -v

# Sprint 10 AI assistant tests (explicit, requires FMAPI)
pytest tests/ai_assistant/sprint_10/ --no-header --timeout=300
```

Expected non-AI output:

```
tests/sprint_10/test_regression_s10.py::TestBugS10005TestSuiteTimeout::test_pyproject_ignores_ai_tests PASSED
tests/sprint_10/test_regression_s10.py::TestBugS10005TestSuiteTimeout::test_ai_conftest_has_fmapi_skip PASSED
tests/sprint_10/test_regression_s10.py::TestBugS10005TestSuiteTimeout::test_default_pytest_collects_no_ai_tests PASSED
...

123 passed in ~3.7s
```

## Test Results

| Suite | Tests | Runtime | AI Calls |
|-------|-------|---------|----------|
| Sprint 10 non-AI regression | 123 | ~3.7s | 0 |
| Sprint 10 AI (multi-workload) | ~40 | ~5 min | 3-5 |
| Full non-AI regression | 1,409 | ~9s | 0 |

## Known Limitations

- DLT and Vector Search SKUs still use fallback pricing (real pricing data gap)
- AI assistant tests remain non-deterministic (LLM responses vary between runs)
- FMAPI reachability check uses TCP socket to port 443 (5s timeout) — doesn't verify authentication
- The AI may propose workloads in a different order than expected — tests check the set of types, not order

## Troubleshooting

| Issue | Resolution |
|-------|-----------|
| Default pytest times out | Verify `pyproject.toml` has `addopts = "--ignore=tests/ai_assistant"` |
| AI tests skip with "FMAPI unreachable" | Check network access to the Databricks workspace and FMAPI endpoint |
| Multi-turn session fails mid-conversation | AI may lose context — check if `conversation_id` is consistent across calls |
| AI proposes fewer than 3 workloads | The AI may bundle multiple workloads or ask clarifying questions — prompt escalation handles this |
