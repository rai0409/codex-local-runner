#!/usr/bin/env bash
set -u

RESULT_DIR="current_prompt_verify_results/prompt413"
SUMMARY_PATH="${RESULT_DIR}/summary.txt"
READY_PATH="${RESULT_DIR}/prompt413_builder_ready_path.json"
BLOCKED_PATH="${RESULT_DIR}/prompt413_builder_blocked_path.json"
SIGNATURE_PATH="${RESULT_DIR}/prompt413_builder_signature.txt"
mkdir -p "${RESULT_DIR}"
: > "${SUMMARY_PATH}"

OVERALL_RC=0
PROMPT413_BUILDER_READY_PATH_OK=false
PROMPT413_BUILDER_BLOCKED_PATH_OK=false

record_fail() {
  OVERALL_RC=1
  printf '%s\n' "$1" >> "${SUMMARY_PATH}"
}

python - <<'PY' > "${RESULT_DIR}/builder_verify.log" 2>&1
import importlib.util
import inspect
import json
import sys
from pathlib import Path

module_path = Path("automation/orchestration/planned_execution_runner.py")
spec = importlib.util.spec_from_file_location(
    "prompt413_verify_planned_execution_runner",
    module_path,
)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

builder = getattr(
    module,
    "_build_prompt413_selected_prompt_execution_adapter_boundary_state",
    None,
)
if not callable(builder):
    Path("current_prompt_verify_results/prompt413/prompt413_builder_signature.txt").write_text(
        "missing\n",
        encoding="utf-8",
    )
    raise SystemExit(2)

signature = inspect.signature(builder)
Path("current_prompt_verify_results/prompt413/prompt413_builder_signature.txt").write_text(
    f"{builder.__name__}{signature}\n",
    encoding="utf-8",
)
parameters = signature.parameters
if list(parameters) != ["run_state_payload"]:
    raise SystemExit(3)
if parameters["run_state_payload"].kind is not inspect.Parameter.KEYWORD_ONLY:
    raise SystemExit(4)

ready = builder(
    run_state_payload={
        "prompt412_physical_prompt_materialization_boundary_status": "ready",
        "prompt412_physical_prompt_materialization_boundary_ready": True,
        "prompt412_execution_adapter_packet_ready": True,
        "prompt412_execution_adapter_packet_target_prompt": "prompt413",
        "prompt412_execution_adapter_packet_mode": "selected_prompt_physical_prompt_boundary",
        "prompt412_execution_adapter_packet_prompt_id": "prompt402",
        "prompt412_next_action": "prepare_prompt413_selected_prompt_execution_adapter",
    }
)
blocked = builder(
    run_state_payload={
        "prompt412_physical_prompt_materialization_boundary_status": "blocked",
        "prompt412_physical_prompt_materialization_boundary_ready": False,
        "prompt412_execution_adapter_packet_ready": False,
        "prompt412_execution_adapter_packet_target_prompt": "prompt413",
        "prompt412_execution_adapter_packet_mode": "blocked",
        "prompt412_execution_adapter_packet_prompt_id": "",
        "prompt412_next_action": "review_prompt411_physical_prompt_materialization_plan",
    }
)

Path("current_prompt_verify_results/prompt413/prompt413_builder_ready_path.json").write_text(
    json.dumps(ready, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
Path("current_prompt_verify_results/prompt413/prompt413_builder_blocked_path.json").write_text(
    json.dumps(blocked, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

ready_expected = {
    "prompt413_selected_prompt_execution_adapter_status": "ready",
    "prompt413_selected_prompt_execution_adapter_ready": True,
    "prompt413_selected_prompt_execution_adapter_blocked_reason": "",
    "prompt413_selected_prompt_id": "prompt402",
    "prompt413_selected_prompt_prompt_path": "current_prompt_verify_results/prompt412/selected_prompt_prompt402.md",
    "prompt413_execution_mode": "planned_no_execute",
    "prompt413_execution_requested": False,
    "prompt413_execution_allowed": False,
    "prompt413_execution_attempted": False,
    "prompt413_execution_performed": False,
    "prompt413_execution_returncode": None,
    "prompt413_execution_returncode_classification": "not_run",
    "prompt413_capture_plan_ready": True,
    "prompt413_capture_written": False,
    "prompt413_review_packet_ready": True,
    "prompt413_review_packet_target_prompt": "prompt414",
    "prompt413_review_packet_mode": "execution_adapter_boundary_no_execute",
    "prompt413_review_packet_prompt_id": "prompt402",
    "prompt413_selected_prompt_execution_allowed": False,
    "prompt413_codex_invocation_allowed": False,
    "prompt413_git_mutation_allowed": False,
    "prompt413_commit_tag_allowed": False,
    "prompt413_next_action": "prepare_prompt414_execution_result_review",
}
blocked_expected = {
    "prompt413_selected_prompt_execution_adapter_status": "blocked",
    "prompt413_selected_prompt_execution_adapter_ready": False,
    "prompt413_selected_prompt_execution_adapter_blocked_reason": (
        "prompt412_execution_adapter_packet_not_ready"
    ),
    "prompt413_selected_prompt_id": "",
    "prompt413_execution_mode": "blocked_no_execute",
    "prompt413_execution_requested": False,
    "prompt413_execution_allowed": False,
    "prompt413_execution_attempted": False,
    "prompt413_execution_performed": False,
    "prompt413_execution_returncode": None,
    "prompt413_execution_returncode_classification": "not_run",
    "prompt413_capture_plan_ready": False,
    "prompt413_capture_written": False,
    "prompt413_review_packet_ready": False,
    "prompt413_review_packet_target_prompt": "prompt414",
    "prompt413_review_packet_mode": "blocked",
    "prompt413_review_packet_prompt_id": "",
    "prompt413_selected_prompt_execution_allowed": False,
    "prompt413_codex_invocation_allowed": False,
    "prompt413_git_mutation_allowed": False,
    "prompt413_commit_tag_allowed": False,
    "prompt413_next_action": "review_prompt412_execution_adapter_packet",
}

ready_ok = all(ready.get(key) == value for key, value in ready_expected.items())
blocked_ok = all(
    blocked.get(key) == value for key, value in blocked_expected.items()
)
print("PROMPT413_BUILDER_READY_PATH_OK=" + str(ready_ok).lower())
print("PROMPT413_BUILDER_BLOCKED_PATH_OK=" + str(blocked_ok).lower())
raise SystemExit(0 if ready_ok and blocked_ok else 1)
PY
case "$?" in
  0) ;;
  2) record_fail "prompt413_builder_missing" ;;
  3) record_fail "prompt413_builder_signature_not_run_state_payload_only" ;;
  4) record_fail "prompt413_builder_run_state_payload_not_keyword_only" ;;
  *) record_fail "prompt413_builder_verification_failed" ;;
esac

if [ -f "${READY_PATH}" ]; then
  PROMPT413_BUILDER_READY_PATH_OK="$(
    python - <<'PY'
import json
from pathlib import Path

ready = json.loads(Path("current_prompt_verify_results/prompt413/prompt413_builder_ready_path.json").read_text(encoding="utf-8"))
print(str(
    ready.get("prompt413_selected_prompt_execution_adapter_status") == "ready"
    and ready.get("prompt413_selected_prompt_execution_adapter_ready") is True
    and ready.get("prompt413_selected_prompt_execution_adapter_blocked_reason") == ""
    and ready.get("prompt413_selected_prompt_id") == "prompt402"
    and ready.get("prompt413_selected_prompt_prompt_path") == "current_prompt_verify_results/prompt412/selected_prompt_prompt402.md"
    and ready.get("prompt413_execution_mode") == "planned_no_execute"
    and ready.get("prompt413_execution_requested") is False
    and ready.get("prompt413_execution_allowed") is False
    and ready.get("prompt413_execution_attempted") is False
    and ready.get("prompt413_execution_performed") is False
    and ready.get("prompt413_execution_returncode") is None
    and ready.get("prompt413_execution_returncode_classification") == "not_run"
    and ready.get("prompt413_capture_plan_ready") is True
    and ready.get("prompt413_capture_written") is False
    and ready.get("prompt413_review_packet_ready") is True
    and ready.get("prompt413_review_packet_target_prompt") == "prompt414"
    and ready.get("prompt413_review_packet_mode") == "execution_adapter_boundary_no_execute"
    and ready.get("prompt413_review_packet_prompt_id") == "prompt402"
    and ready.get("prompt413_selected_prompt_execution_allowed") is False
    and ready.get("prompt413_codex_invocation_allowed") is False
    and ready.get("prompt413_git_mutation_allowed") is False
    and ready.get("prompt413_commit_tag_allowed") is False
    and ready.get("prompt413_next_action") == "prepare_prompt414_execution_result_review"
).lower())
PY
  )"
fi

if [ -f "${BLOCKED_PATH}" ]; then
  PROMPT413_BUILDER_BLOCKED_PATH_OK="$(
    python - <<'PY'
import json
from pathlib import Path

blocked = json.loads(Path("current_prompt_verify_results/prompt413/prompt413_builder_blocked_path.json").read_text(encoding="utf-8"))
print(str(
    blocked.get("prompt413_selected_prompt_execution_adapter_status") == "blocked"
    and blocked.get("prompt413_selected_prompt_execution_adapter_ready") is False
    and blocked.get("prompt413_selected_prompt_execution_adapter_blocked_reason") == "prompt412_execution_adapter_packet_not_ready"
    and blocked.get("prompt413_selected_prompt_id") == ""
    and blocked.get("prompt413_execution_mode") == "blocked_no_execute"
    and blocked.get("prompt413_execution_requested") is False
    and blocked.get("prompt413_execution_allowed") is False
    and blocked.get("prompt413_execution_attempted") is False
    and blocked.get("prompt413_execution_performed") is False
    and blocked.get("prompt413_execution_returncode") is None
    and blocked.get("prompt413_execution_returncode_classification") == "not_run"
    and blocked.get("prompt413_capture_plan_ready") is False
    and blocked.get("prompt413_capture_written") is False
    and blocked.get("prompt413_review_packet_ready") is False
    and blocked.get("prompt413_review_packet_target_prompt") == "prompt414"
    and blocked.get("prompt413_review_packet_mode") == "blocked"
    and blocked.get("prompt413_review_packet_prompt_id") == ""
    and blocked.get("prompt413_selected_prompt_execution_allowed") is False
    and blocked.get("prompt413_codex_invocation_allowed") is False
    and blocked.get("prompt413_git_mutation_allowed") is False
    and blocked.get("prompt413_commit_tag_allowed") is False
    and blocked.get("prompt413_next_action") == "review_prompt412_execution_adapter_packet"
).lower())
PY
  )"
fi

if [ "${PROMPT413_BUILDER_READY_PATH_OK}" != "true" ]; then
  record_fail "prompt413_builder_ready_path_mismatch"
fi
if [ "${PROMPT413_BUILDER_BLOCKED_PATH_OK}" != "true" ]; then
  record_fail "prompt413_builder_blocked_path_mismatch"
fi

{
  printf 'PROMPT413_BUILDER_READY_PATH_OK=%s\n' "${PROMPT413_BUILDER_READY_PATH_OK}"
  printf 'PROMPT413_BUILDER_BLOCKED_PATH_OK=%s\n' "${PROMPT413_BUILDER_BLOCKED_PATH_OK}"
  printf 'OVERALL_RC=%s\n' "${OVERALL_RC}"
  printf 'SUMMARY paths: %s %s %s %s\n' "${SUMMARY_PATH}" "${SIGNATURE_PATH}" "${READY_PATH}" "${BLOCKED_PATH}"
} | tee -a "${SUMMARY_PATH}"

if [ "${BASH_SOURCE[0]}" != "$0" ]; then
  return "${OVERALL_RC}"
fi
true
