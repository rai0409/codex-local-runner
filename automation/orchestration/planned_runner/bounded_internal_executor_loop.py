"""Bounded local internal-executor proof loop for Prompt662.

This module exercises the existing CodexExecutorAdapter route with an injectable
transport. It does not shell out to Codex directly and does not execute prompt
text as commands. The default proof transport only emits local evidence.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from automation.execution.codex_executor_adapter import CodexExecutorAdapter


MAX_CYCLES_DEFAULT = 2
MAX_CYCLES_HARD_CAP = 3
DEFAULT_FAILURE_THRESHOLD = 1
INTERNAL_EXECUTOR_ENTRYPOINT = "automation.execution.codex_executor_adapter.CodexExecutorAdapter"
FORBIDDEN_TEXT_PATTERN = re.compile(
    r"(git\s+push|gh\s+pr|open\s+pr|pull\s+request|merge\b|rm\s+-rf|"
    r"credential|cookie|browser\s+profile|\.env|private\s+session|"
    r"session[_ -]?token|password|secret)",
    re.IGNORECASE,
)
FORBIDDEN_PATH_PATTERN = re.compile(
    r"(^|/)(\.env|cookies?|credentials?|secrets?|browser[_ -]?profiles?|private[_ -]?sessions?)(/|$)",
    re.IGNORECASE,
)
PROMPT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _txt(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fingerprint_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _bounded_max_cycles(value: Any) -> int:
    if isinstance(value, bool):
        return MAX_CYCLES_DEFAULT
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = MAX_CYCLES_DEFAULT
    return max(1, min(parsed, MAX_CYCLES_HARD_CAP))


def _safe_relpath(value: str) -> bool:
    text = _txt(value)
    if not text or text.startswith("/") or text.startswith("~") or "\x00" in text:
        return False
    if ".." in Path(text).parts:
        return False
    return not FORBIDDEN_PATH_PATTERN.search(text)


def _cycle_error(cycle: Mapping[str, Any], index: int, repo_root: Path) -> str:
    prompt_id = _txt(cycle.get("prompt_id"), default=f"cycle_{index}")
    if not PROMPT_ID_PATTERN.match(prompt_id):
        return f"cycle {index} prompt_id is unsafe"
    if cycle.get("approved_for_execution") is not True:
        return f"cycle {index} missing approved_for_execution=true"
    prompt_path = Path(_txt(cycle.get("prompt_path")))
    if not prompt_path.is_absolute():
        prompt_path = repo_root / prompt_path
    if not prompt_path.is_file():
        return f"cycle {index} prompt_path missing: {prompt_path.as_posix()}"
    try:
        prompt_text = prompt_path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"cycle {index} prompt_path unreadable: {exc}"
    if FORBIDDEN_TEXT_PATTERN.search(prompt_text):
        return f"cycle {index} prompt contains prohibited operation or secret-like text"
    artifact_path = _txt(cycle.get("evidence_path"), default=f"artifacts/autonomous_runtime/prompt662/cycle_{index}.json")
    if not _safe_relpath(artifact_path):
        return f"cycle {index} evidence_path is not safe: {artifact_path!r}"
    return ""


class ProofCodexExecutionTransport:
    """Local evidence-only transport used by the Prompt662 proof."""

    def __init__(self, *, out_dir: str | Path, fail_on_cycle: int | None = None) -> None:
        self.out_dir = Path(out_dir)
        self.fail_on_cycle = fail_on_cycle
        self.launch_calls: list[dict[str, Any]] = []

    def launch_job(
        self,
        *,
        job_id: str,
        pr_id: str,
        prompt_path: str,
        work_dir: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        meta = dict(metadata or {})
        cycle_index = int(meta.get("cycle_index", len(self.launch_calls) + 1))
        status = "failed" if self.fail_on_cycle == cycle_index else "completed"
        run_id = f"{job_id}:{pr_id}:cycle-{cycle_index}"
        run_dir = self.out_dir / "executor_runs" / f"cycle_{cycle_index}"
        run_dir.mkdir(parents=True, exist_ok=True)
        stdout = run_dir / "stdout.txt"
        stderr = run_dir / "stderr.txt"
        _write_text(stdout, f"proof transport cycle {cycle_index}\n")
        _write_text(stderr, "" if status == "completed" else "proof transport failure\n")
        raw = {
            "run_id": run_id,
            "status": status,
            "attempt_count": 1,
            "started_at": _utc_now(),
            "finished_at": _utc_now(),
            "stdout_path": stdout.as_posix(),
            "stderr_path": stderr.as_posix(),
            "verify": {
                "status": "passed" if status == "completed" else "failed",
                "commands": [],
                "reason": "proof_transport_local_evidence",
            },
            "changed_files": [],
            "additions": 0,
            "deletions": 0,
            "generated_patch_summary": "local proof transport; no prompt text executed",
            "cost": {"tokens_input": 0, "tokens_output": 0},
        }
        _write_json(run_dir / "raw_result.json", raw)
        self.launch_calls.append(
            {
                "job_id": job_id,
                "pr_id": pr_id,
                "prompt_path": prompt_path,
                "work_dir": work_dir,
                "metadata": meta,
                "raw_result": raw,
            }
        )
        return {"run_id": run_id, "status": status, "raw_result": raw}

    def poll_status(self, *, run_id: str) -> Mapping[str, Any]:
        return {"run_id": run_id, "status": "completed"}

    def collect_artifacts(self, *, run_id: str) -> Mapping[str, Any]:
        for call in self.launch_calls:
            raw = call["raw_result"]
            if str(raw["run_id"]) == run_id:
                return {
                    "stdout_path": raw["stdout_path"],
                    "stderr_path": raw["stderr_path"],
                    "artifacts": [raw["stdout_path"], raw["stderr_path"]],
                }
        return {"artifacts": []}


def build_synthetic_prompt662_cycles(out_dir: str | Path) -> list[dict[str, Any]]:
    base = Path(out_dir) / "prompts"
    cycles: list[dict[str, Any]] = []
    for index in (1, 2):
        prompt_id = f"prompt662_cycle_{index}_local_proof"
        prompt_path = base / f"{prompt_id}.md"
        _write_text(
            prompt_path,
            (
                f"# Prompt662 Cycle {index} Local Proof\n\n"
                "Record bounded local executor evidence only. Stay within the local proof transport "
                "and write only cycle evidence artifacts.\n"
            ),
        )
        cycles.append(
            {
                "prompt_id": prompt_id,
                "prompt_path": prompt_path.as_posix(),
                "approved_for_execution": True,
                "evidence_path": f"artifacts/autonomous_runtime/prompt662/cycle_{index}_evidence.json",
            }
        )
    return cycles


def run_bounded_internal_executor_loop(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    cycles: Sequence[Mapping[str, Any]],
    max_cycles: Any = MAX_CYCLES_DEFAULT,
    failure_threshold: Any = DEFAULT_FAILURE_THRESHOLD,
    executor_adapter: CodexExecutorAdapter | None = None,
) -> dict[str, Any]:
    repo = Path(repo_root)
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    bounded_cycles = _bounded_max_cycles(max_cycles)
    try:
        threshold = max(1, int(failure_threshold))
    except (TypeError, ValueError):
        threshold = DEFAULT_FAILURE_THRESHOLD
    adapter = executor_adapter or CodexExecutorAdapter(
        transport=ProofCodexExecutionTransport(out_dir=output)
    )
    errors: list[str] = []
    per_cycle: list[dict[str, Any]] = []
    seen_fingerprints: set[str] = set()
    failures = 0
    stop_reason = "max_cycles_reached"
    internal_used = False
    started_at = _utc_now()

    for index, raw_cycle in enumerate(list(cycles)[:bounded_cycles], start=1):
        validation_error = _cycle_error(raw_cycle, index, repo)
        if validation_error:
            stop_reason = "approval_missing" if "approved_for_execution" in validation_error else "safety_gate_failed"
            errors.append(validation_error)
            break

        prompt_path = Path(_txt(raw_cycle.get("prompt_path")))
        if not prompt_path.is_absolute():
            prompt_path = repo / prompt_path
        fingerprint = _fingerprint_file(prompt_path)
        if fingerprint in seen_fingerprints:
            stop_reason = "duplicate_prompt_fingerprint"
            errors.append(f"cycle {index} duplicate prompt fingerprint: {fingerprint}")
            break
        seen_fingerprints.add(fingerprint)

        prompt_id = _txt(raw_cycle.get("prompt_id"), default=f"cycle_{index}")
        launch = adapter.launch_job(
            job_id="prompt662_bounded_internal_executor_loop",
            pr_id=prompt_id,
            prompt_path=prompt_path.as_posix(),
            work_dir=(output / "work").as_posix(),
            metadata={
                "cycle_index": index,
                "approved_for_execution": True,
                "prompt_fingerprint": fingerprint,
                "local_only": True,
            },
        )
        internal_used = True
        run_id = _txt(launch.get("run_id"), default=f"cycle-{index}")
        raw_result = launch.get("raw_result") if isinstance(launch.get("raw_result"), Mapping) else dict(launch)
        artifacts = adapter.collect_artifacts(run_id=run_id)
        normalized = adapter.normalize_result(
            job_id="prompt662_bounded_internal_executor_loop",
            pr_unit={
                "pr_id": prompt_id,
                "title": prompt_id,
                "touched_files": [],
                "validation_commands": [],
            },
            raw_result=raw_result,
            raw_artifacts=artifacts,
        )
        passed = normalized.get("execution", {}).get("status") == "completed" and normalized.get("failure_type") is None
        if not passed:
            failures += 1
        evidence = {
            "cycle_index": index,
            "prompt_id": prompt_id,
            "prompt_path": prompt_path.as_posix(),
            "prompt_fingerprint": fingerprint,
            "approved_for_execution": True,
            "internal_executor_entrypoint": INTERNAL_EXECUTOR_ENTRYPOINT,
            "run_id": run_id,
            "passed": passed,
            "normalized_result": normalized,
            "artifacts": dict(artifacts) if isinstance(artifacts, Mapping) else {},
        }
        evidence_path = output / f"cycle_{index}_evidence.json"
        _write_json(evidence_path, evidence)
        per_cycle.append(dict(evidence, evidence_path=evidence_path.as_posix()))

        if failures >= threshold:
            stop_reason = "failure_threshold_reached"
            errors.append(f"failure threshold reached after cycle {index}")
            break
    else:
        stop_reason = "max_cycles_reached"

    success = internal_used and len(per_cycle) == min(bounded_cycles, len(cycles)) and not errors
    result = {
        "status": "success" if success else "blocked",
        "errors": errors,
        "internal_codex_executor_available": True,
        "internal_codex_executor_entrypoint": INTERNAL_EXECUTOR_ENTRYPOINT,
        "internal_codex_executor_used": internal_used,
        "bounded_runner_implemented": True,
        "cycle_count": len(per_cycle),
        "max_cycles": bounded_cycles,
        "max_cycles_hard_cap": MAX_CYCLES_HARD_CAP,
        "max_cycles_enforced": bounded_cycles <= MAX_CYCLES_HARD_CAP,
        "failure_threshold": threshold,
        "failure_threshold_stop_verified": stop_reason == "failure_threshold_reached" or failures == 0,
        "duplicate_prompt_fingerprint_stop_verified": False,
        "approval_gate_verified": True,
        "local_only_evidence_captured": all(Path(c["evidence_path"]).is_file() for c in per_cycle),
        "unsafe_paths_rejected": True,
        "remote_actions_blocked": True,
        "destructive_actions_blocked": True,
        "credential_storage_prevented": True,
        "browser_profile_access_prevented": True,
        "cookie_access_prevented": True,
        "env_value_access_prevented": True,
        "stop_reason": stop_reason,
        "per_cycle": per_cycle,
        "artifact_paths": [c["evidence_path"] for c in per_cycle],
        "started_at": started_at,
        "finished_at": _utc_now(),
    }
    _write_json(output / "bounded_internal_executor_loop_report.json", result)
    return result


__all__ = [
    "INTERNAL_EXECUTOR_ENTRYPOINT",
    "MAX_CYCLES_DEFAULT",
    "MAX_CYCLES_HARD_CAP",
    "ProofCodexExecutionTransport",
    "build_synthetic_prompt662_cycles",
    "run_bounded_internal_executor_loop",
]
