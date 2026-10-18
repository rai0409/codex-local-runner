"""Local-only process supervisor for repository multi-cycle workers."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Any, Callable

from automation.orchestration.repository_multi_cycle_replan_coordinator import (
    RepositoryMultiCycleReplanCoordinatorResult,
    VerifiedTerminalReplanInput,
)
from automation.orchestration.repository_multi_cycle_replan_launch import (
    ReplanLaunchClaimInput,
    ReplanLaunchClaimResult,
    acquire_replan_launch_claim,
)
from automation.orchestration.repository_multi_cycle_replan_launch_execution import (
    ReplanLaunchExecutionInput,
    ReplanLaunchExecutionResult,
    WorkerLaunchRequest,
    WorkerLaunchResult,
    execute_replan_launch,
)
from automation.orchestration.repository_multi_cycle_replan_state import ReplanPersistenceResult
from automation.orchestration.repository_multi_cycle_state import RepositoryMultiCycleStateError, load_latest_checkpoint
from automation.orchestration.repository_multi_cycle_status import read_verified_terminal_receipt
from automation.orchestration.repository_multi_cycle_evidence import CycleEvidenceKind, classify_cycle_evidence

DEFAULT_SUPERVISOR_STATE_ROOT = "~/.local/state/codex-local-runner/repository-multi-cycle-supervisor"
DEFAULT_CYCLE_OUTPUT_ROOT = "~/.local/state/codex-local-runner/repository-multi-cycle-runs"


@dataclass(frozen=True)
class RepositoryMultiCycleSupervisorResult:
    status: str
    reason_code: str
    repository_id: str
    queue_sha256: str | None
    cycle_run_id: str | None
    crash_restart_count: int
    replan_result: RepositoryMultiCycleReplanCoordinatorResult | None = None


class RepositoryMultiCycleSupervisor:
    """One repository-scoped supervisor; workers always run out of process."""
    def __init__(self, repository_id: str, queue_spec_path: str | os.PathLike[str], *, state_root: str | os.PathLike[str] = DEFAULT_SUPERVISOR_STATE_ROOT, cycle_output_root: str | os.PathLike[str] | None = None, registry_path: str | os.PathLike[str] | None = None, bindings_path: str | os.PathLike[str] | None = None, providers_path: str | os.PathLike[str] | None = None, single_task_output_root: str | os.PathLike[str] | None = None, poll_seconds: float = 1.0, max_crash_restarts: int = 3, max_backoff_seconds: float = 30.0, worker_factory: Callable[[str | None], Any] | None = None, sleep: Callable[[float], None] = time.sleep, replan_coordinator: Callable[[VerifiedTerminalReplanInput], RepositoryMultiCycleReplanCoordinatorResult] | None = None, auto_replan_launch: bool = False, replan_claim_acquirer: Callable[[ReplanLaunchClaimInput], ReplanLaunchClaimResult] = acquire_replan_launch_claim, replan_launch_executor: Callable[..., ReplanLaunchExecutionResult] = execute_replan_launch, resume_terminal: bool = False) -> None:
        self.repository_id, self.queue_spec_path = repository_id, Path(queue_spec_path).expanduser()
        self.root_queue_spec_path = self.queue_spec_path; self._root_queue_spec_sha256: str | None = None
        self.state_root = Path(state_root).expanduser()
        self.cycle_output_root = Path(cycle_output_root or DEFAULT_CYCLE_OUTPUT_ROOT).expanduser()
        self.poll_seconds, self.max_crash_restarts, self.max_backoff_seconds = poll_seconds, max_crash_restarts, max_backoff_seconds
        self.worker_factory, self.sleep = worker_factory, sleep
        self.replan_coordinator = replan_coordinator
        self.auto_replan_launch = auto_replan_launch
        self.resume_terminal = resume_terminal
        self.replan_claim_acquirer, self.replan_launch_executor = replan_claim_acquirer, replan_launch_executor
        self.registry_path = Path(registry_path).expanduser() if registry_path is not None else None
        self.bindings_path = Path(bindings_path).expanduser() if bindings_path is not None else None
        self.providers_path = Path(providers_path).expanduser() if providers_path is not None else None
        self.single_task_output_root = Path(single_task_output_root).expanduser() if single_task_output_root is not None else None
        self._cycle_output_root_supplied = cycle_output_root is not None
        self.stop_event = Event(); self._launch_gate = Lock(); self._lock_stream: Any = None; self._worker: Any = None; self._terminal_status_written = False; self._last_replan_result: RepositoryMultiCycleReplanCoordinatorResult | None = None; self._last_replan_launch_result: ReplanLaunchExecutionResult | None = None; self._auto_successor_worker_active = False; self._terminal_resume_consumed = False

    @property
    def _directory(self) -> Path: return self.state_root / hashlib.sha256(self.repository_id.encode("utf-8")).hexdigest()

    def _queue_sha(self) -> str: return hashlib.sha256(self.queue_spec_path.read_bytes()).hexdigest()

    def _root_queue_sha(self) -> str:
        if self._root_queue_spec_sha256 is None:
            self._root_queue_spec_sha256 = hashlib.sha256(self.root_queue_spec_path.read_bytes()).hexdigest()
        return self._root_queue_spec_sha256

    def acquire_lock(self) -> bool:
        self._directory.mkdir(parents=True, exist_ok=True)
        self._lock_stream = (self._directory / "supervisor.lock").open("a+")
        try: fcntl.flock(self._lock_stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: self._lock_stream.close(); self._lock_stream = None; return False
        self._write_status("idle", queue_sha256=None, cycle_run_id=None, worker_pid=None, worker_alive=False, crash_restart_count=0)
        return True

    def release_lock(self) -> None:
        if self._lock_stream is not None:
            fcntl.flock(self._lock_stream.fileno(), fcntl.LOCK_UN); self._lock_stream.close(); self._lock_stream = None

    def _atomic_status(self, value: dict[str, Any]) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)
        path = self._directory / "status.json"; temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        os.replace(temporary, path)

    def _write_status(self, state: str, *, queue_sha256: str | None, cycle_run_id: str | None, worker_pid: int | None, worker_alive: bool, crash_restart_count: int, terminal_status: str | None = None, reason_code: str | None = None) -> None:
        now = time.time()
        value: dict[str, Any] = {"schema_version":"1","repository_id":self.repository_id,"queue_sha256":queue_sha256,"cycle_run_id":cycle_run_id,"state":state,"supervisor_pid":os.getpid(),"worker_pid":worker_pid,"worker_alive":worker_alive,"crash_restart_count":crash_restart_count,"updated_at":now,"last_heartbeat_at":now}
        if terminal_status is not None: value["terminal_status"] = terminal_status
        if reason_code is not None: value["reason_code"] = reason_code
        self._atomic_status(value)

    def _write_terminal_status(self, directory: Path, queue_sha256: str, worker_pid: int | None, crash_restart_count: int) -> bool:
        evidence = classify_cycle_evidence(directory, self.repository_id, queue_sha256)
        if evidence is None or evidence.evidence_kind == CycleEvidenceKind.INVALID:
            return False
        if evidence.evidence_kind == CycleEvidenceKind.PRE_TASK_NO_PROGRESS:
            try: receipt = json.loads((directory / "receipt.json").read_text(encoding="utf-8"))
            except (OSError, ValueError): return False
        else:
            try: receipt = read_verified_terminal_receipt(directory, self.repository_id, queue_sha256)
            except ValueError: return False
        if receipt is None: return False
        self._write_status("terminal", queue_sha256=queue_sha256, cycle_run_id=directory.name, worker_pid=worker_pid, worker_alive=False, crash_restart_count=crash_restart_count, terminal_status=receipt["status"], reason_code=receipt.get("reason_code"))
        self._terminal_status_written = True
        if self.replan_coordinator is not None and receipt["status"] in {"blocked", "failed"}:
            verified = self._verified_replan_input(directory, queue_sha256, receipt)
            if verified is not None:
                self._last_replan_result = self.replan_coordinator(verified)
                if self.auto_replan_launch and self._last_replan_result.status == "successor_ready":
                    self._last_replan_launch_result = self._launch_replan_successor(self._last_replan_result)
        return True

    def _verified_replan_input(self, directory: Path, queue_sha256: str, receipt: dict[str, Any]) -> VerifiedTerminalReplanInput | None:
        """Reconcile verified receipt and checkpoint before crossing into R6-C1a."""
        try:
            state, _ = load_latest_checkpoint(directory / "state")
        except (OSError, RepositoryMultiCycleStateError):
            return None
        terminal_task = state.get("terminal_task_result")
        if not isinstance(terminal_task, dict):
            return None
        completed = state.get("completed_task_results")
        if not isinstance(completed, list):
            return None
        invariants = (
            state.get("cycle_run_id") == receipt.get("cycle_run_id") == directory.name,
            state.get("repository_id") == receipt.get("repository_id") == self.repository_id,
            state.get("queue_spec_sha256") == receipt.get("queue_spec_sha256") == queue_sha256,
            state.get("lifecycle_status") == "finalizing",
            state.get("terminal_status") == receipt.get("status"),
            state.get("terminal_reason_code") == receipt.get("reason_code"),
            state.get("accepted_head_sha") == receipt.get("final_accepted_head_sha"),
            state.get("task_count") == receipt.get("task_count"),
            len(completed) == receipt.get("completed_count"),
            state.get("next_task_index") == receipt.get("completed_count"),
            state.get("stopped_task_id") == receipt.get("stopped_task_id"),
            terminal_task.get("task_index") == receipt.get("completed_count"),
            terminal_task.get("task_id") == receipt.get("stopped_task_id"),
            terminal_task.get("status") == receipt.get("status"),
            isinstance(state.get("source_repository_root"), str),
        )
        if not all(invariants):
            return None
        terminal = dict(receipt)
        terminal["terminal_task_result"] = dict(terminal_task)
        # Scope-deficiency replan is permitted only after the controller's
        # receipt proves the bounded trim/rework sequence.  This keeps the
        # planner from treating a generic scope violation as authority.
        if terminal_task.get("reason_code") == "single_task.task_scope.recovery_exhausted":
            try:
                child_path = Path(str(terminal_task.get("child_receipt_path", "")))
                payload = child_path.read_bytes()
                child = json.loads(payload)
                sidecar = child_path.with_name("receipt.sha256").read_text(encoding="utf-8")
                digest = hashlib.sha256(payload).hexdigest()
            except (OSError, ValueError, json.JSONDecodeError):
                return None
            required = (
                child_path.name == "receipt.json",
                terminal_task.get("child_receipt_sha256") == digest,
                sidecar == f"{digest}  receipt.json\n",
                isinstance(child, dict),
                child.get("repository_id") == self.repository_id,
                child.get("task_id") == terminal_task.get("task_id"),
                child.get("reason_code") == "single_task.task_scope.recovery_exhausted",
                child.get("scope_trim_attempted") is True,
                child.get("scope_constrained_rework_attempted") is True,
                child.get("scope_constrained_rework_status") in {"failed", "succeeded"},
                isinstance(child.get("declared_allowed_changed_paths"), list),
                isinstance(child.get("effective_allowed_changed_paths"), list),
                isinstance(child.get("original_unexpected_changed_files"), list),
                isinstance(child.get("scope_trimmed_paths"), list),
            )
            if not all(required):
                return None
            terminal["completion_evaluation"] = {
                key: child[key]
                for key in (
                    "declared_allowed_changed_paths", "effective_allowed_changed_paths",
                    "original_unexpected_changed_files", "auto_expanded_paths",
                    "scope_trimmed_paths", "scope_constrained_rework_attempted",
                    "scope_constrained_rework_status", "post_trim_validation_status",
                )
                if key in child
            }
        return VerifiedTerminalReplanInput(
            repository_id=self.repository_id,
            source_repository_root=state["source_repository_root"],
            root_queue_spec_path=self.root_queue_spec_path,
            root_queue_spec_sha256=self._root_queue_sha(),
            predecessor_queue_spec_path=self.queue_spec_path,
            predecessor_queue_spec_sha256=queue_sha256,
            verified_terminal_result=terminal,
        )

    def request_shutdown(self, *_: Any) -> None:
        # This handler may run in the main thread while a launcher thread owns
        # the gate.  It never interrupts that thread while it is spawning.
        with self._launch_gate: self.stop_event.set()

    def _verified_terminal(self, directory: Path, queue_sha: str) -> bool:
        evidence = classify_cycle_evidence(directory, self.repository_id, queue_sha)
        return bool(evidence and evidence.evidence_kind in {
            CycleEvidenceKind.PRE_TASK_NO_PROGRESS, CycleEvidenceKind.TASK_TERMINAL,
            CycleEvidenceKind.TASK_TERMINAL_RESUMABLE, CycleEvidenceKind.COMPLETED,
        })

    def _candidates(self, queue_sha: str) -> tuple[list[str], list[str], list[str]]:
        nonterminal, terminal, pre_task = [], [], []
        if not self.cycle_output_root.exists(): return nonterminal, terminal, pre_task
        for directory in sorted(self.cycle_output_root.iterdir(), key=lambda item: item.name):
            if not directory.is_dir() or not directory.name.startswith("cycle-"): continue
            evidence = classify_cycle_evidence(directory, self.repository_id, queue_sha)
            if evidence is None:
                if not (directory / "receipt.json").exists() and not (directory / "state").exists():
                    raise ValueError("supervisor.cycle.checkpoint_invalid")
                continue
            if evidence.evidence_kind == CycleEvidenceKind.INVALID:
                raise ValueError("supervisor.cycle.evidence_invalid")
            if evidence.evidence_kind == CycleEvidenceKind.ACTIVE:
                nonterminal.append(directory.name); continue
            if evidence.evidence_kind == CycleEvidenceKind.PRE_TASK_NO_PROGRESS:
                pre_task.append(directory.name); continue
            terminal.append(directory.name)
        return nonterminal, terminal, pre_task

    def _launch(self, resume_cycle_run_id: str | None, *, queue_spec_path: Path | None = None, terminal_resume_cycle_run_id: str | None = None) -> Any:
        selected_queue = queue_spec_path or self.queue_spec_path
        if self.worker_factory is not None: return self.worker_factory(resume_cycle_run_id)
        command=[sys.executable, str(Path(__file__).resolve().parents[2] / "scripts" / "run_repository_multi_cycle.py"), "--repository-id", self.repository_id, "--queue-spec", str(selected_queue)]
        if resume_cycle_run_id: command.extend(["--resume-cycle-run-id",resume_cycle_run_id])
        if terminal_resume_cycle_run_id: command.extend(["--resume-terminal-cycle-run-id",terminal_resume_cycle_run_id])
        configuration = (("--registry-path", self.registry_path), ("--bindings-path", self.bindings_path), ("--providers-path", self.providers_path), ("--single-task-output-root", self.single_task_output_root))
        for flag, value in configuration:
            if value is not None: command.extend([flag,os.fspath(value)])
        if self._cycle_output_root_supplied:
            command.extend(["--output-root", os.fspath(self.cycle_output_root)])
        return subprocess.Popen(command, shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

    def _claim_input_from_replan(self, result: RepositoryMultiCycleReplanCoordinatorResult) -> ReplanLaunchClaimInput | None:
        if (
            result.status != "successor_ready" or result.campaign_id is None
            or result.successor_queue_path is None or result.successor_queue_sha256 is None
            or result.accepted_head_sha is None or result.replan_attempt_number is None
        ):
            return None
        attempt = result.successor_queue_path.parent
        persisted = ReplanPersistenceResult(
            "successor_ready", "replan.persistence.ready", result.campaign_id, attempt,
            attempt / "accepted_replan.json", result.successor_queue_path,
            result.successor_queue_sha256, attempt / "campaign.json",
            result.replan_attempt_number, None,
        )
        return ReplanLaunchClaimInput(persisted, self.repository_id, result.accepted_head_sha)

    def _launch_verified_successor_worker(self, request: WorkerLaunchRequest) -> WorkerLaunchResult:
        worker = self._launch_or_shutdown(None, queue_spec_path=request.successor_queue_path)
        if worker is None:
            return WorkerLaunchResult("not_confirmed")
        pid = getattr(worker, "pid", None)
        if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
            return WorkerLaunchResult("not_confirmed")
        self._worker = worker
        self._auto_successor_worker_active = True
        return WorkerLaunchResult("confirmed_started", worker_pid=pid)

    def _launch_replan_successor(self, result: RepositoryMultiCycleReplanCoordinatorResult) -> ReplanLaunchExecutionResult | None:
        claim_input = self._claim_input_from_replan(result)
        if claim_input is None:
            return None
        claim = self.replan_claim_acquirer(claim_input)
        if claim.status != "launch_pending":
            return None
        return self.replan_launch_executor(
            ReplanLaunchExecutionInput(claim_input, claim),
            worker_launcher=self._launch_verified_successor_worker,
        )

    def _launch_or_shutdown(self, resume_cycle_run_id: str | None, *, queue_spec_path: Path | None = None, terminal_resume_cycle_run_id: str | None = None) -> Any | None:
        outcome: dict[str, Any] = {}
        completed = Event()
        def launcher() -> None:
            try:
                with self._launch_gate:
                    if not self.stop_event.is_set():
                        if terminal_resume_cycle_run_id is None:
                            outcome["worker"] = self._launch(resume_cycle_run_id, queue_spec_path=queue_spec_path)
                        else:
                            outcome["worker"] = self._launch(resume_cycle_run_id, queue_spec_path=queue_spec_path, terminal_resume_cycle_run_id=terminal_resume_cycle_run_id)
            except BaseException as exc: outcome["error"] = exc
            finally: completed.set()
        thread = Thread(target=launcher, name="repository-multi-cycle-launcher")
        thread.start(); completed.wait(); thread.join()
        if "error" in outcome: raise outcome["error"]
        return outcome.get("worker")

    def run_once(self) -> RepositoryMultiCycleSupervisorResult:
        self._last_replan_result = None
        self._last_replan_launch_result = None
        if self._auto_successor_worker_active:
            return RepositoryMultiCycleSupervisorResult("running","supervisor.replan.successor_started",self.repository_id,self._queue_sha(),None,0)
        try: queue_sha=self._queue_sha(); nonterminal, terminal, pre_task=self._candidates(queue_sha)
        except (OSError, ValueError): return RepositoryMultiCycleSupervisorResult("blocked","supervisor.discovery.invalid",self.repository_id,None,None,0)
        if len(nonterminal)>1: return RepositoryMultiCycleSupervisorResult("blocked","supervisor.discovery.ambiguous_nonterminal",self.repository_id,queue_sha,None,0)
        if self.resume_terminal and pre_task and not nonterminal and not terminal:
            return RepositoryMultiCycleSupervisorResult("blocked","supervisor.terminal_resume.pre_task_not_resumable",self.repository_id,queue_sha,pre_task[-1],0)
        if terminal and not nonterminal:
            self._write_terminal_status(self.cycle_output_root / terminal[-1], queue_sha, None, 0)
            if (
                self._last_replan_launch_result is not None
                and self._last_replan_launch_result.status == "launched"
                and self._worker is not None
                and self._last_replan_launch_result.successor_queue_path is not None
            ):
                self.queue_spec_path = self._last_replan_launch_result.successor_queue_path
                return RepositoryMultiCycleSupervisorResult("running","supervisor.replan.successor_started",self.repository_id,self._queue_sha(),None,0,self._last_replan_result)
            # An R6 successor is authoritative for this terminal event.  A
            # same-queue retry must not race it or create a second worker.
            if self._last_replan_result is not None and self._last_replan_result.status == "successor_ready":
                return RepositoryMultiCycleSupervisorResult("idle","supervisor.queue.terminal_suppressed",self.repository_id,queue_sha,terminal[-1],0,self._last_replan_result)
            if self.resume_terminal and not self._terminal_resume_consumed:
                try:
                    receipt = read_verified_terminal_receipt(self.cycle_output_root / terminal[-1], self.repository_id, queue_sha)
                except ValueError:
                    receipt = None
                evidence = classify_cycle_evidence(self.cycle_output_root / terminal[-1], self.repository_id, queue_sha)
                if receipt is not None and evidence is not None and evidence.evidence_kind in {CycleEvidenceKind.TASK_TERMINAL, CycleEvidenceKind.TASK_TERMINAL_RESUMABLE}:
                    self._terminal_resume_consumed = True
                    worker = self._launch_or_shutdown(None, terminal_resume_cycle_run_id=terminal[-1])
                    if worker is None:
                        return RepositoryMultiCycleSupervisorResult("completed","supervisor.shutdown",self.repository_id,queue_sha,None,0,self._last_replan_result)
                    self._worker = worker
                    self._write_status("worker_active", queue_sha256=queue_sha, cycle_run_id=None, worker_pid=getattr(worker,"pid",None), worker_alive=True, crash_restart_count=0)
                    return RepositoryMultiCycleSupervisorResult("running","supervisor.terminal_resume.started",self.repository_id,queue_sha,None,0,self._last_replan_result)
            return RepositoryMultiCycleSupervisorResult("idle","supervisor.queue.terminal_suppressed",self.repository_id,queue_sha,terminal[-1],0,self._last_replan_result)
        cycle_id=nonterminal[0] if nonterminal else None; worker=self._launch_or_shutdown(cycle_id)
        if worker is None: return RepositoryMultiCycleSupervisorResult("completed","supervisor.shutdown",self.repository_id,queue_sha,cycle_id,0)
        self._worker=worker
        self._write_status("worker_active", queue_sha256=queue_sha, cycle_run_id=cycle_id, worker_pid=getattr(worker,"pid",None), worker_alive=True, crash_restart_count=0)
        return RepositoryMultiCycleSupervisorResult("running","supervisor.worker.started",self.repository_id,queue_sha,cycle_id,0)

    def _wait_for_worker(self, queue_sha256: str, cycle_run_id: str | None, crash_restart_count: int) -> int:
        """Wait with bounded heartbeat polling; retain compatibility with fakes."""
        worker = self._worker
        poll = getattr(worker, "poll", None)
        if not callable(poll): return worker.wait()
        interval = max(float(self.poll_seconds), 0.05)
        while poll() is None:
            self._write_status("worker_active", queue_sha256=queue_sha256, cycle_run_id=cycle_run_id, worker_pid=getattr(worker,"pid",None), worker_alive=True, crash_restart_count=crash_restart_count)
            if self.stop_event.is_set(): break
            self.sleep(interval)
        return worker.wait()

    def run_forever(self) -> RepositoryMultiCycleSupervisorResult:
        if not self.acquire_lock(): return RepositoryMultiCycleSupervisorResult("blocked","supervisor.lock.unavailable",self.repository_id,None,None,0)
        previous_sha=None; restarts=0
        try:
            while not self.stop_event.is_set():
                queue_sha=self._queue_sha()
                if queue_sha != previous_sha:
                    previous_sha, restarts = queue_sha, 0
                result=self.run_once()
                if result.status == "running":
                    worker_pid=getattr(self._worker,"pid",None); code=self._wait_for_worker(queue_sha,result.cycle_run_id,restarts)
                    observed_queue_sha = result.queue_sha256 or queue_sha
                    try: nonterminal,terminal,pre_task=self._candidates(observed_queue_sha)
                    except ValueError:
                        self._write_status("blocked", queue_sha256=observed_queue_sha, cycle_run_id=result.cycle_run_id, worker_pid=worker_pid, worker_alive=False, crash_restart_count=restarts, reason_code="supervisor.discovery.invalid")
                        return RepositoryMultiCycleSupervisorResult("blocked","supervisor.discovery.invalid",self.repository_id,observed_queue_sha,result.cycle_run_id,restarts)
                    if terminal and not nonterminal:
                        self._write_terminal_status(self.cycle_output_root / terminal[-1], observed_queue_sha, worker_pid, restarts)
                    if pre_task and not nonterminal and not terminal:
                        self._write_terminal_status(self.cycle_output_root / pre_task[-1], observed_queue_sha, worker_pid, restarts)
                        if self.stop_event.is_set(): break
                        return RepositoryMultiCycleSupervisorResult("idle","supervisor.queue.pre_task_observed",self.repository_id,observed_queue_sha,pre_task[-1],restarts)
                    self._auto_successor_worker_active = False
                    if self.stop_event.is_set(): break
                    if not nonterminal and not terminal:
                        self._write_status("blocked", queue_sha256=queue_sha, cycle_run_id=result.cycle_run_id, worker_pid=worker_pid, worker_alive=False, crash_restart_count=restarts, reason_code="supervisor.worker.evidence_missing")
                        return RepositoryMultiCycleSupervisorResult("blocked","supervisor.worker.evidence_missing",self.repository_id,queue_sha,result.cycle_run_id,restarts)
                    if code != 0 and len(nonterminal)==1:
                        if restarts >= self.max_crash_restarts:
                            self._write_status("blocked", queue_sha256=queue_sha, cycle_run_id=nonterminal[0], worker_pid=worker_pid, worker_alive=False, crash_restart_count=restarts, reason_code="supervisor.worker.restart_exhausted")
                            return RepositoryMultiCycleSupervisorResult("blocked","supervisor.worker.restart_exhausted",self.repository_id,queue_sha,nonterminal[0],restarts)
                        self.sleep(min(self.max_backoff_seconds, 2 ** restarts)); restarts += 1; continue
                if result.status == "blocked": return result
                self.sleep(self.poll_seconds)
            return RepositoryMultiCycleSupervisorResult("completed","supervisor.shutdown",self.repository_id,previous_sha,None,restarts)
        finally:
            if self.stop_event.is_set() and not self._terminal_status_written:
                self._write_status("idle", queue_sha256=previous_sha, cycle_run_id=None, worker_pid=getattr(self._worker,"pid",None), worker_alive=False, crash_restart_count=restarts, reason_code="supervisor.shutdown")
            self.release_lock()


__all__=["DEFAULT_SUPERVISOR_STATE_ROOT","RepositoryMultiCycleSupervisor","RepositoryMultiCycleSupervisorResult"]
