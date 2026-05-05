
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
