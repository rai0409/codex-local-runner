#!/usr/bin/env bash
set -u

RESULT_DIR="current_prompt_verify_results/prompt410"
SUMMARY_PATH="${RESULT_DIR}/summary.txt"
READY_PATH="${RESULT_DIR}/prompt410_builder_ready_path.json"
BLOCKED_PATH="${RESULT_DIR}/prompt410_builder_blocked_path.json"
SIGNATURE_PATH="${RESULT_DIR}/prompt410_builder_signature.txt"
mkdir -p "${RESULT_DIR}"
: > "${SUMMARY_PATH}"

OVERALL_RC=0
PROMPT410_BUILDER_READY_PATH_OK=false
PROMPT410_BUILDER_BLOCKED_PATH_OK=false

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
spec = importlib.util.spec_from_file_location("prompt410_verify_planned_execution_runner", module_path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

builder = None
for name in (
    "_build_prompt410_strict_route_restore_state",
    "_build_prompt410_strict_route_restore_receipt_state",
    "_build_prompt410_strict_reenable_gate_restore_state",
):
    candidate = getattr(module, name, None)
    if callable(candidate):
        builder = candidate
        break
if builder is None:
    for name, candidate in inspect.getmembers(module, inspect.isfunction):
        if "prompt410" in name and "build" in name:
            builder = candidate
            break
if builder is None:
    Path("current_prompt_verify_results/prompt410/prompt410_builder_signature.txt").write_text(
        "missing\n",
        encoding="utf-8",
    )
    raise SystemExit(2)

signature = inspect.signature(builder)
Path("current_prompt_verify_results/prompt410/prompt410_builder_signature.txt").write_text(
    f"{builder.__name__}{signature}\n",
    encoding="utf-8",
)
if "run_state_payload" not in signature.parameters:
    raise SystemExit(3)

prompt409_builder = module._build_prompt409_strict_reenable_gate_restoration_packet_state
prompt409_ready = prompt409_builder(run_state_payload={
    "prompt408_strict_reenable_plan_status": "ready",
    "prompt408_strict_reenable_plan_ready": True,
    "prompt408_strict_reenable_required": True,
    "prompt408_strict_reenable_first_gate": "prompt381_approve_candidate_boundary",
    "prompt408_strict_reenable_final_gate": "prompt390_enabled_run",
    "prompt408_strict_reenable_order": [
        "prompt381_approve_candidate_boundary",
        "prompt385_next_cycle_handoff",
        "prompt389_bounded_repeated_success_path_loop",
        "prompt390_enabled_run",
    ],
})
ready = builder(run_state_payload=dict(prompt409_ready))
blocked_payload = dict(prompt409_ready)
blocked_payload["prompt409_restoration_packet_ready"] = False
blocked = builder(run_state_payload=blocked_payload)

Path("current_prompt_verify_results/prompt410/prompt410_builder_ready_path.json").write_text(
    json.dumps(ready, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
Path("current_prompt_verify_results/prompt410/prompt410_builder_blocked_path.json").write_text(
    json.dumps(blocked, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
ready_expected = {
    "prompt410_strict_route_restore_status": "restored",
    "prompt410_strict_route_restore_ready": True,
    "prompt410_strict_route_restore_blocked_reason": "",
    "prompt410_prompt381_approve_candidate_boundary_status": "ready",
    "prompt410_prompt385_next_cycle_handoff_ready": True,
    "prompt410_prompt389_repeated_cycle_execution_gate_ready": True,
    "prompt410_prompt389_repeated_cycle_execution_allowed": False,
    "prompt410_prompt390_enabled_run_ready": True,
    "prompt410_prompt390_enabled_run_allowed": False,
    "prompt410_selected_prompt_execution_allowed": False,
    "prompt410_codex_invocation_allowed": False,
    "prompt410_git_mutation_allowed": False,
    "prompt410_commit_tag_allowed": False,
    "prompt410_next_action": "prepare_prompt411_physical_prompt_materialization",
}
blocked_expected = {
    "prompt410_strict_route_restore_status": "blocked",
    "prompt410_strict_route_restore_ready": False,
    "prompt410_strict_route_restore_blocked_reason": "prompt409_restoration_packet_not_ready",
    "prompt410_next_action": "review_prompt409_restoration_packet",
}
ready_ok = all(ready.get(k) == v for k, v in ready_expected.items())
blocked_ok = all(blocked.get(k) == v for k, v in blocked_expected.items())
print("PROMPT410_BUILDER_READY_PATH_OK=" + str(ready_ok).lower())
print("PROMPT410_BUILDER_BLOCKED_PATH_OK=" + str(blocked_ok).lower())
raise SystemExit(0 if ready_ok and blocked_ok else 1)
PY
case "$?" in
  0) ;;
  2) record_fail "prompt410_builder_missing" ;;
  3) record_fail "prompt410_builder_missing_run_state_payload_parameter" ;;
  *) record_fail "prompt410_builder_verification_failed" ;;
esac

if [ -f "${READY_PATH}" ]; then
  PROMPT410_BUILDER_READY_PATH_OK="$(
    python - <<'PY'
import json
from pathlib import Path
ready = json.loads(Path("current_prompt_verify_results/prompt410/prompt410_builder_ready_path.json").read_text(encoding="utf-8"))
print(str(
    ready.get("prompt410_strict_route_restore_status") == "restored"
    and ready.get("prompt410_strict_route_restore_ready") is True
    and ready.get("prompt410_next_action") == "prepare_prompt411_physical_prompt_materialization"
).lower())
PY
  )"
fi

if [ -f "${BLOCKED_PATH}" ]; then
  PROMPT410_BUILDER_BLOCKED_PATH_OK="$(
    python - <<'PY'
import json
from pathlib import Path
blocked = json.loads(Path("current_prompt_verify_results/prompt410/prompt410_builder_blocked_path.json").read_text(encoding="utf-8"))
print(str(
    blocked.get("prompt410_strict_route_restore_status") == "blocked"
    and blocked.get("prompt410_strict_route_restore_ready") is False
    and blocked.get("prompt410_strict_route_restore_blocked_reason") == "prompt409_restoration_packet_not_ready"
    and blocked.get("prompt410_next_action") == "review_prompt409_restoration_packet"
).lower())
PY
  )"
fi

{
  printf 'PROMPT410_BUILDER_READY_PATH_OK=%s\n' "${PROMPT410_BUILDER_READY_PATH_OK}"
  printf 'PROMPT410_BUILDER_BLOCKED_PATH_OK=%s\n' "${PROMPT410_BUILDER_BLOCKED_PATH_OK}"
  printf 'OVERALL_RC=%s\n' "${OVERALL_RC}"
  printf 'SUMMARY paths: %s %s %s %s\n' "${SUMMARY_PATH}" "${SIGNATURE_PATH}" "${READY_PATH}" "${BLOCKED_PATH}"
} | tee -a "${SUMMARY_PATH}"

if [ "${BASH_SOURCE[0]}" != "$0" ]; then
  return "${OVERALL_RC}"
fi
true
