---
sidebar_position: 2
---

# Sprint 1: JOBS Workload Tests

Sprint 1 establishes the test infrastructure and validates the AI assistant's ability to propose **Lakeflow Jobs** workloads from natural language descriptions.

## What's Tested

### Test Infrastructure

The shared test infrastructure in `tests/ai_assistant/conftest.py` provides:

| Component | Purpose |
|-----------|---------|
| `http_client` | Session-scoped FastAPI TestClient with the real backend |
| `test_estimate` | Auto-created test estimate (AWS, us-east-1, Premium) |
| `send_chat_message()` | Send a chat message with retry on 500 errors |
| `extract_proposal()` | Parse `proposed_workload` from response or tool_results |
| `send_chat_until_proposal()` | Send multiple messages until AI proposes a workload |
| `confirm_proposal()` | Confirm a proposed workload via REST API |
| `reject_proposal()` | Reject a proposed workload via REST API |
| `get_conversation_state()` | Check conversation state (pending/confirmed workloads) |

### Classic JOBS Proposal (12 tests)

A single AI call simulates a user asking for a daily ETL job:

> *"I need a daily ETL job processing 1TB of data with 4 workers, running 10 times a day for 30 minutes each on AWS us-east-1."*

The test verifies all required fields:

| Field | Assertion |
|-------|-----------|
| `workload_type` | Equals `"JOBS"` |
| `workload_name` | Non-empty, at least 3 characters |
| `runs_per_day` | Present and > 0 |
| `avg_runtime_minutes` | Present and > 0 |
| `days_per_month` | Present and > 0 |
| `num_workers` | Present and >= 1 |
| `reason` | Populated, at least 10 characters |
| `notes` | Populated, at least 1 character |
| `proposal_id` | Present (required for confirm/reject) |
| `serverless_enabled` | Explicitly set (not null) |
| `photon_enabled` | Set when classic compute |
| Node types | `driver_node_type` or `worker_node_type` populated for classic |

![Workload Configuration](/img/workload-expanded-config.png)
*A configured JOBS workload in the calculator — the AI assistant generates equivalent configurations from natural language.*

### Serverless JOBS Proposal (3 tests)

Tests a serverless variant:

> *"I need a serverless Lakeflow Jobs workload for nightly ETL data processing."*

Verifies:
- `workload_type` is `"JOBS"`
- `serverless_enabled` is `True`
- Scheduling fields (`runs_per_day`, `avg_runtime_minutes`) are present

### Confirm/Reject Workflow (3 tests)

Each test creates its own conversation to verify:

1. **Confirm** — Proposal is accepted, returns `workload_config`
2. **State check** — Confirmed proposal is removed from pending list
3. **Reject** — Proposal is rejected, returns `"rejected"` action

## Running Sprint 1 Tests

```bash
cd "/path/to/lakemeter_app"
source .venv/bin/activate
python -m pytest tests/ai_assistant/sprint_1/ -v
```

Expected output:

```
tests/ai_assistant/sprint_1/test_jobs_proposal.py::TestJobsProposalBasic::test_workload_type_is_jobs PASSED
tests/ai_assistant/sprint_1/test_jobs_proposal.py::TestJobsProposalBasic::test_workload_name_non_empty PASSED
tests/ai_assistant/sprint_1/test_jobs_proposal.py::TestJobsProposalBasic::test_runs_per_day PASSED
...
tests/ai_assistant/sprint_1/test_confirm_flow.py::TestConfirmFlow::test_confirm_returns_config PASSED
tests/ai_assistant/sprint_1/test_confirm_flow.py::TestConfirmFlow::test_state_after_confirm PASSED
tests/ai_assistant/sprint_1/test_confirm_flow.py::TestConfirmFlow::test_reject_returns_rejected PASSED

18 passed in ~164s
```

![Estimate with Workloads](/img/estimate-with-workloads.png)
*An estimate with multiple workloads — the confirm flow creates workloads like these in the database.*

## Architecture Decision: TestClient vs Live App

The tests initially targeted the live Databricks App URL. However, the Databricks Apps proxy re-scopes OAuth tokens, removing the `model-serving` scope needed for FMAPI (Claude API calls). The solution uses FastAPI's `TestClient` which runs the backend in-process and uses the Databricks CLI token directly — this token has `all-apis` scope including `model-serving`.

## Known Limitations

- **Non-determinism**: AI may ask different clarifying questions across runs. Multi-message follow-ups mitigate this but 3 messages may not always be sufficient.
- **Confirm flow latency**: Each confirm test makes its own AI call (~30-60s each) since they need independent conversations.
- **Rate limiting**: Claude FMAPI has queries-per-hour limits. Running the full suite repeatedly may hit rate limits.

## Troubleshooting

| Issue | Resolution |
|-------|-----------|
| `AssertionError: No proposal after 2 messages` | AI asked a clarifying question. Add a more explicit follow-up message to the prompt sequence. |
| `500 status from chat endpoint` | FMAPI rate limit or transient failure. Wait 60s and retry. |
| `Failed to create estimate` | Check that the `lakemeter` CLI profile is configured and has workspace access. |
| `ModuleNotFoundError: app.main` | Ensure the backend directory is on `sys.path`. Run from the project root. |
