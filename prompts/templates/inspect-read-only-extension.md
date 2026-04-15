Create a strict Codex prompt for a narrow inspect-only change in codex-local-runner.

Task type:
- inspect read-only extension

Repository posture:
- codex-local-runner is currently a deterministic, ledger-backed review-control plane.
- inspect output may derive read-only visibility from already-recorded machine-review facts.
- inspect must not become a control plane.
- inspect-derived data must not become an execution trigger.
- ledger remains the source of truth.
- operator_review_decision.py must remain unchanged.

Task request:
[PASTE TASK HERE]

Prompt requirements:
- Codex must first read current implementations of:
  - scripts/inspect_job.py
  - related tests
  - any directly referenced helper functions only if needed
- Codex must keep the change narrow and additive.
- Codex must not alter execution behavior.
- Codex must not alter ledger ownership or semantics.
- Codex must not introduce a second source of truth.
- Codex must maintain compatibility with older payloads and unrecorded cases.
- Codex must update tests for:
  - normal case
  - backward compatibility
  - conservative fallback behavior

Validation requirements:
- compile targeted files
- run only the relevant test modules first
- include exact commands

Output requirements:
- implementation map before edits
- exact files changed
- deterministic behavior summary
- explicit safety statements
- command results summary