# Current architecture constraints

These are the current preserved constraints for new narrow PR prompts. Reuse and preserve unless a prompt explicitly says otherwise.

## Core preserved behavior
- Preserve PR63 approval safety gates and precedence.
- Preserve PR65 one-shot bounded automatic restart execution.
- Preserve PR66 narrow low-risk approval-skip gating.
- Preserve PR67 continuation-budget gating at run/objective/lane scope.
- Preserve PR68 branch-specific continuation ceilings for retry / replan / truth_gather.
- Preserve PR69 no-progress stopping and failure-bucket continuation denial.
- Preserve PR70 deterministic failure-bucket -> repair-playbook selection.
- Preserve PR71 deterministic next-step selection among retry / replan / truth_gather / supported_repair.
- Preserve PR72 one bounded supported_repair execute-verify loop.
- Preserve PR73 explicit final human-review-required gate.
- Preserve PR74 deterministic project-planning summary/compiler.

## Prompting / implementation constraints
- Prefer changing `automation/orchestration/planned_execution_runner.py` and `tests/test_planned_execution_runner.py` first.
- Touch summary / artifact / inspect surfaces only if strictly required.
- Additive changes only.
- Deterministic outputs and decisions only.
- Local-first only.
- No free-form NLP.
- No broad controller / scheduler / autopilot framework redesign.
- Preserve human-gated fallback whenever automation cannot proceed safely.

## Boundedness defaults
- Do not introduce unbounded chaining.
- Preserve one-shot bounded restart behavior unless a prompt explicitly changes it.
- Preserve existing continuation budgets / ceilings / denial precedence unless a prompt explicitly changes them.
