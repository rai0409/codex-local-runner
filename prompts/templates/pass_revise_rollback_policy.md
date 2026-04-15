# Pass / Revise / Rollback Policy

## Purpose
This document standardizes how implementation attempts are judged after Codex output and review.

The goal is to make the decision deterministic and consistent across runs.

## Decision classes

### PASS
Use when:
- requested task is satisfied
- scope remains narrow
- source-of-truth boundary is preserved
- no hidden execution semantics were introduced
- backward compatibility is preserved where required
- tests are aligned and sufficient
- merge risk is low

Typical action:
- add / commit / push / PR

### REVISE
Use when:
- core direction is correct
- change is salvageable from current state
- semantics are mostly correct
- issues are local and fixable with a narrow patch

Typical revise reasons:
- wording is too strong
- default behavior is not conservative enough
- compatibility handling is incomplete
- tests are too shallow
- diff is slightly broader than necessary

Typical action:
- fix from current branch state with minimal patch
- do not reset unless safety is uncertain

### ROLLBACK
Use when:
- source-of-truth boundary is violated
- inspect-derived layer gained control semantics
- hidden runtime behavior was introduced
- contract drift is large
- diff is too wide to safely salvage
- reset is safer than patching

Typical action:
- return to prior safe state
- rewrite prompt with stronger constraints
- re-run from clean baseline

### DISCARD
Use when:
- the attempt is not worth salvaging
- the prompt was poorly framed
- the task should not have been attempted yet
- the result is too noisy to trust

Typical action:
- do not merge
- do not patch
- re-scope task first

## Threshold guidance

### Pass
- no critical blocker
- no F02 / F03 / F09 / F10 taxonomy hit
- tests support the semantic claim
- branch is merge-safe

### Revise
- limited F01 / F04 / F05 / F06 / F07 / F08
- narrow patch likely fixes it
- reset not required

### Rollback
- any serious source-of-truth ambiguity
- any hidden automation drift
- any runtime / visibility boundary collapse
- patching current state is less safe than reset

## Mandatory rollback triggers
- second source of truth introduced
- inspect becomes execution trigger
- recommended_action behaves like authorization
- operator gate semantics silently changed
- advisory / execution_bridge / mode_visibility imply real runtime capability
- old payload compatibility removed without explicit approval

## Mandatory review questions
1. Did the change preserve ledger-backed authority?
2. Did the change remain read-only where expected?
3. Did the wording overstate capability?
4. Did the tests verify semantics, not just shape?
5. Is current-state patch safer than reset?
6. Is this aligned with current repository maturity?

## Output format
- decision
- reasons
- blockers
- whether current-state revise is safe
- whether reset is safer
- exact next action

## Repository-specific rule
For codex-local-runner in its current phase:
- prefer revise over expansion
- prefer rollback over semantic ambiguity
- prefer additive visibility over execution behavior