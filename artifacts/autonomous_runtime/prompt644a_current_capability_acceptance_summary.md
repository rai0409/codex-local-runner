# Prompt644a — Current-Capability Acceptance Run

**Status:** success
**Base:** `128d1dd` (tag `prompt643-daemon-queue-targeted-fix-retry-integration`)
**Capability classification:** **L7.5_confirmed**
**Validation-only:** no source modified.

## Baseline & tests
- HEAD `128d1dd`, tag `prompt643-daemon-queue-targeted-fix-retry-integration`; clean source tree.
- Smoke: `py_compile` + import OK (daemon, targeted_fix_retry, effect_gate, live_loop, cycle).
- Bounded tests: **21 OK** (daemon targeted-fix integration, effect-failed-blocks-commit-tag,
  targeted_fix_retry, sandbox_commit_tag_gate, live-loop effect-failed-blocks-success).

## Live /tmp acceptance (real Codex, `--max-fix-attempts 1`, `--sandbox-commit-tag`, 3 jobs)

| Task | Scenario | Effect statuses | targeted_fix | converged | status | commit/tag | queue |
|------|----------|-----------------|-------------|-----------|--------|-----------|-------|
| a-passed | passed first attempt | `[passed]` | invoked | yes (0 fix) | success | yes | done |
| b-resolved | **self-healing** | `[failed, passed]` | invoked | yes (1 fix) | success | yes | done |
| c-unresolved | always-fail verify | `[failed, failed]` | invoked | no | blocked | **no** | failed |

- **A** passed on the first attempt → success + commit/tag + done.
- **B** self-healed: attempt 0 effect **failed** (never marked success), the daemon
  automatically ran a targeted fix, the fixed effect **passed**, and commit/tag
  happened **only after** the post-retry passed effect (`post_retry_effect_gate_passed=true`).
- **C** never converged → blocked at `targeted_fix_unresolved`, **no commit/tag**,
  routed to queue **failed**, evidence preserved.

## Strict safety assertions (all hold)
- `effect_failed_wrongly_succeeded_count = 0`
- `strict_gate_violations = 0`
- unresolved task: no commit/tag ✓
- resolved task: post-retry passed effect **before** commit/tag ✓
- main repo HEAD `128d1dd` unchanged during runtime; tag at HEAD unchanged ✓
- runtime only in `/tmp` ✓
- generated-artifact leftover count = **0** ✓
- `artifacts/archive` untouched; `handoff_reports` untouched ✓
- sandbox new commits match outcome: a/b +1 (committed+tagged), c +0 (no commit/tag).

## Classification
**L7.5_confirmed** — all execution/self-healing acceptance passes (multi-task queue,
auto self-heal, strict gates, main-repo safety), with task kinds still limited to
`add_function` and the project planner/orchestrator absent. (Not `L8_candidate`
because broad task-kind support is also still missing, so the planner is not the sole
remaining major layer.)

## Confirmed capabilities
Multi-task bounded queue execution · strict effect gate (authoritative) · /tmp
sandbox isolation · commit/tag only after a passed effect · artifact cleanup ·
**daemon-integrated self-healing (auto targeted-fix retry)** · resolved→done ·
unresolved→failed with no commit/tag · main-repo runtime safety.

## Remaining gaps & next
Project intent schema, planner (goal→task decomposition), task-spec generation +
auto queue population, project completion gate + auto loop controller, broad task
kinds, long-running soak.

**Next recommended prompt:** `project_intent_schema_and_task_plan_model` — begin the
project planner stack on the now-confirmed self-healing execution layer.

> Per policy, only this validation's prompt/report/summary artifacts are committed/tagged
> for traceability; no source was changed.
