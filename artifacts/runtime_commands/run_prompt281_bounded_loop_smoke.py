from __future__ import annotations

import importlib.util
import inspect
import json
import sys
import traceback
from pathlib import Path
from typing import Any

REPO = Path("/home/rai/codex-local-runner")
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
MODULE_PATH = REPO / "automation/orchestration/planned_execution_runner.py"
OUT_PATH = REPO / "artifacts/runtime_commands/prompt281_bounded_loop_smoke_result.json"

def main() -> int:
    spec = importlib.util.spec_from_file_location("planned_execution_runner_smoke", MODULE_PATH)
    if spec is None or spec.loader is None:
        print("FAILED: module spec load failed")
        return 2

    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    builder = getattr(mod, "_build_project_browser_autonomous_bounded_local_loop_coordinator_state", None)
    if builder is None:
        print("FAILED: missing _build_project_browser_autonomous_bounded_local_loop_coordinator_state")
        return 2

    sig = inspect.signature(builder)

    def call_builder(
        *,
        controls: dict[str, Any],
        prior: dict[str, Any] | None = None,
        local_loop: dict[str, Any] | None = None,
        codex_connector: dict[str, Any] | None = None,
        codex_capture: dict[str, Any] | None = None,
        review_request: dict[str, Any] | None = None,
        review_decision: dict[str, Any] | None = None,
        safe_revert: dict[str, Any] | None = None,
        commit_gate: dict[str, Any] | None = None,
        commit_execution: dict[str, Any] | None = None,
        pr_queue: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        prior = prior or {}
        local_loop = local_loop or {}
        codex_connector = codex_connector or {}
        codex_capture = codex_capture or {}
        review_request = review_request or {}
        review_decision = review_decision or {}
        safe_revert = safe_revert or {}
        commit_gate = commit_gate or {}
        commit_execution = commit_execution or {}
        pr_queue = pr_queue or {}

        values = {
            "local_loop": local_loop,
            "codex_execution_connector": codex_connector,
            "codex_connector": codex_connector,
            "codex_capture_gate": codex_capture,
            "capture_gate": codex_capture,
            "chatgpt_diff_review_request": review_request,
            "review_request": review_request,
            "chatgpt_diff_review_decision": review_decision,
            "review_decision": review_decision,
            "safe_revert": safe_revert,
            "commit_tag_gate": commit_gate,
            "commit_gate": commit_gate,
            "commit_tag_execution": commit_execution,
            "commit_execution": commit_execution,
            "pr_queue_state": pr_queue,
            "queue_state": pr_queue,
        }

        kwargs: dict[str, Any] = {}
        for name, param in sig.parameters.items():
            lower = name.lower()

            if "prior" in lower:
                kwargs[name] = prior
                continue

            if "approved" in lower or "payload" in lower or "restart" in lower:
                kwargs[name] = controls
                continue

            matched = False
            for hint, value in values.items():
                if hint in lower:
                    kwargs[name] = value
                    matched = True
                    break
            if matched:
                continue

            if "repo" in lower or "path" in lower:
                kwargs[name] = str(REPO)
                continue

            if param.default is inspect._empty:
                raise RuntimeError(f"unknown required parameter: {name}")

        result = builder(**kwargs)
        if not isinstance(result, dict):
            raise RuntimeError(f"builder returned non-dict: {type(result)}")
        return result

    def get(result: dict[str, Any], suffix: str) -> Any:
        return result.get(f"project_browser_autonomous_bounded_local_loop_{suffix}")

    base_local_loop = {
        "project_browser_autonomous_local_loop_status": "local_loop_ready_run_codex_implementation",
        "project_browser_autonomous_local_loop_next_action": "run_codex_implementation",
        "project_browser_autonomous_local_loop_selected_prompt_fingerprint": "smoke-prompt-fp-001",
        "project_browser_autonomous_local_loop_selected_step_fingerprint": "smoke-step-fp-001",
        "project_browser_autonomous_local_loop_active_pr_id": "pr-smoke-1",
        "project_browser_autonomous_local_loop_next_pr_id": "pr-smoke-1",
    }

    base_controls = {
        "project_browser_autonomous_bounded_local_loop_enabled": True,
        "project_browser_autonomous_bounded_local_loop_max_iterations": 3,
        "project_browser_autonomous_bounded_local_loop_iteration": 0,
        "project_browser_autonomous_bounded_local_loop_max_consecutive_failures": 1,
        "project_browser_autonomous_bounded_local_loop_consecutive_failures": 0,
    }

    cases: dict[str, dict[str, Any]] = {}

    c1 = dict(base_controls)
    c1["project_browser_autonomous_bounded_local_loop_continue_enabled"] = False
    cases["decision_only"] = call_builder(controls=c1, local_loop=base_local_loop)

    c2 = dict(base_controls)
    c2["project_browser_autonomous_bounded_local_loop_continue_enabled"] = True
    cases["one_step_continue"] = call_builder(controls=c2, local_loop=base_local_loop)

    prior_fp = get(cases["one_step_continue"], "progress_fingerprint") or ""
    prior = {
        "project_browser_autonomous_bounded_local_loop_progress_fingerprint": prior_fp,
        "project_browser_autonomous_bounded_local_loop_iteration": get(cases["one_step_continue"], "iteration") or 1,
    }
    c3 = dict(base_controls)
    c3["project_browser_autonomous_bounded_local_loop_continue_enabled"] = True
    c3["project_browser_autonomous_bounded_local_loop_iteration"] = prior[
        "project_browser_autonomous_bounded_local_loop_iteration"
    ]
    cases["duplicate_no_progress"] = call_builder(
        controls=c3,
        prior=prior,
        local_loop=base_local_loop,
    )

    c4 = dict(base_controls)
    c4["project_browser_autonomous_bounded_local_loop_continue_enabled"] = True
    cases["project_complete"] = call_builder(
        controls=c4,
        pr_queue={
            "project_browser_autonomous_pr_queue_state_status": "pr_queue_state_project_complete",
            "project_browser_autonomous_pr_queue_state_next_action": "project_local_queue_complete",
        },
    )

    summary = {}
    for name, result in cases.items():
        summary[name] = {
            "status": get(result, "status"),
            "next_action": get(result, "next_action"),
            "iteration": get(result, "iteration"),
            "consecutive_failures": get(result, "consecutive_failures"),
            "progress_fingerprint": get(result, "progress_fingerprint"),
            "selected_component": get(result, "selected_component"),
            "selected_component_status": get(result, "selected_component_status"),
            "blocked_reason": get(result, "blocked_reason"),
        }

    OUT_PATH.write_text(
        json.dumps({"summary": summary, "raw": cases}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))

    errors = []

    if summary["decision_only"]["status"] != "bounded_local_loop_decision_only":
        errors.append("decision_only status mismatch")

    if str(summary["decision_only"]["iteration"]) not in {"0", "None"}:
        errors.append("decision_only incremented iteration")

    if summary["one_step_continue"]["status"] != "bounded_local_loop_ready_continue":
        errors.append("one_step_continue status mismatch")

    if summary["one_step_continue"]["next_action"] != "run_codex_implementation":
        errors.append("one_step_continue next_action mismatch")

    if summary["duplicate_no_progress"]["status"] != "bounded_local_loop_blocked_duplicate_or_no_progress":
        errors.append("duplicate_no_progress status mismatch")

    if summary["project_complete"]["status"] != "bounded_local_loop_project_complete":
        errors.append("project_complete status mismatch")

    if errors:
        print("\nSMOKE_FAILED")
        for err in errors:
            print(f"- {err}")
        print(f"\nFull JSON: {OUT_PATH}")
        return 1

    print("\nSMOKE_PASSED")
    print(f"Full JSON: {OUT_PATH}")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print("SMOKE_EXCEPTION")
        traceback.print_exc()
        raise SystemExit(2)
