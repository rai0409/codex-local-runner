Create a strict Codex prompt for a clean re-run after reset.

Repository: codex-local-runner

We are not salvaging the current branch state.
Assume the previous attempt drifted too far or became unsafe.

Repository posture to preserve:
- deterministic, ledger-backed review-control plane
- inspect-derived layers are read-only only
- no hidden runtime semantics
- no execution-path expansion unless explicitly requested
- preserve backward compatibility
- keep operator_review_decision.py unchanged unless explicitly requested

Original task:
[PASTE TASK HERE]

Failure reasons from the previous attempt:
[PASTE FAILURE SUMMARY HERE]

Your job:
- generate a fresh Codex prompt for a clean implementation
- explicitly prevent the prior failure pattern
- constrain file scope tightly
- require code reading first
- require exact validation commands
- require an implementation map before edits

Output:
- fresh implementation strategy
- failure prevention constraints
- allowed files
- forbidden files
- strict Codex prompt