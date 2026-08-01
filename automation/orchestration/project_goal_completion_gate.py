"""Pure, deterministic domain logic for project-goal completion."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

PROJECT_GOAL_CONTRACT_SCHEMA_VERSION = "1"
CAPABILITY_STATUSES = ("satisfied", "unsatisfied", "unknown", "blocked")
ACCEPTANCE_STATUSES = ("passed", "failed", "unknown", "blocked")
WORKTREE_STATES = ("known_clean", "known_dirty", "unknown")
GATE_ORDER = (
    "required_capabilities", "critical_gaps", "active_tasks",
    "blocked_critical_tasks", "acceptance_verification", "clean_worktree",
)
_CONTRACT_FIELDS = frozenset(("schema_version", "project_id", "goal", "repository_path", "required_capabilities", "completion_gates", "constraints"))
_CAPABILITY_FIELDS = frozenset(("capability_id", "description", "required"))
_GATE_FIELDS = (
    "require_all_required_capabilities", "require_no_critical_gaps", "require_no_active_tasks",
    "require_no_blocked_critical_tasks", "require_acceptance_verification", "require_known_clean_worktree",
)
_CONSTRAINT_FIELDS = frozenset(("automatic_commit", "remote_operations", "max_files_per_task"))
_OBSERVATION_FIELDS = frozenset(("schema_version", "capabilities", "critical_gap_count", "active_task_count", "blocked_critical_task_count", "acceptance_verification", "acceptance_blocked", "worktree_state", "blocking_reasons"))
_OBSERVATION_CAPABILITY_FIELDS = frozenset(("status", "evidence"))
_GATE_SWITCHES = dict(zip(GATE_ORDER, _GATE_FIELDS))


class ProjectGoalContractValidationError(ValueError):
    """Validation failure with a stable machine-readable reason code."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


@dataclass(frozen=True)
class RequiredCapability:
    capability_id: str
    description: str
    required: bool


@dataclass(frozen=True)
class CompletionGates:
    require_all_required_capabilities: bool
    require_no_critical_gaps: bool
    require_no_active_tasks: bool
    require_no_blocked_critical_tasks: bool
    require_acceptance_verification: bool
    require_known_clean_worktree: bool


@dataclass(frozen=True)
class ProjectConstraints:
    automatic_commit: bool
    remote_operations: bool
    max_files_per_task: int


@dataclass(frozen=True)
class ProjectGoalContract:
    schema_version: str
    project_id: str
    goal: str
    repository_path: str
    required_capabilities: tuple[RequiredCapability, ...]
    completion_gates: CompletionGates
    constraints: ProjectConstraints


@dataclass(frozen=True)
class CapabilityObservation:
    status: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ObservedProjectState:
    schema_version: str
    capabilities: Mapping[str, CapabilityObservation]
    critical_gap_count: int
    active_task_count: int
    blocked_critical_task_count: int
    acceptance_verification: str
    acceptance_blocked: bool
    worktree_state: str
    blocking_reasons: tuple[str, ...]


@dataclass(frozen=True)
class NextRequiredAction:
    action_id: str
    target_id: str
    reason_code: str
    reason: str


@dataclass(frozen=True)
class ProjectCompletionDecision:
    schema_version: str
    project_id: str
    status: str
    status_reason_code: str
    completion_ratio: float
    satisfied_required_capabilities: tuple[str, ...]
    unsatisfied_required_capabilities: tuple[str, ...]
    unknown_required_capabilities: tuple[str, ...]
    blocked_required_capabilities: tuple[str, ...]
    passed_gates: tuple[str, ...]
    failed_gates: tuple[str, ...]
    unknown_gates: tuple[str, ...]
    blocked_gates: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    next_required_action: NextRequiredAction

    @property
    def completion_confidence(self) -> float:
        """Backward-compatible alias for the previous public field."""
        return self.completion_ratio


def _error(reason_code: str, message: str) -> ProjectGoalContractValidationError:
    return ProjectGoalContractValidationError(reason_code, message)


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _error(f"{path}.invalid_type", "must be an object")
    return value


def _strict_fields(value: Mapping[str, Any], allowed: frozenset[str] | tuple[str, ...], path: str) -> None:
    unknown = sorted((key for key in value if key not in allowed), key=repr)
    if unknown:
        raise _error(f"{path}.{unknown[0]}.unknown_field", "unknown field")


def _required(value: Mapping[str, Any], key: str, path: str) -> Any:
    if key not in value:
        raise _error(f"{path}.{key}.required", "is required")
    return value[key]


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _error(f"{path}.invalid_type", "must be a non-empty string")
    return value


def _bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise _error(f"{path}.invalid_type", "must be a boolean")
    return value


def _count(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise _error(f"{path}.invalid_type", "must be a non-negative integer")
    return value


def _load_contract(payload: Mapping[str, Any]) -> ProjectGoalContract:
    raw = _mapping(payload, "contract")
    _strict_fields(raw, _CONTRACT_FIELDS, "contract")
    version = _text(_required(raw, "schema_version", "contract"), "contract.schema_version")
    if version != PROJECT_GOAL_CONTRACT_SCHEMA_VERSION:
        raise _error("contract.schema_version.unsupported", "must be '1'")
    capabilities: list[RequiredCapability] = []
    seen: set[str] = set()
    raw_capabilities = _required(raw, "required_capabilities", "contract")
    if not isinstance(raw_capabilities, list):
        raise _error("contract.required_capabilities.invalid_type", "must be a list")
    for index, item in enumerate(raw_capabilities):
        path = f"contract.required_capabilities[{index}]"
        item = _mapping(item, path)
        _strict_fields(item, _CAPABILITY_FIELDS, path)
        capability_id = _text(_required(item, "capability_id", path), f"{path}.capability_id")
        if capability_id in seen:
            raise _error(f"{path}.capability_id.duplicate", "duplicate capability ID")
        seen.add(capability_id)
        capabilities.append(RequiredCapability(capability_id, _text(_required(item, "description", path), f"{path}.description"), _bool(_required(item, "required", path), f"{path}.required")))
    gates_raw = _mapping(_required(raw, "completion_gates", "contract"), "contract.completion_gates")
    _strict_fields(gates_raw, _GATE_FIELDS, "contract.completion_gates")
    gates = CompletionGates(**{field: _bool(_required(gates_raw, field, "contract.completion_gates"), f"contract.completion_gates.{field}") for field in _GATE_FIELDS})
    constraints_raw = _mapping(_required(raw, "constraints", "contract"), "contract.constraints")
    _strict_fields(constraints_raw, _CONSTRAINT_FIELDS, "contract.constraints")
    max_files = _required(constraints_raw, "max_files_per_task", "contract.constraints")
    if isinstance(max_files, bool) or not isinstance(max_files, int) or max_files < 1:
        raise _error("contract.constraints.max_files_per_task.invalid_type", "must be a positive integer")
    return ProjectGoalContract(version, _text(_required(raw, "project_id", "contract"), "contract.project_id"), _text(_required(raw, "goal", "contract"), "contract.goal"), _text(_required(raw, "repository_path", "contract"), "contract.repository_path"), tuple(capabilities), gates, ProjectConstraints(_bool(_required(constraints_raw, "automatic_commit", "contract.constraints"), "contract.constraints.automatic_commit"), _bool(_required(constraints_raw, "remote_operations", "contract.constraints"), "contract.constraints.remote_operations"), max_files))


def validate_project_goal_contract(contract: Mapping[str, Any] | ProjectGoalContract) -> ProjectGoalContract:
    """Validate a contract without changing its input mapping."""
    if isinstance(contract, ProjectGoalContract):
        return contract
    return _load_contract(contract)


def load_project_goal_contract(payload: Mapping[str, Any]) -> ProjectGoalContract:
    """Backward-compatible name for ``validate_project_goal_contract``."""
    return validate_project_goal_contract(payload)


def _load_observation(contract: ProjectGoalContract, payload: Mapping[str, Any]) -> ObservedProjectState:
    raw = _mapping(payload, "observation")
    _strict_fields(raw, _OBSERVATION_FIELDS, "observation")
    version = _text(_required(raw, "schema_version", "observation"), "observation.schema_version")
    if version != PROJECT_GOAL_CONTRACT_SCHEMA_VERSION:
        raise _error("observation.schema_version.unsupported", "must be '1'")
    raw_capabilities = _mapping(_required(raw, "capabilities", "observation"), "observation.capabilities")
    contract_ids = {item.capability_id for item in contract.required_capabilities}
    capabilities: dict[str, CapabilityObservation] = {}
    for capability_id, item in raw_capabilities.items():
        if not isinstance(capability_id, str) or not capability_id.strip():
            raise _error("observation.capabilities.invalid_key", "keys must be non-empty strings")
        path = f"observation.capabilities.{capability_id}"
        if capability_id not in contract_ids:
            raise _error(f"{path}.unknown_capability", "capability is not in the contract")
        item = _mapping(item, path)
        _strict_fields(item, _OBSERVATION_CAPABILITY_FIELDS, path)
        status = _text(_required(item, "status", path), f"{path}.status")
        if status not in CAPABILITY_STATUSES:
            raise _error(f"{path}.status.invalid_value", "unsupported capability status")
        evidence_raw = _required(item, "evidence", path)
        if not isinstance(evidence_raw, list):
            raise _error(f"{path}.evidence.invalid_type", "must be a list of non-empty strings")
        evidence = tuple(_text(entry, f"{path}.evidence[{index}]") for index, entry in enumerate(evidence_raw))
        if status == "satisfied" and not evidence:
            raise _error(f"{path}.evidence.required", "satisfied capability requires evidence")
        capabilities[capability_id] = CapabilityObservation(status, evidence)
    acceptance = _text(_required(raw, "acceptance_verification", "observation"), "observation.acceptance_verification")
    if acceptance not in ACCEPTANCE_STATUSES:
        raise _error("observation.acceptance_verification.invalid_value", "unsupported acceptance status")
    acceptance_blocked = _bool(_required(raw, "acceptance_blocked", "observation"), "observation.acceptance_blocked")
    if acceptance_blocked != (acceptance == "blocked"):
        raise _error("observation.acceptance_blocked.inconsistent", "must be true exactly when acceptance_verification is blocked")
    worktree = _text(_required(raw, "worktree_state", "observation"), "observation.worktree_state")
    if worktree not in WORKTREE_STATES:
        raise _error("observation.worktree_state.invalid_value", "unsupported worktree state")
    reasons_raw = _required(raw, "blocking_reasons", "observation")
    if not isinstance(reasons_raw, list):
        raise _error("observation.blocking_reasons.invalid_type", "must be a list of non-empty strings")
    reasons = tuple(_text(value, f"observation.blocking_reasons[{index}]") for index, value in enumerate(reasons_raw))
    return ObservedProjectState(version, capabilities, _count(_required(raw, "critical_gap_count", "observation"), "observation.critical_gap_count"), _count(_required(raw, "active_task_count", "observation"), "observation.active_task_count"), _count(_required(raw, "blocked_critical_task_count", "observation"), "observation.blocked_critical_task_count"), acceptance, acceptance_blocked, worktree, reasons)


def validate_project_observation(contract: Mapping[str, Any] | ProjectGoalContract, observation: Mapping[str, Any] | ObservedProjectState) -> ObservedProjectState:
    """Validate an observation against its contract without mutating either input."""
    validated_contract = validate_project_goal_contract(contract)
    if isinstance(observation, ObservedProjectState):
        return observation
    return _load_observation(validated_contract, observation)


def load_observed_project_state(payload: Mapping[str, Any]) -> ObservedProjectState:
    """Compatibility loader; validates structural observation rules without a contract."""
    ids = tuple(RequiredCapability(key, key, False) for key in _mapping(_required(_mapping(payload, "observation"), "capabilities", "observation"), "observation.capabilities"))
    return _load_observation(ProjectGoalContract("1", "compatibility", "compatibility", "compatibility", ids, CompletionGates(False, False, False, False, False, False), ProjectConstraints(False, False, 1)), payload)


def project_goal_contract_to_mapping(contract: ProjectGoalContract) -> dict[str, Any]:
    return {"schema_version": contract.schema_version, "project_id": contract.project_id, "goal": contract.goal, "repository_path": contract.repository_path, "required_capabilities": [{"capability_id": item.capability_id, "description": item.description, "required": item.required} for item in contract.required_capabilities], "completion_gates": {field: getattr(contract.completion_gates, field) for field in _GATE_FIELDS}, "constraints": {"automatic_commit": contract.constraints.automatic_commit, "remote_operations": contract.constraints.remote_operations, "max_files_per_task": contract.constraints.max_files_per_task}}


def observed_project_state_to_mapping(state: ObservedProjectState) -> dict[str, Any]:
    return {"schema_version": state.schema_version, "capabilities": {key: {"status": value.status, "evidence": list(value.evidence)} for key, value in sorted(state.capabilities.items())}, "critical_gap_count": state.critical_gap_count, "active_task_count": state.active_task_count, "blocked_critical_task_count": state.blocked_critical_task_count, "acceptance_verification": state.acceptance_verification, "acceptance_blocked": state.acceptance_blocked, "worktree_state": state.worktree_state, "blocking_reasons": list(state.blocking_reasons)}


def _action(action_id: str, target_id: str, reason_code: str, reason: str) -> NextRequiredAction:
    return NextRequiredAction(action_id, target_id, reason_code, reason)


def evaluate_project_completion(contract: Mapping[str, Any] | ProjectGoalContract, observation: Mapping[str, Any] | ObservedProjectState) -> ProjectCompletionDecision:
    """Return the deterministic completion decision after strict validation."""
    contract = validate_project_goal_contract(contract)
    observation = validate_project_observation(contract, observation)
    groups = {status: [] for status in CAPABILITY_STATUSES}
    for capability in sorted((item for item in contract.required_capabilities if item.required), key=lambda item: item.capability_id):
        groups[observation.capabilities.get(capability.capability_id, CapabilityObservation("unknown", ())).status].append(capability.capability_id)
    gate_status = {
        "required_capabilities": "blocked" if groups["blocked"] else "unknown" if groups["unknown"] else "failed" if groups["unsatisfied"] else "passed",
        "critical_gaps": "passed" if observation.critical_gap_count == 0 else "failed",
        "active_tasks": "passed" if observation.active_task_count == 0 else "failed",
        "blocked_critical_tasks": "passed" if observation.blocked_critical_task_count == 0 else "blocked",
        "acceptance_verification": observation.acceptance_verification,
        "clean_worktree": {"known_clean": "passed", "known_dirty": "failed", "unknown": "unknown"}[observation.worktree_state],
    }
    enabled = tuple(gate for gate in GATE_ORDER if getattr(contract.completion_gates, _GATE_SWITCHES[gate]))
    selected = {status: tuple(gate for gate in enabled if gate_status[gate] == status) for status in ("passed", "failed", "unknown", "blocked")}
    reasons = tuple(sorted(set(observation.blocking_reasons)))
    ratio = round(len(selected["passed"]) / len(enabled), 6) if enabled else 0.0
    if reasons:
        status, reason_code = "blocked", "explicit_blocking_reasons"
    elif selected["blocked"]:
        status, reason_code = "blocked", "blocked_gate"
    elif selected["unknown"]:
        status, reason_code = "insufficient_truth", "unknown_gate"
    elif selected["failed"]:
        status, reason_code = "incomplete", "failed_gate"
    elif enabled:
        status, reason_code = "completed", "all_enabled_gates_passed"
    else:
        status, reason_code = "insufficient_truth", "no_completion_gates_enabled"
    action = _next_action(status, reasons, groups, observation, enabled)
    return ProjectCompletionDecision("1", contract.project_id, status, reason_code, ratio, tuple(groups["satisfied"]), tuple(groups["unsatisfied"]), tuple(groups["unknown"]), tuple(groups["blocked"]), selected["passed"], selected["failed"], selected["unknown"], selected["blocked"], reasons, action)


def _next_action(status: str, reasons: tuple[str, ...], groups: Mapping[str, list[str]], observation: ObservedProjectState, enabled: tuple[str, ...]) -> NextRequiredAction:
    if not enabled:
        return _action("configure_completion_gates", "completion_gates", "completion_gates.not_enabled", "Enable at least one completion gate before evaluating project completion")
    if status == "completed":
        return _action("no_action_required", "project", "completed", "all enabled completion gates passed")
    if reasons:
        return _action("resolve_explicit_blocking_reason", reasons[0], "explicit_blocking_reason", "an explicit blocking reason remains")
    if "required_capabilities" in enabled and groups["blocked"]:
        return _action("unblock_required_capability", groups["blocked"][0], "required_capability_blocked", "required capability is blocked")
    if "blocked_critical_tasks" in enabled and observation.blocked_critical_task_count:
        return _action("resolve_blocked_critical_task", "blocked_critical_tasks", "blocked_critical_task", "blocked critical tasks remain")
    if "required_capabilities" in enabled and groups["unknown"]:
        return _action("gather_required_capability_evidence", groups["unknown"][0], "required_capability_unknown", "required capability evidence is missing")
    if "required_capabilities" in enabled and groups["unsatisfied"]:
        return _action("satisfy_required_capability", groups["unsatisfied"][0], "required_capability_unsatisfied", "required capability is unsatisfied")
    if "critical_gaps" in enabled and observation.critical_gap_count:
        return _action("resolve_critical_gap", "critical_gaps", "critical_gaps_present", "critical gaps remain")
    if "active_tasks" in enabled and observation.active_task_count:
        return _action("finish_active_task", "active_tasks", "active_tasks_present", "active tasks remain")
    if "acceptance_verification" in enabled and observation.acceptance_verification != "passed":
        return _action("run_acceptance_verification", "acceptance_verification", f"acceptance_verification_{observation.acceptance_verification}", "acceptance verification has not passed")
    if "clean_worktree" in enabled and observation.worktree_state != "known_clean":
        return _action("clean_worktree", "worktree", f"worktree_{observation.worktree_state}", "worktree is not known clean")
    return _action("no_action_required", "project", "no_enabled_action", "no enabled action is applicable")


def decision_to_mapping(decision: ProjectCompletionDecision) -> dict[str, Any]:
    return {"schema_version": decision.schema_version, "project_id": decision.project_id, "status": decision.status, "status_reason_code": decision.status_reason_code, "completion_ratio": decision.completion_ratio, "completion_confidence": decision.completion_confidence, "satisfied_required_capabilities": list(decision.satisfied_required_capabilities), "unsatisfied_required_capabilities": list(decision.unsatisfied_required_capabilities), "unknown_required_capabilities": list(decision.unknown_required_capabilities), "blocked_required_capabilities": list(decision.blocked_required_capabilities), "passed_gates": list(decision.passed_gates), "failed_gates": list(decision.failed_gates), "unknown_gates": list(decision.unknown_gates), "blocked_gates": list(decision.blocked_gates), "blocking_reasons": list(decision.blocking_reasons), "next_required_action": {"action_id": decision.next_required_action.action_id, "target_id": decision.next_required_action.target_id, "reason_code": decision.next_required_action.reason_code, "reason": decision.next_required_action.reason}}


def serialize_project_goal_contract(contract: ProjectGoalContract) -> str:
    return json.dumps(project_goal_contract_to_mapping(contract), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def serialize_observed_project_state(state: ObservedProjectState) -> str:
    return json.dumps(observed_project_state_to_mapping(state), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def serialize_completion_decision(decision: ProjectCompletionDecision) -> str:
    return json.dumps(decision_to_mapping(decision), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


__all__ = ["ProjectGoalContractValidationError", "ProjectGoalContract", "ObservedProjectState", "ProjectCompletionDecision", "validate_project_goal_contract", "validate_project_observation", "evaluate_project_completion", "load_project_goal_contract", "load_observed_project_state", "project_goal_contract_to_mapping", "observed_project_state_to_mapping", "decision_to_mapping", "serialize_project_goal_contract", "serialize_observed_project_state", "serialize_completion_decision"]
