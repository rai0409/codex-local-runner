# Codex Prompt Retry Template

## Purpose
Use this when the prior attempt was close enough to keep the current branch state, but still needs a corrected re-run.

## Repository
codex-local-runner

## Current repository posture
- deterministic, ledger-backed review-control plane
- inspect-derived layers remain read-only
- no hidden execution semantics
- operator decision path remains explicit unless explicitly changed
- current priority is contract clarity and safe visibility, not autonomy

## Original task
[paste original task here]

## What was correct in the previous attempt
- [list preserved-good parts here]

## What must be fixed now
- [list exact defects here]

## What must remain unchanged
- ledger-backed source-of-truth boundary
- read-only nature of inspect-derived structures
- operator_review_decision.py semantics unless explicitly requested
- compatibility handling already correct
- any already-correct tests or helpers

## Allowed files to modify
- [list exact files]

## Files not to modify
- [list exact files]

## Retry constraints
- keep the diff minimal
- patch current state only
- do not refactor unrelated code
- do not broaden scope
- do not add runtime execution behavior
- do not introduce a second source of truth
- do not rename existing fields unless explicitly required

## Required validation
```bash id="xq9ppx"
# paste exact commands
Required output
implementation map before edits
exact files changed and why
deterministic behavior summary
compatibility summary
commands run
test results
explicit statement that repository posture was preserved