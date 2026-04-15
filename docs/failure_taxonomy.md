# Failure Taxonomy

Deterministic review policy currently emits these baseline failure codes when applicable:

- `scope_explosion`
- `touched_forbidden_file`
- `hidden_runtime_semantics`
- `contract_drift`
- `weak_backward_compat`
- `insufficient_tests`
- `prompt_noncompliance`

## Signal Mapping (High Level)

- `scope_explosion`: diff-size or scope-limit breach signals
- `touched_forbidden_file`: forbidden-path violation signals
- `hidden_runtime_semantics`: runtime-sensitive change signals
- `contract_drift`: category/contract-shape/canonical-contract drift signals
- `weak_backward_compat`: reviewer/contract-shape compatibility-risk signals
- `insufficient_tests`: required test declaration/execution/pass failures
- `prompt_noncompliance`: deterministic request-structure noncompliance

These codes are derived from structured facts only; no LLM reasoning is used.
