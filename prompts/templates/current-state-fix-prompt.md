Create a correction prompt for Codex based on the current branch state.

Repository: codex-local-runner

Important:
- We are not resetting the branch.
- Fix from the current state only.
- Keep the diff as small as possible.
- Do not rewrite working parts.
- Do not expand scope.
- Do not refactor unrelated code.
- Preserve all currently correct behavior.

Goal:
[PASTE WHAT IS WRONG HERE]

Current branch context:
[PASTE CURRENT IMPLEMENTATION SUMMARY HERE]

What must remain true:
- deterministic review-control-plane posture remains intact
- ledger-backed source of truth remains intact
- inspect-derived layers remain read-only
- operator_review_decision.py semantics remain unchanged unless explicitly requested
- backward compatibility remains preserved

Your task:
1. Identify the minimal correction needed.
2. Specify exact files that need edits.
3. State which current behaviors must remain untouched.
4. Generate a strict Codex correction prompt only.

Output:
- problem summary
- minimal fix scope
- files to edit
- files not to edit
- correction prompt
- validation commands