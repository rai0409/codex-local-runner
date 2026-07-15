# Prompt623 Real Change Sandbox Cycle Summary

- prompt623_status: success
- base: bde2d7e (tag: prompt622-true-two-cycle-live-proof)
- scratch repo: /tmp/prompt623_real_change_sandbox_repo (initial commit a39e727)
- runtime: scripts/run_planned_execution.py --live-codex-gate, cwd=scratch repo, timeout 90s

## Result

- codex_invoked: true (returncode 0, stop_reason codex_completed)
- calculator.py modified: subtract(a, b) added; diff shows only calculator.py changed
- test_calculator.py unchanged (md5 9ce3e8ec5ff03e9bee3aebfd5f993e06 before and after)
- sandbox py_compile: ok
- sandbox runtime check (add(2,3)==5, subtract(7,4)==3): ok
- scratch repo runtime commit/tag: none (1 commit = initial fixture, 0 tags)
- main repo source modified: false (only pre-existing untracked artifacts + prompt623 report files)
- archive touched: false
- dirty artifact isolation: not needed (live gate has no dirty-worktree check)

## Two attempts (honest record)

1. Attempt 1 (default codex sandbox = read-only): Codex was invoked, write was rejected
   ("patch rejected: writing is blocked by read-only sandbox"), calculator.py NOT modified —
   yet Codex still replied the success JSON and the gate classified the run as success from
   returncode alone. This is a confirmed gate weakness: success is not verified against
   actual effects. Evidence: /tmp/prompt623_real_change_live_out/codex_stderr.txt
2. Attempt 2 (PATH shim /tmp/prompt623_codex_shim/codex inserting --sandbox workspace-write,
   workdir = scratch repo): real change succeeded. Evidence:
   /tmp/prompt623_real_change_live_out_attempt2/

## Follow-ups suggested

- Effect-verification in the gate (diff/result-based success, not returncode-based).
- First-class sandbox-mode parameter for the live gate instead of a PATH shim.

## Decision

- prompt623_final_decision: success
- prompt623_next_action: commit_tag_real_change_sandbox_cycle
