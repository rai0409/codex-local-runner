# Current architecture constraints

Compressed source of truth for narrow PR prompts.
Keep the full historical version separately for audit/recovery.

## Architecture summary through PR124

The system is a deterministic, local-first, bounded autonomous-development runner.

Preserve PR63+ safety behavior:
- Safety, approval, manual override, safe-stop, human-review, and insufficient-truth gates override automation.
- Human fallback must remain available whenever automation cannot proceed safely.
- Outputs and control decisions must be deterministic and compact.
- Do not add broad controller, scheduler, or autopilot redesign unless explicitly scoped.

Preserve PR91+ browser-orchestrator foundation:
- Browser/task state is compact and machine-readable.
- Metadata-only layers do not imply browser execution.
- Browser execution may occur only through explicitly scoped bounded execution paths.
- Do not infer prompt send, DOM interaction, response read, recovery, retry, or continuation from metadata receipts.

Preserve PR109+ autonomous-development metadata pipeline:
- Assimilation, draft, continuation, controller, ledger, safety, bridge, budget, wrapper, batch evaluation, rolling gate, operation contract, invocation, dispatcher, executor readiness, and execution adapter layers are deterministic and bounded.
- Metadata-only receipts never imply execution.
- Each new layer should emit compact status/kind/permission/source/block/receipt/runtime posture fields when relevant.
- Each new layer should emit exactly one receipt.

Preserve PR116+ budget policy:
- Normal controller max steps is 3.
- Hard limit 5 is metadata-only unless explicitly changed.
- max_failures=2.
- same_prompt_retry_limit=2.
- Budget exhaustion, cooldown, loop risk, duplicate risk, pause, human_review, insufficient_truth, and manual override stop continuation.

Preserve PR121+ no-approval thresholds:
- Standard no-approval continuation requires score>=92 plus extra hard gates clear.
- Simple low-risk path may use score>=90 only when simple-task gates are clear.
- Scores must not bypass hard gates.

Preserve PR124 execution adapter boundary:
- PR124 maps executor candidates to md/browser enqueue adapter candidates.
- Low risk may become executable_candidate.
- Standard risk may become execution_ready_candidate.
- High risk must block or require human_review.
- PR124 itself must not execute, send, enqueue, write, call Codex, drain queues, mutate counters, or loop.

## Detailed preserved behavior from PR125 onward

### PR125 constrained `.md` actual apply

PR125 is the first low-risk actual execution path.

Preserve:
- PR125 may consume one PR124 low-risk `md_update_apply_candidate`.
- PR125 may apply at most one deterministic context `.md` write.
- Allowed targets:
  - `prompts/context/pr_history_index.md`
  - `prompts/context/current_architecture_constraints.md`
- Structured md update payload is required.
- Target, duplicate, anchor, and diff-scope checks must pass.
- Duplicate already present becomes skipped duplicate_noop receipt with no write.
- Missing structured payload, disallowed target, missing anchor, or too-large diff must block.
- No shell command may be used for the write path.
- Preserve fields with prefix:
  - `project_browser_autonomous_md_apply_*`

PR125 must not:
- send prompts
- enqueue or execute browser actions
- perform Playwright/DOM actions
- execute Codex
- execute shell commands
- mutate queue/retry/repair/restart/approval/continuation/counter/project state
- sleep, schedule, loop, or start background runtime

Do not infer prompt send, browser enqueue, browser execution, Codex execution, retry execution, continuation execution, scheduled retry, counter mutation, or multi-step autonomous operation from PR125 md apply metadata.

### PR126 browser command enqueue preparation

PR126 is metadata/prepared-envelope only.

Preserve:
- PR126 may consume one PR124 standard-risk browser enqueue candidate.
- PR126 emits exactly one browser enqueue receipt.
- It prepares:
  - `enqueue_next_prompt_command`
  - `enqueue_retry_same_prompt_command`
- Duplicate prompt becomes skipped duplicate_noop receipt with no new envelope.
- Missing, empty, or too-large prompt payload blocks.
- Retry budget exhausted blocks retry enqueue.
- PR126 must not create a new browser queue implementation.
- If no explicit browser command queue metadata path exists, emit metadata-only enqueue receipt.
- Do not store full prompt text in new PR126 fields; use existing structured prompt payload surfaces only.
- Preserve fields with prefix:
  - `project_browser_autonomous_browser_enqueue_*`

PR126 must not:
- execute browser
- launch Playwright
- touch DOM
- send prompt / send click
- wait/read response
- execute Codex
- write `.md`
- execute shell
- drain queues
- mutate retry/repair/restart/approval/continuation/counter/project state
- sleep, schedule, loop, or start background runtime

Do not infer prompt send, browser execution, response read, Codex execution, applied md updates, retry execution, continuation execution, scheduled retry, counter mutation, or multi-step autonomous operation from PR126 browser enqueue metadata.

### PR127 bounded browser one-command actual execution

PR127 is the bounded browser execution path.

Preserve:
- PR127 may consume exactly one PR126 prepared browser command envelope.
- PR127 may execute exactly one browser command:
  - `send_next_prompt`
  - `retry_same_prompt`
- It uses existing browser primitives for launch/page/selector/fill/send/one wait-read.
- It emits one browser execution receipt.
- Preserve fields with prefix:
  - `project_browser_autonomous_browser_execution_*`

PR127 limits:
- one command only
- no queue drain
- no second command
- no Codex execution
- no `.md` write
- no shell command execution
- no retry/repair/restart/approval/continuation/counter/project-state mutation
- no loop/background runtime

PR127 safety:
- duplicate prompt blocks with no send
- retry budget exhausted blocks retry
- login interruption pauses
- selectors not ready block
- prompt missing/empty/too-large blocks
- response timeout emits timeout receipt
- response empty emits blocked/failed receipt
- response too large must not store broad response text
- never store credentials, cookies, tokens, auth/session values, broad DOM text, or broad response text

Do not infer Codex execution, applied md updates, retry execution, continuation execution, scheduled retry, counter mutation, queue drain, second-command execution, or multi-step autonomous operation from PR127 browser execution metadata.

### PR128 browser result assimilation and Codex candidate

PR128 is metadata-only.

Preserve:
- PR128 consumes exactly one PR127 browser execution receipt.
- PR128 emits at most one Codex invocation candidate receipt.
- It classifies browser result usability and bounded structured implementation handoff.
- It may classify retry-browser candidate posture.
- Preserve fields with prefix:
  - `project_browser_autonomous_result_assimilation_*`
  - `project_browser_autonomous_codex_invocation_*`

PR128 Codex candidate policy:
- PR128 must not execute Codex.
- PR128 must not run shell commands.
- PR128 must not write files.
- PR128 must not synthesize Codex prompts from raw/free-form response text.
- PR128 may only use existing structured/bounded implementation handoff payloads by id/fingerprint.
- PR128 must not store or forward broad response text into new candidate fields.
- Missing structured handoff payload blocks with `codex_prompt_missing` or `insufficient_truth`.
- Empty, timeout, or too-large responses must not become Codex-ready candidates.
- Candidate requires bounded scope, compact token posture, no-tests policy enforced, and upstream gates clear.
- Multiple Codex candidate payloads block with insufficient_truth or candidate_not_ready.

Do not infer Codex execution, shell execution, applied md updates, prompt send, browser enqueue/execution, response wait/read, retry execution, continuation execution, scheduled retry, counter mutation, or multi-step autonomous operation from PR128 result-assimilation metadata.

### PR129 bounded one-Codex-execution path

PR129 is the only bounded Codex execution path in this phase.

Preserve:
- PR129 may consume exactly one PR128 ready Codex invocation candidate.
- PR129 may execute exactly one Codex attempt.
- `max_attempts=1`.
- No second Codex attempt.
- No repair loop.
- No retry loop.
- No tests, validation commands, or sanity checks.
- No arbitrary shell execution outside existing bounded Codex adapter.
- No new subprocess/shell execution owner.
- If bounded Codex adapter is unavailable, block with candidate_not_ready or insufficient_truth.
- Multiple Codex candidates block with candidate_not_ready or insufficient_truth.
- Preserve fields with prefix:
  - `project_browser_autonomous_codex_execution_*`

PR129 must not:
- perform browser action
- send prompts or browser enqueue
- write `.md`
- mutate queue/retry/repair/restart/approval/continuation/counter/project state
- perform git commit/push/PR creation/merge/GitHub mutation
- sleep, schedule, loop, or start background runtime

Do not infer tests, validation, repair execution, retry execution, browser execution, applied md updates, continuation execution, scheduled retry, counter mutation, git/github mutation, or multi-step autonomous operation from PR129 Codex execution metadata.

### PR130 Codex result assimilation

PR130 is metadata-only.

Preserve:
- PR130 consumes one PR129 Codex execution receipt.
- PR130 emits one post-Codex result receipt.
- PR130 executes nothing.
- Preserve fields with prefix:
  - `project_browser_autonomous_codex_result_*`

PR130 result policy:
- `succeeded + files_changed=changed` -> `ready_for_ledger_update`
- `succeeded + files_changed=none` -> `needs_review` / `ready_for_validation_planning`
- `failed/timeout` -> retry/repair candidate metadata only; no retry/repair execution
- tests attempted despite instruction -> block with `tests_policy_violation`
- too many files changed -> block or human_review with `files_changed_too_many`

PR130 must not:
- execute Codex
- run tests, validation, sanity, or shell commands
- perform browser action, prompt send, browser enqueue, or `.md` write
- mutate queue/retry/repair/restart/approval/continuation/counter/project state
- perform git/GitHub mutation
- loop or start background runtime

Do not infer validation, retry, repair, counter update, git/GitHub mutation, or multi-step operation from PR130 metadata.

### PR131 run ledger / counter persistence

Preserve:
- PR131 consumes one PR130 result receipt.
- PR131 emits one ledger/counter receipt.
- PR131 preserves fields with prefix:
  - `project_browser_autonomous_run_ledger_*`

Event/delta policy:
- success+changed -> step_delta=1, failure_delta=0
- success+no_change -> step_delta=1, failure_delta=0
- failed/timeout -> step_delta=1, failure_delta=1
- blocked/pause/human_review/insufficient -> no counter increment unless mirrored metadata requires otherwise

PR131 requirements:
- Build duplicate-safe event fingerprints from compact safe fields only.
- Persist only through an existing explicit ledger/counter persistence path.
- If no explicit persistence path exists, emit prepared metadata-only.
- Do not create a new store.
- Downstream PRs must not treat PR131 prepared metadata-only as persisted counters.

PR131 must not:
- execute Codex/browser/prompt/md/shell/test/git/GitHub actions
- mutate queue/retry/repair/restart/approval/continuation/project state
- run batch loop/background runtime

### PR132 short-batch runner

Preserve:
- PR132 may run at most 3 autonomous steps through existing bounded paths only.
- `hard_limit=5` is metadata-only and must not allow more than 3 steps.
- PR132 must re-check PR114 safety, PR119 cooldown/loop, PR120 contract, and PR131 ledger/counter posture before each step.
- PR132 must not treat PR131 prepared metadata-only as persisted counters.
- Preserve fields with prefix:
  - `project_browser_autonomous_short_batch_*`

Stop conditions:
- max_steps_reached
- budget_exhausted
- failure_budget_exhausted
- retry_budget_exhausted
- cooldown_required
- loop_suspected
- duplicate_detected
- ledger_not_persisted
- pause_required
- human_review_required
- insufficient_truth

PR132 no-long-running posture:
- no fourth step
- no queue drain
- no long-running daemon/background runtime
- no scheduler redesign
- no git/GitHub mutation
- no tests/validation/sanity commands

Do not infer browser availability, DOM availability, login/session availability, or ChatGPT UI availability from PR92 metadata.
Do not infer browser send completion, browser response availability, DOM availability, login/session availability, or ChatGPT UI availability from PR93 prompt payload metadata.
Do not implement real Playwright execution, DOM interaction, browser send/read, login/session recovery, page reload, or new-chat execution unless a later prompt explicitly scopes it.
Future browser-orchestrator PRs should reuse PR91-PR136 compact fields instead of introducing a second browser state owner.


### PR133 resume checkpoint / watchdog

- Preserve PR133 resume checkpoint/watchdog metadata layer: consume PR132 short-batch, PR131 ledger/counter, PR119 cooldown/loop, and safety/manual-stop posture; emit exactly one resume/watchdog receipt; expose compact fields in normalization/defaults, compact summary, supporting truth refs, and final approved restart execution contract payload; keep metadata-only, no next-batch start, no resume execution, no browser/Codex/md/shell/queue/git/GitHub execution; treat `short_batch_stop_reason=none` as blocked with `short_batch_not_stopped_safely`, not resumeable.

PR133 requirements:
- `project_browser_autonomous_resume_*` and `project_browser_autonomous_watchdog_*` are compact deterministic fields.
- PR133 may create checkpoint/watchdog metadata only.
- PR133 must not start the next short batch.
- PR133 must not execute resume.
- PR133 must not mutate queue/retry/repair/restart/approval/continuation/counter/project state.
- PR133 must not run tests, validation commands, shell writes, browser actions, Codex execution, git/GitHub mutation, daemon, or scheduler.
- `short_batch_stop_reason=max_steps_reached` may allow `resume_next_short_batch_later` only when ledger is persisted and watchdog/gates are clear.
- `short_batch_stop_reason=none` must not allow `resume_from_checkpoint`; it must be blocked as `short_batch_not_stopped_safely`.

### PR134 bounded rolling controller candidate

- Preserve PR134 bounded rolling controller candidate metadata layer.
- PR134 consumes PR133 resume/watchdog fields, PR132 short-batch posture, PR131 ledger/counter posture, and PR119 cooldown/loop posture.
- PR134 emits compact deterministic `project_browser_autonomous_rolling_controller_*` fields.
- PR134 exposes rolling controller fields through normalization/defaults, compact planning summary, supporting truth refs, and final approved restart execution contract payload.
- PR134 may emit `prepared` only when:
  - PR133 resume permission is `allowed_candidate`
  - PR133 resume next action is `resume_next_short_batch_later`
  - PR133 watchdog is clear
  - PR132 short-batch stop reason is `max_steps_reached`
  - PR131 ledger/counter posture is persisted
  - PR119 cooldown is `not_required`
  - PR119 loop risk is `clear`
- PR134 must block or mirror pause/human_review/insufficient/stale/missing/duplicate/manual-stop/cooldown/loop/ledger-not-persisted postures.
- PR134 must not start the next short batch.
- PR134 must not execute resume.
- PR134 must not create a daemon/background scheduler.
- PR134 must not drain queues, mutate counters/project state, execute browser/Codex/md/shell actions, run tests/validation/sanity, or perform git/GitHub mutation.
- PR134 prepared state means candidate only:
  - `project_browser_autonomous_rolling_controller_next_action=prepare_next_short_batch_later`
  - no actual continuation execution is implied.

### PR135 bounded rolling continuation launcher

- Preserve PR135 bounded rolling continuation launcher metadata layer.
- PR135 consumes PR134 rolling controller fields, PR133 resume/watchdog fields, PR132 short-batch posture, and PR131 ledger/counter posture.
- PR135 emits compact deterministic `project_browser_autonomous_rolling_continuation_*` fields.
- PR135 exposes rolling continuation fields through normalization/defaults, compact planning summary, supporting truth refs, and final approved restart execution contract payload.
- PR135 may emit `prepared` only when:
  - PR134 rolling controller status is `prepared`
  - PR134 rolling controller permission is `allowed_candidate`
  - PR134 rolling controller source status is `valid`
  - PR134 rolling controller receipt status is `ready`
  - PR134 rolling controller next action is `prepare_next_short_batch_later`
  - PR133 resume permission is `allowed_candidate`
  - PR133 resume next action is `resume_next_short_batch_later`
  - PR133 watchdog is clear
  - PR132 short-batch stop reason is `max_steps_reached`
  - PR131 ledger/counter posture is persisted
- PR135 prepared state means launcher metadata only:
  - `project_browser_autonomous_rolling_continuation_next_action=launch_one_short_batch_later`
  - `project_browser_autonomous_rolling_continuation_launch_mode=bounded_one_short_batch`
  - `project_browser_autonomous_rolling_continuation_max_next_batch_steps=3`
- PR135 must block or mirror pause/human_review/insufficient/stale/missing/duplicate/manual-stop/ledger-not-persisted postures.
- PR135 must not start the next short batch.
- PR135 must not execute rolling continuation.
- PR135 must not create a daemon/background scheduler.
- PR135 must not drain queues, mutate counters/project state, execute browser/Codex/md/shell actions, run tests/validation/sanity, or perform git/GitHub mutation.
- `launch_one_short_batch_later` is metadata only and does not imply execution.

### PR136 bounded rolling multi-launch gate

- Preserve PR136 bounded rolling multi-launch gate/runner metadata layer.
- PR136 consumes PR135 rolling continuation fields, PR132 short-batch posture, PR131 ledger/counter posture, cooldown/loop posture, watchdog posture, and short-batch invocation-path posture.
- PR136 emits compact deterministic `project_browser_autonomous_rolling_multi_launch_*` fields.
- PR136 exposes rolling multi-launch fields through normalization/defaults, compact planning summary, supporting truth refs, and final approved restart execution contract payload.
- PR136 hard limits:
  - `project_browser_autonomous_rolling_multi_launch_max_launches=2`
  - `project_browser_autonomous_rolling_multi_launch_per_launch_max_steps=3`
  - `project_browser_autonomous_rolling_multi_launch_total_step_budget=6`
  - `project_browser_autonomous_rolling_multi_launch_failure_budget=1`
  - no third launch
  - no unbounded loop
  - no daemon/background scheduler
  - no sleep loop
  - no arbitrary queue drain
- PR136 may emit `prepared` with `next_action=launch_up_to_two_short_batches` only when:
  - PR135 rolling continuation is prepared/allowed/ready
  - PR135 next action is `launch_one_short_batch_later`
  - launch mode is `bounded_one_short_batch`
  - ledger/counter posture is persisted
  - cooldown is `not_required`
  - loop risk is `clear`
  - watchdog is clear
  - duplicate status is clear
  - short-batch invocation path is `available`
- Current PR136 behavior must block actual launch with `short_batch_invocation_path_unavailable` while:
  - `project_browser_autonomous_short_batch_invocation_path_status=unavailable`
- PR136 must not fake execution, infer execution from metadata, create a new browser/Codex executor, create a new ledger persistence mechanism, create a daemon/scheduler, drain queues, or perform git/GitHub mutation.
- PR137+ must provide an explicit bounded short-batch invocation adapter before PR136 can become actual multi-launch.

## Default PR style for PR133+

- One PR = one helper / one layer.
- Additive changes only.
- Preferred editable file:
  - `automation/orchestration/planned_execution_runner.py`
- Preserve existing PR59+ behavior unless the prompt explicitly says otherwise.
- Do not create new modules unless explicitly scoped.
- Do not edit tests unless explicitly scoped.
- Do not run tests, validation commands, or sanity checks unless explicitly scoped.
- Do not edit `prompts/context/*.md` from Codex unless explicitly using constrained PR125 md-apply.
- Use compact deterministic enum/int fields.
- Use prefix:
  - `project_browser_autonomous_<layer>_*`
- Include when relevant:
  - status
  - kind
  - permission
  - source_status
  - block_reason
  - receipt_status
  - receipt_kind
  - runtime_posture
- Emit exactly one receipt.
- Wire new layers into existing normalization/defaults, compact planning summary, supporting truth refs, and final approved restart execution contract payload when those surfaces exist.
- Do not store broad free-form text, broad DOM text, broad response text, credentials, cookies, tokens, auth/session values, or secrets.
- Do not add a new persistence store unless explicitly scoped.
- Do not treat metadata-only prepared state as persisted state.
- Do not infer execution from metadata receipts.

## Default forbidden actions for PR133+

Unless explicitly allowed by the current PR, do not add:
- new Codex execution
- browser execution
- Playwright launch
- DOM interaction
- prompt send
- browser enqueue
- `.md` write
- shell execution
- test execution
- validation command execution
- sanity command execution
- queue drain
- retry execution
- repair execution
- restart execution
- approval execution
- continuation execution
- counter mutation
- project-state mutation
- git commit
- git push
- PR creation
- auto merge
- GitHub mutation
- long-running daemon
- background scheduler
- unrelated refactor

## Codex usage reduction / access policy for PR133+

- Codex is used for code modification only.
- Codex output should normally be one line only:
  - `done`
  - `blocked:<short_reason>`
  - `failed:<short_reason>`
- Do not ask Codex for long summaries, implementation reports, validation explanations, PR evaluations, or broad investigation reports.
- Evaluate Codex runs from saved local artifacts instead of Codex prose:
  - diffstat
  - changed files
  - patch
  - symbol extraction
  - forbidden-pattern scan
  - compact receipt
- Prefer relative repo paths rooted at `codex-local-runner`.
- Do not use absolute filesystem paths as the only editable target unless the environment explicitly requires it.
- Preferred editable file for narrow autonomous PRs:
  - `automation/orchestration/planned_execution_runner.py`
- Codex may edit the preferred file only through normal patch/edit.
- Direct patch/edit of the preferred file is allowed and is not shell execution.
- Shell execution remains forbidden unless explicitly permitted.
- Codex must treat `prompts/context/*.md` as read-only source of truth unless the PR explicitly uses constrained PR125 md-apply.
- `.md` updates are performed outside Codex by ChatGPT/local Python or by the existing constrained md-apply path.
- Codex prompts should use contract-style instructions, not long natural-language explanations.
- Codex must not search repository-wide by default.
- Allowed search is only inside the preferred file for existing symbols, helper patterns, normalization/defaults wiring, compact summary wiring, supporting truth refs, and final payload wiring.
- If required symbols are missing from the preferred file, return `blocked:missing_symbols` or `blocked:missing_pr_symbols` unless the prompt explicitly allows a narrow fallback.
- If the preferred file cannot be edited through normal patch/edit, return `blocked:preferred_file_unavailable`.
- Do not create new modules, edit tests, run tests, run validation commands, run sanity checks, or refactor unrelated code.
- Do not introduce a new execution owner unless the PR explicitly permits actual execution.

## Local evaluation artifacts

After each Codex run, prefer local artifacts:
- `artifacts/pr_runs/PRxxx/diffstat.txt`
- `artifacts/pr_runs/PRxxx/files.txt`
- `artifacts/pr_runs/PRxxx/patch.diff`
- `artifacts/pr_runs/PRxxx/scan.json`
- `artifacts/pr_runs/PRxxx/receipt.txt`

Use compact local report first.

Review full patch only when:
- scan flags risk
- changed files are unexpected
- forbidden patterns are detected
- compact report is insufficient
- the PR touches execution, persistence, browser, Codex, queue, git/GitHub, or scheduler behavior

---

## PR137 Architecture Constraint — short-batch invocation adapter

PR137 introduced the short-batch next_action invocation adapter in:

```text
automation/orchestration/planned_execution_runner.py
```

Primary builder:

```text
_build_project_browser_autonomous_short_batch_invocation_state
```

Important fields:

```text
project_browser_autonomous_short_batch_invocation_status
project_browser_autonomous_short_batch_invocation_permission
project_browser_autonomous_short_batch_invocation_receipt_status
project_browser_autonomous_short_batch_invocation_path_status
project_browser_autonomous_short_batch_invocation_runtime_capability
project_browser_autonomous_short_batch_invocation_next_action
project_browser_autonomous_short_batch_invocation_delegation_mode
project_browser_autonomous_short_batch_invocation_call_path_ref
project_browser_autonomous_short_batch_invocation_missing_inputs
```

Verified next_action call-path refs:

```text
run_one_md_apply        -> project_browser_autonomous_md_apply_state
run_one_browser_command -> project_browser_autonomous_browser_execution_state
run_one_codex_attempt   -> project_browser_autonomous_codex_execution_state
assimilate_result       -> project_browser_autonomous_codex_result_assimilation_state
persist_ledger          -> project_browser_autonomous_run_ledger_persistence_state
stop                    -> no_runtime_invocation_stop
```

For non-stop actions, `actual_bounded_invocation` is valid only when:

```text
path_status=available
runtime_capability=actual_bounded_invocation
receipt_status=ready
delegation_mode in {reused_existing_state_call_path, invoked_existing_builder}
call_path_ref != none
missing_inputs == []
```

For `next_action=stop`, no runtime invocation is allowed:

```text
delegation_mode=no_runtime_invocation_stop
call_path_ref=none
```

PR137 must not add:

```text
multi-launch execution
daemon
scheduler
sleep loop
queue drain
unbounded autonomous execution
new browser executor
new Codex executor
new ledger persistence mechanism
GitHub mutation
```


---

## Prompt139 architecture constraints — bounded launch helper discovery and execution honesty

Prompt138 completed only the B-side prepared rolling execution state.

Prompt138 did not implement actual launch execution.

Prompt139 must therefore treat actual launch execution as unproven until an existing safe bounded launch helper or call path is identified.

### Prompt139 hard constraints

Prompt139 must not create:

```text
new browser executor
new Codex executor
new ledger persistence mechanism
new GitHub write path
daemon
scheduler
sleep loop
queue drain
unbounded autonomous execution
third launch
automatic PR creation
automatic merge
CI auto-fix loop
```

### Launch helper rule

Prompt139 must first classify whether an existing safe bounded launch helper or call path exists.

Required classification fields:

```text
project_browser_autonomous_rolling_execution_launch_helper_status
project_browser_autonomous_rolling_execution_launch_helper_ref
project_browser_autonomous_rolling_execution_launch_helper_missing_inputs
project_browser_autonomous_rolling_execution_launch_execution_mode
```

Allowed `launch_helper_status` values:

```text
available
unavailable
insufficient_truth
```

Allowed `launch_execution_mode` values:

```text
existing_helper_invoked
existing_call_path_reused
prepared_only_helper_missing
terminal_stop
insufficient_truth
```

### Execution honesty rule

Prompt139 must not set:

```text
project_browser_autonomous_rolling_execution_launches_attempted > 0
```

unless an existing safe bounded launch helper or call path was actually invoked.

Prompt139 must not set:

```text
project_browser_autonomous_rolling_execution_launches_completed > 0
```

unless receipt and ledger evidence confirm real launch completion.

Readiness, status fields, `call_path_ref`, PR136 gates, or PR137 gates alone are not sufficient evidence for attempted or completed launch execution.

### Missing helper rule

If no existing safe bounded launch helper or call path exists, Prompt139 must not fake execution.

It must emit or preserve:

```text
project_browser_autonomous_rolling_execution_launch_helper_status=unavailable
project_browser_autonomous_rolling_execution_launch_helper_ref=none
project_browser_autonomous_rolling_execution_launch_execution_mode=prepared_only_helper_missing
project_browser_autonomous_rolling_execution_runtime_capability=prepared_only
project_browser_autonomous_rolling_execution_launches_attempted=0
project_browser_autonomous_rolling_execution_launches_completed=0
project_browser_autonomous_rolling_execution_block_reason=bounded_launch_helper_missing
```

### Bound rule

If a proven existing helper is invoked, Prompt139 must enforce:

```text
max_launches=2
per_launch_max_steps=3
total_step_budget=6
failure_budget=1
```

It must never perform or claim a third launch.


---

## Prompt144-Prompt149 architecture constraints

Prompt144-Prompt146 established the one-bounded launch truth model:

- Candidate safety must be classified before actual invocation.
- attempted=1 is allowed only after a real selected mapped existing invocation call path is actually invoked.
- completed=1 is allowed only with explicit confirmed action-specific completion evidence.
- attempted=1 alone, ready receipt alone, and state existence alone must not imply completion.
- completed must never exceed attempted.

Prompt149 established runner result JSON accounting constraints:

- Runner result accounting should preserve raw Codex-reported values.
- Runner result accounting should add git-accounted values from staged and unstaged git diff/status.
- Public changed_files/additions/deletions should match final accounting values.
- Dry-run must not claim live worktree mutation accounting.

Prompt147 constraints:

- Prompt147 may prepare launch_1 / launch_2 state separation only.
- Prompt147 must not execute launch_2.
- Prompt147 must not implement max-two rolling execution.
- Prompt147 must not add a loop, daemon, scheduler, queue drain, new executor, GitHub mutation, PR creation, or merge.

---

## Current local autonomy constraints after Prompt147

The current repository state supports:

- candidate safety validation before invocation
- one bounded existing invocation attempt
- explicit completion evidence evaluation
- result JSON accounting correction from git diff/status
- launch_1 / launch_2 state separation

Hard constraints for Prompt148:

- Prompt148 may execute at most one second bounded launch.
- Prompt148 must never execute or prepare a third launch.
- Prompt148 must not add an unbounded loop.
- Prompt148 must not add daemon, scheduler, sleep loop, queue drain, retry loop, new browser executor, new Codex executor, GitHub mutation, PR creation, or PR merge.
- Prompt148 must not change Prompt149 result JSON accounting.
- If a safe reusable second-launch invocation surface is not available, Prompt148 must block with insufficient_truth and must not invent a new invocation path.


---

## Prompt150 actor separation constraints

Prompt150 established actor separation as a first-class schema/contract layer.

Required invariants:

- `decision_actor` and `implementation_actor` are separate concepts.
- `ChatGPT-Judge` reviews outputs and returns strict decision JSON.
- `ChatGPT-Implementer` may later produce patch plans, unified diffs, full file replacements, or manual steps.
- A ChatGPT-Implementer must not approve its own output for commit.
- A ChatGPT-Judge must not apply patches.
- Codex must not approve its own commit.
- `same_actor_requires_human_review=true` must remain represented.
- If the same actor or same conversation is used for decision and implementation:
  - `human_review_required=true`
  - `commit_allowed=false`

Prompt151 local JSON intake constraints:

- Expected file: `/tmp/codex-local-runner-decision/chatgpt_decision.json`
- Missing file must be waiting/manual handoff, not run failure.
- Invalid JSON, missing required fields, invalid values, actor separation failure, rollback_required, human_review_required, and unsafe commit_allowed must block consumption.

Prompt151 must not:

- call ChatGPT API
- automate or scrape ChatGPT UI
- invoke ChatGPT-Judge or ChatGPT-Implementer
- generate implementation packets
- generate or apply patches
- generate next/fix prompts
- start autonomous loops
- rollback
- commit
- create GitHub branch/PR/CI/merge behavior
- modify Prompt148 max-two semantics
- modify Prompt149 accounting
- modify Prompt150 actor separation semantics
---

## Prompt151 decision validator constraints

Prompt151 established local ChatGPT-Judge decision JSON validation/intake metadata.

Expected local file:

- `/tmp/codex-local-runner-decision/chatgpt_decision.json`

Prompt151 invariants:

- Missing file is waiting/manual handoff, not run failure.
- Invalid JSON must block without crashing.
- Missing required fields must block without crashing.
- Invalid allowed values must block without crashing.
- Actor separation failure must block.
- Same actor condition requires human review and must block commit.
- `commit_allowed=true` from JSON is not trusted directly.
- Effective commit permission requires validation/accounting/safety/actor gates.
- `rollback_required=true` blocks consumption.
- `human_review_required=true` blocks consumption.

Prompt152 constraints:

- Prompt152 may generate ChatGPT-Implementer packet metadata only.
- Prompt152 must not call ChatGPT.
- Prompt152 must not automate browser UI.
- Prompt152 must not validate or apply ChatGPT implementation output.
- Prompt152 must preserve Prompt150 actor separation and Prompt151 decision validator semantics.
- Prompt152 must not generate next/fix prompts, start loops, rollback, commit, create GitHub branch/PR/CI/merge behavior, or modify Prompt148/149/150/151 semantics.
---

## Prompt152 ChatGPT-Implementer packet constraints

Prompt152 established metadata-only ChatGPT-Implementer packet/handoff preparation.

Prompt152 invariants:

- Packet generation is metadata-only.
- Prompt152 must not write implementation packet files.
- Prompt152 must not call ChatGPT.
- Prompt152 must not automate browser UI.
- Prompt152 must not read or validate implementation responses.
- Prompt152 must not generate patches.
- Prompt152 must not apply patches.
- Prompt152 must not generate next/fix prompts.
- Prompt152 must not start loops.
- Prompt152 must not rollback, commit, create GitHub branches, create PRs, check CI, or merge.
- Prompt152 must preserve Prompt150 actor separation.
- Prompt152 must preserve Prompt151 decision validator semantics.

Prompt152 expected future artifact paths:

- `/tmp/codex-local-runner-decision/chatgpt_implementation_packet.md`
- `/tmp/codex-local-runner-decision/chatgpt_implementation_response.md`
- `/tmp/codex-local-runner-decision/chatgpt_implementation_patch.diff`

Prompt153 constraints:

- Prompt153 may validate ChatGPT-Implementer response metadata only.
- Prompt153 may inspect only the expected implementation response/patch paths.
- Prompt153 must not apply patches.
- Prompt153 must not modify files based on the response.
- Prompt153 must not call ChatGPT or automate browser UI.
- Prompt153 must not generate next/fix prompts or start autonomous loops.
- Prompt153 must not perform rollback/GitHub/CI/merge behavior.
---

## Prompt153 implementation response validator constraints

Prompt153 established metadata-only ChatGPT-Implementer response validation.

Prompt153 invariants:

- Prompt153 only reads expected local response/patch paths.
- Prompt153 must not write response files.
- Prompt153 must not generate patch content.
- Prompt153 must not apply patches.
- Prompt153 must not run `git apply`.
- Prompt153 must not call ChatGPT or automate browser UI.
- Prompt153 must not start loops, rollback, commit, create GitHub branches, create PRs, check CI, or merge.
- Patch-like responses without touched-file truth must remain blocked or insufficient_truth.
- Forbidden/out-of-allowed-scope touched files must block.
- Unsafe operation flags must block.
- `full_file_replacement` must remain conservative and must not bypass later apply gates.

Prompt154 constraints:

- Prompt154 may add a safe patch apply gate.
- Prompt154 must only operate on Prompt153 metadata-only patch candidates.
- Prompt154 must require clean or explicitly acceptable worktree state.
- Prompt154 must re-check allowed/forbidden files before any apply posture.
- Prompt154 must prefer dry-run validation before real apply.
- Prompt154 must not add unbounded retry, daemon, scheduler, queue drain, GitHub branch/PR/CI/merge behavior.
