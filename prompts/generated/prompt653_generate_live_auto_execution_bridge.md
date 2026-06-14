PROMPT653_GENERATE_LIVE_AUTO_EXECUTION_BRIDGE

Repository:
- /home/rai/codex-local-runner

Goal:
Generate the next executable implementation prompt for:

live_auto_execution_bridge

This is prompt-generation only.
Do not implement source changes.
Do not stage.
Do not commit.
Do not tag.
Do not push.
Do not PR.
Do not merge.
Do not run Codex jobs.
Do not run daemon queue jobs.
Do not enqueue tasks into any live/default queue.
Do not touch artifacts/archive.
Do not modify handoff_reports.
Proceed autonomously without asking for confirmation.

# User's real goal

The user wants a project-level autonomous development runner.

Given one project-level goal, the system should autonomously:
1. analyze the repo state,
2. generate/decompose tasks,
3. create a bounded project plan,
4. populate daemon-ready queue files,
5. run or coordinate execution safely,
6. collect real task outcomes,
7. feed outcomes into a completion gate,
8. iterate until project completion or a real safety/blocking condition,
9. commit/tag successful changes.

The offline project chain is now proven, but live auto-execution is still missing.

# Current known state to verify

Expected:
- current_head: 650c2b7
- latest_confirmed_implementation: prompt651
- project_level_autonomy_complete=false
- current_capability_boundary=offline_project_autonomy_chain_complete_and_e2e_proven_live_auto_execution_pending
- final_score_out_of_100=88
- next_recommended_target=live_auto_execution_bridge
- next_recommended_action=generate_prompt653_live_auto_execution_bridge

Confirmed completed layers expected:
- Prompt644A / earlier:
  - L7.5 task/job-level self-healing daemon execution
  - strict effect gate
  - targeted-fix retry inside daemon
- Prompt645:
  - ProjectIntent model
  - ProjectTaskPlan model
- Prompt646:
  - deterministic ProjectIntent + descriptors -> ProjectTaskPlan generation
- Prompt647:
  - ProjectTaskPlan -> daemon-ready queue input files
- Prompt648:
  - project progress / completion gate
- Prompt649:
  - bounded offline iterate-until-done controller
- Prompt651:
  - offline project-level E2E acceptance

Missing critical gap:
- live_auto_execution_bridge:
  project loop/controller -> populated queue -> bounded live daemon execution -> real run reports -> completion gate -> next project decision

# Required repo inspection

Inspect at minimum:
- pwd
- git log -1 --oneline
- git tag --points-at HEAD
- git status --short
- git show --stat --oneline HEAD
- artifacts/autonomous_runtime/prompt653_current_completion_and_next_action_analysis_report.json
- artifacts/autonomous_runtime/prompt653_current_completion_and_next_action_analysis_summary.md
- artifacts/autonomous_runtime/project_level_autonomy_loop_final_report.json
- artifacts/autonomous_runtime/project_level_autonomy_loop_final_summary.md
- artifacts/autonomous_runtime/prompt651_report.json
- artifacts/autonomous_runtime/prompt651_summary.md
- artifacts/autonomous_runtime/prompt649_report.json
- artifacts/autonomous_runtime/prompt649_summary.md
- artifacts/autonomous_runtime/prompt648_report.json
- artifacts/autonomous_runtime/prompt648_summary.md
- artifacts/autonomous_runtime/prompt647_report.json
- artifacts/autonomous_runtime/prompt647_summary.md
- scripts/run_task_queue_daemon.py
- automation/orchestration/planned_runner/project_loop_controller.py
- automation/orchestration/planned_runner/project_completion_gate.py
- automation/orchestration/planned_runner/project_queue_population.py
- automation/orchestration/planned_runner/project_task_generator.py
- automation/orchestration/planned_runner/project_plan.py
- automation/orchestration/planned_runner/project_intent.py
- automation/orchestration/planned_runner/daemon_queue.py
- automation/orchestration/planned_runner/targeted_fix_retry.py
- automation/orchestration/planned_runner/task_spec.py
- tests relevant to project loop, completion gate, queue population, daemon queue, targeted fix

Also check if already present:
- automation/orchestration/planned_runner/project_live_execution_bridge.py
- tests/test_project_live_execution_bridge.py
- scripts/run_project_live_bridge.py
- artifacts/autonomous_runtime/prompt653_report.json
- artifacts/autonomous_runtime/prompt653_summary.md
- tag prompt653-live-auto-execution-bridge

# Decision rule

If live_auto_execution_bridge is already implemented, tested, reported, and tagged:
- do not duplicate it
- generate a prompt for the next missing target instead

Otherwise generate the implementation prompt for Prompt653:
- prompts/generated/prompt653_live_auto_execution_bridge.md

# Required implementation-prompt scope

The generated Prompt653 implementation prompt must implement a safe, operator-triggered live auto-execution bridge.

It must be dry-run by default.

It must require explicit live enable conditions for any real daemon/Codex execution:
- dry_run=false
- enable_live=true
- enable_token matches expected_enable_token
- explicit output_queue_dir
- bounded max_project_cycles
- bounded max_daemon_jobs
- bounded max_fix_attempts

It must not run uncontrolled daemon loops.
It must not mutate default/live queues.
It must not bypass strict effect gate.
It must not invent success from queue files or prompt generation.
It must not run live daemon/Codex in tests.

# Expected implementation files in generated prompt

Likely:
- automation/orchestration/planned_runner/project_live_execution_bridge.py
- tests/test_project_live_execution_bridge.py
- artifacts/autonomous_runtime/prompt653_report.json
- artifacts/autonomous_runtime/prompt653_summary.md
- artifacts/autonomous_runtime/prompt653_goal_aligned_implementation_report.json
- artifacts/autonomous_runtime/prompt653_goal_aligned_implementation_summary.md

Optional if justified:
- scripts/run_project_live_bridge.py

# Required behavior for generated implementation prompt

The generated implementation prompt must require a primary function like:

run_project_live_execution_bridge(
    intent,
    task_descriptors,
    output_queue_dir,
    *,
    enable_live=False,
    enable_token="",
    expected_enable_token="I_UNDERSTAND_THIS_RUNS_LIVE_CODEX",
    max_project_cycles=1,
    max_daemon_jobs=1,
    max_fix_attempts=1,
    repo_path_override=None,
    dry_run=True,
    daemon_runner=None
) -> dict

Expected structured return:
{
  "status": "success" | "blocked" | "partial",
  "live_execution_performed": true|false,
  "dry_run": true|false,
  "errors": [...],
  "warnings": [...],
  "queue_dir": "...",
  "plan_result": {...},
  "queue_population_result": {...},
  "daemon_run_summary": {...},
  "completion_gate_result": {...},
  "project_complete": true|false,
  "next_action": "complete" | "continue_project_loop" | "manual_review_required" | "blocked"
}

The implementation prompt must require:
- dry-run path creates plan + queue summary but does not execute daemon/Codex
- live path is blocked unless every explicit enable condition is satisfied
- fake daemon adapter used in tests
- real daemon adapter boundary is explicit and bounded
- daemon outcomes are adapted into completion gate task statuses
- failure outcomes are never marked complete
- result parsing blocks safely if unreliable
- deterministic output for identical dry-run inputs

# Required tests for generated implementation prompt

The generated prompt must require tests for:
- dry_run creates plan/queue summary and live_execution_performed=false
- enable_live=false blocks live execution
- wrong/missing token blocks live execution
- missing output_queue_dir blocks live execution
- live mode uses explicit tmp queue dir only
- fake daemon success feeds completion gate and can complete project
- fake daemon failure feeds completion gate and does not complete project
- max cycles/jobs/fix attempts are bounded
- deterministic dry-run output for same inputs
- no live daemon/Codex/network/git side effects in tests
- existing project-layer tests remain green

Targeted tests expected:
- python -m unittest tests.test_project_live_execution_bridge
- python -m unittest tests.test_project_loop_controller
- python -m unittest tests.test_project_completion_gate
- python -m unittest tests.test_project_queue_population_from_plan
- python -m unittest tests.test_project_task_generator_from_intent
- python -m unittest tests.test_project_intent_plan_model
- python -m unittest tests.test_daemon_queue
- python -m unittest tests.test_targeted_fix_retry

# Generated prompt hard safety boundaries

The generated implementation prompt must explicitly forbid:
- push / PR / merge
- touching artifacts/archive
- modifying handoff_reports
- reading or printing secrets
- modifying .env files
- network operations
- uncontrolled daemon loops
- live/default queue mutation
- live daemon/Codex in tests
- bypassing strict effect gate
- inventing success without real run reports
- task-kind expansion
- long-running soak

# Required output files from this prompt-generation run

Write:
- prompts/generated/prompt653_live_auto_execution_bridge.md
- artifacts/autonomous_runtime/prompt653_prompt_generation_report.json
- artifacts/autonomous_runtime/prompt653_prompt_generation_summary.md

Required generation report fields:
- prompt653_generator_status
- prompt653_generator_base_commit
- prompt653_generator_tags_at_head
- prompt653_generator_latest_confirmed_implementation
- prompt653_generator_current_capability_boundary
- prompt653_generator_project_level_autonomy_complete
- prompt653_generator_next_target_selected
- prompt653_generator_next_target_rationale
- prompt653_generator_prompt_path
- prompt653_generator_prompt_created
- prompt653_generator_scope
- prompt653_generator_excluded_scope
- prompt653_generator_recommended_files
- prompt653_generator_recommended_tests
- prompt653_generator_safety_constraints_included
- prompt653_generator_final_decision
- prompt653_generator_next_action

# Expected final stdout

Print only:
prompt653_generator_status=<success|blocked|partial>
prompt653_generator_base_commit=<commit>
prompt653_generator_next_target_selected=<live_auto_execution_bridge|other>
prompt653_generator_prompt_path=prompts/generated/prompt653_live_auto_execution_bridge.md
prompt653_generator_next_action=execute_prompt653_live_auto_execution_bridge
prompt653_generator_report_path=artifacts/autonomous_runtime/prompt653_prompt_generation_report.json
prompt653_generator_summary_path=artifacts/autonomous_runtime/prompt653_prompt_generation_summary.md
