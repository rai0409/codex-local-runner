from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import time
from typing import Any, Mapping

from automation.orchestration.planned_runner.autonomous_cycle import (
    AUTONOMOUS_CYCLE_ENABLE_TOKEN,
    run_autonomous_cycle_metadata,
)
from automation.orchestration.planned_runner.failure_digest import build_failure_digest


LIVE_CODEX_GATE_ENABLE_TOKEN = "LOCAL_LIVE_CODEX_GATE_ENABLE"
SUPPORTED_SANDBOX_MODES = ("default", "read-only", "workspace-write")
ALLOWED_VERIFY_COMMAND_BASENAMES = {"python", "python3", "pytest"}
DEFAULT_VERIFY_COMMAND_TIMEOUT_SECONDS = 120
PROCESS_TERMINATION_GRACE_SECONDS = 2
MIGRATED_LEGACY_FUNCTIONS = [
    "_build_prompt379_generated_prompt_codex_execution_bridge_state",
    "_build_prompt417_selected_prompt_codex_execution_adapter_state",
    "_build_prompt422_targeted_fix_codex_execution_adapter_state",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _as_positive_int(value: Any, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value > 0:
        return value
    text = _normalize_text(value)
    if text.isdigit() and int(text) > 0:
        return int(text)
    return default


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _summary_lines(payload: Mapping[str, Any]) -> list[str]:
    return [
        "# Live Codex Gate Summary",
        "",
        f"- status: {payload.get('status', '')}",
        f"- enabled: {payload.get('enabled', False)}",
        f"- stop_reason: {payload.get('stop_reason', '')}",
        f"- next_action: {payload.get('next_action', '')}",
        f"- codex_invoked: {payload.get('codex_invoked', False)}",
        f"- result_assimilation_status: {payload.get('result_assimilation_status', '')}",
        f"- sandbox_mode: {payload.get('sandbox_mode', 'default')}",
        f"- effect_verification_status: {payload.get('effect_verification_status', 'not_run')}",
    ]


def _build_codex_command(prompt_text: str, target_repo: str) -> list[str]:
    command = [
        "codex",
        "-a",
        "never",
        "-s",
        "danger-full-access",
        "-C",
        target_repo,
        "exec",
    ]
    command.extend(["--skip-git-repo-check", prompt_text])
    return command


def _normalize_sandbox_mode(value: Any) -> str:
    text = _normalize_text(value, default="default").lower()
    return text if text in SUPPORTED_SANDBOX_MODES else "default"


def _pytest_cache_provider_disabled(options: str) -> bool:
    try:
        tokens = shlex.split(options)
    except ValueError:
        tokens = options.split()
    return any(
        token == "-p" and index + 1 < len(tokens) and tokens[index + 1] == "no:cacheprovider"
        for index, token in enumerate(tokens)
    ) or "-pno:cacheprovider" in tokens


def _build_codex_environment(cache_dir: Path) -> dict[str, str]:
    """Return an execution-only environment that keeps Codex child caches out of the repo."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPYCACHEPREFIX"] = cache_dir.resolve().as_posix()
    existing_options = environment.get("PYTEST_ADDOPTS", "")
    if not _pytest_cache_provider_disabled(existing_options):
        environment["PYTEST_ADDOPTS"] = (existing_options + " -p no:cacheprovider").strip()
    return environment


def _terminal_success_result(stdout_text: str) -> bool:
    for line in reversed(stdout_text.splitlines()):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            isinstance(payload, dict)
            and _normalize_text(payload.get("status")).lower() == "success"
            and _normalize_text(payload.get("summary"))
        ):
            return True
    return False


def _process_group_exists(process_group_id: int | None) -> bool:
    if os.name != "posix" or process_group_id is None:
        return False
    try:
        os.killpg(process_group_id, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return False
    return True


def _terminate_process_group(process: subprocess.Popen[Any], process_group_id: int | None) -> dict[str, Any]:
    """Terminate a dedicated POSIX session, with a bounded KILL fallback."""
    details = {"forced_termination": False, "termination_signal": "", "kill_fallback_used": False}
    if os.name == "posix" and _process_group_exists(process_group_id):
        details["forced_termination"] = True
        details["termination_signal"] = "SIGTERM"
        try:
            os.killpg(int(process_group_id), signal.SIGTERM)
        except ProcessLookupError:
            return details
        deadline = time.monotonic() + PROCESS_TERMINATION_GRACE_SECONDS
        while _process_group_exists(process_group_id) and time.monotonic() < deadline:
            time.sleep(0.05)
        if _process_group_exists(process_group_id):
            details["kill_fallback_used"] = True
            details["termination_signal"] = "SIGKILL"
            try:
                os.killpg(int(process_group_id), signal.SIGKILL)
            except ProcessLookupError:
                pass
    elif process.poll() is None:
        details["forced_termination"] = True
        details["termination_signal"] = "terminate"
        process.terminate()
    try:
        process.wait(timeout=PROCESS_TERMINATION_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        details["kill_fallback_used"] = True
        details["termination_signal"] = "kill"
        process.kill()
        process.wait(timeout=PROCESS_TERMINATION_GRACE_SECONDS)
    return details


def _hash_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _list_repo_files(repo: Path) -> set[str]:
    files: set[str] = set()
    try:
        for entry in repo.rglob("*"):
            if not entry.is_file():
                continue
            rel = entry.relative_to(repo).as_posix()
            if rel == ".git" or rel.startswith(".git/"):
                continue
            files.add(rel)
    except OSError:
        pass
    return files


def _normalize_relative_file_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _normalize_text(item)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _validate_allowed_files(value: Any, errors: list[str]) -> list[str]:
    allowed_files = _normalize_relative_file_list(value)
    if not 1 <= len(allowed_files) <= 3:
        errors.append("effect spec allowed_files must contain 1 to 3 files")
    for path in allowed_files:
        candidate = Path(path)
        if (
            candidate.is_absolute()
            or path.endswith("/")
            or "\\" in path
            or any(part in {"", ".", ".."} for part in candidate.parts)
            or any(character in path for character in "*?[]{}")
        ):
            errors.append("effect spec allowed_files entries must be repo-relative files without traversal, globs, or directories")
            break
    return allowed_files


def _load_effect_spec(path_text: str) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    path = Path(path_text)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return {}, [f"effect spec unreadable: {path_text}"]
    except json.JSONDecodeError:
        return {}, [f"effect spec is not valid JSON: {path_text}"]
    if not isinstance(payload, dict):
        return {}, [f"effect spec must be a JSON object: {path_text}"]

    repo_path = _normalize_text(payload.get("repo_path"))
    if not repo_path:
        errors.append("effect spec missing repo_path")
    elif not Path(repo_path).is_dir():
        errors.append(f"effect spec repo_path is not a directory: {repo_path}")

    required_text = payload.get("required_text", {})
    if not isinstance(required_text, dict):
        errors.append("effect spec required_text must be an object")
        required_text = {}

    raw_commands = payload.get("verify_commands", [])
    verify_commands: list[list[str]] = []
    if raw_commands:
        if not isinstance(raw_commands, list):
            errors.append("effect spec verify_commands must be a list of argv lists")
        else:
            for index, raw in enumerate(raw_commands, start=1):
                if not isinstance(raw, (list, tuple)) or not raw:
                    errors.append(f"verify command {index} must be a non-empty argv list")
                    continue
                argv = [str(item) for item in raw]
                basename = Path(argv[0]).name
                if basename not in ALLOWED_VERIFY_COMMAND_BASENAMES:
                    errors.append(
                        f"verify command {index} executable not allowed: {basename} "
                        f"(allowed: {sorted(ALLOWED_VERIFY_COMMAND_BASENAMES)})"
                    )
                    continue
                verify_commands.append(argv)

    timeout_value = payload.get("verify_command_timeout_seconds", DEFAULT_VERIFY_COMMAND_TIMEOUT_SECONDS)
    verify_timeout = _as_positive_int(timeout_value, default=DEFAULT_VERIFY_COMMAND_TIMEOUT_SECONDS)

    expected_modified_files = _normalize_relative_file_list(payload.get("expected_modified_files"))
    allowed_files = _validate_allowed_files(
        payload.get("allowed_files", expected_modified_files), errors
    )
    if not set(expected_modified_files).issubset(set(allowed_files)):
        errors.append("effect spec expected_modified_files must be included in allowed_files")
    spec = {
        "verify_commands": verify_commands,
        "verify_command_timeout_seconds": verify_timeout,
        "repo_path": repo_path,
        "allowed_files": allowed_files,
        "expected_modified_files": expected_modified_files,
        "expected_unmodified_files": _normalize_relative_file_list(payload.get("expected_unmodified_files")),
        "required_text": {
            _normalize_text(name): [
                str(snippet)
                for snippet in (snippets if isinstance(snippets, (list, tuple)) else [])
            ]
            for name, snippets in required_text.items()
            if _normalize_text(name)
        },
        "forbidden_paths": _normalize_relative_file_list(payload.get("forbidden_paths")),
        "allow_extra_files": bool(payload.get("allow_extra_files", False)),
    }
    return spec, errors


def _verify_effects(
    *,
    spec: Mapping[str, Any],
    repo: Path,
    pre_hashes: Mapping[str, str | None],
    pre_listing: set[str],
) -> dict[str, Any]:
    errors: list[str] = []

    modified_ok = True
    for rel in spec.get("expected_modified_files", []):
        post_hash = _hash_file(repo / rel)
        if post_hash is None:
            modified_ok = False
            errors.append(f"expected modified file missing after run: {rel}")
        elif post_hash == pre_hashes.get(rel):
            modified_ok = False
            errors.append(f"expected modified file did not change: {rel}")

    unmodified_ok = True
    for rel in spec.get("expected_unmodified_files", []):
        if _hash_file(repo / rel) != pre_hashes.get(rel):
            unmodified_ok = False
            errors.append(f"expected unmodified file changed: {rel}")

    required_text_ok = True
    for rel, snippets in spec.get("required_text", {}).items():
        try:
            content = (repo / rel).read_text(encoding="utf-8")
        except OSError:
            required_text_ok = False
            errors.append(f"required_text target unreadable: {rel}")
            continue
        for snippet in snippets:
            if snippet not in content:
                required_text_ok = False
                errors.append(f"required text missing in {rel}: {snippet!r}")

    forbidden_ok = True
    for rel in spec.get("forbidden_paths", []):
        if (repo / rel).exists():
            forbidden_ok = False
            errors.append(f"forbidden path exists after run: {rel}")

    post_listing = _list_repo_files(repo)
    created = post_listing - set(pre_listing)
    allowed_files = set(spec.get("allowed_files", []))
    unexpected = sorted(created - allowed_files)
    changed_outside_scope = sorted(
        path
        for path, pre_hash in pre_hashes.items()
        if path not in allowed_files and _hash_file(repo / path) != pre_hash
    )
    if unexpected:
        errors.append("unexpected files created outside allowed_files: " + ", ".join(unexpected))
    if changed_outside_scope:
        errors.append("files changed outside allowed_files: " + ", ".join(changed_outside_scope))

    passed = modified_ok and unmodified_ok and required_text_ok and forbidden_ok and not errors
    return {
        "effect_verification_status": "passed" if passed else "failed",
        "effect_modified_files_verified": modified_ok,
        "effect_unmodified_files_verified": unmodified_ok,
        "effect_required_text_verified": required_text_ok,
        "effect_forbidden_paths_verified": forbidden_ok,
        "effect_unexpected_files": unexpected,
        "effect_changed_outside_allowed_files": changed_outside_scope,
        "effect_verification_errors": errors,
    }


def _run_verify_commands(
    *,
    spec: Mapping[str, Any],
    repo: Path,
    out_dir: Path,
) -> tuple[list[dict[str, Any]], bool, list[str]]:
    """Run the spec's allowlisted test commands inside the sandbox repo only."""
    commands = list(spec.get("verify_commands", []))
    timeout = int(spec.get("verify_command_timeout_seconds", DEFAULT_VERIFY_COMMAND_TIMEOUT_SECONDS))
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    all_passed = True
    for index, argv in enumerate(commands, start=1):
        stdout_path = out_dir / f"verify_command_{index}_stdout.txt"
        stderr_path = out_dir / f"verify_command_{index}_stderr.txt"
        timed_out = False
        try:
            completed = subprocess.run(
                argv,
                cwd=repo,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            returncode: int | None = completed.returncode
            _write_text(stdout_path, completed.stdout or "")
            _write_text(stderr_path, completed.stderr or "")
        except subprocess.TimeoutExpired as exc:
            returncode = None
            timed_out = True
            _write_text(stdout_path, exc.stdout if isinstance(exc.stdout, str) else "")
            _write_text(
                stderr_path,
                (exc.stderr if isinstance(exc.stderr, str) else "")
                + f"\nverify command timed out after {timeout} seconds\n",
            )
        except OSError as exc:
            returncode = None
            _write_text(stdout_path, "")
            _write_text(stderr_path, f"verify command failed to start: {exc}\n")
        passed = returncode == 0
        if not passed:
            all_passed = False
            errors.append(
                f"verify command {index} failed (returncode={returncode}"
                + (", timed out" if timed_out else "")
                + f"): {' '.join(argv)}"
            )
        results.append(
            {
                "argv": list(argv),
                "returncode": returncode,
                "timed_out": timed_out,
                "passed": passed,
                "stdout_path": stdout_path.as_posix(),
                "stderr_path": stderr_path.as_posix(),
            }
        )
    return results, all_passed, errors


def _base_result(
    *,
    status: str,
    returncode: int | None,
    stdout_path: Path,
    stderr_path: Path,
    stop_reason: str,
    started_at: str,
    finished_at: str,
) -> dict[str, Any]:
    return {
        "status": status,
        "returncode": returncode,
        "returncode_classification": "success" if returncode == 0 else status,
        "started_at": started_at,
        "finished_at": finished_at,
        "stdout_path": stdout_path.as_posix(),
        "stderr_path": stderr_path.as_posix(),
        "stop_reason": stop_reason,
        "next_action": "manual_review_required" if status != "success" else "commit_tag_gate",
        "execution": {
            "status": "completed" if returncode == 0 else status,
            "attempt_count": 1 if returncode is not None else 0,
            "started_at": started_at,
            "finished_at": finished_at,
            "stdout_path": stdout_path.as_posix(),
            "stderr_path": stderr_path.as_posix(),
        },
        "commit_performed": False,
        "tag_performed": False,
        "local_only": True,
    }


def _run_codex_once(
    *,
    generated_prompt_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    timeout_seconds: int,
    sandbox_mode: str = "default",
    codex_cwd: str | None = None,
) -> tuple[dict[str, Any], list[str], bool]:
    prompt_text = generated_prompt_path.read_text(encoding="utf-8")
    target_repo = codex_cwd or Path.cwd().as_posix()
    command = _build_codex_command(prompt_text, target_repo)
    started_at = _utc_now()

    if shutil.which("codex") is None:
        _write_text(stdout_path, "")
        _write_text(stderr_path, "Codex CLI is not available in PATH.\n")
        result = _base_result(
            status="blocked",
            returncode=None,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            stop_reason="codex_cli_unavailable",
            started_at=started_at,
            finished_at=_utc_now(),
        )
        result["execution"]["status"] = "not_started"
        result["error"] = "codex_cli_unavailable"
        return result, command, False

    process_group_id: int | None = None
    termination = {"forced_termination": False, "termination_signal": "", "kill_fallback_used": False}
    try:
        codex_environment = _build_codex_environment(stdout_path.parent / "codex_pycache")
        popen_kwargs: dict[str, Any] = {
            "stdin": subprocess.DEVNULL,
            "cwd": codex_cwd or None,
            "env": codex_environment,
        }
        if os.name == "posix":
            popen_kwargs["start_new_session"] = True
        elif os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open("w", encoding="utf-8") as stderr_file:
            process = subprocess.Popen(command, stdout=stdout_file, stderr=stderr_file, **popen_kwargs)
            process_group_id = process.pid if os.name == "posix" else None
            termination = {"forced_termination": False, "termination_signal": "", "kill_fallback_used": False}
            terminal_result_seen_at: float | None = None
            deadline = time.monotonic() + timeout_seconds
            while process.poll() is None:
                if terminal_result_seen_at is None and stdout_path.exists() and _terminal_success_result(
                    stdout_path.read_text(encoding="utf-8")
                ):
                    terminal_result_seen_at = time.monotonic()
                    deadline = min(deadline, terminal_result_seen_at + PROCESS_TERMINATION_GRACE_SECONDS)
                if time.monotonic() >= deadline:
                    termination = _terminate_process_group(process, process_group_id)
                    raise subprocess.TimeoutExpired(command, timeout_seconds)
                time.sleep(0.05)
            process.wait()
            # A direct Codex exit can leave descendants holding artifact file
            # descriptors.  They cannot block the parent wait, and are reaped
            # through the dedicated session before effect verification starts.
            if _process_group_exists(process_group_id):
                termination = _terminate_process_group(process, process_group_id)
        stdout_text = stdout_path.read_text(encoding="utf-8")
        stderr_text = stderr_path.read_text(encoding="utf-8")
        finished_at = _utc_now()
        terminal_success = _terminal_success_result(stdout_text)
        status = "success" if process.returncode == 0 and terminal_success else "failed"
        result = _base_result(
            status=status,
            returncode=process.returncode,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            stop_reason=("codex_completed" if status == "success" else "codex_terminal_result_invalid" if process.returncode == 0 else "codex_failed"),
            started_at=started_at,
            finished_at=finished_at,
        )
        result["execution"].update({
            "process_group_id": process_group_id,
            "process_group_created": os.name == "posix",
            "terminal_result_valid": terminal_success,
            "terminal_result_grace_seconds": PROCESS_TERMINATION_GRACE_SECONDS,
            "terminal_result_grace_expired": False,
            **termination,
        })
        return result, command, True
    except subprocess.TimeoutExpired as exc:
        finished_at = _utc_now()
        # Output is streamed directly to artifacts, so a timeout never needs
        # to wait for inherited pipe descriptors to reach EOF.
        stdout_text = stdout_path.read_text(encoding="utf-8") if stdout_path.exists() else ""
        stderr_text = stderr_path.read_text(encoding="utf-8") if stderr_path.exists() else ""
        if stderr_text:
            stderr_text += "\n"
        stderr_text += f"Codex timed out after {timeout_seconds} seconds.\n"
        _write_text(stderr_path, stderr_text)
        result = _base_result(
            status="failed",
            returncode=None,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            stop_reason="codex_timeout",
            started_at=started_at,
            finished_at=finished_at,
        )
        result["execution"]["status"] = "timed_out"
        result["execution"]["attempt_count"] = 1
        result["execution"].update({
            "process_group_id": process_group_id,
            "process_group_created": os.name == "posix",
            "terminal_result_valid": _terminal_success_result(stdout_text),
            "terminal_result_grace_seconds": PROCESS_TERMINATION_GRACE_SECONDS,
            "terminal_result_grace_expired": _terminal_success_result(stdout_text),
            **termination,
        })
        result["timed_out"] = True
        return result, command, True


def run_live_codex_gate(
    *,
    generated_prompt_path: str | Path | None,
    out_dir: str | Path,
    live_codex_enable_token: str = "",
    timeout_seconds: Any = 60,
    live_codex_result_path: str | Path | None = None,
    legacy_source_used: bool = True,
    migrated_legacy_functions: list[str] | tuple[str, ...] | None = None,
    sandbox_mode: str = "default",
    effect_spec_path: str | Path | None = None,
) -> dict[str, Any]:
    output_root = Path(out_dir)
    state_path = output_root / "live_codex_gate_state.json"
    summary_path = output_root / "live_codex_gate_summary.md"
    stdout_path = output_root / "codex_stdout.txt"
    stderr_path = output_root / "codex_stderr.txt"
    result_path = Path(live_codex_result_path) if live_codex_result_path else output_root / "codex_execution_result.json"
    cycle_output_dir = output_root / "autonomous_cycle"
    timeout = _as_positive_int(timeout_seconds, default=60)
    token_valid = _normalize_text(live_codex_enable_token) == LIVE_CODEX_GATE_ENABLE_TOKEN
    generated_path_text = _normalize_text(generated_prompt_path)
    generated_path = Path(generated_path_text) if generated_path_text else None
    generated_exists = bool(generated_path and generated_path.exists() and generated_path.is_file())
    migrated = list(migrated_legacy_functions or MIGRATED_LEGACY_FUNCTIONS)
    sandbox = _normalize_sandbox_mode(sandbox_mode)
    effect_spec_text = _normalize_text(effect_spec_path)
    effect_enabled = bool(effect_spec_text)
    effect_spec: dict[str, Any] = {}
    effect_spec_errors: list[str] = []
    effect_repo: Path | None = None
    pre_hashes: dict[str, str | None] = {}
    pre_listing: set[str] = set()
    effect_state: dict[str, Any] = {
        "effect_verification_status": "not_run",
        "effect_modified_files_verified": False,
        "effect_unmodified_files_verified": False,
        "effect_required_text_verified": False,
        "effect_forbidden_paths_verified": False,
        "effect_unexpected_files": [],
        "effect_verification_errors": [],
    }
    if effect_enabled:
        effect_spec, effect_spec_errors = _load_effect_spec(effect_spec_text)
        if not effect_spec_errors:
            effect_repo = Path(effect_spec["repo_path"])
            pre_listing = _list_repo_files(effect_repo)
            pre_hashes = {rel: _hash_file(effect_repo / rel) for rel in pre_listing}
        else:
            effect_state["effect_verification_status"] = "failed"
            effect_state["effect_verification_errors"] = list(effect_spec_errors)

    _write_text(stdout_path, "")
    _write_text(stderr_path, "")
    started_at = _utc_now()
    target_repo = effect_repo if effect_repo is not None and effect_repo.is_dir() else Path.cwd()
    codex_command: list[str] = _build_codex_command(
        "<generated_prompt_text>", target_repo.as_posix()
    )
    codex_invoked = False
    returncode: int | None = None

    if not token_valid:
        status = "disabled"
        stop_reason = "disabled_missing_enable_token"
        result_payload = _base_result(
            status=status,
            returncode=None,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            stop_reason=stop_reason,
            started_at=started_at,
            finished_at=_utc_now(),
        )
        result_payload["execution"]["status"] = "not_started"
    elif not generated_exists:
        status = "blocked"
        stop_reason = "missing_generated_prompt"
        result_payload = _base_result(
            status=status,
            returncode=None,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            stop_reason=stop_reason,
            started_at=started_at,
            finished_at=_utc_now(),
        )
        result_payload["execution"]["status"] = "not_started"
    elif effect_enabled and effect_spec_errors:
        status = "blocked"
        stop_reason = "effect_spec_invalid"
        result_payload = _base_result(
            status=status,
            returncode=None,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            stop_reason=stop_reason,
            started_at=started_at,
            finished_at=_utc_now(),
        )
        result_payload["execution"]["status"] = "not_started"
        result_payload["next_action"] = "manual_review_required"
    else:
        result_payload, codex_command, codex_invoked = _run_codex_once(
            generated_prompt_path=generated_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            timeout_seconds=timeout,
            sandbox_mode=sandbox,
            codex_cwd=target_repo.as_posix(),
        )
        status = "success" if result_payload.get("status") == "success" else "blocked"
        stop_reason = _normalize_text(result_payload.get("stop_reason"), default="codex_failed")
        returncode = result_payload.get("returncode") if isinstance(result_payload.get("returncode"), int) else None

        if effect_enabled and effect_repo is not None:
            effect_state = _verify_effects(
                spec=effect_spec,
                repo=effect_repo,
                pre_hashes=pre_hashes,
                pre_listing=pre_listing,
            )
            # Test commands run after the file-effect snapshot comparison so that
            # bytecode/artifacts created by the tests cannot count as Codex output.
            command_results, commands_passed, command_errors = _run_verify_commands(
                spec=effect_spec,
                repo=effect_repo,
                out_dir=output_root,
            )
            effect_state["effect_verify_command_results"] = command_results
            effect_state["effect_verify_commands_passed"] = commands_passed
            if command_errors:
                effect_state["effect_verification_errors"] = (
                    list(effect_state["effect_verification_errors"]) + command_errors
                )
            if not commands_passed:
                effect_state["effect_verification_status"] = "failed"
            # A zero returncode (or success JSON echoed by Codex) is not proof the
            # requested change happened; only verified effects may keep success.
            if status == "success" and effect_state["effect_verification_status"] != "passed":
                status = "blocked"
                stop_reason = "effect_verification_failed"
                result_payload["status"] = "failed"
                result_payload["returncode_classification"] = "failed"
                result_payload["stop_reason"] = "effect_verification_failed"
                result_payload["next_action"] = "inspect_missing_expected_effects"

    if effect_enabled:
        result_payload.update(effect_state)
        result_payload["effect_verification_enabled"] = True
        result_payload["effect_spec_path"] = effect_spec_text

    _write_json(result_path, result_payload)
    cycle_state = run_autonomous_cycle_metadata(
        generated_prompt_path=generated_path_text,
        codex_result_path=result_path,
        output_dir=cycle_output_dir,
        cycle_index=1,
        max_cycles=1,
        max_seconds=timeout,
        autonomous_enable_token=AUTONOMOUS_CYCLE_ENABLE_TOKEN,
        legacy_source_used=legacy_source_used,
        migrated_legacy_functions=migrated,
    )

    gate_next_action = _normalize_text(cycle_state.get("next_action"), default="manual_review_required")
    if effect_enabled and stop_reason == "effect_verification_failed":
        gate_next_action = "inspect_missing_expected_effects"
    elif effect_enabled and stop_reason == "effect_spec_invalid":
        gate_next_action = "manual_review_required"

    state = {
        "status": status,
        "enabled": token_valid,
        "explicit_enable_required": True,
        "enable_token_valid": token_valid,
        "generated_prompt_path": generated_path_text,
        "generated_prompt_exists": generated_exists,
        "live_codex_enabled": token_valid,
        "codex_invoked": codex_invoked,
        "codex_command": codex_command,
        "sandbox_mode": sandbox,
        "effect_verification_enabled": effect_enabled,
        "effect_spec_path": effect_spec_text,
        "effect_verification_status": effect_state["effect_verification_status"],
        "effect_expected_modified_files": list(effect_spec.get("expected_modified_files", [])),
        "effect_allowed_files": list(effect_spec.get("allowed_files", [])),
        "effect_expected_unmodified_files": list(effect_spec.get("expected_unmodified_files", [])),
        "effect_modified_files_verified": effect_state["effect_modified_files_verified"],
        "effect_unmodified_files_verified": effect_state["effect_unmodified_files_verified"],
        "effect_required_text_verified": effect_state["effect_required_text_verified"],
        "effect_forbidden_paths_verified": effect_state["effect_forbidden_paths_verified"],
        "effect_unexpected_files": list(effect_state["effect_unexpected_files"]),
        "effect_changed_outside_allowed_files": list(
            effect_state.get("effect_changed_outside_allowed_files", [])
        ),
        "effect_verification_errors": list(effect_state["effect_verification_errors"]),
        "effect_verify_command_results": list(effect_state.get("effect_verify_command_results", [])),
        "effect_verify_commands_passed": bool(effect_state.get("effect_verify_commands_passed", True)),
        "timeout_seconds": timeout,
        "returncode": returncode,
        "stdout_path": stdout_path.as_posix(),
        "stderr_path": stderr_path.as_posix(),
        "codex_result_path": result_path.as_posix(),
        "result_assimilation_status": _normalize_text(
            cycle_state.get("result_assimilation_status"),
            default="unavailable",
        ),
        "autonomous_cycle_state_path": _normalize_text(
            cycle_state.get("artifact_paths", [""])[0] if cycle_state.get("artifact_paths") else "",
            default=(cycle_output_dir / "autonomous_cycle_state.json").as_posix(),
        ),
        "next_action": gate_next_action,
        "stop_reason": stop_reason,
        "local_only": True,
        "commit_performed": False,
        "tag_performed": False,
        "legacy_source_used": bool(legacy_source_used),
        "migrated_legacy_functions": migrated,
        "artifact_paths": [
            state_path.as_posix(),
            summary_path.as_posix(),
            result_path.as_posix(),
            stdout_path.as_posix(),
            stderr_path.as_posix(),
            (cycle_output_dir / "autonomous_cycle_state.json").as_posix(),
            (cycle_output_dir / "autonomous_cycle_summary.md").as_posix(),
        ],
        "started_at": started_at,
        "finished_at": _utc_now(),
    }
    if status != "success":
        digest = build_failure_digest(state=state, out_dir=output_root, run_kind="live_codex_gate")
        state["failure_digest_path"] = digest["digest_path"]
    else:
        state["failure_digest_path"] = ""
    _write_json(state_path, state)
    _write_text(summary_path, "\n".join(_summary_lines(state)) + "\n")
    return state


__all__ = [
    "LIVE_CODEX_GATE_ENABLE_TOKEN",
    "MIGRATED_LEGACY_FUNCTIONS",
    "run_live_codex_gate",
]
