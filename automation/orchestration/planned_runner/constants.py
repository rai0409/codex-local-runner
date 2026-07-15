from __future__ import annotations

_UNIT_PROGRESSION_SCHEMA_VERSION = "v1"
_DECISION_SCHEMA_VERSION = "v1"
_CHECKPOINT_SCHEMA_VERSION = "v1"
_RUN_STATE_SCHEMA_VERSION = "v1"
_COMMIT_EXECUTION_SCHEMA_VERSION = "v1"
_PUSH_EXECUTION_SCHEMA_VERSION = "v1"
_PR_EXECUTION_SCHEMA_VERSION = "v1"
_MERGE_EXECUTION_SCHEMA_VERSION = "v1"
_ROLLBACK_EXECUTION_SCHEMA_VERSION = "v1"

__all__ = [
    "_CHECKPOINT_SCHEMA_VERSION",
    "_COMMIT_EXECUTION_SCHEMA_VERSION",
    "_DECISION_SCHEMA_VERSION",
    "_MERGE_EXECUTION_SCHEMA_VERSION",
    "_PR_EXECUTION_SCHEMA_VERSION",
    "_PUSH_EXECUTION_SCHEMA_VERSION",
    "_ROLLBACK_EXECUTION_SCHEMA_VERSION",
    "_RUN_STATE_SCHEMA_VERSION",
    "_UNIT_PROGRESSION_SCHEMA_VERSION",
]

_UNIT_PROGRESSION_SCHEMA_VERSION = 'v1'

_UNIT_STATE_PLANNED = 'planned'

_COMMIT_DECISIONS = {"allowed", "blocked", "manual_required", "unknown"}
_MERGE_DECISIONS = {"allowed", "blocked", "manual_required", "unknown"}
_ROLLBACK_DECISIONS = {"required", "not_required", "blocked", "manual_required", "unknown"}
_READINESS_STATUSES = {
    "ready",
    "not_ready",
    "manual_required",
    "blocked",
    "awaiting_prerequisites",
}
_READINESS_NEXT_ACTIONS = {
    "prepare_commit",
    "prepare_merge",
    "prepare_rollback_evaluation",
    "await_manual_review",
    "resolve_blockers",
    "hold",
}
_CHECKPOINT_STAGES = {
    "post_execution",
    "post_review",
    "pre_commit_evaluation",
    "pre_merge_evaluation",
    "pre_rollback_evaluation",
}
_CHECKPOINT_DECISIONS = {
    "proceed",
    "pause",
    "retry",
    "manual_review_required",
    "escalate",
    "commit_evaluation_ready",
    "merge_evaluation_ready",
    "rollback_evaluation_ready",
    "global_stop_recommended",
}

_APPROVED_RESTART_EXECUTION_SCHEMA_VERSION = 'v1'

_APPROVED_RESTART_EXECUTION_STATUSES = {'executed', 'not_executed'}

_APPROVED_RESTART_ALLOWED_DECISIONS = {'allow_same_lane_retry', 'allow_repair_retry', 'allow_truth_gathering', 'allow_replan_preparation', 'allow_closure_followup'}

_APPROVAL_SKIP_GATE_DECISIONS = {'skip_and_continue_once', 'require_human_approval', 'not_applicable'}

_APPROVAL_SKIP_DIRECTION_TO_POSTURE = {'same_lane_retry': {'response_command': 'OK RETRY', 'restart_decision': 'allow_same_lane_retry'}, 'repair_retry': {'response_command': 'OK RETRY', 'restart_decision': 'allow_repair_retry'}, 'truth_gathering': {'response_command': 'OK TRUTH', 'restart_decision': 'allow_truth_gathering'}, 'replan_preparation': {'response_command': 'OK REPLAN', 'restart_decision': 'allow_replan_preparation'}, 'closure_followup': {'response_command': 'OK CLOSE', 'restart_decision': 'allow_closure_followup'}}

_CONTINUATION_BUDGET_SCHEMA_VERSION = 'v1'

_CONTINUATION_BUDGET_STATUSES = {'available', 'exhausted', 'insufficient_truth'}

_CONTINUATION_BUDGET_DECISIONS = {'allow_under_budget', 'deny_budget_exhausted', 'deny_insufficient_truth'}

_CONTINUATION_BUDGET_RUN_LIMIT_DEFAULT = 2

_CONTINUATION_BUDGET_OBJECTIVE_LIMIT_DEFAULT = 2

_CONTINUATION_BUDGET_LANE_LIMIT_DEFAULT = 2

_CONTINUATION_BUDGET_BRANCH_TYPES = {'retry', 'replan', 'truth_gather'}

_CONTINUATION_BUDGET_BRANCH_STATUSES = {'available', 'exhausted', 'not_applicable'}

_CONTINUATION_BUDGET_BRANCH_DECISIONS = {'allow_under_branch_ceiling', 'deny_branch_ceiling_exhausted', 'not_applicable'}

_CONTINUATION_BUDGET_BRANCH_LIMIT_DEFAULTS = {'retry': 2, 'replan': 2, 'truth_gather': 2}

_CONTINUATION_REPAIR_PLAYBOOK_STATUSES = {'selected', 'not_selected', 'insufficient_truth'}

_CONTINUATION_NEXT_STEP_SELECTION_STATUSES = {'selected', 'not_selected', 'insufficient_truth'}

_CONTINUATION_NEXT_STEP_TARGETS = {'retry', 'replan', 'truth_gather', 'supported_repair', 'none'}

_CONTINUATION_REPAIR_PLAYBOOKS = {'objective_gap': {'repair_plan_class': 'replan_plan', 'repair_plan_candidate_action': 'request_replan'}, 'completion_gap': {'repair_plan_class': 'closure_followup_plan', 'repair_plan_candidate_action': 'request_closure_followup'}, 'approval_blocker': {'repair_plan_class': 'manual_review_plan', 'repair_plan_candidate_action': 'request_manual_review'}, 'reconcile_mismatch': {'repair_plan_class': 'truth_gathering_plan', 'repair_plan_candidate_action': 'gather_missing_truth'}, 'execution_failure': {'repair_plan_class': 'replan_plan', 'repair_plan_candidate_action': 'request_replan'}, 'execution_partial': {'repair_plan_class': 'truth_gathering_plan', 'repair_plan_candidate_action': 'gather_missing_truth'}, 'verification_failure': {'repair_plan_class': 'truth_gathering_plan', 'repair_plan_candidate_action': 'gather_missing_truth'}, 'retry_exhausted': {'repair_plan_class': 'replan_plan', 'repair_plan_candidate_action': 'request_replan'}, 'same_failure_exhausted': {'repair_plan_class': 'replan_plan', 'repair_plan_candidate_action': 'request_replan'}, 'no_progress': {'repair_plan_class': 'manual_review_plan', 'repair_plan_candidate_action': 'request_manual_review'}, 'oscillation': {'repair_plan_class': 'manual_review_plan', 'repair_plan_candidate_action': 'request_manual_review'}, 'lane_mismatch': {'repair_plan_class': 'replan_plan', 'repair_plan_candidate_action': 'request_replan'}, 'closure_unresolved': {'repair_plan_class': 'closure_followup_plan', 'repair_plan_candidate_action': 'request_closure_followup'}, 'terminal_non_success': {'repair_plan_class': 'manual_review_plan', 'repair_plan_candidate_action': 'request_manual_review'}}

_SUPPORTED_REPAIR_EXECUTION_STATUSES = {'not_selected', 'not_executed_precheck_blocked', 'not_executed_qualification_failed', 'not_executed_launch_failed', 'executed_verification_passed', 'executed_verification_failed'}

_FINAL_HUMAN_REVIEW_GATE_STATUSES = {'required', 'not_required'}

_PROJECT_PLANNING_SUMMARY_STATUSES = {'available', 'insufficient_truth'}

_PROJECT_ROADMAP_STATUSES = {'available', 'insufficient_truth'}

_PROJECT_PR_SLICING_STATUSES = {'available', 'insufficient_truth'}

_PROJECT_PR_SIZE_DECISIONS = {'single_theme_single_pr', 'not_available'}

_PROJECT_PR_PRIORITIZATION_MODES = {'blocked_last_narrow_first_prereq_first', 'insufficient_truth'}

_PROJECT_ROADMAP_SCOPE_CLASS_ORDER = {'runner_only': 0, 'runner_and_tests': 1, 'cross_surface': 2, 'unknown': 3}

_PROJECT_ROADMAP_TOPIC_ORDER = ('continuation_budget', 'branch_ceiling', 'failure_bucket_gate', 'next_step_selection', 'supported_repair_posture', 'human_review_gate')

_PROJECT_ROADMAP_ITEM_ORDER = {f'roadmap_{topic}': index for index, topic in enumerate(_PROJECT_ROADMAP_TOPIC_ORDER)}

_PROJECT_ROADMAP_PREREQUISITES = {'roadmap_branch_ceiling': ('roadmap_continuation_budget',), 'roadmap_failure_bucket_gate': ('roadmap_continuation_budget',), 'roadmap_supported_repair_posture': ('roadmap_next_step_selection',), 'roadmap_human_review_gate': ('roadmap_next_step_selection',)}

_REVIEW_ASSIMILATION_STATUSES = {'assimilated', 'no_action', 'insufficient_truth'}

_REVIEW_ASSIMILATION_ACTIONS = {'accept', 'retry', 'replan', 'split', 'escalate', 'none'}

_SELF_HEALING_STATUSES = {'executed', 'selected', 'blocked', 'not_applicable', 'insufficient_truth'}

_SELF_HEALING_TRANSITION_TARGETS = {'retry', 'replan', 'truth_gather', 'alternative_supported_repair', 'none'}

_SELF_HEALING_CHAIN_LIMIT_DEFAULT = 1

_LONG_RUNNING_STALE_AFTER_SECONDS_DEFAULT = 900
_LONG_RUNNING_STABILITY_STATUSES = {
    "monitoring",
    "paused",
    "resume_ready",
    "safe_stop",
    "escalated",
    "insufficient_truth",
}

_LONG_RUNNING_STUCK_CYCLE_THRESHOLD_DEFAULT = 2

_OBJECTIVE_COMPILER_STATUSES = {'available', 'insufficient_truth'}

_OBJECTIVE_DONE_CRITERIA_STATUSES = {'met', 'not_met', 'insufficient_truth'}

_OBJECTIVE_STOP_CRITERIA_STATUSES = {'stop', 'continue', 'insufficient_truth'}

_OBJECTIVE_COMPLETION_POSTURES = {'objective_active', 'objective_completed', 'objective_blocked', 'objective_insufficient_truth'}

_OBJECTIVE_SCOPE_DRIFT_STATUSES = {'detected', 'clear', 'insufficient_truth'}

_PROJECT_AUTONOMY_BUDGET_STATUSES = {'available', 'insufficient_truth'}

_PROJECT_PRIORITY_POSTURES = {'active', 'lower_priority', 'deferred', 'completed', 'insufficient_truth'}

_PROJECT_BUDGET_POSTURES = {'available', 'exhausted', 'insufficient_truth'}

_PROJECT_PR_RETRY_BUDGET_POSTURES = {'available', 'exhausted', 'not_applicable', 'insufficient_truth'}

_PROJECT_HIGH_RISK_DEFER_POSTURES = {'defer', 'clear', 'insufficient_truth'}

_PROJECT_QUALITY_GATE_STATUSES = {'available', 'insufficient_truth'}

_PROJECT_QUALITY_GATE_POSTURES = {'merge_ready', 'review_ready', 'retry_needed', 'insufficient_truth'}

_PROJECT_QUALITY_GATE_NAMES = {'unit', 'targeted_regression', 'lint', 'typecheck'}

_PROJECT_QUALITY_GATE_CHANGED_AREA_CLASSES = {'runner_and_tests', 'runner_only', 'unknown'}

_PROJECT_QUALITY_GATE_RISK_LEVELS = {'high', 'moderate', 'low', 'insufficient_truth'}

_PROJECT_MERGE_BRANCH_LIFECYCLE_STATUSES = {'available', 'insufficient_truth'}

_PROJECT_MERGE_READY_POSTURES = {'merge_ready', 'not_merge_ready', 'insufficient_truth'}

_PROJECT_BRANCH_CANDIDATE_POSTURES = {'candidate', 'not_candidate', 'insufficient_truth'}

_PROJECT_LOCAL_MAIN_SYNC_POSTURES = {'sync_required', 'sync_not_required', 'insufficient_truth'}

_PROJECT_FAILURE_MEMORY_STATUSES = {'available', 'insufficient_truth'}

_PROJECT_FAILURE_MEMORY_SUPPRESSION_POSTURES = {'none', 'suppress_retry', 'suppress_repair', 'suppress_review_issue', 'suppress_failure_bucket', 'insufficient_truth'}

_PROJECT_HUMAN_ESCALATION_STATUSES = {'available', 'insufficient_truth'}

_PROJECT_HUMAN_ESCALATION_POSTURES = {'escalation_required', 'not_required', 'insufficient_truth'}

_PROJECT_HUMAN_ESCALATION_RISK_POSTURES = {'elevated', 'clear', 'insufficient_truth'}

_PROJECT_APPROVAL_NOTIFICATION_STATUSES = {'available', 'insufficient_truth'}

_PROJECT_APPROVAL_NOTIFICATION_READY_POSTURES = {'ready', 'not_ready', 'not_required', 'insufficient_truth'}

_PROJECT_APPROVAL_CHANNEL_POSTURES = {'email_send', 'email_draft', 'review_queue', 'manual_only', 'not_required', 'insufficient_truth'}

_PROJECT_APPROVAL_MOBILE_SUMMARY_POSTURES = {'available', 'not_required', 'insufficient_truth'}

_PROJECT_MULTI_OBJECTIVE_STATUSES = {'available', 'insufficient_truth'}

_PROJECT_ACTIVE_OBJECTIVE_SELECTION_POSTURES = {'selected', 'deferred', 'insufficient_truth'}

_PROJECT_BLOCKED_OBJECTIVE_DEFERRAL_POSTURES = {'deferred', 'not_deferred', 'insufficient_truth'}

_PROJECT_RESUMABLE_QUEUE_ORDERING_POSTURES = {'resume_selected_first', 'resume_blocked', 'resume_empty', 'resume_completed_waiting', 'deferred_non_runnable', 'insufficient_truth'}

_IMPLEMENTATION_PROMPT_PRESERVED_CONSTRAINTS_REFS = ('/home/rai/codex-local-runner/prompts/context/pr_history_index.md', '/home/rai/codex-local-runner/prompts/context/current_architecture_constraints.md', '/home/rai/codex-local-runner/prompts/base_contract_rules.md', '/home/rai/codex-local-runner/prompts/base_token_reduction_rules.md', '/home/rai/codex-local-runner/prompts/base_codex_execution_wrapper.md', '/home/rai/codex-local-runner/prompts/base_codex_return_format.md')

_IMPLEMENTATION_PROMPT_DEFAULT_PREFERRED_FILES = ('automation/orchestration/planned_execution_runner.py', 'tests/test_planned_execution_runner.py')

_IMPLEMENTATION_PROMPT_DEFAULT_OUT_OF_SCOPE = ('queue execution', 'codex invocation redesign', 'roadmap generation redesign', 'PR slicing redesign', 'approval/restart/repair redesign', 'new planner/controller framework', 'broad autonomous execution changes')

_IMPLEMENTATION_PROMPT_IN_SCOPE_BY_THEME = {'continuation_budget': ('deterministic continuation-budget behavior for selected bounded slice', 'compact runner and focused runner-test updates only'), 'branch_ceiling': ('deterministic branch-ceiling behavior for selected bounded slice', 'compact runner and focused runner-test updates only'), 'failure_bucket_gate': ('deterministic failure-bucket gate behavior for selected bounded slice', 'compact runner and focused runner-test updates only'), 'next_step_selection': ('deterministic next-step selection behavior for selected bounded slice', 'compact runner and focused runner-test updates only'), 'supported_repair_posture': ('deterministic supported-repair posture behavior for selected bounded slice', 'compact runner and focused runner-test updates only'), 'human_review_gate': ('deterministic final human-review gate behavior for selected bounded slice', 'compact runner and focused runner-test updates only')}

_SUPPORTED_REPAIR_EXECUTABLE_PLAYBOOK_CLASSES = {'replan_plan', 'truth_gathering_plan', 'closure_followup_plan'}

_SUPPORTED_REPAIR_EXECUTABLE_CANDIDATE_ACTIONS = {'request_replan', 'gather_missing_truth', 'request_closure_followup'}

_CONTINUATION_UNSAFE_FAILURE_BUCKETS = {'truth_missing', 'truth_conflict', 'authorization_denied', 'bridge_blocked', 'manual_only', 'external_truth_pending'}

_UNSAFE_REPO_BLOCKER_REASONS = {'changed_files_outside_strict_scope', 'working_tree_contains_out_of_scope_changes', 'working_tree_conflicts_present', 'working_tree_not_clean', 'repo_not_git_worktree', 'git_status_failed', 'git_add_failed', 'git_commit_failed', 'git_push_failed', 'git_diff_cached_failed', 'git_revert_failed'}

_REMOTE_PR_AMBIGUITY_REASONS = {'open_pr_lookup_unavailable', 'open_pr_lookup_api_failure', 'open_pr_lookup_empty', 'existing_pr_identity_ambiguous', 'pr_number_missing_or_invalid'}

_REMOTE_READINESS_BOUNDARY_METADATA_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/remote_readiness_boundary.json'

_REMOTE_READINESS_PLAN_METADATA_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/remote_readiness_plan.json'

_LOCAL_END_TO_END_CONTROLLER_COMPONENT_MATRIX_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_end_to_end_controller_component_matrix.json'

_LOCAL_END_TO_END_CONTROLLER_READINESS_BOUNDARY_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_end_to_end_controller_readiness_boundary.json'

_LOCAL_END_TO_END_CONTROLLER_GAP_REPORT_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_end_to_end_controller_gap_report.json'

_LOCAL_END_TO_END_DRY_RUN_PLAN_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_end_to_end_dry_run_plan.json'

_LOCAL_END_TO_END_DRY_RUN_STEP_MATRIX_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_end_to_end_dry_run_step_matrix.json'

_LOCAL_END_TO_END_DRY_RUN_RECEIPT_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_end_to_end_dry_run_receipt.json'

_LOCAL_END_TO_END_ONE_SHOT_EXECUTION_GATE_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_end_to_end_one_shot_execution_gate.json'

_LOCAL_END_TO_END_ONE_SHOT_EXECUTION_RECEIPT_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_end_to_end_one_shot_execution_receipt.json'

_BOUNDED_LOCAL_AUTONOMOUS_LOOP_STATE_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/bounded_local_autonomous_loop_state.json'

_BOUNDED_LOCAL_AUTONOMOUS_LOOP_DECISION_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/bounded_local_autonomous_loop_decision.json'

_BOUNDED_LOCAL_AUTONOMOUS_LOOP_RECEIPT_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/bounded_local_autonomous_loop_receipt.json'

_UNIT_STATE_REVIEWED = 'reviewed'

_UNIT_STATE_ADVANCED = 'advanced'

_UNIT_STATE_ESCALATED = 'escalated'

_RUN_STATES = {'intake_received', 'planning_completed', 'units_generated', 'execution_in_progress', 'review_in_progress', 'decision_in_progress', 'commit_ready', 'merge_ready', 'post_merge_verifying', 'paused', 'rollback_in_progress', 'rolled_back', 'completed', 'failed_terminal'}

_RUN_STATE_ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {'intake_received': ('planning_completed', 'failed_terminal'), 'planning_completed': ('units_generated', 'failed_terminal'), 'units_generated': ('execution_in_progress', 'failed_terminal'), 'execution_in_progress': ('review_in_progress', 'failed_terminal'), 'review_in_progress': ('decision_in_progress', 'paused', 'failed_terminal'), 'decision_in_progress': ('commit_ready', 'merge_ready', 'rollback_in_progress', 'paused', 'failed_terminal'), 'commit_ready': ('post_merge_verifying', 'paused', 'failed_terminal'), 'merge_ready': ('post_merge_verifying', 'paused', 'failed_terminal'), 'post_merge_verifying': ('completed', 'rollback_in_progress', 'failed_terminal'), 'paused': ('decision_in_progress', 'execution_in_progress', 'failed_terminal'), 'rollback_in_progress': ('rolled_back', 'failed_terminal'), 'rolled_back': ('completed', 'failed_terminal'), 'completed': (), 'failed_terminal': ()}

_ORCHESTRATION_STATES = {'planning_completed', 'units_generated', 'execution_in_progress', 'checkpoint_evaluation_in_progress', 'run_ready_to_continue', 'paused_for_manual_review', 'rollback_evaluation_pending', 'global_stop_pending', 'completed', 'failed_terminal'}

_RUN_NEXT_ACTIONS = {'continue_run', 'pause_run', 'await_manual_review', 'evaluate_rollback', 'hold_for_global_stop', 'complete_run'}

_LOOP_STATES = {'runnable_waiting', 'runnable_blocked', 'paused', 'manual_intervention_required', 'replan_required', 'rollback_pending', 'rollback_completed_blocked', 'delivery_in_progress', 'terminal_success', 'terminal_failure', 'resumable_interrupted'}

_LOOP_NEXT_SAFE_ACTIONS = {'continue_waiting', 'pause', 'require_manual_intervention', 'require_replanning', 'advance_evaluation_step', 'execute_commit', 'execute_push', 'execute_pr_creation', 'execute_merge', 'execute_rollback', 'stop_terminal_success', 'stop_terminal_failure'}

_POLICY_STATUSES = {'allowed', 'blocked', 'manual_only', 'replan_required', 'resume_eligible', 'terminally_stopped'}

_POLICY_BLOCKER_CLASSES = {'none', 'authority_validation', 'remote_github', 'rollback_aftermath', 'missing_or_ambiguous', 'manual_gate', 'replan_required', 'terminal'}

_POLICY_EXECUTION_INTENT_ACTIONS = {'proceed_to_commit', 'proceed_to_pr', 'proceed_to_merge', 'proceed_to_rollback', 'rollback_required'}

_POLICY_NON_EXECUTION_ACTIONS = {'signal_recollect', 'escalate_to_human', 'roadmap_replan', 'inspect', 'pause'}

_POLICY_LOOP_ACTION_TO_EXECUTION_ACTION = {'execute_commit': 'proceed_to_commit', 'execute_push': 'proceed_to_pr', 'execute_pr_creation': 'proceed_to_pr', 'execute_merge': 'proceed_to_merge', 'execute_rollback': 'rollback_required'}

_POLICY_DUPLICATE_PR_REASONS = {'existing_open_pr_detected', 'blocked_existing_pr', 'existing_pr_identity_ambiguous', 'existing_pr_lookup_ambiguous'}

_ORCHESTRATION_ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {'planning_completed': ('units_generated', 'failed_terminal'), 'units_generated': ('execution_in_progress', 'failed_terminal'), 'execution_in_progress': ('checkpoint_evaluation_in_progress', 'failed_terminal'), 'checkpoint_evaluation_in_progress': ('run_ready_to_continue', 'paused_for_manual_review', 'rollback_evaluation_pending', 'global_stop_pending', 'failed_terminal'), 'run_ready_to_continue': ('checkpoint_evaluation_in_progress', 'completed', 'failed_terminal'), 'paused_for_manual_review': ('checkpoint_evaluation_in_progress', 'rollback_evaluation_pending', 'global_stop_pending', 'failed_terminal'), 'rollback_evaluation_pending': ('checkpoint_evaluation_in_progress', 'failed_terminal'), 'global_stop_pending': ('checkpoint_evaluation_in_progress', 'failed_terminal'), 'completed': (), 'failed_terminal': ()}

_PUSH_EXECUTION_TYPE = 'git_push'

_PR_EXECUTION_TYPE = 'github_pr_create'

_MERGE_EXECUTION_TYPE = 'github_pr_merge'

_ROLLBACK_EXECUTION_TYPE = 'rollback_execution'

_ROLLBACK_MODES = {'local_commit_only', 'pushed_or_pr_open', 'merged', 'unknown'}

_ROLLBACK_AFTERMATH_STATUSES = {'completed_safe', 'completed_manual_followup_required', 'blocked', 'incomplete', 'ambiguous', 'validation_failed', 'remote_followup_required'}

_ROLLBACK_VALIDATION_STATUSES = {'satisfied', 'failed', 'unavailable', 'ambiguous', 'not_applicable'}

_PROJECT_PR_SLICING_REASON_CODES = {'pr_slices_compiled', 'pr_slices_insufficient_truth'}

_PROJECT_PR_SLICING_REASON_ORDER = ('pr_slices_insufficient_truth', 'pr_slices_compiled')

_PROJECT_PR_QUEUE_REASON_CODES = {'queue_item_prepared', 'queue_item_blocked', 'queue_empty', 'queue_state_insufficient_truth', 'prompt_unavailable_for_selected_slice'}

_PROJECT_PR_QUEUE_REASON_ORDER = ('queue_state_insufficient_truth', 'queue_empty', 'prompt_unavailable_for_selected_slice', 'queue_item_blocked', 'queue_item_prepared')

_PROJECT_MERGE_BRANCH_LIFECYCLE_REASON_CODES = {'merge_branch_lifecycle_compiled', 'merge_branch_lifecycle_insufficient_truth', 'merge_branch_posture_merge_ready', 'merge_branch_posture_not_merge_ready', 'merge_branch_posture_insufficient_truth', 'merge_branch_cleanup_candidate_yes', 'merge_branch_cleanup_candidate_no', 'merge_branch_cleanup_candidate_insufficient_truth', 'merge_branch_quarantine_candidate_yes', 'merge_branch_quarantine_candidate_no', 'merge_branch_quarantine_candidate_insufficient_truth', 'merge_branch_local_main_sync_required', 'merge_branch_local_main_sync_not_required', 'merge_branch_local_main_sync_insufficient_truth'}

_PROJECT_MERGE_BRANCH_LIFECYCLE_REASON_ORDER = ('merge_branch_lifecycle_insufficient_truth', 'merge_branch_posture_insufficient_truth', 'merge_branch_cleanup_candidate_insufficient_truth', 'merge_branch_quarantine_candidate_insufficient_truth', 'merge_branch_local_main_sync_insufficient_truth', 'merge_branch_lifecycle_compiled', 'merge_branch_posture_merge_ready', 'merge_branch_posture_not_merge_ready', 'merge_branch_cleanup_candidate_yes', 'merge_branch_cleanup_candidate_no', 'merge_branch_quarantine_candidate_yes', 'merge_branch_quarantine_candidate_no', 'merge_branch_local_main_sync_required', 'merge_branch_local_main_sync_not_required')

_AUTHORITY_BLOCKER_REASONS = {'commit_automation_not_eligible', 'commit_manual_intervention_required', 'commit_readiness_not_ready', 'commit_unresolved_blockers_present', 'merge_automation_not_eligible', 'merge_manual_intervention_required', 'merge_readiness_not_ready', 'merge_unresolved_blockers_present', 'rollback_automation_not_eligible', 'rollback_manual_intervention_required', 'rollback_readiness_not_ready', 'rollback_unresolved_blockers_present', 'dry_run_mode'}

_REMOTE_GITHUB_BLOCKER_REASONS = {'git_remote_missing', 'configured_remote_missing', 'upstream_tracking_unresolved', 'upstream_ref_ambiguous', 'upstream_remote_ambiguous', 'remote_divergence_status_unavailable', 'remote_branch_diverged', 'remote_non_fast_forward_risk', 'remote_branch_lookup_unavailable', 'open_pr_lookup_unavailable', 'open_pr_lookup_api_failure', 'open_pr_lookup_not_found', 'open_pr_lookup_auth_failure', 'open_pr_lookup_unsupported_query', 'existing_open_pr_detected', 'existing_pr_identity_ambiguous', 'existing_pr_lookup_ambiguous', 'github_read_backend_unavailable', 'github_write_backend_unavailable', 'github_pr_status_summary_unavailable', 'merge_pr_status_summary_unavailable', 'merge_pr_not_open', 'mergeability_unknown', 'mergeability_not_ready', 'required_checks_unsatisfied', 'review_requirements_unsatisfied', 'branch_protection_unsatisfied', 'pr_number_missing_or_invalid'}

_REMOTE_GITHUB_MISSING_OR_AMBIGUOUS_REASON_TOKENS = ('ambiguous', 'unknown', 'unavailable', 'missing', 'unresolved', 'not_found', 'api_failure', 'auth_failure', 'unsupported_query')

_ROLLBACK_AFTERMATH_MISSING_OR_AMBIGUOUS_REASON_TOKENS = ('unknown', 'unavailable', 'missing', 'ambiguous', 'unresolved', 'incomplete', 'not_found', 'not_open')

_COMMIT_EXECUTION_TYPE = 'git_commit'

_APPROVE_COMMIT_TAG_EXECUTION_TRACKED_FILE = 'automation/orchestration/planned_execution_runner.py'

_APPROVE_COMMIT_TAG_BOUNDARY_COMMANDS_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/approve_commit_tag_commands.sh'

_APPROVE_COMMIT_TAG_BOUNDARY_METADATA_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/approve_commit_tag_boundary.json'

_APPROVAL_SKIP_GATE_STATUSES = {'skip_allowed', 'approval_required', 'not_applicable', 'insufficient_truth'}

_IMPLEMENTATION_PROMPT_STATUSES = {'available', 'insufficient_truth'}

_PROJECT_PR_QUEUE_STATUSES = {'prepared', 'blocked', 'empty', 'insufficient_truth'}

_PROJECT_EXTERNAL_BOUNDARY_STATUSES = {'available', 'insufficient_truth'}

_PROJECT_EXTERNAL_DEPENDENCY_POSTURES = {'dependency_available', 'dependency_blocked', 'manual_only', 'insufficient_truth'}

_PROJECT_EXTERNAL_BOUNDARY_POSTURES = {'clear', 'blocked', 'manual_only', 'insufficient_truth'}

_PROJECT_APPROVAL_REPLY_REQUIRED_POSTURES = {'reply_required', 'reply_not_required', 'insufficient_truth'}

_AUTONOMY_BROWSER_ORCHESTRATOR_SPEC_REF = '/home/rai/codex-local-runner/prompts/context/autonomy_browser_orchestrator_spec.md'

_MULTI_CYCLE_CONTROLLER_SURFACE_KEYS: tuple[str, ...] = ('project_browser_autonomous_multi_cycle_controller_status', 'project_browser_autonomous_multi_cycle_controller_next_action', 'project_browser_autonomous_multi_cycle_controller_enabled', 'project_browser_autonomous_multi_cycle_controller_execute_enabled', 'project_browser_autonomous_multi_cycle_controller_current_cycle_index', 'project_browser_autonomous_multi_cycle_controller_completed_cycle_count', 'project_browser_autonomous_multi_cycle_controller_max_cycles_requested', 'project_browser_autonomous_multi_cycle_controller_max_cycles_allowed', 'project_browser_autonomous_multi_cycle_controller_cycle_history_path', 'project_browser_autonomous_multi_cycle_controller_cycle_history_status', 'project_browser_autonomous_multi_cycle_controller_blocked_reason', 'project_browser_autonomous_multi_cycle_controller_stop_reason', 'project_browser_autonomous_multi_cycle_controller_can_continue', 'project_browser_autonomous_multi_cycle_controller_remaining_cycle_count', 'project_browser_autonomous_multi_cycle_controller_last_cycle_status', 'project_browser_autonomous_multi_cycle_controller_last_cycle_next_action', 'project_browser_autonomous_multi_cycle_controller_last_cycle_review_request_status', 'project_browser_autonomous_multi_cycle_controller_last_cycle_diff_capture_status', 'project_browser_autonomous_multi_cycle_controller_next_cycle_allowed', 'project_browser_autonomous_multi_cycle_controller_next_cycle_blocked_reason', 'project_browser_autonomous_multi_cycle_controller_should_invoke_codex', 'project_browser_autonomous_multi_cycle_controller_readiness_summary_path')

_APPROVE_COMMIT_TAG_ARTIFACT_RECONCILIATION_RECEIPT_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/approve_commit_tag_artifact_reconciliation_receipt.json'

_LOCAL_END_TO_END_ONE_SHOT_STEP_SELECTION_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_end_to_end_one_shot_step_selection.json'

_LOCAL_ONLY_AUTONOMOUS_LOOP_CLOSURE_STATE_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_only_autonomous_loop_closure_state.json'

_LOCAL_ONLY_AUTONOMOUS_LOOP_CLOSURE_DECISION_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_only_autonomous_loop_closure_decision.json'

_LOCAL_ONLY_AUTONOMOUS_LOOP_CLOSURE_RECEIPT_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_only_autonomous_loop_closure_receipt.json'

_LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE = 1

_LOCAL_AUTONOMOUS_CYCLE_V2_MAX_CYCLES = 2

_LOCAL_AUTONOMOUS_CYCLE_V2_STATE_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_autonomous_cycle_v2_state.json'

_LOCAL_AUTONOMOUS_CYCLE_V2_DECISION_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_autonomous_cycle_v2_decision.json'

_LOCAL_AUTONOMOUS_CYCLE_V2_RECEIPT_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_autonomous_cycle_v2_receipt.json'

_LOCAL_CODEX_ONE_SHOT_PROMPT_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_codex_one_shot_prompt.md'

_LOCAL_BOUNDED_APPROVE_COMMIT_TAG_GATE_STATE_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_bounded_approve_commit_tag_gate_state.json'

_LOCAL_BOUNDED_APPROVE_COMMIT_TAG_EXECUTION_RESULT_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_bounded_approve_commit_tag_execution_result.json'

_LOCAL_BOUNDED_APPROVE_COMMIT_TAG_EXECUTION_RECEIPT_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_bounded_approve_commit_tag_execution_receipt.json'

_LOCAL_BOUNDED_APPROVE_COMMIT_TAG_PLAN_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_bounded_approve_commit_tag_plan.json'

_LOCAL_POST_COMMIT_CYCLE_CLOSURE_STATE_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_post_commit_cycle_closure_state.json'

_LOCAL_POST_COMMIT_CYCLE_CLOSURE_DECISION_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_post_commit_cycle_closure_decision.json'

_LOCAL_POST_COMMIT_CYCLE_CLOSURE_RECEIPT_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_post_commit_cycle_closure_receipt.json'

_LOCAL_NEXT_CYCLE_REENTRY_DECISION_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_next_cycle_reentry_decision.json'

_LOCAL_AUTONOMOUS_CONTINUATION_STATE_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_autonomous_continuation_state.json'

_LOCAL_AUTONOMOUS_CONTINUATION_DECISION_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_autonomous_continuation_decision.json'

_LOCAL_AUTONOMOUS_CONTINUATION_RECEIPT_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_autonomous_continuation_receipt.json'

_LOCAL_AUTONOMOUS_NEXT_CYCLE_SELECTION_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_autonomous_next_cycle_selection.json'

_LOCAL_AUTONOMOUS_LOOP_COMPLETION_SUMMARY_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/local_autonomous_loop_completion_summary.json'

_LOCAL_BOUNDED_APPROVE_COMMIT_TAG_TAG_NAME = 'prompt340-bounded-approve-commit-tag-execution'

_TARGETED_FIX_REENTRY_EXECUTION_PROMPT_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/targeted_fix_codex_prompt.md'

_TARGETED_FIX_REENTRY_EXECUTION_RECEIPT_PATH = '/tmp/codex-local-runner-decision/one_cycle_controller/targeted_fix_reentry_execution_receipt.json'

__all__ = [name for name in globals() if name.startswith("_") and name.upper() == name]
