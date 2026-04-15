# Review Control Plane Vocabulary

## recommendation
A suggested operator-facing action derived from machine-review logic.

Recommendation is not execution.

## policy
Deterministic logic that evaluates review inputs and emits recommendation-oriented outputs.

## policy_reasons
Structured reasons emitted by policy logic to explain review outcomes.

## requires_human_review
A conservative signal that explicit human review remains required.

## inspect-derived
A read-only value computed at inspect time from already-recorded machine-review facts.

## source of truth
The authoritative storage layer for a given fact.

In this repository:
- ledger is the source of truth for recorded payload location
- recorded payload is the source of truth for machine-review facts
- inspect-derived values are not a source of truth

## retry
A recommendation posture indicating a retry may be appropriate.

Retry is not automatic execution.

## rollback
A recommendation posture indicating rollback may be appropriate.

Rollback is not automatic execution.

## escalate
A recommendation posture indicating human escalation is appropriate.

## advisory
An operator-facing summary layer derived from existing facts.

Advisory is not policy authorization.

## confidence
A visibility concept describing how cautiously a recommendation should be read.

Confidence is not execution eligibility.

## execution eligibility
A distinct concept describing whether a bounded runtime action is allowed to proceed.

This is not yet implemented as runtime behavior in the current repository.

## execution_bridge
A conservative read-only visibility layer summarizing bounded execution posture, without performing execution.

## mode_visibility
A read-only layer summarizing current operating mode posture.

It is not a runtime state machine.

## explicit human gate
A boundary where human decision remains required.

In this repository, explicit operator decision semantics are intentionally separate from inspect visibility.

## bounded execution
A future concept in which only narrowly defined, low-risk actions may execute under strict policy and audit constraints.

This is not yet the current repository posture.

## autonomous orchestration
A future concept in which planning, execution, review, retry, and integration are coordinated automatically.

This is not yet implemented.