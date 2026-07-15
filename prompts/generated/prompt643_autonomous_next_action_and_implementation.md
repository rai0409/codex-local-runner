PROMPT643_AUTONOMOUS_NEXT_ACTION_AND_IMPLEMENTATION

Repository:
- /home/rai/codex-local-runner

Goal:
Analyze the current system state and determine the next most important implementation step toward:

"Project-level autonomous development with minimal human intervention"

Then IMPLEMENT it immediately.

This is NOT analysis-only.
This is execution + implementation + validation.

Proceed autonomously.
Do not ask for confirmation.
Do not stop after planning.
Do not wait for approval.

---

Current known state:

- Current branch: local/prompt299-one-cycle-controller-v1
- Commit: 714bb11
- Tag: prompt639-multi-cycle-targeted-fix-acceptance

Confirmed capabilities:
- multi-task daemon queue execution (Prompt639)
- strict effect verification gate (Prompt638B)
- sandbox isolation (/tmp only)
- commit/tag only on success
- cleanup of generated artifacts
- standalone targeted_fix_retry works (Prompt639)
- failure detection is correct (no false success)
- bounded execution already stable (L7.5 system)

Critical missing capability:
- daemon_queue is NOT yet wired to automatically invoke run_targeted_fix_retry
- no project-level planner exists
- no task generation from intent exists
- no full autonomous loop controller exists

---

Your task:

1. Inspect the repository and identify:
   - the next SINGLE most important missing capability to implement
   - must be the highest leverage step toward full autonomy (L8 direction)

2. You MUST choose ONE of the following categories:
   - daemon queue integration fix (likely Prompt640 continuation)
   - targeted fix retry wiring
   - queue orchestration improvement
   - effect gate strengthening
   - task lifecycle correction
   - safety enforcement improvement

Do NOT expand scope into project planner unless prerequisite is done.

---

3. Implement the chosen change:

If code changes are needed:
- modify minimal required files only
- ensure no regression in existing daemon queue
- maintain /tmp sandbox isolation
- preserve strict effect verification logic
- ensure commit/tag only happens after successful effect verification

Likely files:
- scripts/run_task_queue_daemon.py
- automation/orchestration/planned_runner/daemon_queue.py
- automation/orchestration/planned_runner/autonomous_cycle.py
- automation/orchestration/planned_runner/targeted_fix_retry.py
- automation/orchestration/planned_runner/effect_gate.py

---

4. Add tests:

You MUST add or update tests covering:

- effect_failed task triggers targeted_fix_retry automatically
- successful fix leads to:
  → effect verification pass
  → commit/tag
  → queue done
- unsuccessful fix leads to:
  → queue failed
  → no commit/tag
- strict gate prevents false success
- backward compatibility remains intact

---

5. Run validation:

- run full test suite
- ensure no regression
- ensure daemon queue still processes multiple tasks
- ensure sandbox isolation is preserved

---

6. Output required artifacts:

- artifacts/autonomous_runtime/prompt643_next_action_report.json
- artifacts/autonomous_runtime/prompt643_next_action_summary.md

---

7. Final stdout (STRICT FORMAT):

Print ONLY:

prompt643_status=success|partial|blocked
prompt643_next_action=<what was implemented>
prompt643_files_modified=<list>
prompt643_tests_result=passed|failed
prompt643_daemon_behavior_changed=true|false
prompt643_effect_verification_preserved=true|false
prompt643_main_repo_safe=true|false
prompt643_commit=<commit_hash_if_any>
prompt643_tag=<tag_if_any>
prompt643_report_path=artifacts/autonomous_runtime/prompt643_next_action_report.json
prompt643_summary_path=artifacts/autonomous_runtime/prompt643_next_action_summary.md
prompt643_next_action=continue_or_stop

---

Rule:
- Prefer smallest possible change that increases autonomy
- Do NOT implement project planner yet
- Do NOT expand scope beyond daemon execution + retry integration
- Do NOT introduce new task types unless necessary
- Do NOT break existing L7.5 guarantees

