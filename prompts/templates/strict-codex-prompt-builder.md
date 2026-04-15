Build a strict Codex implementation prompt for my repository.

Repository: codex-local-runner

Repository constraints:
- This repository is currently a deterministic, ledger-backed review-control plane.
- Do not turn inspect-derived structures into control signals.
- Do not add hidden runtime behavior.
- Do not change execution semantics unless explicitly requested.
- Preserve ledger-backed source of truth.
- Preserve backward compatibility wherever possible.
- Prefer minimal, additive, narrow changes.
- operator_review_decision.py must remain unchanged unless explicitly requested.
- Do not broaden scope.
- Do not refactor unrelated code.
- Do not invent a new architecture.
- Do not introduce a second source of truth.

Task:
[PASTE TASK HERE]

What I want from you:
1. Write a production-grade Codex prompt.
2. Make it very strict and minimal-diff.
3. Force Codex to read the current code first.
4. Require Codex to state exact files to change.
5. Require Codex to explain why those files are sufficient.
6. Require compile/test commands.
7. Require backward compatibility.
8. Require a final implementation map and exact change summary.
9. Require Codex not to modify files outside the approved scope.
10. Require Codex to keep the repository aligned with its current review-control-plane role.

Output format:
- Title
- Objective
- Repository context
- Hard constraints
- Files to read first
- Allowed files to modify
- Files that must remain unchanged
- Implementation requirements
- Backward compatibility requirements
- Validation commands
- Output requirements
- Refusal conditions if the task would violate constraints

Do not implement the task yourself. Only generate the Codex prompt.