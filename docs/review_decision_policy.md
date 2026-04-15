# Review Decision Policy

The deterministic policy maps score + failure codes to exactly one recovery decision.

## Decisions

- `keep`
- `revise_current_state`
- `reset_and_retry`
- `escalate`

## Thresholds

- `keep`: `score_total >= 9.3` and no blocking failure code
- `revise_current_state`: `8.0 <= score_total < 9.3`
- `reset_and_retry`: `7.0 <= score_total < 8.0`
- `escalate`: `score_total < 7.0` or blocking failure code present

## Blocking Failure Codes

Current blocking set:

- `touched_forbidden_file`
- `hidden_runtime_semantics`
- `contract_drift`
- `prompt_noncompliance`

Blocking codes force `escalate` conservatively.

## Operator Gate

Policy output is advisory and visibility-only.
It does not trigger execution, merge, rollback, or autonomous retries.
Explicit human decision remains the execution gate.
