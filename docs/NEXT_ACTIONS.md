
## Next after Prompt284.9

1. Run continuation guard runtime verification.

Expected values:
- project_browser_autonomous_codex_live_continuation_guard_status=blocked
- project_browser_autonomous_codex_live_continuation_guard_reason=codex_live_network_unavailable
- project_browser_autonomous_codex_live_continuation_retry_allowed=false
- project_browser_autonomous_codex_live_continuation_next_action=manual_network_setup_required

2. Restore Codex CLI network/WebSocket access.

3. Rerun the live Codex connector.

4. Only after Codex creates local changes, run Prompt285-B to capture local git diff from repository state.

## Next after Prompt285-A-fix PASS

1. Fix external Codex CLI network/WebSocket access.

2. Confirm Codex CLI can run outside the runner:
   printf 'Say OK only.' | codex exec - --cd ~/codex-local-runner --sandbox read-only

3. Rerun the live Codex connector.

4. After Codex creates local file changes, run Prompt285-B:
   - capture local git status/diff from repository state
   - do not rely on Codex self-reported diff text
   - emit diff_capture.json, diff_summary.md, reviewable_diff.patch, changed_files.json

Still prohibited until later phases:
- commit/tag automation
- push
- PR creation
- merge
- daemon or unbounded loop

Next after Codex CLI write confirmation

Current confirmed state:

Codex CLI works with gpt-5.3-codex high.
workspace-write allows repository writes.
approval_policy="never" works via -c.
--ask-for-approval is not a valid codex exec option in Codex CLI v0.128.0.

Next required prompt:

Update the runner live Codex connector so implementation steps use:
--sandbox workspace-write
-m gpt-5.3-codex
-c 'model_reasoning_effort="high"'
-c 'approval_policy="never"'

Still prohibited:

danger-full-access
Prompt285-B local git diff capture before runner-driven local changes exist
commit/tag automation
push
PR creation
merge
daemon or unbounded loop

## Next after Prompt285-C

Run runner-driven live Codex connector verification.

Goal:
- Confirm the runner now invokes Codex with workspace-write and gpt-5.3-codex high.
- Confirm network_denied is cleared.
- Confirm Codex can create local repository changes through the runner path.

If local changes appear:
- Proceed to Prompt285-B local git diff capture.

Still prohibited:
- Prompt285-B before runner-driven local changes exist
- commit/tag automation
- push
- PR creation
- merge
- daemon or unbounded loop

## Next after Prompt285-C live probe

Run Prompt285-D.

Goal:
- Allow explicit one-shot retry-context enablement of:
  - project_browser_autonomous_codex_execution_gate_enabled
  - project_browser_autonomous_codex_execution_gate_execute_enabled
  - project_browser_autonomous_codex_execution_connector_enabled
  - project_browser_autonomous_codex_execution_connector_execute_enabled

Expected:
- gate_disabled should clear when explicitly enabled.
- connector_disabled should clear when explicitly enabled.
- If other readiness checks pass, invocation_command should be populated with the Prompt285-C command shape:
  - --sandbox workspace-write
  - -m gpt-5.3-codex
  - -c 'model_reasoning_effort="high"'
  - -c 'approval_policy="never"'

Still prohibited:
- Prompt285-B local git diff capture before runner-driven local changes exist
- commit/tag automation
- push
- PR creation
- merge
- daemon or unbounded loop

## Next after Prompt285-D

Run Prompt285-E.

Goal:
- Carry selected prompt metadata for /tmp/codex-local-runner-decision/generated_next_prompt.txt into invocation readiness.
- Populate invocation_command with the Prompt285-C command shape.

Still prohibited:
- Prompt285-B local git diff capture before runner-driven local changes exist
- commit/tag automation
- push
- PR creation
- merge
- daemon or unbounded loop

## Next after Prompt285-F

Run Prompt285-G.

Goals:
1. Fix invocation_command shape so approval_policy="never" is passed with its own -c.
2. Compare direct shell Codex execution and runner subprocess execution using the exact same command/environment posture.
3. Determine whether remaining WebSocket Operation not permitted is caused by command shape, subprocess invocation, inherited process restrictions, or external network policy.

Do not proceed to Prompt285-B until runner-driven Codex exits 0 and creates tmp_runner_live_write_probe.txt.

## Next after Phase B/C PASS

Run Prompt285-B local git diff capture.

Goal:
- Capture local repository changes from git directly.
- Do not trust Codex self-reported diff text.
- Use tmp_runner_live_write_probe.txt as the current known local change for the first capture pass.

Expected artifacts:
- diff_capture.json
- diff_summary.md
- reviewable_diff.patch
- changed_files.json

Still prohibited:
- commit/tag automation
- push
- PR creation
- merge
- daemon or unbounded loop

## Next after Prompt285-B

Run Prompt286 review request generation.

Goal:
- Build a review request from local git diff capture artifacts.
- Use diff_capture.json, diff_summary.md, reviewable_diff.patch, and changed_files.json as authoritative inputs.
- Do not trust Codex self-reported diff text.

Still prohibited:
- push
- PR creation
- merge
- daemon or unbounded loop
- autonomous commit/tag automation

## Next after Prompt286

Run Prompt287 review response assimilation.

Goal:
- Read a ChatGPT review response artifact.
- Normalize the review decision into approve / fix / revert / manual_review.
- Enforce safety rules before any approve/fix/revert routing.

Still prohibited:
- push
- PR creation
- merge
- daemon or unbounded loop
- autonomous commit/tag automation

## Next after Prompt287

Run Prompt288 approve/fix/revert route preparation.

Goal:
- Read review_decision.json if available.
- Route normalized decision into approve / fix / revert / manual_review preparation.
- Do not execute commit, tag, fix, revert, push, PR, or merge.

Expected behavior:
- Missing review_decision.json -> wait_for_chatgpt_diff_review_response.
- approve allowed only when safe_to_commit=true and requires_fix=false and requires_revert=false.
- fix -> prepare_fix_route.
- revert -> prepare_revert_route.
- manual_review -> manual_review_required.

Still prohibited:
- autonomous commit/tag automation
- push
- PR creation
- merge
- daemon or unbounded loop

## Next after Prompt288

Current route:
- manual_review_required

Options:
1. Replace review_decision.json with a real high/medium-confidence review decision and rerun Prompt288.
2. If keeping manual_review, run Prompt289 to record PR queue state as manual_review/blocked.

Still prohibited:
- autonomous commit/tag execution
- push
- PR creation
- merge
- unbounded loop

## Next after Prompt288-fix

Current route:
- selected_route=fix
- next_action=prepare_codex_fix_prompt

Next:
- Generate a bounded Codex fix prompt that removes or explicitly excludes tmp_runner_live_write_probe.txt from commit/readiness path, or otherwise prepares the fix route without executing commit/tag/push/PR/merge.

Still prohibited:
- autonomous commit/tag execution
- push
- PR creation
- merge
- unbounded loop

## Next after Prompt288-fix-followup

Current state:
- selected_route=fix
- next_action=ready_for_bounded_codex_fix_invocation

Next:
- Run a single bounded Codex fix invocation using:
  /tmp/codex-local-runner-decision/codex_fix_prompt/codex_fix_prompt.md

Still prohibited:
- autonomous commit/tag execution
- push
- PR creation
- merge
- unbounded loop

## Next after Prompt288 approval route

Run Prompt290 commit/tag readiness preparation.

Goal:
- Consume selected_route=approve.
- Build commit/tag readiness metadata.
- Generate a commit plan without executing commit/tag.
- Exclude runtime artifacts.
- Confirm tmp_runner_live_write_probe.txt is absent.
- Do not push, PR, merge, or execute commit/tag yet.

Expected next_action:
- ready_for_bounded_commit_tag_execution

## Next after Prompt296 / Prompt296-fix

Run Prompt297.

Goal:
- Read /tmp/codex-local-runner-decision/next_dev_slice/next_dev_slice.json.
- Generate local Codex implementation prompt artifacts.
- Do not invoke Codex from inside runner.
- Do not execute the generated implementation prompt yet.
- Do not commit/tag/push/PR/merge.

Expected next_action:
- ready_for_bounded_local_codex_implementation

## Next after Prompt297 readiness

Run Prompt298.

Goal:
- Confirm local_codex_exec_plan.sh is present and safe.
- Execute local Codex once from local shell using the generated plan.
- Do not commit/tag/push/PR/merge.
- After execution, run syntax check and return to local git diff capture/review flow.

Expected after Prompt298:
- local Codex has produced repo changes, or no-op with a clear result.
- Next action returns to local_git_diff_capture.
