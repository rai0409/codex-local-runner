#!/usr/bin/env bash
set -u

RESULT_DIR="current_prompt_verify_results/prompt411"
SUMMARY_PATH="${RESULT_DIR}/summary.txt"
READY_PATH="${RESULT_DIR}/prompt411_builder_ready_path.json"
BLOCKED_PATH="${RESULT_DIR}/prompt411_builder_blocked_path.json"
SIGNATURE_PATH="${RESULT_DIR}/prompt411_builder_signature.txt"
mkdir -p "${RESULT_DIR}"
: > "${SUMMARY_PATH}"

OVERALL_RC=0
PROMPT411_BUILDER_READY_PATH_OK=false
PROMPT411_BUILDER_BLOCKED_PATH_OK=false

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
    "prompt411_verify_planned_execution_runner",
    module_path,
)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

builder = getattr(
    module,
    "_build_prompt411_physical_prompt_materialization_plan_state",
    None,
)
if not callable(builder):
    Path("current_prompt_verify_results/prompt411/prompt411_builder_signature.txt").write_text(
        "missing\n",
        encoding="utf-8",
    )
    raise SystemExit(2)

signature = inspect.signature(builder)
Path("current_prompt_verify_results/prompt411/prompt411_builder_signature.txt").write_text(
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
        "prompt410_strict_route_restore_status": "restored",
        "prompt410_strict_route_restore_ready": True,
        "prompt410_next_action": "prepare_prompt411_physical_prompt_materialization",
    }
)
blocked = builder(
    run_state_payload={
        "prompt410_strict_route_restore_status": "blocked",
        "prompt410_strict_route_restore_ready": False,
        "prompt410_next_action": "review_prompt409_restoration_packet",
    }
)

Path("current_prompt_verify_results/prompt411/prompt411_builder_ready_path.json").write_text(
    json.dumps(ready, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
Path("current_prompt_verify_results/prompt411/prompt411_builder_blocked_path.json").write_text(
    json.dumps(blocked, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

ready_expected = {
    "prompt411_physical_prompt_materialization_status": "ready",
    "prompt411_physical_prompt_materialization_ready": True,
    "prompt411_physical_prompt_materialization_blocked_reason": "",
    "prompt411_selected_prompt_id": "prompt402",
    "prompt411_selected_prompt_source": "prompt402_generated_prompt_surface",
    "prompt411_selected_prompt_materialization_ready": True,
    "prompt411_materialization_mode": "metadata_only",
    "prompt411_materialization_target_prompt": "prompt412",
    "prompt411_physical_prompt_path_planned": True,
    "prompt411_physical_prompt_path": "",
    "prompt411_physical_prompt_write_allowed": False,
    "prompt411_physical_prompt_written": False,
    "prompt411_selected_prompt_execution_allowed": False,
    "prompt411_codex_invocation_allowed": False,
    "prompt411_git_mutation_allowed": False,
    "prompt411_commit_tag_allowed": False,
    "prompt411_next_action": "prepare_prompt412_selected_prompt_execution_adapter",
}
blocked_expected = {
    "prompt411_physical_prompt_materialization_status": "blocked",
    "prompt411_physical_prompt_materialization_ready": False,
    "prompt411_physical_prompt_materialization_blocked_reason": (
        "prompt410_strict_route_restore_not_ready"
    ),
    "prompt411_selected_prompt_id": "",
    "prompt411_selected_prompt_source": "",
    "prompt411_selected_prompt_materialization_ready": False,
    "prompt411_physical_prompt_path_planned": False,
    "prompt411_physical_prompt_write_allowed": False,
    "prompt411_physical_prompt_written": False,
    "prompt411_next_action": "review_prompt410_strict_route_restore",
}

ready_ok = all(ready.get(key) == value for key, value in ready_expected.items())
blocked_ok = all(
    blocked.get(key) == value for key, value in blocked_expected.items()
)
print("PROMPT411_BUILDER_READY_PATH_OK=" + str(ready_ok).lower())
print("PROMPT411_BUILDER_BLOCKED_PATH_OK=" + str(blocked_ok).lower())
raise SystemExit(0 if ready_ok and blocked_ok else 1)
PY
case "$?" in
  0) ;;
  2) record_fail "prompt411_builder_missing" ;;
  3) record_fail "prompt411_builder_signature_not_run_state_payload_only" ;;
  4) record_fail "prompt411_builder_run_state_payload_not_keyword_only" ;;
  *) record_fail "prompt411_builder_verification_failed" ;;
esac

if [ -f "${READY_PATH}" ]; then
  PROMPT411_BUILDER_READY_PATH_OK="$(
    python - <<'PY'
import json
from pathlib import Path

ready = json.loads(Path("current_prompt_verify_results/prompt411/prompt411_builder_ready_path.json").read_text(encoding="utf-8"))
print(str(
    ready.get("prompt411_physical_prompt_materialization_status") == "ready"
    and ready.get("prompt411_physical_prompt_materialization_ready") is True
    and ready.get("prompt411_selected_prompt_id") == "prompt402"
    and ready.get("prompt411_physical_prompt_write_allowed") is False
    and ready.get("prompt411_next_action") == "prepare_prompt412_selected_prompt_execution_adapter"
).lower())
PY
  )"
fi

if [ -f "${BLOCKED_PATH}" ]; then
  PROMPT411_BUILDER_BLOCKED_PATH_OK="$(
    python - <<'PY'
import json
from pathlib import Path

blocked = json.loads(Path("current_prompt_verify_results/prompt411/prompt411_builder_blocked_path.json").read_text(encoding="utf-8"))
print(str(
    blocked.get("prompt411_physical_prompt_materialization_status") == "blocked"
    and blocked.get("prompt411_physical_prompt_materialization_ready") is False
    and blocked.get("prompt411_physical_prompt_materialization_blocked_reason") == "prompt410_strict_route_restore_not_ready"
    and blocked.get("prompt411_physical_prompt_path_planned") is False
    and blocked.get("prompt411_physical_prompt_write_allowed") is False
    and blocked.get("prompt411_next_action") == "review_prompt410_strict_route_restore"
).lower())
PY
  )"
fi

{
  printf 'PROMPT411_BUILDER_READY_PATH_OK=%s\n' "${PROMPT411_BUILDER_READY_PATH_OK}"
  printf 'PROMPT411_BUILDER_BLOCKED_PATH_OK=%s\n' "${PROMPT411_BUILDER_BLOCKED_PATH_OK}"
  printf 'OVERALL_RC=%s\n' "${OVERALL_RC}"
  printf 'SUMMARY paths: %s %s %s %s\n' "${SUMMARY_PATH}" "${SIGNATURE_PATH}" "${READY_PATH}" "${BLOCKED_PATH}"
} | tee -a "${SUMMARY_PATH}"

if [ "${BASH_SOURCE[0]}" != "$0" ]; then
  return "${OVERALL_RC}"
fi
true
