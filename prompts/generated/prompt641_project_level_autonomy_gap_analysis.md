PROMPT641_PROJECT_LEVEL_AUTONOMY_GAP_ANALYSIS

Repository:
- /home/rai/codex-local-runner

Goal:
Analyze the current codex-local-runner state and determine exactly what must be implemented to reach the user's real goal:

"Given a project-level goal, run development as autonomously as possible with Codex/ChatGPT until completion, minimizing human intervention."

This is analysis-only.
Do not implement source changes.
Do not stage.
Do not commit.
Do not tag.
Do not push.
Do not PR.
Do not merge.
Do not touch artifacts/archive.
Do not modify handoff_reports.
Do not run unbounded live daemon loops.
Proceed autonomously without asking for confirmation.

Known current state:
- Current branch: local/prompt299-one-cycle-controller-v1
- Current committed/tagged state:
  - commit: 714bb11
  - tag: prompt639-multi-cycle-targeted-fix-acceptance
- Prompt637 verified sandbox cleanup and final clean checks.
- Prompt638B implemented strict effect verification success gate.
- Prompt638C verified current level as L7.
- Prompt639 verified multi-cycle targeted-fix acceptance:
  - daemon queue processed multiple jobs
  - 3 passed-effect tasks succeeded with sandbox commit/tag/done
  - 1 deterministic failed-effect task was blocked with no commit/tag/failed
  - standalone run_targeted_fix_retry triggered and resolved a failed effect in 1 fix attempt
  - strict_gate_violations=0
  - main repo unchanged during runtime
- Prompt640 implementation prompt was generated for daemon_queue_targeted_fix_retry_integration.
- Current important gap:
  - run_targeted_fix_retry is proven standalone
  - daemon queue runner is not yet wired to invoke it automatically
- User's real goal is NOT just prompt-by-prompt automation.
- User's real goal is project-level autonomous development:
  - project intent -> task planning -> queue execution -> verification -> targeted fix -> commit/tag -> next task -> completion report
  - as little human intervention as possible

Required analysis:

1. Verify current repo baseline
Inspect:
- git branch
- HEAD commit
- tags at HEAD
- git status
- staged changes
- known untracked archive/handoff artifacts

2. Verify current capability from committed state and artifacts
Inspect at minimum:
- scripts/run_task_queue_daemon.py
- automation/orchestration/planned_runner/autonomous_cycle.py
- automation/orchestration/planned_runner/autonomous_live_loop.py
- automation/orchestration/planned_runner/effect_gate.py
- automation/orchestration/planned_runner/targeted_fix_retry.py
- automation/orchestration/planned_runner/task_spec.py
- automation/orchestration/planned_runner/task_planner.py
- automation/orchestration/planned_runner/daemon_queue.py
- artifacts/autonomous_runtime/prompt637_sandbox_generated_artifact_cleanup_policy_report.json
- artifacts/autonomous_runtime/prompt638b_strict_effect_verification_success_gate_report.json
- artifacts/autonomous_runtime/prompt638c_current_state_deep_verification_report.json if present
- artifacts/autonomous_runtime/prompt639_report.json
- artifacts/autonomous_runtime/prompt640_prompt_generation_report.json if present
- prompts/generated/prompt640_daemon_queue_targeted_fix_retry_integration.md if present

3. Determine exactly what is already proven
Classify evidence for:
- multiple queue task execution
- effect verification
- strict failed-effect gate
- sandbox cleanup
- sandbox commit/tag
- main repo runtime safety
- standalone targeted-fix retry
- bounded daemon acceptance
- task kind support
- crash/recover/resume support, if present
- long-running daemon support, if present

4. Determine what is NOT yet proven or not implemented
Specifically analyze:
- Is project-level planning implemented?
- Is there a project intent file/schema?
- Is there automatic task decomposition?
- Is there automatic task spec generation beyond add_function?
- Is there automatic queue population from a project plan?
- Is daemon queue wired to targeted-fix retry?
- Is there a project-level loop controller that continues until project done?
- Is there a completion criterion for a project?
- Is there a risk/stop policy?
- Is there a summary/handoff/reporting layer?
- Is there a way to ask ChatGPT/Codex to generate the next task based on previous results?
- Is there a task dependency graph?
- Is there prioritization?
- Is there broad task kind support?
- Is there long-running daemon soak proof?
- Is there human approval only at high-risk boundaries?

5. Define the user's target architecture
Create a concrete architecture for project-level autonomy with these layers:
- Project Intent Layer
- Planner Layer
- Task Spec Generator Layer
- Queue Orchestrator Layer
- Execution Layer
- Verification Layer
- Self-Healing / Targeted Fix Layer
- Commit/Tag Layer
- Project Progress / Completion Layer
- Safety / Stop Policy Layer

6. Map current repo modules to that architecture
For each layer, state:
- existing module(s)
- current maturity
- missing pieces
- recommended implementation file(s)
- likely tests

7. Recommend the next implementation sequence
Create a strict sequence of prompts from Prompt640 onward.
The sequence should be optimized for reaching project-level autonomous development as fast as safely possible.

Consider at least:
- Prompt640 daemon_queue_targeted_fix_retry_integration
- Prompt641 project_intent_schema_and_plan_model
- Prompt642 project_task_generator_from_intent
- Prompt643 project_queue_orchestrator
- Prompt644 project_progress_and_completion_gate
- Prompt645 project_level_auto_loop_controller
- Prompt646 task_kind_expansion
- Prompt647 long_running_daemon_soak
- Prompt648 project_level_acceptance_e2e

But do not blindly use these names. Choose the best sequence based on actual repo state.

8. Decide what should be implemented next
Choose exactly one next implementation target.
It must be justified by evidence.

Possible next actions:
- execute_prompt640_daemon_queue_targeted_fix_retry_integration
- implement_project_intent_schema
- implement_project_planner_task_generation
- implement_project_queue_orchestrator
- expand_task_kinds
- long_running_daemon_soak
- manual_review_required

9. Generate a detailed recommendation
The recommendation must answer:
- What should be implemented next?
- Why that before other options?
- What should be postponed?
- What files are likely involved?
- What tests are required?
- What acceptance scenario proves progress toward the user's goal?
- What would still remain after the next prompt?

Required report:
Write:
- artifacts/autonomous_runtime/prompt641_project_level_autonomy_gap_analysis_report.json
- artifacts/autonomous_runtime/prompt641_project_level_autonomy_gap_analysis_summary.md

Required report fields:
- prompt641_status
- prompt641_base_commit
- prompt641_tags_at_head
- prompt641_current_capability_level
- prompt641_user_goal_interpretation
- prompt641_proven_capabilities
- prompt641_unproven_capabilities
- prompt641_missing_architecture_layers
- prompt641_target_architecture
- prompt641_current_module_mapping
- prompt641_next_implementation_target
- prompt641_next_implementation_rationale
- prompt641_recommended_prompt_sequence
- prompt641_recommended_files_for_next_prompt
- prompt641_recommended_tests_for_next_prompt
- prompt641_acceptance_scenario_for_next_prompt
- prompt641_post_next_remaining_gaps
- prompt641_risks
- prompt641_final_decision
- prompt641_next_action

Expected final stdout:
Print only:
prompt641_status=<success|blocked|partial>
prompt641_current_capability_level=<L5|L6|L7|L7.5|L8_candidate|unknown>
prompt641_user_goal=project_level_autonomous_development
prompt641_next_implementation_target=<target>
prompt641_next_action=<execute_prompt640_daemon_queue_targeted_fix_retry_integration|implement_project_intent_schema|implement_project_planner_task_generation|implement_project_queue_orchestrator|expand_task_kinds|long_running_daemon_soak|manual_review_required>
prompt641_report_path=artifacts/autonomous_runtime/prompt641_project_level_autonomy_gap_analysis_report.json
prompt641_summary_path=artifacts/autonomous_runtime/prompt641_project_level_autonomy_gap_analysis_summary.md
