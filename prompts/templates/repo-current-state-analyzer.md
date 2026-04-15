You are analyzing the current state of my repository before any implementation work.

Repository: codex-local-runner

Current repository posture:
- This repository is not an autonomous execution engine.
- It is currently a deterministic, ledger-backed review-control plane.
- The current goal is to strengthen machine-review -> inspect -> operator decision flow in a deterministic, read-only-centered way.
- We must preserve ledger-backed source of truth.
- Inspect-derived structures must remain read-only and must not become control signals.
- operator_review_decision.py remains the explicit human decision path unless I explicitly request otherwise.

Your job:
1. Identify the repository’s current role and maturity.
2. Identify what is already implemented.
3. Identify what is not yet implemented.
4. Identify dangerous areas where a change would violate current design goals.
5. Identify likely target files for the requested task.
6. Identify forbidden files or areas unless explicitly requested.
7. Summarize the current state in a way that can be reused for a Codex prompt.

Output format:
- Repository identity
- Current implemented capabilities
- Current non-goals
- Source-of-truth boundary
- Read-only derived layers
- Explicit human gate boundary
- Likely target files
- Forbidden or high-risk files
- Recommended implementation scope
- Risks to watch

Be concrete and repository-specific. Do not give generic advice.