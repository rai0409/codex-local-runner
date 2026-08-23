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
from automation.orchestration.repository_multi_cycle_state import RepositoryMultiCycleStateError, load_latest_checkpoint
from automation.orchestration.repository_multi_cycle_status import read_verified_terminal_receipt

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
    def __init__(self, repository_id: str, queue_spec_path: str | os.PathLike[str], *, state_root: str | os.PathLike[str] = DEFAULT_SUPERVISOR_STATE_ROOT, cycle_output_root: str | os.PathLike[str] | None = None, registry_path: str | os.PathLike[str] | None = None, bindings_path: str | os.PathLike[str] | None = None, providers_path: str | os.PathLike[str] | None = None, single_task_output_root: str | os.PathLike[str] | None = None, poll_seconds: float = 1.0, max_crash_restarts: int = 3, max_backoff_seconds: float = 30.0, worker_factory: Callable[[str | None], Any] | None = None, sleep: Callable[[float], None] = time.sleep, replan_coordinator: Callable[[VerifiedTerminalReplanInput], RepositoryMultiCycleReplanCoordinatorResult] | None = None) -> None:
        self.repository_id, self.queue_spec_path = repository_id, Path(queue_spec_path).expanduser()
        self.state_root = Path(state_root).expanduser()
        self.cycle_output_root = Path(cycle_output_root or DEFAULT_CYCLE_OUTPUT_ROOT).expanduser()
        self.poll_seconds, self.max_crash_restarts, self.max_backoff_seconds = poll_seconds, max_crash_restarts, max_backoff_seconds
        self.worker_factory, self.sleep = worker_factory, sleep
        self.replan_coordinator = replan_coordinator
        self.registry_path = Path(registry_path).expanduser() if registry_path is not None else None
        self.bindings_path = Path(bindings_path).expanduser() if bindings_path is not None else None
        self.providers_path = Path(providers_path).expanduser() if providers_path is not None else None
        self.single_task_output_root = Path(single_task_output_root).expanduser() if single_task_output_root is not None else None
        self._cycle_output_root_supplied = cycle_output_root is not None
        self.stop_event = Event(); self._launch_gate = Lock(); self._lock_stream: Any = None; self._worker: Any = None; self._terminal_status_written = False; self._last_replan_result: RepositoryMultiCycleReplanCoordinatorResult | None = None

    @property
    def _directory(self) -> Path: return self.state_root / hashlib.sha256(self.repository_id.encode("utf-8")).hexdigest()

    def _queue_sha(self) -> str: return hashlib.sha256(self.queue_spec_path.read_bytes()).hexdigest()

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
        try: receipt = read_verified_terminal_receipt(directory, self.repository_id, queue_sha256)
        except ValueError: return False
        if receipt is None: return False
        self._write_status("terminal", queue_sha256=queue_sha256, cycle_run_id=directory.name, worker_pid=worker_pid, worker_alive=False, crash_restart_count=crash_restart_count, terminal_status=receipt["status"], reason_code=receipt.get("reason_code"))
        self._terminal_status_written = True
        if self.replan_coordinator is not None and receipt["status"] in {"blocked", "failed"}:
            verified = self._verified_replan_input(directory, queue_sha256, receipt)
            if verified is not None:
                self._last_replan_result = self.replan_coordinator(verified)
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
        return VerifiedTerminalReplanInput(
            repository_id=self.repository_id,
            source_repository_root=state["source_repository_root"],
            root_queue_spec_path=self.queue_spec_path,
            root_queue_spec_sha256=queue_sha256,
            predecessor_queue_spec_path=self.queue_spec_path,
            predecessor_queue_spec_sha256=queue_sha256,
            verified_terminal_result=terminal,
        )

    def request_shutdown(self, *_: Any) -> None:
        # This handler may run in the main thread while a launcher thread owns
        # the gate.  It never interrupts that thread while it is spawning.
        with self._launch_gate: self.stop_event.set()

    def _verified_terminal(self, directory: Path, queue_sha: str) -> bool:
        try: return read_verified_terminal_receipt(directory, self.repository_id, queue_sha) is not None
        except ValueError: return False

    def _candidates(self, queue_sha: str) -> tuple[list[str], list[str]]:
        nonterminal, terminal = [], []
        if not self.cycle_output_root.exists(): return nonterminal, terminal
        for directory in sorted(self.cycle_output_root.iterdir(), key=lambda item: item.name):
            if not directory.is_dir() or not directory.name.startswith("cycle-"): continue
            receipt = directory / "receipt.json"
            if receipt.exists():
                try: value=json.loads(receipt.read_text(encoding="utf-8"))
                except (OSError, ValueError): raise ValueError("supervisor.cycle.receipt_invalid")
                if value.get("repository_id") == self.repository_id and value.get("queue_spec_sha256") == queue_sha:
                    if not self._verified_terminal(directory,queue_sha): raise ValueError("supervisor.cycle.receipt_invalid")
                    terminal.append(directory.name); continue
                # A verified historical terminal receipt for another queue revision
                # must not be reclassified as a nonterminal candidate.
                continue
            try:
                state,_=load_latest_checkpoint(directory / "state")
            except RepositoryMultiCycleStateError as exc:
                raise ValueError("supervisor.cycle.checkpoint_invalid") from exc
            if state.get("cycle_run_id") != directory.name: raise ValueError("supervisor.cycle.checkpoint_invalid")
            if state.get("repository_id") == self.repository_id and state.get("queue_spec_sha256") == queue_sha and state.get("lifecycle_status") in {"initialized","active_task","accepted_task","finalizing"}: nonterminal.append(directory.name)
        return nonterminal, terminal

    def _launch(self, resume_cycle_run_id: str | None) -> Any:
        if self.worker_factory is not None: return self.worker_factory(resume_cycle_run_id)
        command=[sys.executable, str(Path(__file__).resolve().parents[2] / "scripts" / "run_repository_multi_cycle.py"), "--repository-id", self.repository_id, "--queue-spec", str(self.queue_spec_path)]
        if resume_cycle_run_id: command.extend(["--resume-cycle-run-id",resume_cycle_run_id])
        configuration = (("--registry-path", self.registry_path), ("--bindings-path", self.bindings_path), ("--providers-path", self.providers_path), ("--single-task-output-root", self.single_task_output_root))
        for flag, value in configuration:
            if value is not None: command.extend([flag,os.fspath(value)])
        if self._cycle_output_root_supplied:
            command.extend(["--output-root", os.fspath(self.cycle_output_root)])
        return subprocess.Popen(command, shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

    def _launch_or_shutdown(self, resume_cycle_run_id: str | None) -> Any | None:
        outcome: dict[str, Any] = {}
        completed = Event()
        def launcher() -> None:
            try:
                with self._launch_gate:
                    if not self.stop_event.is_set(): outcome["worker"] = self._launch(resume_cycle_run_id)
            except BaseException as exc: outcome["error"] = exc
            finally: completed.set()
        thread = Thread(target=launcher, name="repository-multi-cycle-launcher")
        thread.start(); completed.wait(); thread.join()
        if "error" in outcome: raise outcome["error"]
        return outcome.get("worker")

    def run_once(self) -> RepositoryMultiCycleSupervisorResult:
        self._last_replan_result = None
        try: queue_sha=self._queue_sha(); nonterminal, terminal=self._candidates(queue_sha)
        except (OSError, ValueError): return RepositoryMultiCycleSupervisorResult("blocked","supervisor.discovery.invalid",self.repository_id,None,None,0)
        if len(nonterminal)>1: return RepositoryMultiCycleSupervisorResult("blocked","supervisor.discovery.ambiguous_nonterminal",self.repository_id,queue_sha,None,0)
        if terminal and not nonterminal:
            self._write_terminal_status(self.cycle_output_root / terminal[-1], queue_sha, None, 0)
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
                    try: nonterminal,terminal=self._candidates(queue_sha)
                    except ValueError:
                        self._write_status("blocked", queue_sha256=queue_sha, cycle_run_id=result.cycle_run_id, worker_pid=worker_pid, worker_alive=False, crash_restart_count=restarts, reason_code="supervisor.discovery.invalid")
                        return RepositoryMultiCycleSupervisorResult("blocked","supervisor.discovery.invalid",self.repository_id,queue_sha,result.cycle_run_id,restarts)
                    if terminal and not nonterminal:
                        self._write_terminal_status(self.cycle_output_root / terminal[-1], queue_sha, worker_pid, restarts)
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
