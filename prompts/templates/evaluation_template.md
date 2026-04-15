# Evaluation Template

## Input
- Prompt name:
- Repo:
- Branch:
- Goal:
- Scope constraints:
- Allowed files:
- Forbidden changes:

## Evidence reviewed
- Files read and why:
- Exact files changed:
- Commands run:
- Test results:
- Diff reviewed:

## Scoring (0-5 each)
### 1. Scope adherence
- Did the change stay inside the requested scope?
- Score:
- Evidence:
- Risk:

### 2. Source-of-truth protection
- Did the change preserve ledger-backed source of truth?
- Score:
- Evidence:
- Risk:

### 3. Read-only / execution boundary preservation
- Did the change avoid introducing hidden execution semantics?
- Score:
- Evidence:
- Risk:

### 4. Backward compatibility
- Did the change preserve old payload / old job / old inspect behavior where required?
- Score:
- Evidence:
- Risk:

### 5. Minimal-diff discipline
- Were file count and semantic surface kept narrow?
- Score:
- Evidence:
- Risk:

### 6. Test quality
- Are tests focused, sufficient, and aligned with the contract?
- Score:
- Evidence:
- Risk:

### 7. Operator clarity
- Is the result clearer for operators without expanding automation?
- Score:
- Evidence:
- Risk:

### 8. Merge safety
- Is this safe to merge on current branch strategy?
- Score:
- Evidence:
- Risk:

## Weighted summary
- Total score:
- Recommended decision: pass / revise / rollback / discard

## Mandatory blockers
- [ ] scope drift
- [ ] source-of-truth violation
- [ ] hidden execution path
- [ ] contract drift
- [ ] weak or misleading tests
- [ ] unsafe merge surface

## Final judgment
### Pass when
- Contract preserved
- Tests aligned
- No hidden semantics
- Diff remains narrow

### Revise when
- Core direction is correct but wording / defaults / tests / compatibility need tightening

### Rollback when
- Semantics drifted
- Repo boundary violated
- Automation leaked into read-only layer
- Source-of-truth became ambiguous

## Next action
- Accept as-is:
- Revise with minimal patch:
- Rewind to prior commit and re-prompt: