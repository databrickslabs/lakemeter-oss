---
sidebar_position: 3
---

# Sprint 2: ALL_PURPOSE Compute Tests

Sprint 2 validates the AI assistant's ability to propose **All-Purpose Compute** (interactive cluster) workloads and correctly distinguish them from batch JOBS workloads.

## What's Tested

### Basic ALL_PURPOSE Proposal (11 tests)

A single AI call simulates a user requesting an interactive data science cluster:

> *"I need an interactive all-purpose cluster for data science work. 8 workers, running about 8 hours a day on weekdays on AWS us-east-1."*

The test verifies all required fields:

| Field | Assertion |
|-------|-----------|
| `workload_type` | Equals `"ALL_PURPOSE"` |
| `workload_name` | Non-empty, at least 3 characters |
| `num_workers` | Present and >= 1 |
| `hours_per_month` | Present and in range 50-750 |
| `driver_node_type` | Populated |
| `worker_node_type` | Populated |
| Pricing tier | At least one pricing tier field present |
| `reason` | Populated, at least 10 characters |
| `notes` | Populated, at least 1 character |
| `proposal_id` | Present |
| `serverless_enabled` | Explicitly set |

![All Workloads Overview](/img/all-workloads-overview.png)
*The workload type selector showing All-Purpose Compute — tests verify the AI correctly selects this type for interactive use cases.*

### Edge Case: Interactive vs Batch Disambiguation (2 tests)

A separate conversation tests whether the AI correctly identifies an ambiguous request as ALL_PURPOSE rather than JOBS:

> *"I need an interactive notebook environment for ad-hoc data exploration and development."*

This is a critical edge case because:
- The prompt doesn't explicitly say "All-Purpose Compute"
- The use case (ad-hoc exploration) could theoretically be served by a JOBS workload
- The AI must recognize "interactive" and "ad-hoc" as signals for ALL_PURPOSE

The tests verify:
1. `workload_type` is `"ALL_PURPOSE"` (not `"JOBS"`)
2. `hours_per_month` is present and > 0

### Flakiness Mitigation

Sprint 2 introduced a third follow-up message for edge case prompts. The AI sometimes asks clarifying questions instead of proposing on the second message. The third message is maximally explicit:

> *"Please go ahead and propose the All-Purpose Compute workload with 4 workers, m5.xlarge instances, 132 hours per month, standard tier, no Photon. This is interactive compute, not a batch job."*

This reduces non-determinism significantly while still testing the AI's disambiguation ability on the initial prompt.

![Calculator Overview](/img/calculator-overview.png)
*The calculator page with workload configuration — ALL_PURPOSE workloads include hours-per-month and node type fields validated by these tests.*

## Running Sprint 2 Tests

```bash
cd "/path/to/lakemeter_app"
source .venv/bin/activate
python -m pytest tests/ai_assistant/sprint_2/ -v
```

Expected output:

```
tests/ai_assistant/sprint_2/test_allpurpose_proposal.py::TestAllPurposeBasic::test_workload_type PASSED
tests/ai_assistant/sprint_2/test_allpurpose_proposal.py::TestAllPurposeBasic::test_workload_name PASSED
tests/ai_assistant/sprint_2/test_allpurpose_proposal.py::TestAllPurposeBasic::test_num_workers PASSED
...
tests/ai_assistant/sprint_2/test_allpurpose_proposal.py::TestAllPurposeEdgeCases::test_interactive_maps_to_allpurpose PASSED
tests/ai_assistant/sprint_2/test_allpurpose_proposal.py::TestAllPurposeEdgeCases::test_interactive_has_hours PASSED

13 passed in ~120s
```

## Test Design: Module-Scoped Fixtures

Following the Sprint 1 pattern, expensive AI calls are shared across test methods via module-scoped fixtures:

```python
@pytest.fixture(scope="module")
def allpurpose_proposal(http_client, test_estimate):
    """Single AI call for ALL_PURPOSE — shared by all basic tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [ALLPURPOSE_PRIMARY, ALLPURPOSE_FOLLOWUP, ALLPURPOSE_FINAL],
        test_estimate,
    )
    return proposal
```

This means 11 tests share 1 AI call instead of making 11 separate calls — reducing runtime from ~10 minutes to ~1 minute.

## Known Limitations

- `hours_per_month` uses a wide assertion range (50-750) because the AI interprets "8 hours a day on weekdays" differently across runs
- Edge case prompts may occasionally need retry if the AI is unusually terse or misinterprets the request
- Each edge case variant makes its own AI call (~30-60s each)

## Troubleshooting

| Issue | Resolution |
|-------|-----------|
| Edge case returns JOBS instead of ALL_PURPOSE | AI misinterpreted the prompt. The 3-message retry handles most cases. If persistent, make the follow-up more explicit about "interactive compute." |
| `hours_per_month` out of range | The AI may calculate hours differently. Widen the assertion range if the calculated value is reasonable for the described use case. |
| Timeout on AI call | Claude FMAPI can take up to 90s on complex requests. Ensure the test timeout is set appropriately. |
