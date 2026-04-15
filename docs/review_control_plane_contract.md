# Review Control Plane Contract

## Purpose

This document defines the current contract boundaries for machine-review and inspect-derived visibility fields.

The goal is to prevent semantic drift before bounded execution or deeper automation is introduced.

## Source-of-truth rule

- The ledger is the source of truth for recorded machine-review payload location.
- The machine-review payload is the source of truth for recorded machine-review facts.
- Inspect-derived fields are derived views only.
- Inspect-derived fields must not become an independent persistence authority.

## Contract inventory

### machine_review
Top-level review visibility object shown by inspect.

Contains recorded machine-review data and inspect-derived read-only visibility.

### recommended_action
Meaning:
- review recommendation only

Allowed values:
- `keep`
- `rollback`
- `retry`
- `escalate`
- `null` when unavailable or invalid

Rules:
- does not authorize execution
- does not trigger automation by itself

### policy_version
Meaning:
- version identifier of the policy logic that produced the recommendation

Rules:
- descriptive only
- used for traceability and reproducibility

### policy_reasons
Meaning:
- deterministic reasons emitted by policy evaluation

Rules:
- basis for operator understanding
- may be reused by inspect-derived visibility
- should remain structured and stable over time

### requires_human_review
Meaning:
- explicit signal that human review remains required

Rules:
- conservative by default
- does not imply execution eligibility when false
- should remain separate from confidence-like interpretations

### retry_metadata
Meaning:
- inspect-visible summary of retry posture derived from existing recommendation facts

Shape:
- `retry_recommended`: `true | false | null`
- `retry_basis`: `string[]`
- `retry_blockers`: `string[]`

Rules:
- derived from existing machine-review facts
- additive and read-only
- backward compatible when absent

### advisory
Meaning:
- inspect-time operator aid derived from machine-review facts

Shape:
- `display_recommendation`
- `decision_confidence`
- `operator_attention_flags`
- `execution_allowed`

Rules:
- read-only
- operator-facing
- not a control signal
- `execution_allowed` visibility must not be treated as runtime authorization

### execution_bridge
Meaning:
- conservative inspect-time visibility describing whether any bounded execution eligibility is visible

Shape:
- `eligible_for_bounded_execution`
- `eligibility_basis`
- `eligibility_blockers`
- `requires_explicit_operator_decision`

Rules:
- currently conservative
- does not execute anything
- does not mutate state
- does not bridge inspect into runtime execution

### mode_visibility
Meaning:
- read-only visibility of current repository operating mode

Shape:
- `current_mode`
- `next_possible_mode`
- `mode_basis`
- `mode_blockers`

Rules:
- descriptive only
- not a runtime mode controller
- not a state transition mechanism

## Backward compatibility

If older payloads do not contain newer additive fields:
- inspect must remain conservative
- missing additive fields must resolve to safe defaults
- no missing field should be interpreted as execution permission

## Non-goals

The following are out of scope for the current contract:
- auto execution
- auto retry
- auto rollback
- merge automation
- state-machine automation
- hidden side effects

## Future extension rule

Any future execution-facing field must:
- be introduced separately from inspect-only visibility
- have explicit source-of-truth ownership
- define side effects
- define idempotency
- define preconditions / postconditions
- not overload existing read-only fields