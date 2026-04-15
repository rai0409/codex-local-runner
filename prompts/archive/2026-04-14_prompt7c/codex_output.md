# Codex Output Summary

## Implementation Map (Before Edits)

- codex-local-runner/scripts/build_operator_summary.py: generates machine-review payload (recommended_action, policy_*, retry_metadata) and syncs ledger path; unchanged.
- codex-local-runner/scripts/inspect_job.py: ledger-backed read-only view; already derives advisory and execution_bridge; extended here.
- codex-local-runner/scripts/operator_review_decision.py: explicit human decision path; unchanged.
- codex-local-runner/scripts/inspect_decision_history.py: read-only history; unchanged.
- codex-local-runner/orchestrator/ledger.py: source-of-truth persistence; unchanged.
- Tests reviewed: codex-local-runner/tests/test_build_operator_summary.py, codex-local-runner/tests/test_inspect_job.py, codex-local-runner/tests/test_operator_review_decision.py.

## Reused existing fields exactly
- recommended_action
- policy_version
- policy_reasons
- requires_human_review
- retry_metadata
- advisory
- execution_bridge

## What Changed
- Added inspect-time derived, read-only mode_visibility in codex-local-runner/scripts/inspect_job.py.
- Added/updated assertions in codex-local-runner/tests/test_inspect_job.py for:
  - normal JSON output includes mode_visibility
  - retry-recommendation case still conservative
  - old payload without retry_metadata
  - old payload without advisory/execution_bridge fields
  - unrecorded machine-review case

## Final mode_visibility shape

```json id="e7w30k"
{
  "current_mode": "manual_review_only",
  "next_possible_mode": null,
  "mode_basis": ["..."],
  "mode_blockers": ["..."]
}
Current deterministic behavior
current_mode: always "manual_review_only"
next_possible_mode: always null
mode_basis: small, conservative (ledger_backed_machine_review_visible when recorded, plus explicit_operator_decision_required)
mode_blockers: primarily from execution_bridge.eligibility_blockers, then advisory flags (deduped), with conservative foundational blockers retained
Exact files changed
codex-local-runner/scripts/inspect_job.py
codex-local-runner/tests/test_inspect_job.py
Commands run
python -m compileall scripts/inspect_job.py tests/test_inspect_job.py
python -m unittest tests.test_build_operator_summary tests.test_inspect_job tests.test_operator_review_decision -v
Test results
Compile: passed
Unit tests: passed
Ran 37 tests in 3.529s / OK
Explicit confirmations
Execution behavior did not change.
operator_review_decision.py semantics did not change.
This is inspect-only, ledger-backed, read-only visibility.
No control signal, no state transition, no hidden runtime bridge was introduced.
