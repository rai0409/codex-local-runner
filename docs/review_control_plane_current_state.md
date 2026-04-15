# Review Control Plane Current State

## Repository identity

This repository is currently a deterministic, ledger-backed review-control plane.

It is not yet:
- an autonomous execution engine
- a policy-driven execution runtime
- a fully automated software delivery orchestrator

Its current role is to make machine review output visible, structured, inspectable, and operator-safe before any bounded automation is introduced.

## Current repository posture

The repository currently prioritizes:

- deterministic machine-review generation
- ledger-backed source of truth
- inspect-time read-only derivation
- explicit human operator decision boundaries
- conservative semantics over automation speed

This means the repository is intentionally stronger on review visibility than on execution capability.

## Implemented capabilities

The following capabilities are currently present:

- machine-review payload generation
- ledger-backed machine_review_payload_path persistence
- inspect-time machine-review visibility
- retry_metadata
- advisory
- execution_bridge
- mode_visibility
- explicit human operator decision path

## Source of truth

The ledger is the source of truth for machine-review visibility.

The inspect layer reads ledger-recorded state and derives additional read-only visibility structures from existing machine-review facts. Inspect does not establish an independent source of truth.

## Current read-only derived layers

### retry_metadata
A deterministic view derived from existing recommendation facts, intended to clarify whether retry is recommended, what the basis is, and what blocks it.

### advisory
A read-only operator aid derived from existing machine-review facts, intended to summarize recommendation posture, confidence, and operator attention flags.

### execution_bridge
A read-only, conservative visibility structure intended to show whether any bounded execution eligibility is currently visible. At present it remains non-executable and conservative.

### mode_visibility
A read-only visibility structure intended to show the repository's current operating mode. At present it remains manual-review-only and does not imply runtime transition capability.

## Explicit human gate

Human decision semantics remain explicit and separate.

`operator_review_decision.py` is the decision path for explicit operator action.

Inspect output is not a control signal. Inspect-derived structures are visibility only and must not be treated as execution permission, state transition input, or runtime automation trigger.

## What is intentionally not implemented

The repository does not yet implement:

- bounded execution runtime
- automatic retry
- automatic rollback
- automatic merge
- automatic mode transition
- autonomous orchestration

## Current design boundary

The repository is intentionally designed so that:

- recommendation is not execution
- inspect visibility is not control
- derived advisory is not policy authorization
- mode visibility is not runtime mode control
- human review remains explicit

## Why this matters

This boundary is necessary because future automation should be layered on top of stable review semantics, not mixed into them prematurely.

A reliable automation system requires:
- fixed source-of-truth boundaries
- stable inspect contracts
- explicit human override points
- deterministic review outputs
- narrow, bounded execution only after those contracts are fixed

## Immediate next step

Before introducing bounded execution, the repository should fix:
- current-state documentation
- field contracts
- vocabulary
- review scoring
- pass / revise / rollback decision policy