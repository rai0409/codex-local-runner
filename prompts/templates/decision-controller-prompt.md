Decide the next action for this codex-local-runner implementation attempt.

Repository posture:
- deterministic, ledger-backed review-control plane
- conservative, read-only-centered evolution
- no hidden runtime expansion
- explicit human decision path remains separate

Inputs:
- task goal: [PASTE]
- expected files: [PASTE]
- actual changed files: [PASTE]
- test results: [PASTE]
- review score: [PASTE]
- major review findings: [PASTE]

Decision policy:
- 9.3+ => pass / PR candidate
- 8.7 to <9.3 => pass with minor fix optional
- 8.0 to <8.7 => revise from current state
- 7.0 to <8.0 => regenerate prompt / rerun
- <7.0 => rollback/reset candidate

Output:
- chosen action
- why this action is correct
- whether current-state salvage is acceptable
- whether reset is safer
- exact next step
- if revise: what to fix
- if regenerate: what constraints to tighten
- if pass: what commit / PR scope should be