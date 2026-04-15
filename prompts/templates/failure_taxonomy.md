# Failure Taxonomy

## F01 Scope Drift
The implementation exceeds the requested task boundary.
Examples:
- touches unrelated modules
- adds new workflow states
- broadens CLI into service/UI
Action:
- usually revise, sometimes rollback

## F02 Source-of-Truth Violation
The implementation introduces a second authority or weakens ledger-backed truth.
Examples:
- loose-file fallback becomes authoritative
- inspect derives from non-ledger source
Action:
- rollback unless trivially reversible

## F03 Hidden Execution Semantics
A read-only or visibility layer starts to imply or trigger execution.
Examples:
- advisory becomes control signal
- recommended_action acts like execution trigger
Action:
- rollback

## F04 Contract Drift
Existing payload / inspect / CLI / output contract changes without explicit requirement.
Examples:
- renamed key with no compatibility handling
- changed semantics of recorded fields
Action:
- revise or rollback depending on impact

## F05 Backward-Compatibility Failure
Old payloads, old jobs, or prior outputs are no longer handled conservatively.
Examples:
- missing retry_metadata crashes or misclassifies
- old inspect payload no longer renders safely
Action:
- revise

## F06 Weak Test Coverage
Tests pass but do not actually verify the important contract.
Examples:
- tests only check presence, not semantics
- no old-payload compatibility test
Action:
- revise

## F07 Misleading Operator Surface
Output wording implies capabilities that do not exist.
Examples:
- “eligible” sounds executable
- “approved” sounds auto-authorizing
Action:
- revise

## F08 Noisy Diff
Too many files or too much churn for a narrow change.
Examples:
- refactors mixed with feature patch
- unrelated formatting churn
Action:
- revise

## F09 Premature Automation
The patch moves toward autonomy before visibility/contract layers are fixed.
Examples:
- auto retry
- auto rollback
- scheduler-triggered actions
Action:
- rollback

## F10 Runtime / Visibility Boundary Collapse
Inspect-time derivation and runtime orchestration are blended.
Examples:
- inspect writes state
- visibility layer mutates execution path
Action:
- rollback

## Decision mapping
- pass: no critical taxonomy hit
- revise: F01/F04/F05/F06/F07/F08 in narrow form
- rollback: F02/F03/F09/F10, or severe F01/F04