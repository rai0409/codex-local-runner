# Prompt628-636 Daemon Candidate Program Summary

- program_status: success
- base: c32d90f (tag: prompt626-reproducible-acceptance-fixture), HEAD unchanged
- maturity: L4 -> **L7 (first local daemon candidate)** — with L8 partially covered
  (synthetic crash-resume + locking proven; mid-cycle resume not implemented)
- live Codex invocations: 6, all bounded (90s timeouts, capped cycles/attempts)
- main repo: no commit, no tag, no staging, no runtime modification; archive untouched

## Phase results (all 9 succeeded)

| Phase | Capability | Proof | Score |
|---|---|---|---|
| 628 | failure digest (15 classes) wired into gate/loop/acceptance | unit tests, no codex | 94 |
| 629 | offline fix prompt builder | unit tests, no codex | 94 |
| 630 | live targeted-fix retry | induced fail -> digest -> fix prompt -> converged in 1 attempt | 95 |
| 631 | sandbox-only commit/tag gate (7 policies) | real /tmp commit+tag + 5 refusal proofs | 93 |
| 632 | verify_commands test layer (allowlisted argv) | unit tests incl. pre-codex blocking | 91 |
| 633 | real-repo clone acceptance | codex created exact marker in full clone, tests ran, no commits | 88 |
| 634 | task spec + planner v1 | spec-only live run, no hand-written prompt | 93 |
| 635 | bounded queue daemon | full chain live: enqueue->plan->loop->verify->sandbox commit/tag->done | 93 |
| 636 | crash resume/lock/logs | synthetic interrupted state recovered; contention refused | 94 |

## Final daemon candidate acceptance (live, passing)

`python scripts/run_daemon_candidate_acceptance.py --json` -> acceptance_status=success:
1 queued task processed bounded; codex invoked once; effect+test verification passed;
sandbox repo got subtract + commit + tag `sandbox-daemon-acceptance-subtract`; queue moved
to done/; lock released; JSONL log, daemon state, and run reports persisted; main repo
status and HEAD identical before/after.

Honest note: the first acceptance run blocked at the commit policy because the verify
command's `__pycache__` tripped the strict allowlist — fixed by excluding Python bytecode
caches as generated artifacts (new unit test), then re-proven clean.

## Tests

70/70 program tests across 12 modules; full suite 556 tests with only the known
pre-existing import error in tests/test_planned_execution_runner.py (untouched module).

## Explicitly NOT commercial-grade

Single task kind (add_function), fixture-grade /tmp changes only, main-repo modification
still gated, foreground-only daemon, no mid-cycle resume, single-run reliability evidence,
intent tokens are not auth, plaintext prompt/stdout storage, no packaging/config/multi-user,
nested read-only environments unsupported, legacy debt remains.

## Decision

- final_decision: success
- next_action: commit_tag_daemon_candidate_program
