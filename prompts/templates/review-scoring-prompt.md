Review the implementation result for codex-local-runner and score it rigorously.

Repository posture:
- deterministic, ledger-backed review-control plane
- inspect-derived structures must remain read-only
- no hidden execution semantics
- preserve source-of-truth boundaries
- preserve explicit human decision boundaries

Task goal:
[PASTE TASK GOAL HERE]

Expected files:
[PASTE EXPECTED FILES HERE]

Forbidden or high-risk files:
[PASTE FORBIDDEN FILES HERE]

Implementation result:
[PASTE IMPLEMENTATION MAP / DIFF SUMMARY / TEST RESULTS HERE]

Score using this rubric out of 10:
- Correctness: 3.0
- Scope control: 2.0
- Safety: 2.5
- Maintainability: 1.0
- Repo alignment: 1.5

You must output:
- total score
- sub-scores
- what is good
- what is risky
- whether to:
  - pass
  - pass with minor fix
  - revise from current state
  - regenerate
  - rollback/reset
- exact reasons for that decision
- whether current-state fix is safe or reset is safer

Be strict and repository-specific.