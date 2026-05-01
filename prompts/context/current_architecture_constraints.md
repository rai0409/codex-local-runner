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
---

## Prompt154 safe patch dry-run readiness constraints

Prompt154 established metadata-only safe patch apply readiness.

Prompt154 invariants:

- `apply_allowed=false`.
- `apply_performed=false`.
- `ready_for_dry_run_later` does not mean patch application.
- Prompt154 must not run `git apply`.
- Prompt154 must not run `git apply --check`.
- Prompt154 must not write patch files.
- Prompt154 must not modify repo files.
- Dirty worktree blocks.
- Unknown worktree truth blocks with insufficient_truth.
- Forbidden touched files block.
- Unsafe operation flags block.
- `full_file_replacement` is blocked by default and requires later explicit human-review handling.
- Prompt148 through Prompt153 semantics remain unchanged.

Prompt155 constraints:

- Prompt155 may run only bounded `git apply --check`.
- Prompt155 must run dry-run check only when Prompt154 gate status is `ready_for_dry_run_later`.
- Prompt155 must use only the exact expected patch path already surfaced by Prompt153/154.
- Prompt155 must not run real `git apply`.
- Prompt155 must not modify repo files.
- Prompt155 must not stage files.
- Prompt155 must not commit.
- Prompt155 must not rollback.
- Prompt155 must not create GitHub branch/PR/CI/merge behavior.
- Prompt155 must not start an autonomous loop.

<!-- PROMPT155_BOUNDED_PATCH_DRY_RUN_START -->
## Prompt155 — bounded patch dry-run executor

Status:
  Completed.

Checkpoint:
  checkpoint-prompt155-bounded-patch-dry-run-ready

Purpose:
  Prompt155 adds the first bounded non-mutating patch execution check after Prompt154.
  It runs only `git apply --check <expected_patch_path>` when the Prompt154 safe patch gate is ready.

What was added:
  - `project_browser_autonomous_patch_dry_run_check_*`
  - `project_browser_autonomous_patch_dry_run_execution_*`
  - `project_browser_autonomous_patch_dry_run_result_*`

Behavior:
  - Dry-run is attempted only when the Prompt154 gate is ready for dry-run.
  - The expected patch path is consistently:
    `/tmp/codex-local-runner-decision/chatgpt_implementation_patch.diff`
  - The dry-run command is bounded and executed as an argv list:
    `["apply", "--check", normalized_expected_patch_path]`
  - The command is attempted at most once.
  - Timeout is bounded.
  - stdout/stderr are stored only as compact excerpts.

Blocked conditions:
  - no ready Prompt154 gate
  - missing expected patch path
  - dirty worktree
  - forbidden touched files
  - unsafe operations
  - human review required
  - rollback required
  - command unavailable
  - timeout
  - insufficient truth
  - dry-run mutation signal

Result semantics:
  - `dry_run_attempted=true` only when the command is actually invoked.
  - `dry_run_completed=true` only when the command returns or times out.
  - `dry_run_passed=true` only when exit code is 0.
  - `dry_run_failed=true` on non-zero exit, timeout, or execution error.
  - dry-run mutation signal is detected and blocked.

Safety posture:
  - No real `git apply` is performed.
  - `apply_performed` remains false.
  - No patch writing or patch generation is added.
  - No `git reset`, `git clean`, `git add`, `git commit`, or staging behavior is added.
  - No rollback execution is added.
  - No ChatGPT API or browser automation is added.
  - No next/fix prompt generator or autonomous loop is added.
  - No GitHub branch, PR, CI, or merge behavior is added.
  - Prompt148–154 semantics are preserved.

Validation:
  - `python -m py_compile automation/orchestration/planned_execution_runner.py` passed.
  - `python -m py_compile scripts/run_planned_execution.py` passed.

Next:
  Prompt156 should add a bounded safe real patch apply gate/executor.
  It may run `git apply <expected_patch_path>` only after Prompt155 dry-run passed.
  Prompt156 must add stricter patch path checks:
    - exact path match
    - exists
    - regular file
    - not symlink
    - resolved path equals canonical expected path
  Prompt156 must not stage, commit, rollback, create GitHub PR/CI/merge behavior, or start an autonomous loop.
<!-- PROMPT155_BOUNDED_PATCH_DRY_RUN_END -->

<!-- PROMPT156_SAFE_REAL_APPLY_GATE_START -->
## Prompt156 — bounded safe real patch apply gate

Status:
  Completed.

Checkpoint:
  checkpoint-prompt156-safe-real-apply-gate-ready

Purpose:
  Prompt156 adds the first bounded real patch apply gate/executor.
  It may run `git apply <expected_patch_path>` only after Prompt155 dry-run passed.

What was added:
  - `project_browser_autonomous_safe_patch_real_apply_gate_*`
  - `project_browser_autonomous_safe_patch_real_apply_execution_*`
  - `project_browser_autonomous_safe_patch_real_apply_result_*`

Gate requirements:
  - Prompt155 dry-run completed.
  - Prompt155 dry-run passed.
  - Prompt155 dry-run failed is false.
  - Prompt155 dry-run exit code is 0.
  - Prompt154 safe patch gate is ready.
  - Expected patch path is exactly:
    `/tmp/codex-local-runner-decision/chatgpt_implementation_patch.diff`
  - Expected patch path exists.
  - Expected patch path is a regular file.
  - Expected patch path is not a symlink.
  - Resolved path matches the canonical expected path.
  - Worktree is clean before apply.
  - No forbidden touched files.
  - No unsafe operations.
  - No active human-review or rollback posture.

Execution:
  - Runs at most one bounded real apply command:
    `git apply <expected_patch_path>`
  - Uses argv list execution:
    `["apply", normalized_expected_patch_path]`
  - Uses `timeout_seconds=5.0`.
  - Does not retry.

Result semantics:
  - `apply_attempted=true` only when the command is actually invoked.
  - `apply_completed=true` only when the command returns or times out.
  - `apply_performed=true` only when exit code is 0 and post-apply truth confirms expected changes.
  - `apply_passed=true` only when changed files are non-empty, within expected touched files, and no forbidden/unexpected changes exist.
  - Exit code 0 alone is not sufficient for success.
  - Dirty worktree after successful apply is expected when changed files match expected touched files.

Safety posture:
  - No staging.
  - No commit.
  - No rollback execution.
  - No git reset, git clean, checkout, or restore.
  - No GitHub branch, PR, CI, or merge behavior.
  - No next/fix generator.
  - No autonomous loop.
  - Prompt156 py_compile validates implementation only.
  - Post-apply target validation is deferred to Prompt157.

Next:
  Prompt157 should add post-apply validation and rollback posture refinement.
  Prompt157 should validate applied changes with bounded py_compile, changed-file consistency, metadata consistency, and rollback/human-review posture.
  Prompt157 must not execute rollback or commit.
<!-- PROMPT156_SAFE_REAL_APPLY_GATE_END -->

<!-- PROMPT157_POST_APPLY_VALIDATION_START -->
## Prompt157 — post-apply validation and rollback posture

Status:
  Completed.

Checkpoint:
  checkpoint-prompt157-post-apply-validation-ready

Purpose:
  Prompt157 adds post-apply validation and rollback posture metadata after Prompt156 real apply.

What was added:
  - `project_browser_autonomous_post_apply_validation_check_*`
  - `project_browser_autonomous_post_apply_validation_execution_*`
  - `project_browser_autonomous_post_apply_validation_result_*`
  - `project_browser_autonomous_rollback_posture_*`
  - authoritative summary keys:
    - `project_browser_autonomous_post_apply_validation_status`
    - `project_browser_autonomous_post_apply_validation_next_action`

Behavior:
  - Validation runs only after Prompt156 apply truth is successful.
  - Blocks on no apply performed, apply failure, missing post-apply truth, forbidden/unexpected changes, changed-file mismatch, metadata inconsistency, command unavailable, or timeout.
  - Required validation commands are bounded argv-list py_compile checks:
    - `python -m py_compile automation/orchestration/planned_execution_runner.py`
    - `python -m py_compile scripts/run_planned_execution.py`
  - Changed-file consistency requires non-empty changed files, subset-of-expected touched files, and no forbidden/unexpected changes.
  - Metadata consistency checks include Prompt155 dry-run truth and Prompt156 apply truth.

Rollback posture:
  - `rollback_required` may be set as metadata.
  - Rollback execution is disabled.
  - `rollback_execution_allowed=false`
  - `rollback_executed=false`
  - `rollback_attempted=false`
  - `rollback_completed=false`
  - No rollback commands are executed.

Exposure:
  - Prompt157 fields are exposed in compact planning summary.
  - Prompt157 fields are exposed in supporting truth refs.
  - Prompt157 fields are exposed in the final approved restart execution payload.

Validation:
  - Focused planned_execution_runner unittest checks passed.
  - `python -m py_compile automation/orchestration/planned_execution_runner.py` passed.
  - `python -m py_compile scripts/run_planned_execution.py` passed.

Next:
  Prompt158 should add dedicated unit tests for the Prompt157 status matrix and contract-surface exposure.
  Prompt158 must not add rollback execution, commit behavior, GitHub PR/CI/merge behavior, next/fix generator, or autonomous loop.
<!-- PROMPT157_POST_APPLY_VALIDATION_END -->

<!-- PROMPT158_PROMPT157_TESTS_START -->
## Prompt158 — Prompt157 status matrix and contract exposure tests

Status:
  Completed.

Checkpoint:
  checkpoint-prompt158-prompt157-tests-ready

Purpose:
  Prompt158 adds focused regression coverage for Prompt157 post-apply validation and rollback posture metadata.

What was added:
  - `test_prompt157_post_apply_validation_status_matrix`
  - `test_prompt157_validation_passed_and_field_presence`
  - `test_prompt157_contract_surface_exposure_in_payload`
  - Helper:
    - `_build_prompt157_state(...)`

Strategy:
  - Direct private-builder tests cover Prompt157 status matrix behavior precisely.
  - Contract-surface test uses `PlannedExecutionRunner.run(...)` and `approved_restart_execution_contract.json` to verify real payload exposure.
  - This locks both Prompt157 semantics and wiring.

Status matrix coverage:
  - `blocked_no_apply_performed`
  - `blocked_apply_failed`
  - `blocked_missing_post_apply_truth`
  - `blocked_forbidden_changes`
  - `blocked_unexpected_changes`
  - `blocked_changed_file_mismatch`
  - `blocked_metadata_inconsistency`
  - `validation_passed`

Rollback metadata-only coverage:
  - `rollback_execution_allowed=false`
  - `rollback_executed=false`
  - `rollback_attempted=false`
  - `rollback_completed=false`
  - `rollback_command` remains empty in passed-path coverage.
  - No rollback execution behavior was added.

Contract exposure coverage:
  - Prompt157 check/execution/result status fields are present in the final approved restart payload.
  - Rollback posture status and execution-disabled fields are present.
  - Prompt157 status and next_action summary keys are present.
  - Prompt157 fields are exposed in:
    - `project_planning_summary_compact`
    - supporting compact truth refs
    - `approved_restart_execution_contract.json`

Production changes:
  - Minimal production fix only:
    - Added missing `import sys` in `automation/orchestration/planned_execution_runner.py` for Prompt157 `sys.executable` usage.
  - No new runtime features were added.

Validation:
  - Baseline focused tests passed:
    - `test_manifest_paths_and_status_fields_are_preserved`
    - `test_manifest_generation_and_required_fields`
  - New Prompt158 tests passed:
    - `test_prompt157_post_apply_validation_status_matrix`
    - `test_prompt157_validation_passed_and_field_presence`
    - `test_prompt157_contract_surface_exposure_in_payload`
  - Compile checks passed:
    - `python -m py_compile automation/orchestration/planned_execution_runner.py`
    - `python -m py_compile scripts/run_planned_execution.py`

Known unrelated failures:
  - `python -m unittest tests.test_planned_execution_runner` still has 3 unrelated existing high-level posture failures:
    - `test_runner_allows_one_low_risk_approval_skip_and_executes_once`
    - `test_runner_continuation_budget_exhausts_after_repeated_auto_continuations`
    - `test_runner_final_human_review_required_for_high_risk_posture`

Next:
  Prompt159 should add an isolated regression test for Prompt157 `insufficient_truth` semantics where no definitive blocker exists and `validation_failed` must remain false.
  Prompt159 should also triage the 3 unrelated full-suite posture failures separately without changing Prompt157 semantics.
<!-- PROMPT158_PROMPT157_TESTS_END -->

<!-- PROMPT159_INSUFFICIENT_TRUTH_TRIAGE_START -->
## Prompt159 — Prompt157 insufficient truth regression and posture failure triage

Status:
  Completed.

Checkpoint:
  checkpoint-prompt159-insufficient-truth-regression-ready

Purpose:
  Prompt159 locks Prompt157 ambiguous `insufficient_truth` semantics and triages the remaining full-suite high-level posture failures.

What was added:
  - `test_prompt157_insufficient_truth_keeps_validation_failed_false_without_definitive_blocker`

Prompt157 insufficient truth semantics locked:
  - `project_browser_autonomous_post_apply_validation_status == "insufficient_truth"`
  - `validation_attempted=false`
  - `validation_completed=false`
  - `validation_passed=false`
  - `validation_failed=false`
  - `source_status == "apply_truth_unavailable"`
  - `block_reason == "insufficient_truth"`
  - `missing_inputs` is non-empty or explicitly explains unavailable truth.
  - rollback execution flags remain false.
  - `subprocess.run` is not called, so no validation commands are attempted.

Regression coverage:
  - Prompt158 Prompt157 tests still pass.
  - Baseline manifest/status field tests still pass.
  - Prompt159 added no new production behavior.

Known remaining failures:
  `python -m unittest tests.test_planned_execution_runner` still fails with 3 high-level posture tests:
  - `test_runner_allows_one_low_risk_approval_skip_and_executes_once`
    - expected `project_priority_posture="active"`, actual `"deferred"`
    - repro shows `objective_completion_posture="objective_blocked"` and `objective_stop_criteria_status="stop"` causing deferred priority.
  - `test_runner_continuation_budget_exhausts_after_repeated_auto_continuations`
    - expected third `project_priority_posture="lower_priority"`, actual `"deferred"`
    - repro shows `project_run_budget_posture="exhausted"` but `objective_completion_posture="objective_blocked"` still wins.
  - `test_runner_final_human_review_required_for_high_risk_posture`
    - expected `project_autonomy_budget_status="available"`, actual `"insufficient_truth"`
    - repro shows `continuation_budget_status="insufficient_truth"` propagating into autonomy budget status.

Conclusion:
  - The remaining 3 failures are not caused by Prompt157/158/159 field exposure.
  - They are legacy high-level posture precedence / expectation mismatches.
  - Prompt157 ambiguous insufficient-truth behavior is now deterministic and protected.

Validation:
  - Prompt159 insufficient-truth regression test passed.
  - Prompt158 Prompt157 regression tests passed.
  - Baseline manifest/status field tests passed.
  - `python -m py_compile automation/orchestration/planned_execution_runner.py` passed.
  - `python -m py_compile scripts/run_planned_execution.py` passed.

Next:
  Prompt160 should reconcile the 3 legacy high-level posture failures:
  - objective-blocked vs active/lower-priority precedence
  - run-budget exhaustion vs objective-blocked precedence
  - continuation-budget insufficient-truth propagation into autonomy budget status
  Prompt160 must not change Prompt157 semantics and must not add rollback execution, commit behavior, GitHub behavior, next/fix generator, or autonomous loop.
<!-- PROMPT159_INSUFFICIENT_TRUTH_TRIAGE_END -->

<!-- PROMPT160_FIX_PROMPT_READINESS_START -->
## Prompt160 — fix-prompt generator readiness metadata

Status:
  Completed.

Checkpoint:
  checkpoint-prompt160-fix-prompt-readiness-ready

Purpose:
  Prompt160 adds metadata-only readiness classification for future fix-prompt generation.
  It decides whether a failure is safe and actionable enough for Prompt161 to generate a repair prompt.

What was added:
  - `_build_project_browser_autonomous_fix_prompt_readiness_state(...)`
  - `project_browser_autonomous_fix_prompt_readiness_*`
  - normalization/wiring
  - compact summary exposure
  - supporting truth refs exposure
  - final approved restart payload exposure

Behavior:
  - `validation_passed=true` blocks fix generation as no fix is needed.
  - ambiguous `insufficient_truth` blocks fix generation and waits for more truth.
  - `rollback_required=true` blocks fix generation.
  - `human_review_required=true` blocks fix generation.
  - forbidden or unexpected changed files block fix generation.
  - metadata inconsistency blocks fix generation.
  - actionable failures such as py_compile failure, dry-run failure, apply failure, changed-file mismatch, or validation failure with useful detail can become `ready_to_generate_fix_prompt`.
  - safe `fix_target_files` are derived only from existing changed/touched-file truth and exclude forbidden/unexpected files.

Safety:
  - No fix prompt body is generated.
  - No fix prompt file is created.
  - `prompt_generation_attempted=false`
  - `prompt_generated=false`
  - `prompt_path=""`
  - No rollback execution.
  - No git reset/clean/checkout/restore/add/commit/push.
  - No GitHub/PR/CI/merge behavior.
  - No autonomous loop behavior.

Tests:
  - Prompt160 readiness tests passed:
    - validation passed blocks generation
    - insufficient truth blocks generation
    - rollback required blocks generation
    - human review required blocks generation
    - actionable py_compile failure is ready
    - metadata inconsistency blocks generation
    - contract-surface exposure
  - Prompt157/158/159 regression tests passed.
  - Baseline manifest/status tests passed.
  - py_compile checks passed.

Known out of scope:
  The 3 legacy high-level posture tests remain out of Prompt160 scope and were not modified.

Next:
  Prompt161 should generate a bounded fix-prompt body and optional fixed handoff file only when Prompt160 readiness is `ready_to_generate_fix_prompt` and generation is allowed.
  Prompt161 must still not invoke Codex/ChatGPT, apply patches, rollback, commit, push, use GitHub, or start a loop.
<!-- PROMPT160_FIX_PROMPT_READINESS_END -->

<!-- PROMPT162_NEXT_PROMPT_READINESS_START -->
## Prompt162 — next-prompt readiness metadata

Status:
  Completed.

Checkpoint:
  checkpoint-prompt162-next-prompt-readiness-ready

Purpose:
  Prompt162 adds readiness-only metadata for deciding whether a future Prompt163 may generate the next development prompt.

What was added:
  - `_build_project_browser_autonomous_next_prompt_readiness_state(...)`
  - `project_browser_autonomous_next_prompt_readiness_*`
  - normalization/wiring near Prompt161
  - compact planning summary exposure
  - supporting truth refs exposure
  - final approved restart payload exposure

Ready state:
  `ready_to_generate_next_prompt` requires:
  - `validation_passed=true`
  - `validation_failed=false`
  - `rollback_required=false`
  - `human_review_required=false`
  - no active `insufficient_truth`
  - no active fix-required path
  - bounded next work available
  - bounded next scope
  - safe next target files available

Blocked states:
  - validation not passed
  - validation failed
  - fix flow required
  - insufficient truth
  - rollback required
  - human review required
  - prompt generation already attempted
  - missing/ambiguous next work
  - explicit no remaining work

Next work source policy:
  Prompt162 determines next work only from bounded existing signals:
  - `implementation_prompt_status`
  - `implementation_prompt_payload`
  - `project_pr_queue_status`
  - `project_pr_queue_selected_slice_id`
  - `objective_completion_posture`

  If no deterministic bounded next work, target files, or scope is available:
  - use `blocked_missing_next_work` or `blocked_no_remaining_work`
  - populate `missing_inputs`

Safety:
  Prompt162 does not:
  - generate next prompt body
  - write `/tmp/codex-local-runner-decision/generated_next_prompt.txt`
  - invoke Codex/ChatGPT/browser/external models
  - apply patches
  - execute rollback
  - run git reset/clean/checkout/restore/add/commit/push/gh
  - use GitHub/CI/merge
  - start an autonomous loop
  - edit tests or docs

Validation:
  - `python -m py_compile automation/orchestration/planned_execution_runner.py` passed.
  - `python -m py_compile scripts/run_planned_execution.py` passed.
  - focused Prompt160 checks passed.

Known remaining risk:
  Prompt162 has no dedicated unit tests yet.

Next:
  Prompt163 should generate a bounded next-prompt body and optional fixed handoff file at:
  - `/tmp/codex-local-runner-decision/generated_next_prompt.txt`

  Prompt163 must be gated by:
  - `project_browser_autonomous_next_prompt_readiness_status == "ready_to_generate_next_prompt"`
  - `generation_allowed=true`

  Prompt163 must still not invoke Codex/ChatGPT, apply patches, rollback, commit, use GitHub, or start a loop.
<!-- PROMPT162_NEXT_PROMPT_READINESS_END -->

<!-- PROMPT163_NEXT_PROMPT_GENERATION_START -->
## Prompt163 — next-prompt body generation and handoff file

Status:
  Completed.

Checkpoint:
  checkpoint-prompt163-next-prompt-generation-ready

Purpose:
  Prompt163 generates a bounded next-prompt body for a future Codex/ChatGPT run when Prompt162 readiness allows it.

What was added:
  - `_build_project_browser_autonomous_next_prompt_generation_state(...)`
  - `project_browser_autonomous_next_prompt_generation_*`
  - normalization/wiring near Prompt162
  - compact planning summary exposure
  - supporting truth refs exposure
  - final approved restart payload exposure

Generation gate:
  Prompt body generation is allowed only when Prompt162 readiness is ready:
  - `project_browser_autonomous_next_prompt_readiness_status == "ready_to_generate_next_prompt"`
  - `generation_allowed=true`
  - `ready_to_generate=true`
  - `validation_passed=true`
  - `validation_failed=false`
  - `rollback_required=false`
  - `human_review_required=false`
  - no active `insufficient_truth`
  - bounded next work is available
  - bounded next scope is available
  - safe next target files are available

Generated prompt body:
  The generated next prompt includes:
  - repository path: `/home/rai/codex-local-runner`
  - checkpoint: `checkpoint-prompt162-docs-synced-before-prompt163`
  - next work kind/scope/targets
  - exact implementation goal
  - strict non-goals
  - safety constraints
  - validation commands
  - expected report format
  - smallest safe additive change instruction

Handoff file:
  Fixed handoff path:
  - `/tmp/codex-local-runner-decision/generated_next_prompt.txt`

  Handoff path rules:
  - exact path only
  - parent directory must exist
  - path must not be a symlink
  - write only prompt body text
  - do not write patches or source code files
  - no alternate paths
  - no directory scan

Handoff failure behavior:
  If prompt body generation succeeds but handoff write/path validation fails:
  - keep `status=prompt_generated`
  - keep `prompt_generated=true`
  - keep `prompt_body`
  - set handoff failure flags
  - set `next_action=manual_next_prompt_required`

Safety:
  Prompt163 does not invoke Codex/ChatGPT, use browser automation, generate implementation patches, apply patches, execute rollback, stage/commit/push, use GitHub/PR/CI/merge, or start an autonomous loop.

Validation:
  - `python -m py_compile automation/orchestration/planned_execution_runner.py` passed.
  - `python -m py_compile scripts/run_planned_execution.py` passed.
  - Focused Prompt160 checks passed.

Known remaining risk:
  Prompt163 has no dedicated unit tests yet.

Current autonomous prompt-flow state:
  - failure path: Prompt160 readiness -> Prompt161 `/tmp/codex-local-runner-decision/generated_fix_prompt.txt`
  - success path: Prompt162 readiness -> Prompt163 `/tmp/codex-local-runner-decision/generated_next_prompt.txt`

Next:
  Prompt164 should add a prompt selection controller that selects either:
  - fix prompt: `/tmp/codex-local-runner-decision/generated_fix_prompt.txt`
  - next prompt: `/tmp/codex-local-runner-decision/generated_next_prompt.txt`

  Prompt164 must still not invoke Codex/ChatGPT, apply patches, rollback, commit, use GitHub, or start a loop.
<!-- PROMPT163_NEXT_PROMPT_GENERATION_END -->

<!-- PROMPT164_PROMPT_SELECTION_START -->
## Prompt164 — prompt selection controller

Status:
  Completed.

Checkpoint:
  checkpoint-prompt164-prompt-selection-ready

Purpose:
  Prompt164 selects which generated prompt should be handed to a future Codex invocation readiness stage.

What was added:
  - `_build_project_browser_autonomous_prompt_selection_state(...)`
  - `project_browser_autonomous_prompt_selection_*`
  - normalization/wiring near Prompt163
  - compact planning summary exposure
  - supporting truth refs exposure
  - final approved restart payload exposure

Selection behavior:
  - Selects fix prompt only when a failure/fix-required path is active and Prompt161 fix-prompt generation is valid.
  - Selects next prompt only when validation passed path is active and Prompt163 next-prompt generation is valid.
  - If both fix and next prompts are valid, blocks with `blocked_conflicting_prompts`.
  - If neither prompt is valid, blocks with `blocked_no_ready_prompt`.

Allowed selected paths:
  - fix: `/tmp/codex-local-runner-decision/generated_fix_prompt.txt`
  - next: `/tmp/codex-local-runner-decision/generated_next_prompt.txt`

Selection safety checks:
  - exact allowed handoff path
  - handoff write completed
  - no handoff write failure
  - path exists
  - path is not a symlink
  - prompt body exists / non-empty
  - no rollback-required posture
  - no human-review-required posture
  - no active insufficient-truth posture

Hard blocks:
  - `blocked_rollback_required`
  - `blocked_human_review_required`
  - `blocked_insufficient_truth`
  - `blocked_handoff_write_failed`
  - `blocked_prompt_path_missing`
  - `blocked_prompt_path_unexpected`
  - `blocked_prompt_path_symlink`
  - `blocked_prompt_body_missing`
  - `blocked_conflicting_prompts`
  - `blocked_no_ready_prompt`

Safety:
  Prompt164 selects only. It does not generate prompt bodies, create handoff files, invoke Codex/ChatGPT, apply patches, execute rollback, stage/commit/push, use GitHub/PR/CI/merge, or start an autonomous loop.

Validation:
  - `python -m py_compile automation/orchestration/planned_execution_runner.py` passed.
  - `python -m py_compile scripts/run_planned_execution.py` passed.
  - focused Prompt160 checks passed.

Known remaining risk:
  Prompt164 has no dedicated unit tests yet.

Current autonomous prompt-flow state:
  - failure path: Prompt160 readiness -> Prompt161 generated fix prompt -> Prompt164 selected fix prompt
  - success path: Prompt162 readiness -> Prompt163 generated next prompt -> Prompt164 selected next prompt

Next:
  Prompt165 should add Codex invocation readiness metadata for the selected prompt.
  Prompt165 must still not invoke Codex/ChatGPT, apply patches, rollback, commit, use GitHub, or start a loop.
<!-- PROMPT164_PROMPT_SELECTION_END -->

<!-- PROMPT166_READONLY_CODEX_INVOCATION_START -->
## Prompt166 — bounded read-only Codex invocation

Status:
  Completed.

Checkpoint:
  checkpoint-prompt166-readonly-codex-invocation-ready

Purpose:
  Prompt166 adds one bounded Codex invocation path for the Prompt165-selected prompt.

What was added:
  - `_build_project_browser_autonomous_codex_invocation_execution_state(...)`
  - `project_browser_autonomous_codex_invocation_execution_*`
  - `project_browser_autonomous_codex_invocation_result_*`
  - normalization/wiring near Prompt165
  - compact planning summary exposure
  - supporting truth refs exposure
  - final approved restart payload exposure

Invocation gate:
  Codex invocation proceeds only when Prompt165 readiness is ready:
  - `project_browser_autonomous_codex_invocation_readiness_status == "ready_to_invoke_codex"`
  - `invocation_allowed=true`
  - `max_invocations=1`
  - no prior invocation attempt/completion
  - selected prompt path is exact, exists, non-symlink, non-empty, and not too large
  - `rollback_required=false`
  - `human_review_required=false`
  - no active `insufficient_truth`

Command:
  - Uses argv-list, no shell:
    `codex exec - --cd <repository_path> --sandbox read-only`
  - Selected prompt file content is passed as stdin.
  - At most one attempt.
  - No retry loop.

Fixed output paths:
  - stdout: `/tmp/codex-local-runner-decision/codex_invocation_stdout.txt`
  - stderr: `/tmp/codex-local-runner-decision/codex_invocation_stderr.txt`
  - result: `/tmp/codex-local-runner-decision/codex_invocation_result.json`

Semantics:
  - `invocation_attempted=true` only when the command is actually entered.
  - `invocation_completed=true` only after return, timeout, or terminal execution error handling.
  - stdout/stderr are saved to fixed files.
  - metadata stores only compact excerpts.

Safety:
  Prompt166 does not classify Codex output as a patch candidate.
  Prompt166 does not apply patches, execute rollback, stage/commit/push, use GitHub/PR/CI/merge, or start a loop.

Important limitation:
  Prompt166 uses `--sandbox read-only`.
  This means it captures Codex output but does not allow Codex to directly edit the repo.
  For fastest practical autonomous implementation, the next step should add a separate write-enabled bounded Codex invocation path, guarded by Prompt165/166 safety gates.

Validation:
  - `python -m py_compile automation/orchestration/planned_execution_runner.py` passed.
  - `python -m py_compile scripts/run_planned_execution.py` passed.
  - focused Prompt160 checks passed.

Next:
  Prompt167 should add a bounded write-enabled Codex invocation mode.
  It must still enforce max_invocations=1, no retry, no loop, no commit, no GitHub, no rollback execution, and should capture git diff/status after Codex returns.
<!-- PROMPT166_READONLY_CODEX_INVOCATION_END -->

<!-- PROMPT167_WRITE_CODEX_INVOCATION_START -->
## Prompt167 — write-enabled bounded Codex invocation

Status:
  Completed.

Checkpoint:
  checkpoint-prompt167-write-enabled-codex-invocation-ready

Purpose:
  Prompt167 adds a write-enabled, one-invocation Codex execution path that can let Codex edit the repo once under strict gates.

What was added:
  - `_build_project_browser_autonomous_codex_write_invocation_state(...)`
  - `project_browser_autonomous_codex_write_invocation_readiness_*`
  - `project_browser_autonomous_codex_write_invocation_execution_*`
  - `project_browser_autonomous_codex_write_invocation_result_*`
  - compact planning summary exposure
  - supporting truth refs exposure
  - final approved restart payload exposure

Command:
  - argv-only, no shell:
    `codex exec - --cd <repo> --sandbox workspace-write`
  - selected prompt file content is passed as stdin.
  - no fallback to read-only.
  - if workspace-write support is unavailable, block with `blocked_codex_command_unavailable`.

Invocation gates:
  - Prompt165 readiness must be `ready_to_invoke_codex`.
  - selected prompt must be valid and safe.
  - selected prompt path must be one of:
    - `/tmp/codex-local-runner-decision/generated_fix_prompt.txt`
    - `/tmp/codex-local-runner-decision/generated_next_prompt.txt`
  - selected prompt file must exist, be non-symlink, non-empty, and not too large.
  - worktree must be clean before invocation.
  - `rollback_required=false`
  - `human_review_required=false`
  - no active `insufficient_truth`
  - `max_invocations=1`
  - no prior write invocation attempt/completion.

Fixed output paths:
  - stdout: `/tmp/codex-local-runner-decision/codex_write_invocation_stdout.txt`
  - stderr: `/tmp/codex-local-runner-decision/codex_write_invocation_stderr.txt`
  - result: `/tmp/codex-local-runner-decision/codex_write_invocation_result.json`
  - diff name-only: `/tmp/codex-local-runner-decision/codex_write_git_diff_name_only.txt`
  - diff numstat: `/tmp/codex-local-runner-decision/codex_write_git_diff_numstat.txt`

Post-invocation accounting:
  After command return, timeout, or terminal error handling, Prompt167 captures:
  - `git status --short`
  - `git diff --name-only`
  - `git diff --numstat`

Result classifications:
  - `completed_with_changes`
  - `completed_no_changes`
  - `completed_failure`
  - `completed_timeout`
  - `blocked`
  - `failed_execution_error`
  - `insufficient_truth`

Safety:
  Prompt167 does not classify patch candidates, create patch files, run git apply, run git apply --check, execute rollback, stage, commit, push, use GitHub/PR/CI/merge, run runtime tests, or start retry/autonomous loops.

Smoke result:
  Prompt167 fields are exposed, but the smoke run did not invoke Codex because upstream Prompt157 was `blocked_no_apply_performed`, setting `human_review_required=true`.
  This blocked Prompt161/163 prompt generation, Prompt164 prompt selection, Prompt165 invocation readiness, and Prompt167 write invocation.

Current blocker:
  - `project_browser_autonomous_post_apply_validation_status=blocked_no_apply_performed`
  - `project_browser_autonomous_post_apply_validation_*_human_review_required=true`
  - `project_browser_autonomous_prompt_selection_selected_prompt_kind=none`
  - `project_browser_autonomous_codex_write_invocation_readiness_status=blocked_human_review_required`

Validation:
  - `python -m py_compile automation/orchestration/planned_execution_runner.py` passed.
  - `python -m py_compile scripts/run_planned_execution.py` passed.
  - focused Prompt160 checks passed.

Known remaining risk:
  Prompt167 has no dedicated unit tests yet.
  Runtime behavior depends on local Codex CLI workspace-write behavior.

Next:
  Prompt168 should add an explicit smoke/manual selected prompt override so the write-enabled invocation path can be exercised without requiring the full Prompt154-157 apply/validation chain.
  The override must be disabled by default, explicit, max-one-invocation, clean-worktree-only, no rollback, no stage, no commit, no GitHub, and no loop.
<!-- PROMPT167_WRITE_CODEX_INVOCATION_END -->

<!-- PROMPT168_SMOKE_PROMPT_OVERRIDE_START -->
## Prompt168 — smoke/manual selected prompt override

Status:
  Completed.

Checkpoint:
  checkpoint-prompt168-smoke-override-ready

Purpose:
  Prompt168 adds an explicit smoke/manual selected prompt override so Prompt167 write-enabled Codex invocation can be exercised without requiring the full Prompt154-157 apply/validation chain.

What was added:
  - `_build_project_browser_autonomous_smoke_prompt_override_state(...)`
  - `project_browser_autonomous_smoke_prompt_override_*`
  - smoke override wiring into Prompt167 write invocation through smoke/effective selection values
  - compact planning summary exposure
  - supporting truth refs exposure
  - final approved restart payload exposure

Activation:
  Disabled by default.
  Enabled only when:
  - `PROJECT_BROWSER_AUTONOMOUS_SMOKE_PROMPT_OVERRIDE=1`

Allowed smoke prompt paths:
  - `/tmp/codex-local-runner-decision/generated_next_prompt.txt`
  - `/tmp/codex-local-runner-decision/generated_fix_prompt.txt`

Selection behavior:
  - prefers generated_next_prompt.txt when both fixed prompt files are safe
  - otherwise selects the one safe fixed prompt file
  - emits selected_prompt_* and override_prompt_* metadata

Safety gates:
  - exact fixed path only
  - file exists
  - non-symlink
  - non-empty
  - size <= 20000 bytes
  - clean worktree required
  - max_invocations=1

Smoke bypass:
  Prompt168 may bypass upstream `human_review_required` only for explicit smoke invocation.
  It exposes:
  - `human_review_bypass_for_smoke=true`
  - `override_used=true`

Safety:
  Prompt168 does not generate prompt files, classify Codex output, create patch candidate metadata, apply patches, rollback, stage, commit, push, use GitHub/PR/CI/merge, or start retry/autonomous loops.

Validation:
  - `python -m py_compile automation/orchestration/planned_execution_runner.py` passed.
  - `python -m py_compile scripts/run_planned_execution.py` passed.

Known remaining risk:
  The smoke override intentionally bypasses human-review posture only when the explicit env var is set.
  Operational safety depends on not leaving `PROJECT_BROWSER_AUTONOMOUS_SMOKE_PROMPT_OVERRIDE=1` enabled outside controlled smoke runs.

Next:
  Prompt169 should run/assimilate the controlled smoke write invocation result:
  - verify smoke override selection
  - verify Prompt167 write invocation result
  - classify changed files / no changes / failure / timeout
  - do not apply patches
  - do not rollback
  - do not commit
  - do not use GitHub
  - do not start a loop
<!-- PROMPT168_SMOKE_PROMPT_OVERRIDE_END -->


<!-- prompt169-update -->
## Prompt169 architecture constraint update

Prompt169 adds Codex write-result assimilation only. It must not run validation,
rollback, commit, GitHub operations, retries, loops, or create new executors.

Authoritative next-step gate:
- Prompt169 `safe_for_validation_routing=true` is only a routing eligibility signal.
- Validation must be introduced separately by a bounded post-write validation routing
  state, metadata-only first.
- Changed-file safety is mandatory: unexpected, forbidden, too-many, missing-truth,
  timeout, failure, or not-completed outcomes must not auto-route to validation.

Smoke-specific constraint:
- When smoke override is used, only the expected smoke output file may be treated as
  expected unless explicit upstream metadata allows otherwise.


<!-- prompt170-update -->
## Prompt170 architecture constraint update

Prompt170 adds metadata-only post-write validation routing from Prompt169 assimilation.
It must not execute validation commands, tests, rollback, staging, commit, GitHub
operations, retries, loops, schedulers, daemons, queue drainers, or new executors.

Authoritative routing rule:
- Prompt170 may allow validation only when Prompt169 reports safe bounded expected
  changes and changed-file safety checks are clean.
- Prompt170 `validation_allowed=true` is the only entry point for Prompt171 bounded
  post-write validation execution.
- Prompt170 candidate lists are metadata only:
  `validation_target_files`, `py_compile_candidate_files`, and
  `targeted_test_candidate_files`.

Blocked cases:
- human review, forbidden files, unexpected files, too many files, timeout, failure,
  not-completed, insufficient-truth, no changed files, or unsafe assimilation must not
  route into validation execution.


<!-- prompt171-update -->
## Prompt171 architecture constraint update

Prompt171 adds bounded post-write py_compile validation execution from Prompt170
routing. It must execute only py_compile candidates that Prompt170 has routed as
safe.

Authoritative execution gate:
- Prompt171 may execute only when Prompt170 `validation_allowed=true`,
  `py_compile_candidate_files` is non-empty, and human review is not required.
- Prompt171 must reject unsafe candidate paths before execution.
- Prompt171 must not run unittest, rollback, staging, commit, GitHub operations,
  retries, loops, schedulers, daemons, queue drainers, or new executors.

Prompt171 result semantics:
- `validation_passed` may continue toward the one-step autonomous cycle summary.
- `validation_failed` should route toward fix-prompt generation.
- `validation_timeout`, unsafe candidates, missing candidates, or blocked routing
  should stop safely and require manual review or safe stop metadata.


<!-- prompt172-update -->
## Prompt172 architecture constraint update

Prompt172 adds a metadata-only one-step autonomous cycle state. It summarizes one
bounded autonomous cycle from existing Prompt164-171 state only.

Authoritative cycle rule:
- Prompt172 must not run commands or add execution behavior.
- Prompt172 must not retry, loop, rollback, stage, commit, create GitHub operations,
  or create new executors.
- Prompt172 may classify the current one-step cycle as passed, failed, blocked, or
  insufficient-truth based on existing source states only.

Known conservative behavior:
- Prompt172 currently aggregates human-review signals from multiple source states.
  This is safe but can over-block if stale or unrelated upstream manual-review flags
  remain present.
- The next hardening step should prefer definitive downstream Prompt171 validation
  truth when available and restrict human-review blocking to the active path.


<!-- prompt173-update -->
## Prompt173 architecture constraint update

Prompt173 hardens one-step cycle classification only.

Authoritative precedence:
- Definitive Prompt171 validation results from the active path take precedence over
  stale or unrelated upstream human-review flags.
- `validation_passed` may classify the one-step cycle as passed when it belongs to
  the active downstream validation path.
- `validation_failed` may classify the cycle as failed and route toward fix-prompt
  generation.
- `validation_timeout` blocks safely with manual review.
- Missing Prompt167-only fields must not override definitive Prompt169/170/171
  downstream truth.

Current limitation:
- Prompt173 classifies the next safe action but does not yet hand it off to the
  existing fix/next prompt generation flow.


<!-- prompt174-update -->
## Prompt174 architecture constraint update

Prompt174 adds a cycle handoff controller from Prompt173 one-step cycle results to
existing fix/next prompt readiness flows.

Authoritative handoff rule:
- `cycle_passed` may hand off to the next-prompt readiness flow.
- `cycle_failed_validation` may hand off to the fix-prompt readiness flow.
- blocked, timeout, unsafe, or manual-review cases must not hand off to generation.
- Prompt174 must not generate prompt files, invoke Codex, rollback, commit, create
  GitHub operations, retry, loop, or create new executors.

Current limitation:
- Prompt174 adds advisory bridge metadata to Prompt160/162 readiness maps.
- Prompt175 must explicitly consume this metadata inside readiness decision logic.


<!-- prompt175-update -->
## Prompt175 architecture constraint update

Prompt175 consumes Prompt174 cycle handoff metadata inside existing fix/next prompt
readiness builders.

Authoritative safety rule:
- `cycle_handoff_acknowledged=true` is a positive input only.
- It must not bypass human review, missing truth, unsafe status, or existing
  readiness blockers.
- Fix readiness may acknowledge only `fix` handoff with reason `validation_failed`.
- Next readiness may acknowledge only `next` handoff with reason `cycle_passed`.
- Prompt175 must not generate prompt files, invoke Codex, rollback, commit, create
  GitHub operations, retry, loop, or create new executors.

Current limitation:
- Readiness status is not yet re-evaluated from acknowledged handoff in the same run.
- Prompt176 should add a small safety-gated precedence layer for in-run readiness
  re-evaluation.


<!-- prompt176-update -->
## Prompt176 architecture constraint update

Prompt176 adds safety-gated in-run readiness re-evaluation from acknowledged cycle
handoff.

Authoritative safety rule:
- `cycle_handoff_acknowledged=true` can re-drive readiness only when existing safety
  gates are clean.
- Re-evaluation must not bypass human review, rollback safety, missing truth,
  unsafe status, or existing readiness blockers.
- Fix readiness may become `cycle_handoff_fix_ready` only for acknowledged fix
  handoff from validation failure.
- Next readiness may become `cycle_handoff_next_ready` only for acknowledged next
  handoff from cycle pass.
- Prompt176 must not generate prompt files, invoke Codex, rollback, commit, create
  GitHub operations, retry, loop, or create new executors.

Current limitation:
- Prompt161/163 generation states do not yet consume re-evaluated readiness in the
  same run. Prompt177 should add that wiring without introducing new executors.


<!-- prompt177-update -->
## Prompt177 architecture constraint update

Prompt177 wires re-evaluated cycle-handoff readiness into existing Prompt161/163
generation states in the same run.

Authoritative safety rule:
- Same-run generation refresh may occur only through existing Prompt161/163 generation
  builders.
- Existing generation safety checks remain authoritative.
- Prompt177 must not create a new generator, writer, executor, retry loop, rollback,
  commit, GitHub operation, scheduler, daemon, or queue drainer.
- Prompt177 does not reorder the full pipeline; refresh is scoped to fix/next
  generation states.

Current limitation:
- Generated fix/next prompt outputs are not yet routed back into Prompt164 selection,
  Prompt165 invocation readiness, or Prompt167 workspace-write invocation.
- Prompt178 should add re-entry readiness metadata for that path without invoking
  Codex yet.


<!-- prompt178-update -->
## Prompt178 architecture constraint update

Prompt178 adds generated prompt re-entry readiness from refreshed Prompt161/163
generation outputs.

Authoritative re-entry rule:
- Only fixed generated prompt handoff paths are allowed:
  `/tmp/codex-local-runner-decision/generated_fix_prompt.txt`
  `/tmp/codex-local-runner-decision/generated_next_prompt.txt`
- Re-entry must block unexpected paths, symlinks, missing/non-file paths, empty files,
  oversized files, human-review cases, insufficient truth, and ambiguous fix+next
  readiness.
- Prompt178 must not invoke Codex, start a next cycle, rollback, commit, create
  GitHub operations, retry, loop, or create new executors.

Current limitation:
- Re-entry readiness does not yet refresh Prompt164 selection or Prompt165/167
  invocation readiness. Prompt179 should add that wiring without executing Codex.


<!-- prompt179-update -->
## Prompt179 architecture constraint update

Prompt179 connects generated prompt re-entry readiness into Prompt164 selection,
Prompt165 invocation readiness, and Prompt167 workspace-write invocation re-entry
metadata.

Authoritative safety rule:
- Re-entry routing may only use fixed generated prompt handoff paths:
  `/tmp/codex-local-runner-decision/generated_fix_prompt.txt`
  `/tmp/codex-local-runner-decision/generated_next_prompt.txt`
- Re-entry metadata may prepare at most one future invocation:
  `reentry_max_invocations=1`.
- Prompt179 must not invoke Codex, retry, loop, rollback, commit, create GitHub
  operations, schedulers, daemons, queue drainers, or new executors.

Current limitation:
- Prompt179 prepares re-entry metadata only. Prompt180 must consume it and perform
  a controlled single bounded re-entry invocation path.


<!-- prompt180-update -->
## Prompt180 architecture constraint update

Prompt180 adds controlled single bounded Codex re-entry invocation from generated
fix/next prompt re-entry metadata.

Authoritative safety rule:
- Prompt180 may invoke Codex at most once.
- Prompt180 must not retry, loop, rollback, commit, create GitHub operations,
  schedulers, daemons, queue drainers, or new executors.
- Prompt180 must use fixed generated prompt paths only:
  `/tmp/codex-local-runner-decision/generated_fix_prompt.txt`
  `/tmp/codex-local-runner-decision/generated_next_prompt.txt`
- Prompt180 owns the re-entry execution decision; Prompt179
  `reentry_should_invoke_codex=false` is not a blocker because Prompt179 was
  metadata-only.
- Prompt180 must block if a prior Prompt167 write invocation already attempted in
  the same run.

Current limitation:
- Prompt180 executes bounded re-entry but does not yet feed the re-entry result back
  into the Prompt169-style assimilation and Prompt170-style validation routing path.
- Prompt181 should add that re-entry result assimilation/routing metadata.


<!-- prompt181-update -->
## Prompt181 architecture constraint update

Prompt181 assimilates Prompt180 re-entry invocation results back toward the
post-write safety pipeline.

Authoritative source rule:
- Prompt180 re-entry result is authoritative when
  `reentry_result_ready_for_assimilation=true`.
- Do not merge Prompt180 re-entry and normal Prompt167 write outputs.
- Do not fall back to stale normal Prompt167 output when re-entry routing was active
  but re-entry assimilation is blocked/not-ready.
- Ambiguous active write sources must block safely.

Safety rule:
- Prompt181 must not invoke Codex, execute validation, rollback, commit, create
  GitHub operations, retry, loop, or create new executors.
- Prompt181 may emit Prompt170-compatible routing inputs only.

Current limitation:
- Prompt181 does not yet refresh validation routing, bounded py_compile validation,
  or cycle classification. Prompt182 should do that without invoking Codex.


<!-- prompt182-update -->
## Prompt182 architecture constraint update

Prompt182 refreshes post-reentry validation and cycle classification from Prompt181
re-entry assimilation.

Authoritative post-reentry rule:
- Prompt182 post-reentry safety refresh fields are authoritative for re-entry-aware
  continuation decisions.
- Downstream continuation logic must prefer:
  `project_browser_autonomous_post_reentry_safety_refresh_*`
  over legacy non-reentry Prompt170/171/172/173 states when Prompt182 has produced
  definitive post-reentry status.
- Prompt182 may emit continuation and rollback candidate metadata only.
- Prompt182 must not invoke Codex, start another cycle, rollback, commit, create
  GitHub operations, retry, loop, or create new executors.

Current limitation:
- Prompt182 does not decide cycle budgets, fix budgets, stop reasons, or continuation
  permission. Prompt183 should add bounded continuation control.


<!-- prompt183-update -->
## Prompt183 architecture constraint update

Prompt183 adds bounded continuation control from Prompt182 post-reentry safety
refresh.

Authoritative continuation rule:
- Prompt183 must prefer:
  `project_browser_autonomous_post_reentry_safety_refresh_*`
  as the authoritative source for re-entry-aware continuation.
- Prompt183 may decide only metadata control state:
  next continuation, fix continuation, rollback preparation, manual review, or stop.
- Prompt183 must not generate prompts, invoke Codex, start a cycle, rollback, commit,
  create GitHub operations, retry, loop, or create new executors.

Current limitation:
- Prompt183 can mark rollback as required/candidate but does not determine concrete
  rollback files or strategy.
- Prompt184 should add rollback readiness without executing rollback.


<!-- prompt184-update -->
## Prompt184 architecture constraint update

Prompt184 adds metadata-only rollback readiness.

Authoritative rollback readiness rule:
- Prompt184 may derive rollback targets and strategy, but must not execute rollback.
- Prompt184 must prefer latest post-reentry truth when re-entry is active.
- Prompt184 must not fall back to stale normal Prompt167 write outputs when re-entry
  source is active.
- Prompt184 may set `rollback_execution_allowed_next=true` only when rollback targets
  and strategy are safe and deterministic.
- Prompt184 must not run `git checkout`, `git reset`, `git clean`, `rm`, invoke
  Codex, start another cycle, commit, create GitHub operations, retry, loop, or
  create new executors.

Current limitation:
- Rollback tracked/untracked classification relies on current git status metadata
  plus source metadata. Prompt185 must revalidate paths and plan before executing.


<!-- prompt185-update -->
## Prompt185 architecture constraint update

Prompt185 adds bounded rollback execution.

Authoritative rollback execution rule:
- Prompt185 may execute rollback only from Prompt184's safe emitted plan.
- Prompt185 must not use `git reset --hard`, `git clean -fd`, recursive deletion,
  broad globs, arbitrary rm, shell-based rollback commands, or new executors.
- Tracked rollback is limited to validated explicit files.
- Untracked/runtime removal is limited to explicitly listed safe generated/runtime
  files.
- Prompt185 must capture post-rollback status and route failures to manual review.

Current limitation:
- Prompt185 executes rollback and captures result metadata, but does not yet classify
  whether the autonomous flow can continue after rollback or must stop.
- Prompt186 should add rollback result assimilation and post-rollback routing
  metadata without executing more commands.


<!-- prompt186-update -->
## Prompt186 architecture constraint update

Prompt186 assimilates rollback execution results.

Authoritative rollback result rule:
- Rollback success means unsafe changes were recovered, not that the development
  task succeeded.
- Clean or expected-dirty rollback may route toward fix prompt generation only.
- Rollback failure, partial failure, timeout, or unexpected dirty must route to
  manual review.
- Rollback result must never be used as a commit-ready source.
- Prompt186 must not execute rollback, invoke Codex, generate prompts, commit,
  create GitHub operations, retry, loop, or create new executors.

Current limitation:
- Prompt186 can recommend `generate_fix_prompt_after_rollback`, but does not yet
  check remaining fix/failure budgets for post-rollback continuation.
- Prompt187 should add that budget-gated post-rollback continuation decision.


<!-- prompt187-update -->
## Prompt187 architecture constraint update

Prompt187 adds a post-rollback continuation gate.

Authoritative post-rollback continuation rule:
- Prompt187 must consume Prompt186 rollback result assimilation as authoritative.
- Clean or expected-dirty rollback may continue only to fix prompt generation, and
  only when fix/failure budgets allow it.
- Rollback failure, timeout, partial failure, unexpected dirty, or review-required
  states must hard-stop to manual review.
- Rollback result must never be used as a commit-ready source.
- Prompt187 must not generate prompts, invoke Codex, execute rollback, commit, create
  GitHub operations, retry, loop, or create new executors.

Current limitation:
- Prompt187 can allow post-rollback fix continuation, but it does not yet feed that
  decision into existing fix prompt readiness/generation flow.
- Prompt188 should add that handoff/readiness wiring without invoking Codex.


<!-- prompt188-update -->
## Prompt188 architecture constraint update

Prompt188 connects post-rollback fix continuation into existing fix prompt
readiness/generation metadata.

Authoritative post-rollback fix handoff rule:
- Prompt188 must consume Prompt187 post-rollback continuation gate as authoritative.
- Post-rollback fix handoff may be a positive input to existing fix readiness /
  generation only when all Prompt187 safety and budget gates pass.
- Existing fix readiness/generation gates remain authoritative.
- Prompt188 must not bypass readiness, create a new fix generator, invoke Codex,
  execute rollback, commit, create GitHub operations, retry, loop, or create new
  executors.
- Rollback-derived fix handoff must never mark commit readiness.

Current limitation:
- Prompt188 adds additive metadata fields, but same-run fix generation outcome still
  depends on existing Prompt160/161 readiness/generation refresh logic consuming
  those fields.
- Prompt189 should add that explicit consumer-side hardening.


<!-- prompt189-update -->
## Prompt189 architecture constraint update

Prompt189 makes post-rollback fix handoff an explicit positive input to the existing
fix readiness/generation refresh path.

Authoritative rule:
- Post-rollback fix handoff is a positive input only, not a safety bypass.
- Existing fix readiness/generation gates remain authoritative.
- Prompt189 must not create a new fix generator, invoke Codex, execute rollback,
  commit, create GitHub operations, retry, loop, or create new executors.
- Rollback-derived fix generation input must never mark commit readiness.

Current limitation:
- Prompt189 refreshes fix generation inputs, but downstream generated-prompt
  re-entry readiness/routing may already have been computed earlier in the pipeline.
- Prompt190 should add deterministic downstream propagation from refreshed fix
  generation outputs to the existing generated-prompt re-entry path.


<!-- prompt190-update -->
## Prompt190 architecture constraint update

Prompt190 propagates post-rollback fix generation into generated-prompt re-entry
readiness/routing metadata.

Authoritative post-rollback re-entry propagation rule:
- Prompt190 may update generated-prompt re-entry readiness/routing metadata from
  post-rollback fix generation only when Prompt189 fix generation input is effective
  and generated fix prompt path is safe.
- Prompt190 must not call or re-run Codex invocation execution.
- Prompt190 must not execute rollback, commit, create GitHub operations, retry, loop,
  or create new executors.
- Rollback-derived generated fix prompts must never mark commit readiness.
- Downstream execution must rely on a later final readiness checkpoint.

Current limitation:
- Prompt190 updates normalized metadata, but does not finalize the execution decision
  for post-rollback fix Codex re-entry.
- Prompt191 should add final downstream recompute/readiness checkpoint without
  executing Codex.


<!-- prompt191-update -->
## Prompt191 architecture constraint update

Prompt191 adds the final checkpoint for post-rollback fix re-entry readiness.

Authoritative checkpoint rule:
- Prompt191 is the final source for whether post-rollback generated fix prompt is
  ready for bounded Codex re-entry execution.
- Prompt191 must not invoke Codex, execute rollback, commit, create GitHub operations,
  retry, loop, or create new executors.
- Prompt191 must keep rollback-derived re-entry separate from commit readiness.
- Prompt192 must consume Prompt191 checkpoint fields and reuse existing bounded
  workspace-write invocation machinery instead of creating a new Codex executor.

Current limitation:
- Prompt191 only confirms readiness. It does not execute the post-rollback fix
  Codex re-entry. Prompt192 should perform exactly one guarded execution attempt.


<!-- prompt192-update -->
## Prompt192 architecture constraint update

Prompt192 adds bounded post-rollback fix Codex re-entry execution.

Authoritative execution rule:
- Prompt192 may execute Codex only when Prompt191 final checkpoint is ready.
- Prompt192 must execute at most one invocation.
- Prompt192 must reuse existing Prompt180 / Prompt167 workspace-write invocation
  machinery.
- Prompt192 must not create a new Codex executor.
- Prompt192 must not retry, loop, execute rollback, commit, tag, create GitHub
  operations, or create new executors.
- Prompt192 must emit handoff metadata for post-execution assimilation.

Current limitation:
- Prompt192 executes post-rollback fix re-entry and records result metadata, but does
  not yet classify changed files, run validation, or update cycle outcome from that
  result.
- Prompt193 should add that post-rollback-fix re-entry result assimilation and
  safety refresh without invoking Codex again.


<!-- prompt193-update -->
## Prompt193 architecture constraint update

Prompt193 routes Prompt192 post-rollback fix re-entry execution results back into
the safety/validation/cycle pipeline.

Authoritative Prompt193 result rule:
- Prompt193 is the authoritative source for commit-readiness consideration after
  post-rollback fix re-entry execution.
- Commit readiness may only consume Prompt193 when:
  `commit_candidate=true`, `cycle_passed=true`, `validation_passed=true`, and all
  changed-file safety conditions are clean.
- Rollback success, fix prompt generation success, Codex invocation completion, or
  changed-files existence alone must never be treated as commit-ready evidence.
- Prompt193 must not invoke Codex, execute rollback, commit, tag, create GitHub
  operations, retry, loop, or create new executors.

Current limitation:
- Prompt193 emits `commit_candidate`, but does not decide or execute commit/tag.
- Prompt194 should add commit/tag readiness metadata only.


<!-- prompt194-update -->
## Prompt194 architecture constraint update

Prompt194 adds metadata-only commit/tag readiness.

Authoritative commit readiness rule:
- Prompt194 may consider commit/tag readiness only from Prompt193 validated successful
  cycle truth.
- Rollback success, fix prompt generation success, Codex invocation completion, or
  changed files alone must never be treated as commit-ready evidence.
- Commit files must be derived only from Prompt193 safe allowed changed files.
- Prompt194 must not run `git add`, `git commit`, `git tag`, `git push`, invoke Codex,
  execute rollback, create GitHub operations, retry, loop, or create new executors.

Current limitation:
- Prompt194 emits commit/tag readiness metadata but does not execute git mutation.
- Prompt195 should perform bounded commit/tag execution with pre-execution
  revalidation, no broad staging, no push, and no GitHub mutation.


<!-- prompt195-update -->
## Prompt195 architecture constraint update

Prompt195 adds bounded commit/tag execution.

Authoritative commit/tag execution rule:
- Prompt195 may mutate git only when Prompt194 readiness explicitly allows commit/tag.
- Prompt195 must stage only Prompt194 `git_add_allowed_files`.
- Prompt195 must not use broad staging, commit-all, push, GitHub mutations, rollback,
  Codex invocation, retry, loop, or new executors.
- Prompt195 must run pre-mutation safety checks, `git diff --check`, and tag collision
  check.
- Prompt195 must record command/result metadata and route failures to manual review.

Current limitation:
- Prompt195 executes commit/tag and records execution metadata, but does not yet
  assimilate the outcome for post-commit handoff or next-cycle control.
- Prompt196 should add metadata-only commit/tag execution result assimilation.


<!-- prompt196-update -->
## Prompt196 architecture constraint update

Prompt196 adds metadata-only commit/tag execution result assimilation.

Authoritative post-commit handoff rule:
- Prompt196 may prepare next-cycle handoff only from successful Prompt195 commit/tag
  completion.
- Prompt196 must not infer success from Prompt194 readiness alone.
- Partial commit/tag failure, git add failure, git commit failure, git tag failure,
  timeout, blocked insufficient truth, or unexpected dirty after commit/tag must route
  to manual review.
- Prompt196 must not mutate git, push, invoke Codex, execute rollback, create GitHub
  operations, retry, loop, or create new executors.
- Prompt197 should require clean post-commit handoff for automatic continuation unless
  a future explicit policy permits expected runtime dirty files.

Current limitation:
- Prompt196 prepares next-cycle/GitHub-readiness handoff but does not choose or start
  the next autonomous cycle.
- Prompt197 should add bounded multi-cycle autonomous controller metadata only.


<!-- prompt197-update -->
## Prompt197 architecture constraint update

Prompt197 adds the bounded multi-cycle autonomous controller.

Authoritative controller rule:
- Prompt197 may decide the next safe high-level direction, but must not execute it.
- Prompt197 must not generate prompts, invoke Codex, validate, execute rollback,
  mutate git, push, create GitHub operations, retry, loop, or create new executors.
- Prompt197 must prioritize newer Prompt196 commit/tag assimilation over older cycle
  states.
- Automatic next-cycle continuation requires clean post-commit state.
- Budget exhaustion and manual-review signals must stop automation.

Current limitation:
- Prompt197 chooses high-level intent, but does not enforce a single downstream lane
  contract.
- Prompt198 should add terminal lane selection with strict mutual exclusivity.


<!-- prompt198-update -->
## Prompt198 architecture constraint update

Prompt198 adds the terminal single-lane decision gate.

Authoritative lane decision rule:
- Prompt198 converts Prompt197 controller intent into exactly one selected lane.
- Conflicting non-stop lanes must block to manual review.
- GitHub lane is disabled until explicit GitHub readiness is implemented.
- Prompt198 must not execute selected lane, generate prompts, invoke Codex, validate,
  execute rollback, mutate git, push, create GitHub operations, retry, loop, or
  create new executors.

Current limitation:
- Prompt198 emits `lane_contract_payload`, but does not validate its schema beyond
  construction and does not refresh downstream flow inputs.
- Prompt199 should add lane contract validation/guard metadata only.


<!-- prompt199-update -->
## Prompt199 architecture constraint update

Prompt199 adds lane contract validation before downstream refresh.

Authoritative lane contract rule:
- Prompt199 is the guard for Prompt198 selected lane contracts.
- Only validated, non-conflicting, non-stop, non-GitHub lane contracts may be passed
  to downstream refresh.
- Manual-stop, malformed, conflicting, GitHub-disabled, or unsafe contracts must not
  trigger downstream execution.
- Prompt199 must not generate prompts, invoke Codex, validate code, execute rollback,
  mutate git, push, create GitHub operations, retry, loop, or create new executors.

Current limitation:
- Prompt199 validates the lane contract but does not yet dispatch it to existing
  downstream readiness/generation flows.
- Prompt200 should add metadata-only downstream refresh dispatch for exactly one
  guarded lane.


<!-- prompt200-update -->
## Prompt200 architecture constraint update

Prompt200 adds guarded lane downstream refresh dispatch.

Authoritative dispatch rule:
- Prompt200 may dispatch only one validated lane from Prompt199.
- Prompt200 must not execute the lane.
- Prompt200 must not generate prompts, invoke Codex, validate code, execute rollback,
  mutate git, push, create GitHub operations, retry, loop, or create new executors.
- Multiple downstream refreshes must block to manual review.
- GitHub lane remains disabled until explicit GitHub readiness is implemented.

Current limitation:
- Prompt200 connects the selected guarded lane to existing downstream metadata, but
  does not execute the selected lane action.
- Prompt201 should execute exactly one selected bounded lane action and keep all
  non-selected lanes as no-op.


<!-- prompt201-update -->
## Prompt201 architecture constraint update

Prompt201 adds exactly-one selected lane action execution.

Authoritative selected-lane execution rule:
- Prompt201 may execute only the single lane selected and dispatched by Prompt200.
- Non-selected lanes must remain no-op.
- Prompt201 must not invoke Codex, execute rollback, run validation, mutate git,
  push, call GitHub, retry, loop, or create new executors.
- Prompt201 may only execute:
  - existing next/fix prompt generation readiness outcome paths
  - rollback readiness refresh
  - commit/tag readiness refresh
  - manual stop no-op
- Prompt201 must always emit Prompt202 assimilation handoff metadata.

Current limitation:
- Prompt201 executes the selected lane action, but does not yet classify the result
  as controller feedback.
- Prompt202 should add selected action result assimilation and feedback routing.


<!-- prompt202-update -->
## Prompt202 architecture constraint update

Prompt202 adds selected lane result assimilation and controller feedback.

Authoritative feedback rule:
- Prompt202 may derive controller feedback only from Prompt201 selected lane execution.
- Prompt202 must not infer success from lane selection, contract validation, or dispatch
  metadata alone.
- Successful non-stop selected lane results require non-selected lanes to remain no-op.
- Prompt202 must not generate prompts, invoke Codex, validate, execute rollback,
  mutate git, push, create GitHub operations, retry, loop, or create new executors.

Current limitation:
- Prompt202 emits controller feedback and next-controller input metadata, but does not
  yet define the bounded local loop contract that decides whether the next step may
  proceed.
- Prompt203 should add that local loop contract metadata only.


<!-- prompt203-update -->
## Prompt203 architecture constraint update

Prompt203 adds bounded local loop contract metadata.

Authoritative local loop contract rule:
- Prompt203 may derive local loop contract only from Prompt202 selected-lane feedback.
- Prompt203 must not execute the contract action.
- Non-manual-stop contracts require sufficient budget truth and clean safety signals.
- Generated prompt re-entry contracts require fixed prompt path truth.
- Rollback execution contracts require rollback readiness and rollback budget.
- Commit execution contracts require commit readiness and commit budget.
- Prompt203 must not generate prompts, invoke Codex, validate, execute rollback,
  mutate git, push, create GitHub operations, retry, loop, or create new executors.

Current limitation:
- Prompt203 emits local loop contract metadata but does not yet produce a strict
  single next-step launch contract.
- Prompt204 should create exactly one non-executing launch contract or manual-stop
  contract.


<!-- prompt204-update -->
## Prompt204 architecture constraint update

Prompt204 adds a single bounded next-step launch contract.

Authoritative launch-contract rule:
- Prompt204 may derive launch readiness only from Prompt203 bounded local loop
  contract metadata.
- Prompt204 must select exactly one launch contract or manual stop.
- Prompt204 must not execute the launch contract.
- Prompt204 must not create new executors.
- Generated prompt re-entry launch is not direct Codex invocation; it must pass
  through existing generated-prompt re-entry readiness/routing/execution gates.
- Rollback execution launch must use the existing bounded rollback execution path.
- Commit execution launch must use the existing bounded commit/tag execution path.
- Prompt204 must not invoke Codex, execute rollback, commit/tag, validate, generate
  prompts, push, create GitHub operations, retry, loop, or create new executors.

Current limitation:
- Prompt204 emits the launch contract but does not execute it.
- Prompt205 should execute exactly one selected launch via existing bounded paths and
  emit result handoff metadata for Prompt206.


<!-- prompt205-update -->
## Prompt205 architecture constraint update

Prompt205 adds next-step launch execution integration.

Authoritative launch execution rule:
- Prompt205 may integrate exactly one launch kind selected by Prompt204.
- Prompt205 must not create new executors.
- Prompt205 must not run multiple launches.
- Prompt205 must not push, call GitHub, retry, loop, create daemons, schedulers, or
  queue drainers.
- Generated prompt re-entry launch must use existing re-entry invocation metadata/path.
- Rollback execution launch must use existing bounded rollback execution metadata/path.
- Commit execution launch must use existing bounded commit/tag execution metadata/path.
- Non-selected launch kinds must remain no-op.
- Prompt205 must always emit Prompt206 result assimilation handoff metadata.

Current limitation:
- Prompt205 integrates delegated launch execution state, but does not yet classify
  launch result outcomes into controller feedback.
- Prompt206 should add next-step launch result assimilation metadata only.


<!-- prompt206-update -->
## Prompt206 architecture constraint update

Prompt206 adds next-step launch result assimilation.

Authoritative launch-result rule:
- Prompt206 may derive launch-result feedback only from Prompt205 next-step launch
  execution output.
- Prompt206 must not infer launch-result success from Prompt204 launch contract or
  Prompt203 local loop contract alone.
- Successful non-stop launch results require non-selected launches to remain no-op.
- Prompt206 must not continue the local loop directly.
- Prompt206 must not generate prompts, invoke Codex, validate, execute rollback,
  mutate git, push, create GitHub operations, retry, loop, or create new executors.

Current limitation:
- Prompt206 emits launch-result feedback, but does not yet select the next bounded
  control contract.
- Prompt207 should reconcile Prompt206 feedback into exactly one next control
  contract without executing it.


<!-- prompt207-update -->
## Prompt207 architecture constraint update

Prompt207 adds bounded local control decision reconciliation.

Authoritative control-decision rule:
- Prompt207 may derive the next control contract only from Prompt206 launch-result
  feedback.
- Prompt207 must not infer control readiness from Prompt205 launch execution or
  Prompt204 launch contract alone.
- Prompt207 must select exactly one non-stop control contract or stop/block.
- Terminal delegated status truth is required before non-stop assimilation routing.
- Prompt207 must not dispatch assimilation, generate prompts, invoke Codex, validate,
  execute rollback, execute commit/tag, push, create GitHub operations, retry, loop,
  or create new executors.

Current limitation:
- Prompt207 emits the selected control contract but does not dispatch it to the
  corresponding existing assimilation path.
- Prompt208 should add metadata-only dispatch to exactly one existing assimilation
  path.


<!-- prompt208-update -->
## Prompt208 architecture constraint update

Prompt208 adds control contract dispatch metadata.

Authoritative dispatch rule:
- Prompt208 may dispatch only the single selected control contract from Prompt207.
- Prompt208 must not infer dispatch readiness from Prompt206 or older assimilation maps alone.
- Prompt208 may add selected-path-only additive metadata to existing assimilation maps.
- Prompt208 must not execute assimilation, generate prompts, invoke Codex, validate,
  execute rollback, execute commit/tag, mutate git, push, create GitHub operations,
  retry, loop, or create new executors.
- Multiple dispatch paths must block to manual review.
- Manual-stop and blocked contracts must not trigger downstream assimilation refresh.

Current limitation:
- Prompt208 dispatches metadata to the selected assimilation path, but does not refresh
  that path or classify the dispatch result.
- Prompt209 should perform exactly one bounded assimilation refresh from the selected
  dispatch and emit Prompt210 handoff metadata.


<!-- prompt209-update -->
## Prompt209 architecture constraint update

Prompt209 adds exactly-one downstream assimilation refresh.

Authoritative refresh rule:
- Prompt209 may refresh only the single selected assimilation path dispatched by
  Prompt208.
- Prompt209 must not infer refresh readiness from Prompt207 or older assimilation maps alone.
- Prompt209 must not execute Codex, rollback, commit/tag, validation, prompt
  generation, git mutation, push, GitHub operation, retry, loop, or create new
  executors.
- Non-selected assimilation paths must remain no-op.
- Multiple refresh paths must block to manual review.
- Prompt209 must always emit Prompt210 result assimilation handoff metadata.

Current limitation:
- Prompt209 emits refresh result metadata, but does not yet classify it into final
  controller feedback / next bounded control target.
- Prompt210 should add that metadata-only classification.


<!-- prompt210-update -->
## Prompt210 architecture constraint update

Prompt210 adds control dispatch refresh result assimilation and final controller feedback.

Authoritative feedback rule:
- Prompt210 may derive final controller feedback only from Prompt209 control dispatch refresh result.
- Prompt210 must not infer final feedback from Prompt208 dispatch, Prompt207 control decision, or older assimilation maps alone.
- Safe completed selected assimilation refresh results may target the multi-cycle controller via:
  `prepare_next_multi_cycle_decision`.
- Prompt210 must not start the next loop step.
- `should_continue_local_loop` remains false.
- Prompt210 must not generate prompts, invoke Codex, validate, execute rollback,
  execute commit/tag, mutate git, push, create GitHub operations, retry, loop, or
  create new executors.

Current limitation:
- Prompt210 emits a next bounded control target for the multi-cycle controller, but
  does not decide whether the runtime may continue.
- Prompt211 should add the final runtime continuation guard.


<!-- prompt211-update -->
## Prompt211 architecture constraint update

Prompt211 adds the final runtime continuation guard.

Authoritative continuation rule:
- Prompt211 may allow multi-cycle handback only from Prompt210 final controller feedback.
- Prompt211 must not infer continuation from Prompt197, Prompt209, or older controller
  states alone.
- Prompt211 must not start the next step.
- Prompt211 must keep:
  - `should_continue_local_loop=false`
  - `should_start_unbounded_loop=false`
- Prompt211 must block continuation on:
  - manual review
  - stop
  - unsafe state
  - dirty state
  - conflict state
  - forbidden execution flags
  - missing/empty budget truth
  - cycle budget exhaustion
- Prompt211 must not generate prompts, invoke Codex, validate, execute rollback,
  execute commit/tag, mutate git, push, call GitHub, retry, loop, or create new
  executors.

Current limitation:
- Prompt211 decides whether handback to the multi-cycle controller is safe, but it
  does not coordinate the next bounded step.
- Prompt212 should build the one-bounded continuation coordinator.


<!-- prompt212-update -->
## Prompt212 architecture constraint update

Prompt212 adds a one-bounded local continuation coordinator.

Authoritative continuation coordinator rule:
- Prompt212 may coordinate continuation only from Prompt211 final runtime continuation guard.
- Prompt212 must not infer continuation from Prompt210 or Prompt197 alone.
- Prompt212 may set `should_continue_local_loop=true` only as a one-bounded handback contract.
- `should_continue_local_loop=true` must mean:
  - max next steps = 1
  - no unbounded loop
  - no daemon
  - no scheduler
  - no queue drain
  - no retry loop
  - no recursive self-invocation
- Prompt212 must not call or re-run the multi-cycle controller.
- Prompt212 must not invoke Codex, execute rollback, execute commit/tag, validate,
  generate prompts, mutate git, push, create GitHub operations, retry, loop, or
  create new executors.
- Prompt213 must verify stale/fresh state and execution ordering before any direct
  re-trigger coordinator is allowed.


<!-- prompt213-update -->
## Prompt213 architecture constraint update

Prompt213 adds stale/fresh ordering verification and Prompt214 preflight metadata.

Authoritative preflight rule:
- Prompt213 may prepare Prompt214 direct retrigger only from Prompt212 one-bounded
  continuation coordinator output.
- Prompt213 must not infer retrigger readiness from Prompt211 or Prompt197 alone.
- Prompt213 emits only preflight metadata; it must not perform direct retrigger.
- Prompt213 must not invoke Codex, execute rollback, execute commit/tag, validate,
  generate prompts, mutate git, push, create GitHub operations, retry, loop, or
  create new executors.
- Prompt214 must not blindly trust Prompt213; it must revalidate:
  - `prompt214_retrigger_ready=true`
  - `prompt214_retrigger_source="prompt213_stale_fresh_ordering_gate"`
  - `prompt214_retrigger_contract`
  - exactly one selected retrigger kind
  - no stale-block/manual-stop/blocked/conflict condition
  - required existing bounded path availability.


<!-- prompt214-update -->
## Prompt214 architecture constraint update

Prompt214 adds exactly-one bounded direct re-trigger coordination.

Authoritative direct-retrigger rule:
- Prompt214 may proceed only from Prompt213 stale/fresh ordering gate preflight.
- Prompt214 must revalidate Prompt213 preflight contract before any selected retrigger classification.
- Prompt214 must select exactly one retrigger kind or manual stop / blocked.
- Prompt214 must not create new executors.
- Prompt214 must not retry, loop, push, call GitHub, start daemons, start schedulers,
  drain queues, or create background workers.
- Prompt214 must emit Prompt215 handoff metadata for all completed / manual-stop /
  blocked outcomes.
- Prompt214 classification is currently based on existing bounded-path truth surfaces.
- Prompt215 must distinguish:
  - fresh attempted bounded path
  - existing truth surface classification
  - stale truth only
  - blocked / manual-stop / failed


<!-- prompt215-update -->
## Prompt215 architecture constraint update

Prompt215 adds direct re-trigger result assimilation.

Authoritative result-assimilation rule:
- Prompt215 may classify direct re-trigger results only from Prompt214 handoff metadata.
- Prompt215 must not infer direct re-trigger result from Prompt213 preflight or
  Prompt212 continuation contract alone.
- Prompt215 must distinguish:
  - fresh attempted bounded path
  - existing truth surface classification
  - stale truth only
  - existing bounded path not callable
  - blocked / failed / manual stop
- Prompt215 must not generate prompts, invoke Codex, validate, execute rollback,
  execute commit/tag, mutate git, push, create GitHub operations, retry, loop, or
  create new executors.
- Prompt215 must not start another loop step.
- Prompt216 should select exactly one next safe follow-up contract from Prompt215
  classification.


<!-- prompt216-update -->
## Prompt216 architecture constraint update

Prompt216 adds direct re-trigger follow-up guard metadata.

Authoritative follow-up rule:
- Prompt216 may select follow-up only from Prompt215 direct re-trigger result
  assimilation.
- Prompt216 must not infer follow-up directly from Prompt214 coordinator or
  Prompt213 preflight.
- Prompt216 must select exactly one follow-up target or stop/block.
- Stale truth, not-callable bounded paths, failed, blocked, insufficient-truth, and
  manual-stop outcomes must not proceed to bounded multi-step continuation.
- Completed existing truth may proceed only with metadata preserving that fresh
  runtime attempt was not proven.
- Prompt216 must not execute the follow-up contract.
- Prompt216 must not generate prompts, invoke Codex, validate, execute rollback,
  execute commit/tag, mutate git, push, create GitHub operations, retry, loop, or
  create new executors.
- Prompt217 must revalidate Prompt216 multistep contract before any bounded
  multi-step handoff.


<!-- prompt217-update -->
## Prompt217 architecture constraint update

Prompt217 adds bounded multi-step handoff guard metadata.

Authoritative bounded handoff rule:
- Prompt217 may prepare bounded execution only from Prompt216 direct re-trigger
  follow-up guard output.
- Prompt217 must not infer bounded execution readiness from Prompt215, Prompt214, or
  older controller states alone.
- Prompt217 must revalidate Prompt216 multistep contract before preparing Prompt218.
- Prompt217 must preserve:
  - `max_next_steps=1`
  - `allow_unbounded_loop=false`
  - no retry
  - stop-policy guard required
  - budget guard required
  - result-assimilation required
- Prompt217 must preserve existing-truth revalidation metadata when fresh runtime
  attempt was not proven.
- Prompt217 must not execute multi-step actions.
- Prompt217 must not generate prompts, invoke Codex, validate, execute rollback,
  execute commit/tag, mutate git, push, create GitHub operations, retry, loop, or
  create new executors.
- Prompt218 must revalidate Prompt217 execution preflight before any bounded action.


<!-- prompt218-update -->
## Prompt218 architecture constraint update

Prompt218 adds bounded multi-step execution coordinator metadata.

Authoritative execution-coordinator rule:
- Prompt218 may derive bounded action execution only from Prompt217 bounded
  multi-step handoff guard output.
- Prompt218 must not infer execution readiness from Prompt216, Prompt215, or older
  controller states alone.
- Prompt218 must revalidate Prompt217 execution preflight before deriving action.
- Prompt218 must select exactly one bounded action or stop/block.
- Prompt218 remains bounded:
  - `max_next_steps=1`
  - no retry
  - no unbounded loop
  - no new executor
  - no push
  - no GitHub operation
- Prompt218 delegates metadata-only to existing bounded-path truth surfaces.
- Fresh runtime execution is not proven unless path-specific attempted / terminal
  metadata exists.
- Prompt219 must classify Prompt218 outcomes into fresh action, existing-truth
  revalidated, existing path block, manual stop, blocked, failed, or insufficient
  truth.


<!-- prompt219-update -->
## Prompt219 architecture constraint update

Prompt219 adds bounded multi-step execution result assimilation.

Authoritative bounded result rule:
- Prompt219 may classify bounded multi-step execution results only from Prompt218
  result handoff metadata.
- Prompt219 must not infer execution result from Prompt217 preflight or Prompt216
  follow-up guard alone.
- Prompt219 must distinguish:
  - completed fresh action
  - completed existing truth revalidated
  - blocked existing truth revalidation
  - blocked existing path
  - blocked non-selected action activity
  - manual stop / failed / blocked / insufficient truth
- Prompt219 must not start another loop step.
- Prompt219 must keep:
  - `should_continue_local_loop=false`
  - `should_start_unbounded_loop=false`
- Prompt219 must not generate prompts, invoke Codex, validate, execute rollback,
  execute commit/tag, mutate git, push, create GitHub operations, retry, loop, or
  create new executors.
- Prompt220 must use Prompt219 as the sole bounded continuation decision input.


<!-- prompt220-update -->
## Prompt220 architecture constraint update

Prompt220 adds bounded continuation decision metadata.

Authoritative bounded continuation rule:
- Prompt220 may select bounded continuation only from Prompt219 bounded multi-step
  execution result assimilation.
- Prompt220 must not infer continuation from Prompt218, Prompt217, or older
  bounded-path states alone.
- Prompt220 must distinguish:
  - completed fresh action
  - completed existing truth revalidated
  - manual stop
  - blocked / failed / insufficient truth
- Prompt220 must emit only bounded preflight metadata for Prompt221.
- Prompt220 must preserve:
  - `max_continuation_steps=1`
  - `allow_unbounded_loop=false`
  - `allow_retry=false`
  - no retry
  - no loop start
- Prompt220 must not generate prompts, invoke Codex, validate, execute rollback,
  execute commit/tag, mutate git, push, create GitHub operations, retry, loop, or
  create new executors.
- Prompt221 must consume Prompt220's Prompt221 preflight contract as the sole
  continuation input and must not raise continuation steps above 1.


<!-- prompt221-update -->
## Prompt221 architecture constraint update

Prompt221 adds bounded N-step coordinator metadata with `max_continuation_steps=1`.

Authoritative bounded N-step rule:
- Prompt221 may coordinate bounded continuation only from Prompt220 bounded
  continuation decision preflight.
- Prompt221 must not infer N-step readiness from Prompt219, Prompt218, or older
  states alone.
- Prompt221 must keep:
  - `max_continuation_steps=1`
  - `actual_steps_attempted<=1`
  - `actual_steps_completed<=1`
  - `allow_unbounded_loop=false`
  - `allow_retry=false`
- Prompt221 must coordinate only existing bounded surfaces.
- Prompt221 must not create new executors, retry, loop, push, call GitHub, run
  tests, edit docs, or start daemon / scheduler / queue / background workers.
- Prompt221 must always emit Prompt222 result handoff metadata.
- Prompt222 must classify Prompt221 output and decide whether any later prompt may
  safely raise the continuation bound beyond 1.


<!-- prompt222-update -->
## Prompt222 architecture constraint update

Prompt222 adds bounded N-step result assimilation and stop-policy hardening.

Authoritative bounded N-step result rule:
- Prompt222 may classify bounded N-step result only from Prompt221 result handoff.
- Prompt222 must not infer result from Prompt220 preflight, Prompt219 assimilation,
  or older states alone.
- Prompt222 must verify:
  - one-step accounting
  - non-selected step no-op
  - terminal result evidence
  - stop-policy pass/fail
- Prompt222 must not raise `max_continuation_steps` above 1.
- Prompt222 may only emit metadata indicating whether a future prompt may prepare
  raise-to-2 preflight.
- N=2 may be considered only when Prompt222 reports:
  - `result_class=="completed_fresh_surface"`
  - `n_step_runtime_safety_confidence=="high"`
  - `n_step_raise_to_2_candidate=true`
  - `one_step_accounting_valid=true`
  - `non_selected_steps_noop_confirmed=true`
  - `stop_policy_passed=true`
- Existing-truth-only and guarded-existing-truth outcomes must not directly raise
  N to 2.
- Prompt222 must not generate prompts, invoke Codex, validate, execute rollback,
  execute commit/tag, mutate git, push, create GitHub operations, retry, loop, or
  create new executors.


<!-- prompt223-update -->
## Prompt223 architecture constraint update

Prompt223 adds raise-to-2 preflight decision metadata.

Authoritative raise-to-2 rule:
- Prompt223 may consider N=2 only from Prompt222 bounded N-step result assimilation.
- Prompt223 must not infer raise-to-2 readiness from Prompt221, Prompt220, or older
  state alone.
- N=2 may be prepared only when Prompt222 proves:
  - `result_class=="completed_fresh_surface"`
  - `completed_fresh_surface_detected=true`
  - `n_step_runtime_safety_confidence=="high"`
  - `one_step_accounting_valid=true`
  - `non_selected_steps_noop_confirmed=true`
  - `stop_policy_passed=true`
  - terminal result/source evidence exists
  - budget truth is checked and sufficient
- Existing-truth-only and guarded-existing-truth outcomes must not raise to N=2.
- Prompt223 must emit only Prompt224 N=2 preflight metadata.
- Prompt223 must not execute N=2, generate prompts, invoke Codex, validate, execute
  rollback, execute commit/tag, mutate git, push, create GitHub operations, retry,
  loop, or create new executors.
- Prompt224 must revalidate Prompt223's N=2 contract and enforce per-step guards
  before any future execution coordinator may run.


<!-- prompt224-update -->
## Prompt224 architecture constraint update

Prompt224 adds bounded N=2 execution preflight consumer metadata.

Authoritative N=2 preflight rule:
- Prompt224 may prepare N=2 execution only from Prompt223 raise-to-2 preflight
  decision output.
- Prompt224 must not infer N=2 execution readiness from Prompt222, Prompt221, or
  older state alone.
- Prompt224 must revalidate the Prompt223 N=2 contract before preparing Prompt225.
- Prompt224 must preserve:
  - `max_continuation_steps=2`
  - `allow_unbounded_loop=false`
  - `allow_retry=false`
  - per-step stop-policy guard required
  - per-step budget guard required
  - per-step result-assimilation guard required
  - per-step fresh-surface evidence required
- Prompt224 must not execute step1 or step2.
- Prompt224 must not generate prompts, invoke Codex, validate, execute rollback,
  execute commit/tag, mutate git, push, create GitHub operations, retry, loop, or
  create new executors.
- Prompt225 must revalidate Prompt224's execution coordinator preflight before any
  step coordination.
- Prompt225 must attempt step2 only after step1 completes safely and post-step1
  stop / budget / result-assimilation / fresh-evidence checks pass.


<!-- prompt225-update -->
## Prompt225 architecture constraint update

Prompt225 adds bounded N=2 execution coordinator metadata.

Authoritative N=2 execution rule:
- Prompt225 may coordinate N=2 only from Prompt224 bounded N=2 execution preflight.
- Prompt225 must not infer N=2 execution readiness from Prompt223, Prompt222, or
  older state alone.
- Prompt225 must preserve:
  - `max_continuation_steps=2`
  - `allow_unbounded_loop=false`
  - `allow_retry=false`
  - no new executor
  - no push / GitHub operation
  - no daemon / scheduler / queue drain
- Prompt225 must coordinate step1 before step2.
- Prompt225 must not attempt step2 unless step1 completes safely and post-step1
  stop / budget / result-assimilation / fresh-evidence guards pass.
- Prompt225 must always emit Prompt226 result handoff metadata.
- Prompt226 must classify whether Prompt225 produced:
  - two fresh runtime steps
  - one fresh runtime step
  - existing truth only
  - blocked step1
  - blocked step2
  - manual stop / failed / insufficient truth.


<!-- prompt226-update -->
## Prompt226 architecture constraint update

Prompt226 adds bounded N=2 execution result assimilation.

Authoritative N=2 result rule:
- Prompt226 may classify bounded N=2 result only from Prompt225 result handoff.
- Prompt226 must not infer N=2 result from Prompt224 preflight, Prompt223 raise gate,
  or older states alone.
- Prompt226 must validate:
  - 0..2 step accounting
  - step2-after-step1 constraint
  - non-selected step no-op
  - fresh runtime evidence
  - existing-truth-only result
  - manual stop / blocked / failed / insufficient truth
- `fresh_runtime_execution_confirmed=true` only when two fresh runtime steps are
  detected.
- One fresh step or existing-truth-only outcomes may proceed only to an E2E or
  fresh-runtime-evidence gate, not to further raising.
- Prompt226 must keep:
  - `further_raise_candidate=false`
  - no local loop continuation
  - no unbounded loop
  - no retry
  - no push / GitHub operation
- Prompt226 must not generate prompts, invoke Codex, validate, execute rollback,
  execute commit/tag, mutate git, push, create GitHub operations, retry, loop, or
  create new executors.
- Prompt227 must consume Prompt226 as the sole next-stage decision input.


<!-- prompt227-update -->
## Prompt227 architecture constraint update

Prompt227 adds bounded N=2 post-result decision metadata.

Authoritative post-result decision rule:
- Prompt227 may choose the next post-N=2 contract only from Prompt226 bounded N=2
  execution result assimilation.
- Prompt227 must not infer next contract readiness from Prompt225, Prompt224, or
  older state alone.
- Prompt227 must choose exactly one next contract:
  - end-to-end flow check
  - fresh runtime evidence gate
  - manual stop
  - blocked
- If `fresh_runtime_execution_confirmed=false`, Prompt227 must prefer fresh runtime
  evidence gate over E2E flow check.
- If `fresh_runtime_execution_confirmed=true`, Prompt227 may prepare E2E flow check.
- Prompt227 must not raise beyond N=2.
- Prompt227 must not execute E2E checks, fresh runtime checks, prompt generation,
  Codex invocation, validation, rollback, commit/tag, git mutation, push, GitHub
  operations, retry, loop, or create new executors.
- Prompt228 must consume only the selected Prompt227 contract and must not execute
  both E2E and fresh-runtime-evidence paths.


<!-- prompt228-update -->
## Prompt228 architecture constraint update

Prompt228 adds selected post-N=2 preflight consumer metadata.

Authoritative selected preflight rule:
- Prompt228 may prepare the next stage only from Prompt227 selected contract output.
- Prompt228 must not infer readiness from Prompt226, Prompt225, or older state alone.
- Prompt228 must select exactly one:
  - E2E flow check preflight
  - fresh runtime evidence preflight
  - manual stop
  - blocked
- Prompt228 must not execute E2E checks, fresh runtime evidence checks, prompt
  generation, Codex invocation, validation, rollback, commit/tag, git mutation,
  push, GitHub operations, retry, loop, or raise beyond N=2.
- Prompt229 must consume only the selected Prompt228 contract and validate local-only
  / no-push / no-GitHub / no-retry / no-loop constraints before any runnable stage.

## Prompt228-fix6 constraint update

Prompt228-fix6 confirmed that N=2 raise is currently blocked by genuine upstream Prompt222 truth, not by a Prompt222→223 or Prompt223→224 field-name mismatch.

Current authoritative chain behavior:
- Prompt222 is authoritative but blocked:
  - one_step_accounting_valid=false
  - completed_fresh_surface_detected=false
  - stop_policy_passed=false
  - manual_review_required=true
  - should_stop=true
- Prompt223 correctly remains not allowed:
  - prompt222_authoritative=true
  - raise_to_2_decision_allowed=false
  - raise_to_2_decision_block_reason=blocked_not_completed_fresh_surface
- Prompt224 now reports a precise upstream-derived block reason:
  - blocked_prompt222_not_fresh_surface

Architecture constraint:
- Do not force N=2 readiness when Prompt222 lacks fresh successful one-step evidence.
- Do not weaken Prompt226 step-accounting validation.
- Downstream stages may improve block-reason propagation, but must not relax authority, no-loop, no-retry, no-push, or no-executor boundaries.

## Prompt228-fix7 constraint update

Prompt228-fix7 confirmed that zero-step N=2 no-attempt paths must not be classified as step-accounting violations when N=2 was never authorized.

Current behavior:
- Prompt224 exposes the precise upstream block reason:
  - blocked_prompt222_not_fresh_surface
- Prompt225 preserves that reason:
  - n2_execution_block_reason=blocked_prompt222_not_fresh_surface
- Prompt226 classifies zero-step no-attempt/manual-stop coherently:
  - status=bounded_n2_result_manual_stop
  - result_class=manual_stop
  - result_block_reason=blocked_prompt222_not_fresh_surface

Architecture constraints:
- Do not weaken real step-accounting violations.
- Do not force N=2 readiness when Prompt222 lacks fresh successful one-step evidence.
- Downstream stages should preserve specific upstream block reasons while also exposing stable reason families.
- No-loop, no-retry, no-push, no-GitHub, and no-new-executor boundaries remain mandatory.

## Prompt228-fix8 constraint update

Prompt228-fix8 added stable reason taxonomy surfaces across Prompt224→228.

Current N=2 blocked/manual-stop taxonomy behavior:
- Prompt224/225/226 preserve the root specific reason:
  - primary_reason=blocked_prompt222_not_fresh_surface
  - reason_family=fresh_surface_missing
  - upstream_reason_source=prompt222_bounded_n_step_result_assimilation
- Prompt227/228 remain safe manual-stop:
  - reason_family=manual_stop
- Prompt229 readiness remains false for the current no-fresh-surface path.

Architecture constraints:
- Downstream routing should prefer reason_family over parsing raw blocked_* tokens.
- primary_reason must remain available for diagnostics.
- Existing raw block reason fields must remain backward-compatible.
- Do not relax N=2 authority, readiness, accounting, no-loop, no-retry, no-push, no-GitHub, or no-new-executor boundaries.

## Prompt228-fix9 constraint update

Prompt228-fix9 added a consolidated N=2 reason taxonomy readout surface.

Current readout behavior:
- Terminal selected stage:
  - selected_reason_stage=prompt228_selected_post_n2_preflight
  - selected_reason_family=manual_stop
  - selected_primary_reason=blocked_manual_review_required
- Root cause:
  - root_cause_reason_family=fresh_surface_missing
  - root_cause_primary_reason=blocked_prompt222_not_fresh_surface
  - root_cause_upstream_reason_source=prompt222_bounded_n_step_result_assimilation
- Prompt229 readiness remains false.

Architecture constraints:
- Use selected_reason_family for immediate downstream action routing.
- Use root_cause_reason_family/root_cause_primary_reason for diagnosis and remediation routing.
- Do not infer Prompt229 readiness from reason_family alone.
- Prompt229 readiness must remain controlled by explicit Prompt228 readiness booleans.
- Existing no-loop, no-retry, no-push, no-GitHub, no-new-executor, and accounting-safety boundaries remain mandatory.

## Prompt228-fix10 constraint update

Prompt228-fix10 added an explicit N=2 reason consumer policy surface.

Current policy behavior:
- selected_reason_family is for immediate action routing.
- root_cause_reason_family is for remediation and diagnostics.
- Prompt229 readiness must be controlled only by explicit Prompt228 readiness booleans.
- reason_family alone must never make Prompt229 ready.

Current dry-run policy:
- selected_reason_family=manual_stop
- root_cause_reason_family=fresh_surface_missing
- prompt229_allowed_by_policy=false
- should_prepare_prompt229=false
- should_prepare_manual_review=true
- should_preserve_manual_stop=true

Architecture constraints:
- Downstream consumers should use project_browser_autonomous_bounded_n2_reason_consumer_policy_* before legacy raw reason tokens.
- Legacy raw reason tokens remain diagnostic/backward-compatible only.
- Do not infer execution readiness from selected_reason_family or root_cause_reason_family alone.
- Existing no-loop, no-retry, no-push, no-GitHub, no-new-executor, and accounting-safety boundaries remain mandatory.

## Prompt228-fix11 constraint update

Prompt228-fix11 added a downstream N=2 policy conformance gate.

Current conformance behavior:
- policy_surface_available=true
- policy_surface_authoritative=true
- legacy_token_only_routing_detected=false
- reason_family_routing_available=true
- root_cause_routing_available=true
- prompt229_readiness_policy_respected=true
- conformance_passed=true
- should_prepare_prompt229=false
- should_prepare_manual_review=true

Architecture constraints:
- Downstream routing must prefer project_browser_autonomous_bounded_n2_policy_conformance_gate_* over legacy raw reason-token parsing.
- Prompt229 readiness must remain controlled by explicit Prompt228 readiness booleans.
- reason_family/root_cause_reason_family may guide routing and remediation, but must not imply execution readiness by themselves.
- Existing no-loop, no-retry, no-push, no-GitHub, no-new-executor, and accounting-safety boundaries remain mandatory.

## Prompt228-fix12 constraint update

Prompt228-fix12 added a canonical Prompt229 handoff packet.

Current handoff behavior:
- handoff_ready=false
- selected_prompt229_path=none
- prompt229_handoff_block_reason=prompt228_not_ready
- selected_reason_family=manual_stop
- root_cause_reason_family=fresh_surface_missing
- should_prepare_prompt229=false
- should_prepare_manual_review=true
- should_stop=true

Architecture constraints:
- Prompt229+ should read project_browser_autonomous_bounded_n2_prompt229_handoff_packet_* as the canonical handoff surface.
- Do not infer Prompt229 readiness from reason_family alone.
- Prompt229 readiness must remain controlled by explicit readiness booleans and the handoff packet.
- The current blocker is fresh_surface_missing; next work should prepare fresh runtime evidence / E2E readiness without adding execution, push, GitHub, retry, or unbounded-loop behavior.

## Prompt229 architecture note - fresh runtime E2E readiness gate

Prompt229 adds a metadata-only readiness gate:

- Prefix:
  - project_browser_autonomous_fresh_runtime_e2e_readiness_gate_*
- Source:
  - project_browser_autonomous_bounded_n2_prompt229_handoff_packet_*
- Root cause handled:
  - root_cause_reason_family=fresh_surface_missing
- Contract emitted:
  - project_browser_autonomous_fresh_runtime_e2e_readiness_gate_prompt230_check_contract
  - project_browser_autonomous_fresh_runtime_e2e_readiness_gate_check_command_contract
  - expected_output_files
  - success_criteria
  - failure_triage_fields

Interpretation rule:

- prompt230_check_ready=true means Prompt230 may prepare/check fresh runtime evidence metadata.
- It does not mean fresh runtime evidence already exists.
- It does not authorize Codex execution, rollback, commit, tag, push, GitHub mutation, retry, unbounded loop, or N=2 execution.

Current next step:

- Prompt230 should consume the Prompt229 contract and expose project_browser_autonomous_fresh_runtime_evidence_check_* without mutating git state or invoking Codex.

## Prompt230 architecture note - fresh runtime evidence check surface

Prompt230 adds a metadata-only evidence check surface:

- Prefix:
  - project_browser_autonomous_fresh_runtime_evidence_check_*
- Source:
  - project_browser_autonomous_fresh_runtime_e2e_readiness_gate_*
- Current status:
  - fresh_runtime_evidence_check_prepared
- Current interpretation:
  - Prompt230 consumed the Prompt229 check contract.
  - It did not execute the check command.
  - It did not observe fresh runtime evidence.
  - Therefore completed_fresh_surface_detected, one_step_accounting_valid, and stop_policy_passed remain false.
- Safety invariant:
  - should_execute_check_command=false
  - should_invoke_codex=false
  - should_execute_commit=false
  - should_execute_rollback=false
  - should_push=false
  - should_start_unbounded_loop=false

Next step:

- Prompt231 may prepare a metadata-only fresh runtime evidence result review surface.
- Prompt231 must not infer evidence from Prompt230 readiness alone.
- Prompt231 must not mutate git state or invoke Codex.

## Prompt231 architecture note - fresh runtime evidence result review surface

Prompt231 adds a metadata-only result review surface:

- Prefix:
  - project_browser_autonomous_fresh_runtime_evidence_result_review_*
- Source:
  - project_browser_autonomous_fresh_runtime_evidence_check_*
- Current status:
  - fresh_runtime_evidence_result_review_prepared_no_observed_outputs
- Current interpretation:
  - Prompt231 consumed the Prompt230 evidence check surface.
  - It did not execute the check command.
  - It did not observe fresh runtime evidence.
  - Therefore observed_outputs_available, fresh_runtime_evidence_detected, fresh_runtime_evidence_valid, completed_fresh_surface_detected, one_step_accounting_valid, and stop_policy_passed remain false.
- Safety invariant:
  - should_execute_check_command=false
  - should_invoke_codex=false
  - should_execute_commit=false
  - should_execute_rollback=false
  - should_push=false
  - should_start_unbounded_loop=false

Next step:

- Prompt232 may prepare a bounded/manual fresh runtime evidence runbook contract.
- In Prompt232, execution_contract means contract/runbook metadata only.
- Prompt232 must not execute the command, invoke Codex, mutate git, push, rollback, retry, or start an unbounded loop.

## Prompt232 architecture note - fresh runtime evidence runbook contract

Prompt232 adds a metadata-only bounded/manual runbook contract:

- Prefix:
  - project_browser_autonomous_fresh_runtime_evidence_runbook_contract_*
- Source:
  - project_browser_autonomous_fresh_runtime_evidence_result_review_*
- Current status:
  - fresh_runtime_evidence_runbook_contract_prepared
- Current interpretation:
  - Prompt232 prepared a bounded/manual runbook contract.
  - It did not execute the runbook.
  - It did not execute a check command.
  - It did not observe fresh runtime evidence.
  - Therefore observed_outputs_available, fresh_runtime_evidence_detected, fresh_runtime_evidence_valid, completed_fresh_surface_detected, one_step_accounting_valid, and stop_policy_passed remain false.
- Safety invariant:
  - should_execute_runbook=false
  - should_execute_check_command=false
  - should_invoke_codex=false
  - should_execute_commit=false
  - should_execute_rollback=false
  - should_push=false
  - should_start_unbounded_loop=false

Next step:

- Prompt233 should prepare a bounded manual run command packet from the Prompt232 runbook contract.
- Prompt233 must not execute the command, execute the runbook, invoke Codex, mutate git, push, rollback, retry, or start an unbounded loop.

## Prompt233 architecture note - fresh runtime evidence manual run command packet

Prompt233 adds a metadata-only bounded manual command packet:

- Prefix:
  - project_browser_autonomous_fresh_runtime_evidence_manual_run_command_packet_*
- Source:
  - project_browser_autonomous_fresh_runtime_evidence_runbook_contract_*
- Current status:
  - fresh_runtime_evidence_manual_run_command_packet_prepared
- Current interpretation:
  - Prompt233 prepared a command packet only.
  - It did not execute the command packet.
  - It did not execute the runbook.
  - It did not invoke Codex.
  - It did not mutate git state.
  - It did not observe fresh runtime evidence.
  - Therefore observed_outputs_available, fresh_runtime_evidence_detected, fresh_runtime_evidence_valid, completed_fresh_surface_detected, one_step_accounting_valid, and stop_policy_passed remain false.
- Safety invariant:
  - should_execute_manual_command=false
  - should_execute_runbook=false
  - should_execute_check_command=false
  - should_invoke_codex=false
  - should_execute_commit=false
  - should_execute_rollback=false
  - should_push=false
  - should_start_unbounded_loop=false
- Required artifacts for later review:
  - approved_restart_execution_contract.json
  - run_state.json
  - manifest.json
- Forbidden actions:
  - codex_invocation
  - git_mutation
  - commit
  - tag
  - push
  - rollback
  - retry
  - github_mutation
  - unbounded_loop

Next step:

- Prompt234 may prepare a metadata-only manual run result review surface.
- Prompt234 must not infer observed evidence from command_packet_ready alone.
- Prompt234 must not execute the command, execute the runbook, invoke Codex, mutate git, push, rollback, retry, or start an unbounded loop.

## Prompt234 architecture note - fresh runtime evidence manual run result review surface

Prompt234 adds a metadata-only manual run result review surface:

- Prefix:
  - project_browser_autonomous_fresh_runtime_evidence_manual_run_result_review_*
- Source:
  - project_browser_autonomous_fresh_runtime_evidence_manual_run_command_packet_*
- Current status:
  - fresh_runtime_evidence_manual_run_result_review_prepared_no_observed_outputs
- Current interpretation:
  - Prompt234 consumed the Prompt233 command packet.
  - It did not execute the command packet.
  - It did not execute the runbook.
  - It did not invoke Codex.
  - It did not mutate git state.
  - It did not observe fresh runtime evidence.
  - Required artifacts are known, but observed_artifacts is empty.
  - Therefore observed_outputs_available, fresh_runtime_evidence_detected, fresh_runtime_evidence_valid, completed_fresh_surface_detected, one_step_accounting_valid, and stop_policy_passed remain false.
- Required artifacts for later intake:
  - approved_restart_execution_contract.json
  - run_state.json
  - manifest.json
- Safety invariant:
  - should_execute_manual_command=false
  - should_execute_runbook=false
  - should_execute_check_command=false
  - should_invoke_codex=false
  - should_execute_commit=false
  - should_execute_rollback=false
  - should_push=false
  - should_start_unbounded_loop=false

Next step:

- Prompt235 may prepare an observed artifact intake contract.
- Prompt235 must not read files, scan the filesystem, execute commands, infer evidence, update Prompt222, or re-evaluate N=2.

## Prompt235 architecture note - fresh runtime evidence observed artifact intake contract

Prompt235 adds a metadata-only observed artifact intake contract:

- Prefix:
  - project_browser_autonomous_fresh_runtime_evidence_observed_artifact_intake_*
- Source:
  - project_browser_autonomous_fresh_runtime_evidence_manual_run_result_review_*
- Current status:
  - fresh_runtime_evidence_observed_artifact_intake_contract_prepared
- Current interpretation:
  - Prompt235 prepared artifact intake metadata only.
  - It did not read files.
  - It did not scan the filesystem.
  - It did not execute commands.
  - It did not invoke Codex.
  - It did not mutate git state.
  - It did not infer fresh runtime evidence.
  - Therefore observed_outputs_available, fresh_runtime_evidence_detected, fresh_runtime_evidence_valid, completed_fresh_surface_detected, one_step_accounting_valid, and stop_policy_passed remain false.
- Required artifacts:
  - approved_restart_execution_contract.json
  - run_state.json
  - manifest.json
- Safety invariant:
  - should_read_files=false
  - should_scan_filesystem=false
  - should_execute_manual_command=false
  - should_execute_runbook=false
  - should_execute_check_command=false
  - should_invoke_codex=false
  - should_execute_commit=false
  - should_execute_rollback=false
  - should_push=false
  - should_start_unbounded_loop=false

Next step:

- Prompt236 may prepare a supplied artifact path review surface.
- Prompt236 must not parse file contents, validate JSON contents, infer evidence, update Prompt222 fields, or re-evaluate N=2.

## Prompt236 architecture note - fresh runtime evidence supplied artifact path review surface

Prompt236 adds a metadata-only supplied artifact path review surface:

- Prefix:
  - project_browser_autonomous_fresh_runtime_evidence_supplied_artifact_path_review_*
- Source:
  - project_browser_autonomous_fresh_runtime_evidence_observed_artifact_intake_*
- Current status:
  - fresh_runtime_evidence_supplied_artifact_path_review_prepared_no_supplied_paths
- Current interpretation:
  - Prompt236 prepared path review metadata only.
  - No explicit supplied artifact paths are currently present.
  - It did not read files.
  - It did not parse JSON.
  - It did not validate file existence.
  - It did not scan the filesystem.
  - It did not execute commands.
  - It did not invoke Codex.
  - It did not mutate git state.
  - It did not infer fresh runtime evidence.
  - Therefore observed_outputs_available, fresh_runtime_evidence_detected, fresh_runtime_evidence_valid, completed_fresh_surface_detected, one_step_accounting_valid, and stop_policy_passed remain false.
- Artifact path requirements:
  - explicit_paths_only
  - no_filesystem_discovery
  - no_glob_expansion
  - same_out_dir_required
  - same_job_id_required
  - required_artifact_names_must_match
- Safety invariant:
  - should_read_files=false
  - should_parse_json=false
  - should_validate_file_existence=false
  - should_scan_filesystem=false
  - should_execute_manual_command=false
  - should_execute_runbook=false
  - should_execute_check_command=false
  - should_invoke_codex=false
  - should_execute_commit=false
  - should_execute_rollback=false
  - should_push=false
  - should_start_unbounded_loop=false

Next step:

- Prompt237 may prepare an artifact existence review surface.
- Prompt237 must not parse JSON contents, infer evidence validity, update Prompt222 fields, or re-evaluate N=2.

## Prompt237 architecture note - fresh runtime evidence artifact existence review surface

Prompt237 adds a metadata-only artifact existence review surface:

- Prefix:
  - project_browser_autonomous_fresh_runtime_evidence_artifact_existence_review_*
- Source:
  - project_browser_autonomous_fresh_runtime_evidence_supplied_artifact_path_review_*
- Current status:
  - fresh_runtime_evidence_artifact_existence_review_prepared_no_supplied_paths
- Current interpretation:
  - Prompt237 prepared existence-review metadata only.
  - No explicit supplied artifact paths are currently present.
  - Required artifacts are therefore not reviewable yet:
    - approved_restart_execution_contract.json
    - run_state.json
    - manifest.json
  - It did not read files.
  - It did not parse JSON.
  - It did not validate file existence.
  - It did not scan the filesystem.
  - It did not execute commands.
  - It did not invoke Codex.
  - It did not mutate git state.
  - It did not infer fresh runtime evidence.
  - Therefore observed_outputs_available, fresh_runtime_evidence_detected, fresh_runtime_evidence_valid, completed_fresh_surface_detected, one_step_accounting_valid, and stop_policy_passed remain false.
- Safety invariant:
  - should_read_files=false
  - should_parse_json=false
  - should_validate_file_existence=false
  - should_scan_filesystem=false
  - should_execute_manual_command=false
  - should_execute_runbook=false
  - should_execute_check_command=false
  - should_invoke_codex=false
  - should_execute_commit=false
  - should_execute_rollback=false
  - should_push=false
  - should_start_unbounded_loop=false

Next step:

- Prompt238 should prepare a broader artifact review readiness surface.
- Prompt238 should combine supplied path readiness, existence review readiness, content/JSON review readiness, and evidence validation preconditions.
- Prompt238 must not read files, parse JSON, execute commands, infer evidence validity, update Prompt222 fields, or re-evaluate N=2.

## Prompt238 architecture note - fresh runtime evidence artifact review readiness surface

Prompt238 adds a metadata-only artifact review readiness surface:

- Prefix:
  - project_browser_autonomous_fresh_runtime_evidence_artifact_review_readiness_*
- Source:
  - project_browser_autonomous_fresh_runtime_evidence_artifact_existence_review_*
- Current status:
  - fresh_runtime_evidence_artifact_review_readiness_blocked_missing_supplied_paths
- Current interpretation:
  - Prompt238 consolidated path, existence, content, JSON, and evidence-validation readiness metadata.
  - No explicit supplied artifact paths are currently present.
  - Content review, JSON review, and evidence validation are not ready.
  - It did not read files.
  - It did not parse JSON.
  - It did not validate file existence.
  - It did not scan the filesystem.
  - It did not execute commands.
  - It did not invoke Codex.
  - It did not mutate git state.
  - It did not update Prompt222 fields.
  - It did not re-evaluate N=2.
  - Therefore observed_outputs_available, fresh_runtime_evidence_detected, fresh_runtime_evidence_valid, completed_fresh_surface_detected, one_step_accounting_valid, and stop_policy_passed remain false.
- Current blocker:
  - readiness_block_reason=missing_supplied_artifact_paths
- Safety invariant:
  - should_read_files=false
  - should_parse_json=false
  - should_validate_file_existence=false
  - should_scan_filesystem=false
  - should_execute_manual_command=false
  - should_execute_runbook=false
  - should_execute_check_command=false
  - should_invoke_codex=false
  - should_execute_commit=false
  - should_execute_rollback=false
  - should_push=false
  - should_start_unbounded_loop=false

Next step:

- Prompt239 may prepare an artifact consistency review surface.
- Prompt239 must not read files, parse JSON, infer evidence validity, update Prompt222 fields, or re-evaluate N=2.
- Because supplied_artifact_paths is currently empty, Prompt239 should preserve a blocked/not-reviewable consistency posture.

## Prompt239 architecture note - fresh runtime evidence artifact consistency review surface

Prompt239 adds a metadata-only artifact consistency review surface:

- Prefix:
  - project_browser_autonomous_fresh_runtime_evidence_artifact_consistency_review_*
- Source:
  - project_browser_autonomous_fresh_runtime_evidence_artifact_review_readiness_*
- Current status:
  - fresh_runtime_evidence_artifact_consistency_review_not_reviewable_missing_supplied_paths
- Current interpretation:
  - Prompt239 summarized required artifact consistency readiness.
  - Required artifacts are known, but supplied artifact paths are still empty.
  - Artifact set consistency is not reviewable yet.
  - prompt240_preconditions_ready=false.
  - prompt240_ready=true only means Prompt240 may prepare the next metadata surface.
  - It does not mean evidence validity can be decided true.
  - It did not read files, parse JSON, validate file existence, scan filesystem, execute commands, invoke Codex, mutate git, update Prompt222, or re-evaluate N=2.
- Current blocker:
  - consistency_block_reason=missing_supplied_artifact_paths
- Safety invariant:
  - should_read_files=false
  - should_parse_json=false
  - should_validate_file_existence=false
  - should_scan_filesystem=false
  - should_execute_manual_command=false
  - should_execute_runbook=false
  - should_execute_check_command=false
  - should_invoke_codex=false
  - should_execute_commit=false
  - should_execute_rollback=false
  - should_push=false
  - should_start_unbounded_loop=false

Next step:

- Prompt240 may prepare a fresh runtime evidence validity decision surface.
- Since prompt240_preconditions_ready=false, Prompt240 must keep fresh_runtime_evidence_valid, completed_fresh_surface_detected, one_step_accounting_valid, and stop_policy_passed false.
- Prompt240 must not read files, parse JSON, infer validity true, update Prompt222 fields, or re-evaluate N=2.

## Prompt240 architecture note - fresh runtime evidence validity decision surface

Prompt240 adds a metadata-only validity decision surface:

- Prefix:
  - project_browser_autonomous_fresh_runtime_evidence_validity_decision_*
- Source:
  - project_browser_autonomous_fresh_runtime_evidence_artifact_consistency_review_*
- Current status:
  - fresh_runtime_evidence_validity_decision_blocked_artifact_consistency_not_reviewable
- Current interpretation:
  - Prompt240 consumed artifact consistency review metadata.
  - Artifact consistency is not reviewable because supplied artifact paths are missing.
  - prompt240_preconditions_ready=false.
  - validity_decision_ready=false.
  - fresh_runtime_evidence_valid remains false.
  - completed_fresh_surface_detected, one_step_accounting_valid, and stop_policy_passed remain false.
  - prompt241_bridge_ready=true only means Prompt241 may prepare the next metadata-only bridge surface.
  - It does not authorize Prompt222 updates, truth updates, or N=2 readiness changes.
- Current blocker:
  - validity_block_reason=missing_supplied_artifact_paths
- Safety invariant:
  - should_read_files=false
  - should_parse_json=false
  - should_validate_file_existence=false
  - should_scan_filesystem=false
  - should_execute_manual_command=false
  - should_execute_runbook=false
  - should_execute_check_command=false
  - should_invoke_codex=false
  - should_execute_commit=false
  - should_execute_rollback=false
  - should_push=false
  - should_start_unbounded_loop=false

Next step:

- Prompt241 may prepare a combined truth bridge readiness / blocked Prompt222 reflection / N=2 blocked summary / manual artifact supply direction surface.
- Since validity_decision_ready=false, Prompt241 must keep truth_update_allowed=false and must not update Prompt222 or re-evaluate N=2.

## Prompt241 architecture note - fresh runtime evidence truth bridge and blocked readiness summary

Prompt241 adds a metadata-only truth bridge / blocked readiness surface:

- Prefix:
  - project_browser_autonomous_fresh_runtime_evidence_truth_bridge_*
- Source:
  - project_browser_autonomous_fresh_runtime_evidence_validity_decision_*
- Current status:
  - fresh_runtime_evidence_truth_bridge_blocked_validity_not_ready
- Current interpretation:
  - Prompt241 consumed Prompt240 validity decision metadata.
  - Validity is blocked because required artifact paths are missing.
  - truth_update_allowed=false.
  - prompt222_reflection_allowed=false.
  - n2_readiness_allowed=false.
  - manual_artifact_supply_required=true.
  - The next required artifacts are:
    - approved_restart_execution_contract.json
    - run_state.json
    - manifest.json
  - It did not read files, parse JSON, validate file existence, scan filesystem, execute commands, invoke Codex, mutate git, update Prompt222, or re-evaluate N=2.
- Current blocker:
  - manual_artifact_supply_reason=missing_supplied_artifact_paths
- Safety invariant:
  - should_read_files=false
  - should_parse_json=false
  - should_validate_file_existence=false
  - should_scan_filesystem=false
  - should_execute_manual_command=false
  - should_execute_runbook=false
  - should_execute_check_command=false
  - should_invoke_codex=false
  - should_execute_commit=false
  - should_execute_rollback=false
  - should_push=false
  - should_start_unbounded_loop=false

Next step:

- Prompt242 should prepare manual artifact supply path intake plus review permission gates.
- Prompt242 may define explicit path intake, path-shape requirements, same out_dir/job_id requirements, and existence/content/JSON review permission gates.
- Prompt242 must not read files, parse JSON, mark evidence valid, update Prompt222, or re-evaluate N=2.

## Prompt242 architecture note - manual artifact supply path intake and review gates

Prompt242 adds a metadata-only manual artifact supply path intake surface:

- Prefix:
  - project_browser_autonomous_manual_artifact_supply_path_intake_*
- Source:
  - project_browser_autonomous_fresh_runtime_evidence_truth_bridge_*
- Current status:
  - manual_artifact_supply_path_intake_awaiting_explicit_paths
- Current interpretation:
  - Prompt242 prepared explicit artifact path intake metadata.
  - Required artifact paths are still not supplied.
  - Path intake is ready, but existence/content/JSON review permissions remain false.
  - Artifact review assimilation is not ready.
  - It did not read files, parse JSON, validate file existence, scan filesystem, execute commands, invoke Codex, mutate git, update Prompt222, or re-evaluate N=2.
- Required artifacts:
  - approved_restart_execution_contract.json
  - run_state.json
  - manifest.json
- Current blocker:
  - artifact_review_assimilation_block_reason=missing_supplied_artifact_paths
- Safety invariant:
  - should_read_files=false
  - should_parse_json=false
  - should_validate_file_existence=false
  - should_scan_filesystem=false
  - should_execute_manual_command=false
  - should_execute_runbook=false
  - should_execute_check_command=false
  - should_invoke_codex=false
  - should_execute_commit=false
  - should_execute_rollback=false
  - should_push=false
  - should_start_unbounded_loop=false

Next step:

- Prompt243 should prepare a broader artifact supply and review readiness phase.
- Prompt243 may combine artifact supply status, path intake summary, review permission summary, assimilation readiness, and validity recheck readiness.
- Prompt243 must not read files, parse JSON, mark evidence valid, update Prompt222, or re-evaluate N=2.

## Prompt243 architecture note - artifact supply and review readiness phase

Prompt243 adds a metadata-only artifact supply/review readiness phase:

- Prefix:
  - project_browser_autonomous_artifact_supply_review_readiness_phase_*
- Source:
  - project_browser_autonomous_manual_artifact_supply_path_intake_*
- Current status:
  - artifact_supply_review_readiness_phase_blocked_missing_supplied_paths
- Current interpretation:
  - Prompt243 consolidated manual artifact supply status, path intake, review permissions, assimilation readiness, validity recheck readiness, and blocked truth/N=2 posture.
  - Explicit artifact paths are still missing.
  - Artifact review assimilation is not ready.
  - Validity recheck is not ready.
  - truth_update_allowed=false.
  - prompt222_reflection_allowed=false.
  - n2_readiness_allowed=false.
  - It did not read files, parse JSON, validate file existence, scan filesystem, execute commands, invoke Codex, mutate git, update Prompt222, or re-evaluate N=2.
- Current blocker:
  - artifact_review_assimilation_block_reason=missing_supplied_artifact_paths
  - validity_recheck_block_reason=missing_supplied_artifact_paths
- Required artifacts:
  - approved_restart_execution_contract.json
  - run_state.json
  - manifest.json
- Safety invariant:
  - should_read_files=false
  - should_parse_json=false
  - should_validate_file_existence=false
  - should_scan_filesystem=false
  - should_execute_manual_command=false
  - should_execute_runbook=false
  - should_execute_check_command=false
  - should_invoke_codex=false
  - should_execute_commit=false
  - should_execute_rollback=false
  - should_push=false
  - should_start_unbounded_loop=false

Next step:

- Prompt244 should prepare manual supplied path handling, explicit path extraction/normalization metadata, path requirement conformance, review permission recalculation, artifact review assimilation readiness, validity recheck readiness, and next read/parse gate direction.
- Prompt244 must not read files, parse JSON, mark evidence valid, update Prompt222, or re-evaluate N=2.

## Prompt244 architecture note - artifact review manual supply handling phase

Prompt244 adds a metadata-only artifact review/manual supply handling phase:

- Prefix:
  - project_browser_autonomous_artifact_review_manual_supply_handling_phase_*
- Source:
  - project_browser_autonomous_artifact_supply_review_readiness_phase_*
- Current status:
  - artifact_review_manual_supply_handling_phase_awaiting_explicit_paths
- Current interpretation:
  - Prompt244 prepared manual supply handling and read/parse gate direction metadata.
  - Explicit artifact paths are still missing.
  - Path extraction has no explicit paths to extract.
  - Review permission recalculation is blocked.
  - Artifact review assimilation is not ready.
  - Validity recheck is not ready.
  - Read/parse gate is not ready.
  - truth_update_allowed=false.
  - prompt222_reflection_allowed=false.
  - n2_readiness_allowed=false.
  - It did not read files, parse JSON, validate file existence, scan filesystem, execute commands, invoke Codex, mutate git, update Prompt222, or re-evaluate N=2.
- Current blocker:
  - read_parse_gate_status=blocked_missing_supplied_artifact_paths
  - artifact_review_assimilation_status=blocked_missing_supplied_artifact_paths
  - validity_recheck_status=blocked_artifact_review_not_ready
- Required artifacts:
  - approved_restart_execution_contract.json
  - run_state.json
  - manifest.json
- Safety invariant:
  - should_read_files=false
  - should_parse_json=false
  - should_validate_file_existence=false
  - should_scan_filesystem=false
  - should_execute_manual_command=false
  - should_execute_runbook=false
  - should_execute_check_command=false
  - should_invoke_codex=false
  - should_execute_commit=false
  - should_execute_rollback=false
  - should_push=false
  - should_start_unbounded_loop=false

Next step:

- Prompt245 should prepare a read/parse permission gate plus content/JSON consistency contract.
- Prompt245 may define read permission, parse permission, content consistency contract, JSON key/schema expectation contract, and triad consistency preconditions.
- Prompt245 must not actually read files, parse JSON, mark fresh evidence valid, update Prompt222, or re-evaluate N=2.

## Prompt245 architecture note - read/parse permission and content consistency phase

Prompt245 adds a metadata-only read/parse permission and content consistency phase:

- Prefix:
  - project_browser_autonomous_read_parse_permission_content_consistency_*
- Source:
  - project_browser_autonomous_artifact_review_manual_supply_handling_phase_*
- Current status:
  - read_parse_permission_content_consistency_blocked_missing_supplied_paths
- Current interpretation:
  - Prompt245 prepared read/parse/existence permission gates and content/JSON consistency contracts.
  - Explicit artifact paths are still missing.
  - read_permission=false.
  - parse_permission=false.
  - existence_validation_permission=false.
  - artifact_review_readiness=false.
  - prompt246_artifact_content_review_ready=false.
  - fresh_runtime_evidence_valid=false.
  - truth_update_allowed=false.
  - prompt222_reflection_allowed=false.
  - n2_readiness_allowed=false.
  - It did not read files, parse JSON, validate file existence, scan filesystem, execute commands, invoke Codex, mutate git, update Prompt222, or re-evaluate N=2.
- Current blocker:
  - missing_supplied_artifact_paths
- Required artifacts:
  - approved_restart_execution_contract.json
  - run_state.json
  - manifest.json
- Safety invariant:
  - should_read_files=false
  - should_parse_json=false
  - should_validate_file_existence=false
  - should_scan_filesystem=false
  - should_execute_manual_command=false
  - should_execute_runbook=false
  - should_execute_check_command=false
  - should_invoke_codex=false
  - should_execute_commit=false
  - should_execute_rollback=false
  - should_push=false
  - should_start_unbounded_loop=false

Next step:

- Prompt246 should prepare artifact content review and fresh evidence validity readiness/decision metadata.
- Since supplied_artifact_paths is still empty and read/parse permissions are false, Prompt246 must keep all evidence/truth/Prompt222/N=2 outcomes blocked/false.
- Prompt246 must not read files, parse JSON, mark evidence valid, update Prompt222, or re-evaluate N=2.

## Prompt246 architecture note - artifact content review and fresh evidence validity readiness phase

Prompt246 adds a metadata-only artifact content review / fresh evidence validity readiness phase:

- Prefix:
  - project_browser_autonomous_artifact_content_review_fresh_evidence_validity_*
- Source:
  - project_browser_autonomous_read_parse_permission_content_consistency_*
- Current status:
  - artifact_content_review_fresh_evidence_validity_blocked_missing_supplied_paths
- Current interpretation:
  - Prompt246 prepared artifact content review, JSON review, artifact triad review, fresh evidence validity, and Prompt247 bridge readiness metadata.
  - Explicit artifact paths are still missing.
  - read/parse/existence permissions are still false.
  - Artifact content is not reviewable.
  - Fresh evidence validity remains blocked.
  - truth_update_allowed=false.
  - prompt222_reflection_allowed=false.
  - n2_readiness_allowed=false.
  - prompt247_bridge_ready=true only means the next metadata bridge surface may be prepared.
  - It does not authorize Prompt222 updates or N=2 re-evaluation.
- Current blocker:
  - prompt247_bridge_block_reason=missing_supplied_artifact_paths
  - fresh_evidence_validity_block_reason=missing_supplied_artifact_paths
- Safety invariant:
  - should_read_files=false
  - should_parse_json=false
  - should_validate_file_existence=false
  - should_scan_filesystem=false
  - should_execute_manual_command=false
  - should_execute_runbook=false
  - should_execute_check_command=false
  - should_invoke_codex=false
  - should_execute_commit=false
  - should_execute_rollback=false
  - should_push=false
  - should_start_unbounded_loop=false

Next step:

- Prompt247 should prepare Prompt222/N=2 bridge readiness metadata.
- Since fresh_runtime_evidence_valid=false, Prompt247 must keep Prompt222 update, N=2 re-evaluation, completed_fresh_surface_detected, one_step_accounting_valid, and stop_policy_passed blocked/false.
- Prompt247 must not update Prompt222, re-evaluate N=2, execute commands, or mutate git.

## Prompt247 architecture note - Prompt222/N=2 bridge readiness phase

Prompt247 adds a metadata-only Prompt222/N=2 bridge readiness phase:

- Prefix:
  - project_browser_autonomous_prompt222_n2_bridge_readiness_phase_*
- Source:
  - project_browser_autonomous_artifact_content_review_fresh_evidence_validity_*
- Current status:
  - prompt222_n2_bridge_readiness_phase_blocked_fresh_evidence_not_valid
- Current interpretation:
  - Prompt247 prepared Prompt222 bridge readiness, N=2 readiness summary, and bounded continuation readiness metadata.
  - Fresh runtime evidence is not valid because explicit supplied artifact paths are missing.
  - Prompt222 update is not allowed.
  - N=2 re-evaluation is not allowed.
  - Bounded continuation is not allowed.
  - Manual artifact supply is still required.
  - It did not update Prompt222, re-evaluate N=2, start bounded continuation, read files, parse JSON, validate existence, scan filesystem, execute commands, invoke Codex, mutate git, or set fresh evidence/accounting booleans true.
- Current blocker:
  - missing_supplied_artifact_paths
- Required next supplied path fields:
  - approved_restart_execution_contract_json_path
  - run_state_json_path
  - manifest_json_path
- Safety invariant:
  - should_update_prompt222=false
  - should_re_evaluate_n2=false
  - should_start_bounded_continuation=false
  - should_read_files=false
  - should_parse_json=false
  - should_validate_file_existence=false
  - should_scan_filesystem=false
  - should_execute_manual_command=false
  - should_execute_runbook=false
  - should_execute_check_command=false
  - should_invoke_codex=false
  - should_execute_commit=false
  - should_execute_rollback=false
  - should_push=false
  - should_start_unbounded_loop=false

Next step:

- Prompt248 should define an explicit supplied-path ingestion interface and payload schema.
- Prompt248 should specify how approved_restart_execution_contract_json_path, run_state_json_path, and manifest_json_path are represented in the final approved restart payload normalized map.
- Prompt248 must not read files, parse JSON, validate existence, update Prompt222, re-evaluate N=2, start bounded continuation, execute commands, or mutate git.

## Prompt249 architecture note - supplied path payload normalization and permission recalculation

Prompt249 adds a metadata-only supplied path payload normalization and permission recalculation surface:

- Prefix:
  - project_browser_autonomous_supplied_path_payload_normalization_permission_*
- Source:
  - project_browser_autonomous_supplied_path_ingestion_interface_*
- Current status:
  - supplied_path_payload_normalization_permission_awaiting_explicit_payload
- Current interpretation:
  - Prompt249 defined supplied-path payload normalization and permission recalculation metadata.
  - No explicit supplied-path payload is present yet.
  - accepted_supplied_path_fields is empty.
  - missing_supplied_path_fields still includes all required artifact path fields.
  - normalized_supplied_artifact_paths is empty.
  - review/read/parse permissions remain false.
  - Prompt222 update, N=2 readiness, and bounded continuation remain blocked.
  - It did not read files, parse JSON, validate existence, scan filesystem, execute commands, update Prompt222, re-evaluate N=2, start bounded continuation, invoke Codex, or mutate git.
- Current blocker:
  - prompt250_gate_block_reason=missing_supplied_path_payload
- Required supplied path fields:
  - approved_restart_execution_contract_json_path
  - run_state_json_path
  - manifest_json_path
- Safety invariant:
  - should_update_prompt222=false
  - should_re_evaluate_n2=false
  - should_start_bounded_continuation=false
  - should_read_files=false
  - should_parse_json=false
  - should_validate_file_existence=false
  - should_scan_filesystem=false
  - should_execute_manual_command=false
  - should_execute_runbook=false
  - should_execute_check_command=false
  - should_invoke_codex=false
  - should_execute_commit=false
  - should_execute_rollback=false
  - should_push=false
  - should_start_unbounded_loop=false

Next step:

- Prompt250 should prepare a bounded artifact existence/read/parse gate.
- Since no explicit supplied-path payload is present yet, Prompt250 must keep actual existence validation, file reading, JSON parsing, evidence validity, Prompt222 update, N=2 re-evaluation, and bounded continuation blocked/false.

## Prompt250 architecture constraint update

Prompt250 added a metadata-only bounded artifact existence/read/parse gate.

The current blocker remains:
- `missing_supplied_path_payload`

The following operations are still forbidden before an explicit supplied-path payload carrier and normalization bridge exists:
- actual file existence validation
- actual file read
- actual JSON parse
- filesystem scan
- glob expansion
- log scraping
- shell command execution
- git mutation
- Prompt222 update
- N=2 re-evaluation
- bounded continuation start

Next required step:
- Prompt251 must add an explicit supplied-path payload carrier / normalization bridge.
- Prompt251 must remain metadata-only.
- Prompt251 must not perform artifact content review, file access, JSON parsing, Prompt222 update, N=2 re-evaluation, or bounded continuation.

## Prompt250 constraint update - bounded artifact existence/read/parse gate

Prompt250 established a metadata-only gate before artifact existence validation, file read, and JSON parse.

Current invariant:
- Explicit supplied artifact paths are still missing.
- Therefore artifact review and fresh evidence validity remain blocked.
- Prompt251 must focus on explicit supplied-path payload carrier / normalization bridge, not artifact content review.

Safety constraints preserved:
- No actual file read.
- No JSON parse.
- No file existence validation.
- No filesystem scan.
- No glob expansion.
- No log scraping.
- No shell command execution.
- No Codex/browser executor addition.
- No git mutation.
- No Prompt222 update.
- No N=2 re-evaluation.
- No bounded continuation execution.

Required artifact path fields remain:
- approved_restart_execution_contract_json_path
- run_state_json_path
- manifest_json_path

## Prompt251 constraint update - supplied path payload carrier

Prompt251 added the metadata-only carrier / normalization bridge for explicit supplied artifact path payloads.

Current invariant:
- No explicit supplied artifact path payload is present yet.
- The chain remains blocked on missing_supplied_path_payload.
- Payload classification exists, but artifact access is still not allowed.

Safety constraints preserved:
- No actual file read.
- No JSON parse.
- No file existence validation.
- No filesystem scan or glob expansion.
- No log scraping.
- No shell command execution.
- No Codex/browser executor addition.
- No git mutation.
- No Prompt222 update.
- No N=2 re-evaluation.
- No bounded continuation execution.

Next direction:
- Move faster toward the autonomous development MVP.
- Prompt252 should not be only another tiny payload surface.
- Prompt252 should add a compact autonomous development control spine while preserving explicit permission separation and safe blocked defaults.

## Prompt252 constraint update - autonomous development MVP spine

Prompt252 added the autonomous development MVP control spine.

Current invariant:
- The chain now has a dev-loop input carrier and MVP control state.
- No project request is currently supplied, so the correct state is:
  - current_stage=project_intake
  - next_action=provide_project_request
  - block_reason=missing_project_request
- External execution is still not allowed by the runner.

Safety constraints preserved:
- No ChatGPT API call.
- No Codex invocation.
- No artifact read or JSON parse.
- No filesystem scan.
- No shell/manual/check command execution.
- No git mutation.
- No commit/tag/merge/push.
- No Prompt222 update.
- No N=2 re-evaluation.
- No bounded continuation execution.

Next direction:
- Prompt253 should not add another tiny blocked surface.
- Prompt253 should add explicit synthetic dev-loop input support and verify the MVP spine can advance to PR prompt generation and Codex handoff readiness without external execution.

## Prompt253 constraint update - synthetic input / PR prompt readiness

Prompt253 validates the autonomous development MVP spine using metadata-only synthetic input.

Current invariant:
- Synthetic input is dry-run / MVP verification only.
- Synthetic input must not override explicit dev-loop input.
- The MVP spine can now reach:
  - pr_prompt_ready=true
  - codex_handoff_ready=true
  - current_stage=codex_result_review
  - next_action=await_codex_result

Safety constraints preserved:
- No ChatGPT API call.
- No Codex invocation.
- No artifact read or JSON parse.
- No filesystem scan.
- No command execution.
- No git mutation.
- No commit/tag/merge/push.
- No Prompt222 update.
- No N=2 re-evaluation.
- No bounded continuation execution.

Next direction:
- Prompt254 should add explicit/synthetic Codex result ingestion and review/fix decision metadata.
- It must not execute commit, merge, push, Codex, ChatGPT, or shell commands.
