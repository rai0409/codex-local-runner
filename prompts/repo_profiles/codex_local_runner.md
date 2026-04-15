# codex-local-runner Repo Profile

## Repository identity
codex-local-runner is currently a deterministic, ledger-backed review-control plane.

It is not yet:
- an autonomous execution engine
- a bounded execution runtime
- a policy-driven orchestration runtime

## Current goal
Strengthen the machine-review -> inspect -> operator decision flow in a deterministic, conservative, read-only-centered way.

## Current repository posture
- prefer additive changes
- prefer narrow diffs
- preserve ledger-backed source of truth
- keep inspect-derived structures read-only
- preserve explicit human operator decision boundary
- avoid premature automation

## Source-of-truth boundary
- ledger-backed machine_review_payload_path is authoritative for recorded machine-review payload location
- recorded machine-review payload is authoritative for machine-review facts
- inspect-derived layers are visibility only and not a second source of truth

## Implemented read-only layers
- retry_metadata
- advisory
- execution_bridge
- mode_visibility

## Explicit human gate
operator_review_decision.py remains the explicit human decision path unless a task explicitly changes it.

Inspect output is not:
- execution authorization
- control signal
- runtime transition trigger

## Forbidden semantic drift
Do not:
- turn recommended_action into execution authorization
- make inspect-derived fields trigger behavior
- add hidden runtime semantics
- introduce loose-file authority outside ledger
- blur runtime and visibility boundaries
- overstate current repository maturity
- silently change operator_review_decision.py semantics

## Preferred implementation style
- minimal-diff
- narrow file scope
- additive fields over contract replacement
- conservative defaults
- backward-compatible handling for old payloads where required
- tests focused on semantics and fallback behavior

## Typical high-signal files
- scripts/build_operator_summary.py
- scripts/inspect_job.py
- scripts/operator_review_decision.py
- scripts/inspect_decision_history.py
- orchestrator/ledger.py
- tests/test_build_operator_summary.py
- tests/test_inspect_job.py
- tests/test_operator_review_decision.py

## Typical validation pattern
```bash
python -m compileall <target files>
python -m unittest <relevant test modules> -v
Review standard

A good change in this repository:

strengthens deterministic review visibility
preserves ledger-backed authority
remains read-only where intended
keeps operator gate explicit
stays narrower than the task could have become
Current maturity summary

This repository is best understood as:
a strong foundation for future automation,
not yet the automation runtime itself.