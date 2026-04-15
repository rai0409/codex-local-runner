md id="tya33j"
# PR Review Checklist

## Repository posture check
- [ ] Change fits current review-control-plane maturity
- [ ] Change does not assume autonomous execution
- [ ] Change does not overstate current repository capability

## Scope check
- [ ] Only intended files changed
- [ ] No unrelated refactor mixed in
- [ ] Diff is narrow and additive where expected

## Source-of-truth check
- [ ] Ledger-backed authority remains intact
- [ ] No second source of truth introduced
- [ ] Missing data falls back conservatively

## Read-only boundary check
- [ ] Inspect-derived fields remain read-only
- [ ] No control signal leaked into inspect layer
- [ ] No hidden side effects were introduced

## Explicit human gate check
- [ ] operator_review_decision semantics unchanged unless explicitly intended
- [ ] recommended_action remains recommendation, not authorization
- [ ] advisory does not imply execution permission

## Contract check
- [ ] Existing payload semantics preserved
- [ ] Existing inspect behavior preserved where required
- [ ] Backward compatibility handled for old payloads / old jobs

## Test check
- [ ] Commands are reproducible
- [ ] Tests verify semantic intent, not only presence
- [ ] Compatibility and fallback cases are covered

## Merge check
- [ ] Branch is safe to merge
- [ ] PR title/body accurately describe the narrow change
- [ ] No hidden future-facing capability implied by wording

## Final reviewer judgment
- Pass:
- Revise:
- Rollback:
- Key reason: