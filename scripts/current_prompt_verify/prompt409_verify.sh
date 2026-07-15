#!/usr/bin/env bash
set -u

RESULT_DIR="current_prompt_verify_results/prompt409"
SUMMARY_PATH="${RESULT_DIR}/summary.txt"
FIELDS_PATH="${RESULT_DIR}/prompt409_fields.json"
READY_PATH="${RESULT_DIR}/prompt409_builder_ready_path.json"
BLOCKED_PATH="${RESULT_DIR}/prompt409_builder_blocked_path.json"
PY_COMPILE_LOG="${RESULT_DIR}/py_compile.log"
CHANGED_FILES_LOG="${RESULT_DIR}/changed_files.log"
mkdir -p "${RESULT_DIR}"
: > "${SUMMARY_PATH}"

OVERALL_RC=0
PROMPT409_FIELDS_FOUND=false
PROMPT409_STATUS=
PROMPT409_READY=
PROMPT409_BLOCKED_REASON=
PROMPT409_RESTORATION_PACKET_READY=
PROMPT409_NEXT_ACTION=
PROMPT409_BUILDER_READY_PATH_OK=false

record_fail() {
  OVERALL_RC=1
  printf '%s\n' "$1" >> "${SUMMARY_PATH}"
}

if git rev-parse --show-toplevel >/dev/null 2>&1; then
  git status --porcelain --untracked-files=all > "${CHANGED_FILES_LOG}"
  while IFS= read -r line; do
    path="${line:3}"
    case "${path}" in
      automation/orchestration/planned_execution_runner.py|scripts/current_prompt_verify/*.sh|.gitignore) ;;
      "") ;;
      *) record_fail "unexpected_changed_file=${path}" ;;
    esac
  done < "${CHANGED_FILES_LOG}"
else
  record_fail "git_status_unavailable"
fi

if ! python -m py_compile automation/orchestration/planned_execution_runner.py scripts/run_planned_execution.py > "${PY_COMPILE_LOG}" 2>&1; then
  record_fail "py_compile_failed"
fi

python - <<'PY' > "${RESULT_DIR}/builder_verify.log" 2>&1
import importlib.util
import json
import sys
from pathlib import Path

module_path = Path("automation/orchestration/planned_execution_runner.py")
spec = importlib.util.spec_from_file_location("prompt409_verify_planned_execution_runner", module_path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
builder = module._build_prompt409_strict_reenable_gate_restoration_packet_state
ready_run_state = {
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
}
ready = builder(run_state_payload=ready_run_state)
blocked = builder(run_state_payload={})
Path("current_prompt_verify_results/prompt409/prompt409_builder_ready_path.json").write_text(
    json.dumps(ready, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
Path("current_prompt_verify_results/prompt409/prompt409_builder_blocked_path.json").write_text(
    json.dumps(blocked, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
expected = {
    "prompt409_strict_reenable_gate_status": "ready",
    "prompt409_strict_reenable_gate_ready": True,
    "prompt409_strict_reenable_gate_blocked_reason": "",
    "prompt409_restoration_packet_ready": True,
    "prompt409_next_action": "restore_strict_route_in_prompt410",
}
ok = all(ready.get(k) == v for k, v in expected.items())
ok = ok and blocked.get("prompt409_strict_reenable_gate_blocked_reason") == "prompt408_strict_reenable_plan_not_ready"
print("PROMPT409_BUILDER_READY_PATH_OK=" + str(ok).lower())
raise SystemExit(0 if ok else 1)
PY
if [ "$?" -ne 0 ]; then
  record_fail "prompt409_builder_ready_path_failed"
fi

python - <<'PY' > "${FIELDS_PATH}.tmp" 2> "${RESULT_DIR}/field_extract.log"
import json
from pathlib import Path

keys = [
    "prompt409_strict_reenable_gate_status",
    "prompt409_strict_reenable_gate_ready",
    "prompt409_strict_reenable_gate_blocked_reason",
    "prompt409_restoration_packet_ready",
    "prompt409_next_action",
]
roots = [Path("artifacts"), Path("current_prompt_verify_results/prompt409")]
matches = []
for root in roots:
    if not root.exists():
        continue
    for path in sorted(root.rglob("*.json")):
        if "RUNLOG" in path.name.upper() or path.stat().st_size > 5_000_000:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and any(k in data for k in keys):
            matches.append((str(path), {k: data.get(k) for k in keys}))
preferred = None
for item in matches:
    fields = item[1]
    if fields.get("prompt409_strict_reenable_gate_status") == "ready" and fields.get("prompt409_restoration_packet_ready") is True:
        preferred = item
        break
if preferred is None and matches:
    preferred = matches[0]
source, found = preferred if preferred else ("", {})
print(json.dumps({"source": source, "fields": found}, indent=2, sort_keys=True))
raise SystemExit(0 if found else 1)
PY
if [ "$?" -eq 0 ]; then
  mv "${FIELDS_PATH}.tmp" "${FIELDS_PATH}"
  PROMPT409_FIELDS_FOUND=true
else
  rm -f "${FIELDS_PATH}.tmp"
  record_fail "prompt409_fields_not_found"
fi

if [ -f "${FIELDS_PATH}" ]; then
  eval "$(
    python - <<'PY'
import json
from pathlib import Path
data = json.loads(Path("current_prompt_verify_results/prompt409/prompt409_fields.json").read_text(encoding="utf-8"))
fields = data.get("fields", {})
mapping = {
    "PROMPT409_STATUS": "prompt409_strict_reenable_gate_status",
    "PROMPT409_READY": "prompt409_strict_reenable_gate_ready",
    "PROMPT409_BLOCKED_REASON": "prompt409_strict_reenable_gate_blocked_reason",
    "PROMPT409_RESTORATION_PACKET_READY": "prompt409_restoration_packet_ready",
    "PROMPT409_NEXT_ACTION": "prompt409_next_action",
}
for shell_name, key in mapping.items():
    value = fields.get(key, "")
    if isinstance(value, bool):
        value = str(value).lower()
    print(f"{shell_name}={json.dumps(str(value))}")
PY
  )"
fi

if [ -f "${READY_PATH}" ]; then
  PROMPT409_BUILDER_READY_PATH_OK="$(
    python - <<'PY'
import json
from pathlib import Path
ready = json.loads(Path("current_prompt_verify_results/prompt409/prompt409_builder_ready_path.json").read_text(encoding="utf-8"))
print(str(
    ready.get("prompt409_strict_reenable_gate_status") == "ready"
    and ready.get("prompt409_strict_reenable_gate_ready") is True
    and ready.get("prompt409_restoration_packet_ready") is True
    and ready.get("prompt409_next_action") == "restore_strict_route_in_prompt410"
).lower())
PY
  )"
fi

{
  printf 'PROMPT409_FIELDS_FOUND=%s\n' "${PROMPT409_FIELDS_FOUND}"
  printf 'PROMPT409_STATUS=%s\n' "${PROMPT409_STATUS}"
  printf 'PROMPT409_READY=%s\n' "${PROMPT409_READY}"
  printf 'PROMPT409_BLOCKED_REASON=%s\n' "${PROMPT409_BLOCKED_REASON}"
  printf 'PROMPT409_RESTORATION_PACKET_READY=%s\n' "${PROMPT409_RESTORATION_PACKET_READY}"
  printf 'PROMPT409_NEXT_ACTION=%s\n' "${PROMPT409_NEXT_ACTION}"
  printf 'PROMPT409_BUILDER_READY_PATH_OK=%s\n' "${PROMPT409_BUILDER_READY_PATH_OK}"
  printf 'OVERALL_RC=%s\n' "${OVERALL_RC}"
  printf 'SUMMARY paths: %s %s %s %s %s\n' "${SUMMARY_PATH}" "${FIELDS_PATH}" "${READY_PATH}" "${BLOCKED_PATH}" "${PY_COMPILE_LOG}"
} | tee -a "${SUMMARY_PATH}"

if [ "${BASH_SOURCE[0]}" != "$0" ]; then
  return "${OVERALL_RC}"
fi
true
