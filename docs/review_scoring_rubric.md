# Review Scoring Rubric

This repository uses a deterministic scoring layer for machine-review policy.

## Output Contract

Policy output includes:

- `score_total` (`0.0` to `10.0`)
- `dimension_scores.correctness` (`0.0` to `4.0`)
- `dimension_scores.scope_control` (`0.0` to `2.0`)
- `dimension_scores.safety` (`0.0` to `2.5`)
- `dimension_scores.repo_alignment` (`0.0` to `1.5`)
- `failure_codes` (deterministic list)
- `recovery_decision` (`keep|revise_current_state|reset_and_retry|escalate`)
- `decision_basis` (deterministic reasons)
- `requires_human_review` (always `true` in current operator-gated mode)

`score_total` is the exact sum of dimension scores.

## Deterministic Inputs

The score uses structured facts only:

- canonical `result.json.execution` status and verify fields
- `rubric.json` booleans, warnings, fail reasons
- `merge_gate.json` pass/fail reasons
- ledger rollback trace / rollback execution facts
- category and artifact-backed job metadata
- deterministic changed-file and diff signals when available

Unknown/missing facts degrade score conservatively.
