from __future__ import annotations
import subprocess

from automation.orchestration.approval_email_delivery import (
    build_approval_email_delivery_contract_surface,
)
from automation.orchestration.approval_response_ingest import (
    build_approval_response_contract_surface,
    build_approved_restart_contract_surface,
)
from automation.orchestration.approval_safety import build_approval_safety_contract_surface
from automation.orchestration.failure_bucketing_hardening import (
    build_failure_bucketing_hardening_contract_surface,
)
from automation.orchestration.fleet_safety_control import (
    build_fleet_safety_control_contract_surface,
)
from automation.orchestration.loop_hardening_contract import (
    build_loop_hardening_contract_surface,
)

from automation.orchestration.planned_runner.runner import PlannedExecutionRunner
from automation.orchestration.planned_runner.transports import DryRunCodexExecutionTransport


def _augment_run_state_with_closed_loop(*args, **kwargs):
    from automation.orchestration.planned_runner.state.run_state import (
        _augment_run_state_with_closed_loop as _closed_loop_impl,
    )

    return _closed_loop_impl(*args, **kwargs)



def _augment_run_state_with_lifecycle_terminal_contract(*args, **kwargs):
    from automation.orchestration.planned_runner.state.lifecycle import (
        _augment_run_state_with_lifecycle_terminal_contract as _impl,
    )

    return _impl(*args, **kwargs)


def _augment_run_state_with_operator_explainability(*args, **kwargs):
    from automation.orchestration.planned_runner.state.operator_explainability import (
        _augment_run_state_with_operator_explainability as _impl,
    )

    return _impl(*args, **kwargs)


def _augment_run_state_with_policy_overlay(*args, **kwargs):
    from automation.orchestration.planned_runner.state.policy_overlay import (
        _augment_run_state_with_policy_overlay as _impl,
    )

    return _impl(*args, **kwargs)


def _augment_run_state_with_rollback_aftermath(*args, **kwargs):
    from automation.orchestration.planned_runner.state.run_state import (
        _augment_run_state_with_rollback_aftermath as _impl,
    )

    return _impl(*args, **kwargs)


def _execute_bounded_merge(*args, **kwargs):
    from automation.orchestration.planned_runner.git_ops.pr_merge import _execute_bounded_merge as _impl

    return _impl(*args, **kwargs)


def _execute_bounded_pr_creation(*args, **kwargs):
    from automation.orchestration.planned_runner.git_ops.pr_merge import _execute_bounded_pr_creation as _impl

    return _impl(*args, **kwargs)


def _execute_bounded_push(*args, **kwargs):
    from automation.orchestration.planned_runner.git_ops.pr_merge import _execute_bounded_push as _impl

    return _impl(*args, **kwargs)


def _execute_bounded_rollback(*args, **kwargs):
    from automation.orchestration.planned_runner.git_ops.rollback import _execute_bounded_rollback as _impl

    return _impl(*args, **kwargs)


def _build_bounded_self_healing_state(*args, **kwargs):
    from automation.orchestration.planned_runner.summaries.approved_restart_payload import _build_bounded_self_healing_state as _impl

    return _impl(*args, **kwargs)


def _build_project_external_boundary_state(*args, **kwargs):
    from automation.orchestration.planned_runner.summaries.approved_restart_payload import _build_project_external_boundary_state as _impl

    return _impl(*args, **kwargs)


def _build_project_failure_memory_state(*args, **kwargs):
    from automation.orchestration.planned_runner.summaries.approved_restart_payload import _build_project_failure_memory_state as _impl

    return _impl(*args, **kwargs)


def _build_project_approval_notification_state(*args, **kwargs):
    from automation.orchestration.planned_runner.summaries.approved_restart_payload import _build_project_approval_notification_state as _impl

    return _impl(*args, **kwargs)


def _build_project_browser_task_state(*args, **kwargs):
    from automation.orchestration.planned_runner.project_browser.local_loop_state import _build_project_browser_task_state as _impl

    return _impl(*args, **kwargs)


def _build_project_human_escalation_state(*args, **kwargs):
    from automation.orchestration.planned_runner.summaries.approved_restart_payload import _build_project_human_escalation_state as _impl

    return _impl(*args, **kwargs)


def _build_project_multi_objective_state(*args, **kwargs):
    from automation.orchestration.planned_runner.summaries.approved_restart_payload import _build_project_multi_objective_state as _impl

    return _impl(*args, **kwargs)


def _build_long_running_stability_state(*args, **kwargs):
    from automation.orchestration.planned_runner.summaries.approved_restart_payload import _build_long_running_stability_state as _impl

    return _impl(*args, **kwargs)


def _build_objective_done_compiler_state(*args, **kwargs):
    from automation.orchestration.planned_runner.summaries.approved_restart_payload import _build_objective_done_compiler_state as _impl

    return _impl(*args, **kwargs)


def _build_project_browser_autonomous_post_apply_validation_state(*args, **kwargs):
    from automation.orchestration.planned_runner.project_browser.local_loop_state import _build_project_browser_autonomous_post_apply_validation_state as _impl

    return _impl(*args, **kwargs)


def _build_project_browser_autonomous_fix_prompt_readiness_state(*args, **kwargs):
    from automation.orchestration.planned_runner.project_browser.prompt_payload import _build_project_browser_autonomous_fix_prompt_readiness_state as _impl

    return _impl(*args, **kwargs)


def _build_project_autonomy_budget_state(*args, **kwargs):
    from automation.orchestration.planned_runner.summaries.approved_restart_payload import _build_project_autonomy_budget_state as _impl

    return _impl(*args, **kwargs)


def _build_project_merge_branch_lifecycle_state(*args, **kwargs):
    from automation.orchestration.planned_runner.state.lifecycle import _build_project_merge_branch_lifecycle_state as _impl

    return _impl(*args, **kwargs)


def _build_project_quality_gate_state(*args, **kwargs):
    from automation.orchestration.planned_runner.summaries.approved_restart_payload import _build_project_quality_gate_state as _impl

    return _impl(*args, **kwargs)


def _build_review_assimilation_state(*args, **kwargs):
    from automation.orchestration.planned_runner.summaries.approved_restart_payload import _build_review_assimilation_state as _impl

    return _impl(*args, **kwargs)


def _with_rollback_aftermath_surface(*args, **kwargs):
    from automation.orchestration.planned_runner.git_ops.rollback import _with_rollback_aftermath_surface as _impl

    return _impl(*args, **kwargs)

__all__ = [
    "DryRunCodexExecutionTransport",
    "PlannedExecutionRunner",
    "_augment_run_state_with_closed_loop",
    "_augment_run_state_with_lifecycle_terminal_contract",
    "_augment_run_state_with_operator_explainability",
    "_augment_run_state_with_policy_overlay",
    "_augment_run_state_with_rollback_aftermath",
    "_execute_bounded_merge",
    "_execute_bounded_pr_creation",
    "_execute_bounded_push",
    "_execute_bounded_rollback",
    "_build_bounded_self_healing_state",
    "_build_project_external_boundary_state",
    "_build_project_failure_memory_state",
    "_build_project_approval_notification_state",
    "_build_project_browser_task_state",
    "_build_project_human_escalation_state",
    "_build_project_multi_objective_state",
    "_build_long_running_stability_state",
    "_build_objective_done_compiler_state",
    "_build_project_browser_autonomous_post_apply_validation_state",
    "_build_project_browser_autonomous_fix_prompt_readiness_state",
    "_build_project_autonomy_budget_state",
    "_build_project_merge_branch_lifecycle_state",
    "_build_project_quality_gate_state",
    "_build_review_assimilation_state",
    "_with_rollback_aftermath_surface",
    "build_approval_email_delivery_contract_surface",
    "build_approval_response_contract_surface",
    "build_approved_restart_contract_surface",
    "build_approval_safety_contract_surface",
    "build_failure_bucketing_hardening_contract_surface",
    "build_fleet_safety_control_contract_surface",
    "build_loop_hardening_contract_surface",
    "subprocess",
]
