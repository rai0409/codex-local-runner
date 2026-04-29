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
