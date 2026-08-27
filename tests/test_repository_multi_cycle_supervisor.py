from __future__ import annotations
import hashlib, importlib.util, io, json, signal, tempfile, threading, unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from automation.orchestration.repository_multi_cycle_replan_coordinator import RepositoryMultiCycleReplanCoordinatorResult
from automation.orchestration.repository_multi_cycle_replan_launch import ReplanLaunchClaimResult
from automation.orchestration.repository_multi_cycle_replan_launch_execution import ReplanLaunchExecutionResult, WorkerLaunchRequest
from automation.orchestration.repository_multi_cycle_state import load_latest_checkpoint, write_checkpoint
from automation.orchestration.repository_multi_cycle_supervisor import RepositoryMultiCycleSupervisor
from automation.orchestration.repository_multi_cycle_status import inspect_repository_multi_cycle_status
from automation.orchestration.repository_multi_cycle_task_executor import _child_run_id, _runtime_single_task_spec, run_repository_multi_cycle
from tests.test_repository_multi_cycle_task_executor import ExecutorTests, git

def supervisor_cli_module():
 spec=importlib.util.spec_from_file_location("supervisor_cli",Path(__file__).resolve().parents[1]/"scripts/run_repository_multi_cycle_supervisor.py"); value=importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value

def worker_cli_module():
 spec=importlib.util.spec_from_file_location("worker_cli",Path(__file__).resolve().parents[1]/"scripts/run_repository_multi_cycle.py"); value=importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value

def status_cli_module():
 spec=importlib.util.spec_from_file_location("status_cli",Path(__file__).resolve().parents[1]/"scripts/show_repository_multi_cycle_status.py"); value=importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value

class Worker:
 def __init__(self, code=0): self.pid=123; self.code=code
 def wait(self): return self.code

class SupervisorTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name); self.queue=self.root/"queue.json"; self.queue.write_text('{"schema_version":"1","tasks":[{"task_id":"one","prompt":"SUPERVISOR_PROMPT_SENTINEL","allowed_changed_paths":["one.txt"],"commit_message":"one"}]}'); self.state=self.root/"state"; self.cycles=self.root/"cycles"; self.calls=[]
 def tearDown(self): self.temp.cleanup()
 def make(self, factory=None): return RepositoryMultiCycleSupervisor("repo",self.queue,state_root=self.state,cycle_output_root=self.cycles,worker_factory=factory or (lambda resume:self.calls.append(resume) or Worker()))
 def checkpoint(self,name,lifecycle="active_task",terminal=None):
  directory=self.cycles/name; directory.mkdir(parents=True); sha=hashlib.sha256(self.queue.read_bytes()).hexdigest(); write_checkpoint(directory/"state",{"cycle_run_id":name,"repository_id":"repo","queue_spec_sha256":sha,"lifecycle_status":lifecycle,"terminal_status":terminal,"accepted_head_sha":"a"*40})
  return directory
 def terminal(self,name,status="completed"):
  directory=self.cycles/name; directory.mkdir(parents=True); sha=hashlib.sha256(self.queue.read_bytes()).hexdigest(); value={"schema_version":"1","cycle_run_id":name,"repository_id":"repo","queue_spec_sha256":sha,"status":status,"task_count":1,"completed_count":0,"executed_task_results":[],"source_anchor_sha":"a"*40,"final_accepted_head_sha":"a"*40}; payload=json.dumps(value,sort_keys=True,separators=(",",":")).encode(); (directory/"receipt.json").write_bytes(payload); (directory/"receipt.sha256").write_text(f"{hashlib.sha256(payload).hexdigest()}  receipt.json\n"); return directory
 def pre_task_terminal(self,name,queue_sha=None):
  directory=self.cycles/name; directory.mkdir(parents=True); sha=queue_sha or hashlib.sha256(self.queue.read_bytes()).hexdigest(); value={"schema_version":"1","cycle_run_id":name,"repository_id":"repo","queue_spec_sha256":sha,"status":"blocked","reason_code":"multi_cycle.continuation.evidence_invalid","task_count":1,"completed_count":0,"stopped_task_id":None,"executed_task_results":[],"source_anchor_sha":"a"*40,"continuation_base_sha":"a"*40,"final_accepted_head_sha":"a"*40,"pre_task_terminal":True}; payload=json.dumps(value,sort_keys=True,separators=(",",":")).encode(); (directory/"receipt.json").write_bytes(payload); (directory/"receipt.sha256").write_text(f"{hashlib.sha256(payload).hexdigest()}  receipt.json\n"); return directory
 def replan_terminal(self,name="cycle-20260823000000000001",reason="single_task.task_completion.rework_exhausted"):
  directory=self.cycles/name; directory.mkdir(parents=True); sha=hashlib.sha256(self.queue.read_bytes()).hexdigest(); receipt={"schema_version":"1","cycle_run_id":name,"repository_id":"repo","queue_spec_sha256":sha,"status":"blocked","reason_code":"multi_cycle.child.blocked","task_count":1,"completed_count":0,"stopped_task_id":"one","executed_task_results":[],"source_anchor_sha":"a"*40,"final_accepted_head_sha":"a"*40}; payload=json.dumps(receipt,sort_keys=True,separators=(",",":")).encode(); (directory/"receipt.json").write_bytes(payload); (directory/"receipt.sha256").write_text(f"{hashlib.sha256(payload).hexdigest()}  receipt.json\n")
  write_checkpoint(directory/"state",{"cycle_run_id":name,"repository_id":"repo","queue_spec_sha256":sha,"source_repository_root":str(self.root/"source"),"lifecycle_status":"finalizing","terminal_status":"blocked","terminal_reason_code":"multi_cycle.child.blocked","accepted_head_sha":"a"*40,"task_count":1,"next_task_index":0,"completed_task_results":[],"stopped_task_id":"one","terminal_task_result":{"task_index":0,"task_id":"one","status":"blocked","reason_code":reason}}); return directory
 def observe(self, pid_exists=lambda pid: False):
  return inspect_repository_multi_cycle_status("repo",self.queue,state_root=self.state,cycle_output_root=self.cycles,pid_exists=pid_exists)
 def test_kernel_lock_blocks_then_reacquires_and_ignores_stale_metadata(self):
  first=self.make(); second=self.make(); self.assertTrue(first.acquire_lock()); (first._directory/"status.json").write_text('{"pid":999}'); self.assertFalse(second.acquire_lock()); first.release_lock(); self.assertTrue(second.acquire_lock()); second.release_lock()
 def test_unseen_queue_launches_once_terminal_suppresses_and_change_launches(self):
  supervisor=self.make(); self.assertEqual(supervisor.run_once().status,"running"); self.assertEqual(self.calls,[None]); self.terminal("cycle-00000000000000000000"); self.assertEqual(supervisor.run_once().reason_code,"supervisor.queue.terminal_suppressed"); self.queue.write_text(self.queue.read_text()+" "); self.assertEqual(supervisor.run_once().status,"running"); self.assertEqual(self.calls,[None,None])
 def test_every_terminal_status_suppresses_and_corrupt_evidence_blocks(self):
  for status in ("completed","blocked","failed"):
   with self.subTest(status=status):
    self.terminal(f"cycle-0000000000000000000{len(status)}",status); self.assertEqual(self.make().run_once().reason_code,"supervisor.queue.terminal_suppressed")
    self.temp.cleanup(); self.setUp()
  directory=self.terminal("cycle-00000000000000000009"); (directory/"receipt.sha256").write_text("0"*64+"  receipt.json\n"); self.assertEqual(self.make().run_once().reason_code,"supervisor.discovery.invalid"); self.assertEqual(self.calls,[])

 def test_structurally_invalid_terminal_receipt_remains_rejected(self):
  directory=self.terminal("cycle-00000000000000000012","blocked")
  value=json.loads((directory/"receipt.json").read_text()); value["final_accepted_head_sha"]=None
  payload=json.dumps(value,sort_keys=True,separators=(",", ":")).encode(); (directory/"receipt.json").write_bytes(payload); (directory/"receipt.sha256").write_text(f"{hashlib.sha256(payload).hexdigest()}  receipt.json\n")
  supervisor=self.make(); self.assertFalse(supervisor._verified_terminal(directory,hashlib.sha256(self.queue.read_bytes()).hexdigest()))
  self.assertEqual(supervisor.run_once().reason_code,"supervisor.discovery.invalid")
 def test_explicit_terminal_resume_launches_one_fresh_attempt_but_completed_stays_suppressed(self):
  predecessor=self.terminal("cycle-00000000000000000010","blocked"); calls=[]
  supervisor=self.make(); supervisor.resume_terminal=True
  def launch(resume, *, queue_spec_path=None, terminal_resume_cycle_run_id=None):
   calls.append((resume,terminal_resume_cycle_run_id)); return Worker()
  supervisor._launch=launch
  first=supervisor.run_once(); second=supervisor.run_once()
  self.assertEqual(first.reason_code,"supervisor.terminal_resume.started"); self.assertEqual(calls,[(None,predecessor.name)])
  self.assertEqual(second.reason_code,"supervisor.queue.terminal_suppressed"); self.assertEqual(calls,[(None,predecessor.name)])
  self.temp.cleanup(); self.setUp(); self.terminal("cycle-00000000000000000011","completed"); supervisor=self.make(); supervisor.resume_terminal=True
  self.assertEqual(supervisor.run_once().reason_code,"supervisor.queue.terminal_suppressed"); self.assertEqual(self.calls,[])

 def test_pre_task_no_progress_terminal_is_historical_not_fresh_launch_suppression(self):
  predecessor=self.pre_task_terminal("cycle-00000000000000000013"); before=(predecessor/"receipt.json").read_bytes(),(predecessor/"receipt.sha256").read_bytes()
  self.pre_task_terminal("cycle-00000000000000000014","f"*64)
  supervisor=self.make(); nonterminal,terminal,pre_task=supervisor._candidates(hashlib.sha256(self.queue.read_bytes()).hexdigest())
  self.assertEqual((nonterminal,terminal,pre_task),([],[],[predecessor.name]))
  result=supervisor.run_once(); self.assertEqual((result.status,result.reason_code),("running","supervisor.worker.started")); self.assertEqual(self.calls,[None])
  self.assertEqual(((predecessor/"receipt.json").read_bytes(),(predecessor/"receipt.sha256").read_bytes()),before)
  self.assertEqual(self.observe()["terminal_status"],"blocked")

 def test_pre_task_no_progress_terminal_is_not_a_terminal_resume_seed(self):
  predecessor=self.pre_task_terminal("cycle-00000000000000000015")
  supervisor=self.make(); supervisor.resume_terminal=True
  result=supervisor.run_once(); self.assertEqual((result.status,result.reason_code,result.cycle_run_id),("blocked","supervisor.terminal_resume.pre_task_not_resumable",predecessor.name)); self.assertEqual(self.calls,[])
 def test_replan_hook_defaults_disabled_and_existing_terminal_behavior_is_unchanged(self):
  self.replan_terminal(); supervisor=self.make(); result=supervisor.run_once()
  self.assertEqual((result.status,result.reason_code),("idle","supervisor.queue.terminal_suppressed")); self.assertIsNone(result.replan_result); self.assertEqual(self.calls,[])
 def test_verified_terminal_invokes_optional_replan_hook_after_reconciliation(self):
  directory=self.replan_terminal(); calls=[]
  expected=RepositoryMultiCycleReplanCoordinatorResult("successor_ready","ready",1,"one","a"*40,self.root/"successor.json","b"*64,"c"*64,1)
  supervisor=RepositoryMultiCycleSupervisor("repo",self.queue,state_root=self.state,cycle_output_root=self.cycles,worker_factory=lambda resume:self.fail("worker launched"),replan_coordinator=lambda value:calls.append(value) or expected)
  result=supervisor.run_once(); self.assertEqual(result.replan_result,expected); self.assertEqual(len(calls),1); value=calls[0]
  self.assertEqual(value.verified_terminal_result["cycle_run_id"],directory.name); self.assertEqual(value.verified_terminal_result["terminal_task_result"]["reason_code"],"single_task.task_completion.rework_exhausted"); self.assertEqual(value.verified_terminal_result["final_accepted_head_sha"],"a"*40); self.assertEqual(value.predecessor_queue_spec_sha256,hashlib.sha256(self.queue.read_bytes()).hexdigest())
 def test_scope_deficiency_replan_requires_checksymmetric_controller_evidence(self):
  directory=self.replan_terminal(reason="single_task.task_scope.recovery_exhausted"); state,_=load_latest_checkpoint(directory/"state")
  child_path=self.root/"child"/"receipt.json"; child_path.parent.mkdir(); child={"repository_id":"repo","task_id":"one","reason_code":"single_task.task_scope.recovery_exhausted","scope_trim_attempted":True,"scope_constrained_rework_attempted":True,"scope_constrained_rework_status":"failed","declared_allowed_changed_paths":["one.py"],"effective_allowed_changed_paths":["one.py"],"original_unexpected_changed_files":["two.py"],"auto_expanded_paths":[],"scope_trimmed_paths":["two.py"],"post_trim_validation_status":"failed"}; payload=json.dumps(child,sort_keys=True,separators=(",",":")).encode(); child_path.write_bytes(payload); (child_path.parent/"receipt.sha256").write_text(f"{hashlib.sha256(payload).hexdigest()}  receipt.json\n")
  state["terminal_task_result"].update({"child_receipt_path":str(child_path),"child_receipt_sha256":hashlib.sha256(payload).hexdigest(),"commit_created":False,"commit_sha":None,"commit_parent_sha":None}); write_checkpoint(directory/"state",state); calls=[]
  outcome=RepositoryMultiCycleReplanCoordinatorResult("not_eligible","test",None,"one","a"*40,None,None,None,0)
  supervisor=RepositoryMultiCycleSupervisor("repo",self.queue,state_root=self.state,cycle_output_root=self.cycles,replan_coordinator=lambda value:calls.append(value) or outcome)
  self.assertEqual(supervisor.run_once().replan_result,outcome); self.assertEqual(calls[0].verified_terminal_result["completion_evaluation"]["scope_trimmed_paths"],["two.py"])
 def test_replan_hook_never_receives_invalid_receipt_or_raw_worker_exit(self):
  directory=self.replan_terminal(); calls=[]; (directory/"receipt.sha256").write_text("0"*64+"  receipt.json\n")
  supervisor=RepositoryMultiCycleSupervisor("repo",self.queue,state_root=self.state,cycle_output_root=self.cycles,replan_coordinator=lambda value:calls.append(value))
  self.assertEqual(supervisor.run_once().reason_code,"supervisor.discovery.invalid"); self.assertEqual(calls,[])
  self.temp.cleanup(); self.setUp(); supervisor=RepositoryMultiCycleSupervisor("repo",self.queue,state_root=self.state,cycle_output_root=self.cycles,worker_factory=lambda resume:Worker(0),poll_seconds=0,replan_coordinator=lambda value:calls.append(value))
  self.assertEqual(supervisor.run_forever().reason_code,"supervisor.worker.evidence_missing"); self.assertEqual(calls,[])
 def test_replan_hook_requires_verified_checkpoint_reconciliation(self):
  directory=self.replan_terminal(); calls=[]; checkpoint=directory/"state"/"checkpoint-000000.sha256"; checkpoint.write_text("0"*64+"  checkpoint-000000.json\n")
  supervisor=RepositoryMultiCycleSupervisor("repo",self.queue,state_root=self.state,cycle_output_root=self.cycles,replan_coordinator=lambda value:calls.append(value))
  result=supervisor.run_once(); self.assertEqual(result.reason_code,"supervisor.queue.terminal_suppressed"); self.assertEqual(calls,[]); self.assertIsNone(result.replan_result)
 def test_replan_outcomes_never_launch_or_rewrite_predecessor_terminal(self):
  for status in ("successor_ready","not_eligible","stopped","blocked"):
   with self.subTest(status=status):
    directory=self.replan_terminal(); receipt=directory/"receipt.json"; before=(receipt.read_bytes(),receipt.stat().st_mtime_ns); calls=[]
    outcome=RepositoryMultiCycleReplanCoordinatorResult(status,status,1,"one","a"*40,None,None,None,0)
    supervisor=RepositoryMultiCycleSupervisor("repo",self.queue,state_root=self.state,cycle_output_root=self.cycles,worker_factory=lambda resume:self.fail("worker launched"),replan_coordinator=lambda value:calls.append(value) or outcome)
    result=supervisor.run_once(); self.assertEqual(result.replan_result,outcome); self.assertEqual(len(calls),1); self.assertEqual(self.calls,[]); self.assertEqual((receipt.read_bytes(),receipt.stat().st_mtime_ns),before); persisted=json.loads(receipt.read_text()); self.assertEqual((persisted["status"],persisted["reason_code"]),("blocked","multi_cycle.child.blocked"))
    self.temp.cleanup(); self.setUp()
 def test_repeated_terminal_polling_delegates_idempotency_without_launch(self):
  self.replan_terminal(); calls=[]; outcome=RepositoryMultiCycleReplanCoordinatorResult("successor_ready","ready",1,"one","a"*40,None,"b"*64,"c"*64,0)
  supervisor=RepositoryMultiCycleSupervisor("repo",self.queue,state_root=self.state,cycle_output_root=self.cycles,worker_factory=lambda resume:self.fail("worker launched"),replan_coordinator=lambda value:calls.append(value) or outcome)
  first=supervisor.run_once(); second=supervisor.run_once(); self.assertEqual(first.replan_result,outcome); self.assertEqual(second.replan_result,outcome); self.assertEqual(len(calls),2); self.assertEqual(self.calls,[])
 def _auto_launch_supervisor(self, *, claim_status="launch_pending", execution_status="launched"):
  directory=self.replan_terminal(); successor=self.root/"replans"/"attempt-001"/"successor_queue.json"; successor.parent.mkdir(parents=True); successor.write_text(self.queue.read_text()); claim_path=successor.with_name("launch_claim.json")
  outcome=RepositoryMultiCycleReplanCoordinatorResult("successor_ready","ready",1,"one","a"*40,successor,"b"*64,"c"*64,1)
  claim=ReplanLaunchClaimResult(claim_status,"claim", "repo","c"*64,1,"d"*64,claim_path,successor,"b"*64,"a"*40)
  calls={"claim":[],"execution":[],"launch":[]}
  def claim_acquirer(value): calls["claim"].append(value); return claim
  def executor(value, *, worker_launcher):
   calls["execution"].append(value)
   if execution_status == "launched":
    worker=worker_launcher(WorkerLaunchRequest("repo","c"*64,1,"d"*64,"e"*64,"a"*40,successor,"b"*64))
    return ReplanLaunchExecutionResult("launched","launched","d"*64,"e"*64,successor.with_name("launch_execution.json"),successor,"b"*64,worker.worker_pid,worker.cycle_run_id,1)
   if execution_status == "already_launched":
    return ReplanLaunchExecutionResult("launched","launched","d"*64,"e"*64,successor.with_name("launch_execution.json"),successor,"b"*64,123,None,0)
   return ReplanLaunchExecutionResult(execution_status,"uncertain","d"*64,"e"*64,successor.with_name("launch_execution.json"),successor,"b"*64,None,None,0)
  supervisor=RepositoryMultiCycleSupervisor("repo",self.queue,state_root=self.state,cycle_output_root=self.cycles,worker_factory=lambda resume:calls["launch"].append(resume) or Worker(),replan_coordinator=lambda value:outcome,auto_replan_launch=True,replan_claim_acquirer=claim_acquirer,replan_launch_executor=executor)
  return directory,successor,supervisor,calls
 def test_auto_replan_launches_verified_successor_through_existing_helper(self):
  directory,successor,supervisor,calls=self._auto_launch_supervisor(); receipt=directory/"receipt.json"; before=receipt.read_bytes(); launches=[]; original=supervisor._launch
  def launch(resume, *, queue_spec_path=None): launches.append((resume,queue_spec_path)); return original(resume,queue_spec_path=queue_spec_path)
  supervisor._launch=launch; result=supervisor.run_once()
  self.assertEqual(result.status,"running"); self.assertEqual(len(calls["claim"]),1); self.assertEqual(len(calls["execution"]),1); self.assertEqual(calls["launch"],[None]); self.assertEqual(launches,[(None,successor)]); self.assertEqual(supervisor._worker.pid,123); self.assertEqual(receipt.read_bytes(),before)
 def test_auto_replan_same_event_or_durable_execution_never_launches_twice(self):
  _,_,supervisor,calls=self._auto_launch_supervisor(); self.assertEqual(supervisor.run_once().status,"running"); self.assertEqual(supervisor.run_once().status,"running"); self.assertEqual(calls["launch"],[None])
  self.temp.cleanup(); self.setUp(); _,_,supervisor,calls=self._auto_launch_supervisor(execution_status="already_launched"); self.assertEqual(supervisor.run_once().status,"idle"); self.assertEqual(calls["launch"],[])
  self.temp.cleanup(); self.setUp(); _,_,supervisor,calls=self._auto_launch_supervisor(execution_status="launching"); self.assertEqual(supervisor.run_once().status,"idle"); self.assertEqual(calls["launch"],[])
  self.temp.cleanup(); self.setUp(); _,_,supervisor,calls=self._auto_launch_supervisor(execution_status="launch_uncertain"); self.assertEqual(supervisor.run_once().status,"idle"); self.assertEqual(calls["launch"],[])
 def test_auto_replan_claim_or_execution_blocked_never_launches(self):
  _,_,supervisor,calls=self._auto_launch_supervisor(claim_status="blocked"); self.assertEqual(supervisor.run_once().status,"idle"); self.assertEqual(len(calls["execution"]),0); self.assertEqual(calls["launch"],[])
  self.temp.cleanup(); self.setUp(); _,_,supervisor,calls=self._auto_launch_supervisor(execution_status="blocked"); self.assertEqual(supervisor.run_once().status,"idle"); self.assertEqual(calls["launch"],[])
 def test_auto_replan_fake_launch_preserves_source_and_does_not_override_continuation(self):
  source=self.root/"source"; source.mkdir(); marker=source/"marker.txt"; marker.write_text("A"); before=marker.read_bytes(); _,_,supervisor,_=self._auto_launch_supervisor(); self.assertEqual(supervisor.run_once().status,"running"); self.assertEqual(marker.read_bytes(),before); self.assertEqual(supervisor.root_queue_spec_path,self.queue); self.assertNotIn("continuation",supervisor._launch_verified_successor_worker.__code__.co_names)
 def test_supervisor_has_no_direct_r6b_or_r3_dependency(self):
  import automation.orchestration.repository_multi_cycle_supervisor as module
  for name in ("run_codex","run_replan_planner","persist_replan_result"): self.assertFalse(hasattr(module,name))
 def test_active_and_finalizing_discovery_resume_and_ambiguous_blocks(self):
  self.checkpoint("cycle-00000000000000000001","active_task"); supervisor=self.make(); result=supervisor.run_once(); self.assertEqual(result.cycle_run_id,"cycle-00000000000000000001"); self.assertEqual(self.calls,["cycle-00000000000000000001"])
  self.temp.cleanup(); self.setUp(); self.checkpoint("cycle-00000000000000000001","finalizing"); supervisor=self.make(); self.assertEqual(supervisor.run_once().cycle_run_id,"cycle-00000000000000000001")
  self.temp.cleanup(); self.setUp(); self.checkpoint("cycle-00000000000000000001"); self.checkpoint("cycle-00000000000000000002"); self.assertEqual(self.make().run_once().reason_code,"supervisor.discovery.ambiguous_nonterminal"); self.assertEqual(self.calls,[])
 def test_crash_restart_is_bounded_and_shutdown_is_clean(self):
  self.checkpoint("cycle-00000000000000000001"); sleeps=[]; supervisor=self.make(lambda resume: Worker(9)); supervisor.sleep=sleeps.append; supervisor.max_crash_restarts=2; supervisor.poll_seconds=0; result=supervisor.run_forever(); self.assertEqual(result.reason_code,"supervisor.worker.restart_exhausted"); self.assertEqual(sleeps,[1,2]); idle=self.make(); idle.request_shutdown(); self.assertEqual(idle.run_forever().reason_code,"supervisor.shutdown")
 def test_shutdown_before_launch_boundary_creates_no_worker(self):
  supervisor=self.make(); supervisor.request_shutdown(); result=supervisor.run_once()
  self.assertEqual(result.reason_code,"supervisor.shutdown"); self.assertEqual(self.calls,[])
 def test_shutdown_wins_after_discovery_before_launch_boundary(self):
  supervisor=self.make(); original=supervisor._candidates; discovered=threading.Event(); proceed=threading.Event(); outcome=[]
  def candidates(queue_sha):
   value=original(queue_sha); discovered.set(); self.assertTrue(proceed.wait(1)); return value
  supervisor._candidates=candidates
  thread=threading.Thread(target=lambda:outcome.append(supervisor.run_once())); thread.start(); self.assertTrue(discovered.wait(1)); supervisor.request_shutdown(); proceed.set(); thread.join(1)
  self.assertFalse(thread.is_alive()); self.assertEqual(outcome[0].reason_code,"supervisor.shutdown"); self.assertEqual(self.calls,[])
 def test_launch_wins_boundary_before_shutdown_is_accepted(self):
  supervisor=self.make(); spawn_started=threading.Event(); allow_spawn_finish=threading.Event(); shutdown_attempted=threading.Event(); shutdown_accepted=threading.Event(); outcome=[]; worker_calls=[]
  class ObservedGate:
   def __init__(inner): inner.lock=threading.Lock()
   def __enter__(inner):
    if threading.current_thread().name != "repository-multi-cycle-launcher": shutdown_attempted.set()
    inner.lock.acquire(); return inner
   def __exit__(inner,*args): inner.lock.release()
  def factory(resume): worker_calls.append(resume); spawn_started.set(); self.assertTrue(allow_spawn_finish.wait(1)); return Worker()
  supervisor.worker_factory=factory; supervisor._launch_gate=ObservedGate()
  launch_thread=threading.Thread(target=lambda:outcome.append(supervisor.run_once())); launch_thread.start(); self.assertTrue(spawn_started.wait(1))
  def shutdown(): supervisor.request_shutdown(); shutdown_accepted.set()
  shutdown_thread=threading.Thread(target=shutdown); shutdown_thread.start(); self.assertTrue(shutdown_attempted.wait(1)); self.assertFalse(shutdown_accepted.is_set())
  allow_spawn_finish.set(); launch_thread.join(1); shutdown_thread.join(1)
  self.assertFalse(launch_thread.is_alive()); self.assertFalse(shutdown_thread.is_alive()); self.assertTrue(shutdown_accepted.is_set()); self.assertEqual(worker_calls,[None]); self.assertEqual(outcome[0].status,"running")
 def test_incomplete_child_resume_preserves_directory_and_sigterm_active_starts_no_second_worker(self):
  directory=self.checkpoint("cycle-00000000000000000001"); child=directory/"child"; child.mkdir(); supervisor=self.make(); self.assertEqual(supervisor.run_once().cycle_run_id,"cycle-00000000000000000001"); self.assertTrue(child.is_dir()); self.assertEqual(self.calls,["cycle-00000000000000000001"])
  self.temp.cleanup(); self.setUp(); self.checkpoint("cycle-00000000000000000001"); calls=[]; supervisor=self.make()
  class SignalWorker:
   pid=77
   def wait(inner): supervisor.request_shutdown(signal.SIGTERM,None); return 0
  supervisor.worker_factory=lambda resume: calls.append(resume) or SignalWorker(); self.assertEqual(supervisor.run_forever().reason_code,"supervisor.shutdown"); self.assertEqual(calls,["cycle-00000000000000000001"])
 def test_stdout_is_discarded_and_artifacts_are_authoritative(self):
  supervisor=RepositoryMultiCycleSupervisor("repo",self.queue,state_root=self.state,cycle_output_root=self.cycles)
  with patch("automation.orchestration.repository_multi_cycle_supervisor.subprocess.Popen") as popen:
   supervisor._launch(None); self.assertIs(popen.call_args.kwargs["stdout"],__import__("subprocess").DEVNULL); self.assertIs(popen.call_args.kwargs["stderr"],__import__("subprocess").DEVNULL)
  # A zero-exit worker which only claims success has no authority without artifacts.
  self.assertEqual(self.make(lambda resume: Worker(0)).run_forever().reason_code,"supervisor.worker.evidence_missing")
  # A corrupt receipt wins over the same non-authoritative zero exit.
  directory=self.terminal("cycle-00000000000000000008"); (directory/"receipt.sha256").write_text("0"*64+"  receipt.json\n"); self.assertEqual(self.make(lambda resume: Worker(0)).run_forever().reason_code,"supervisor.discovery.invalid")
  # A valid artifact suppresses a duplicate fresh worker regardless of worker output.
  self.temp.cleanup(); self.setUp(); self.terminal("cycle-00000000000000000008"); self.assertEqual(self.make().run_once().reason_code,"supervisor.queue.terminal_suppressed")
 def test_actual_executor_propagates_incomplete_child_without_reinvocation(self):
  fixture=ExecutorTests("test_real_git_chain_and_receipts"); fixture.setUp()
  try:
   run_id="cycle-20260811123456789071"; cycle=fixture.output/run_id; cycle.mkdir(parents=True); queue=__import__("automation.orchestration.repository_multi_cycle_task_spec",fromlist=["load_repository_multi_cycle_task_spec"]).load_repository_multi_cycle_task_spec(fixture.queue); task=queue.tasks[0]; _,spec_sha=_runtime_single_task_spec(task,fixture.a); child_id=_child_run_id(run_id,0,task.task_id); child_dir=fixture.base/"child"/child_id; child_dir.mkdir(parents=True)
   active={"task_index":0,"task_id":task.task_id,"expected_parent_sha":fixture.a,"child_run_id":child_id,"child_output_directory":str(child_dir),"child_receipt_path":str(child_dir/"receipt.json"),"task_spec_sha256":spec_sha}; write_checkpoint(cycle/"state",fixture._state(run_id,anchor=fixture.a,active=active)); selected=[]; observed=[]
   supervisor=RepositoryMultiCycleSupervisor("repo",fixture.queue,state_root=fixture.base/"supervisor",cycle_output_root=fixture.output,poll_seconds=0)
   class ResumeWorker:
    pid=991
    def wait(inner):
     observed.append(run_repository_multi_cycle("repo",fixture.queue,registry_path=fixture.registry,bindings_path=fixture.bindings,output_root=fixture.output,single_task_output_root=fixture.base/"child",resume_cycle_run_id=selected[-1])); supervisor.request_shutdown(); return 2
   supervisor.worker_factory=lambda resume:selected.append(resume) or ResumeWorker(); result=supervisor.run_forever(); actual=observed[0]
   self.assertEqual(result.reason_code,"supervisor.shutdown"); self.assertEqual(selected,[run_id]); self.assertEqual(actual.reason_code,"multi_cycle.resume.child_incomplete"); self.assertEqual(actual.status,"blocked"); self.assertTrue(child_dir.is_dir()); self.assertFalse((child_dir/"receipt.json").exists()); self.assertEqual(git(fixture.source,"rev-list","--all","--count").stdout.strip(),"1"); self.assertEqual(git(fixture.source,"rev-parse","HEAD").stdout.strip(),fixture.a); self.assertEqual(git(fixture.source,"status","--porcelain").stdout,"")
  finally: fixture.tearDown()
 def test_artifacts_do_not_persist_prompt_or_evaluator_envelope(self):
  supervisor=self.make(); supervisor.acquire_lock(); supervisor.release_lock(); text="\n".join(item.read_text(errors="ignore") for item in self.state.rglob("*") if item.is_file()); self.assertNotIn("SUPERVISOR_PROMPT_SENTINEL",text); self.assertNotIn("TASK_COMPLETION_EVALUATION_JSON_BEGIN",text)
 def test_supervisor_cli_forwards_optional_configuration_without_changing_defaults(self):
  cli=supervisor_cli_module(); calls=[]
  class FakeSupervisor:
   def __init__(inner,*args,**kwargs): calls.append((args,kwargs))
   def request_shutdown(inner,*args): pass
   def run_forever(inner): return SimpleNamespace(status="completed",reason_code="supervisor.shutdown",repository_id="repo",queue_sha256=None,cycle_run_id=None,crash_restart_count=0)
  with patch.object(cli,"RepositoryMultiCycleSupervisor",FakeSupervisor),patch.object(cli.signal,"signal"):
   with redirect_stdout(io.StringIO()): self.assertEqual(cli.main(["--repository-id","repo","--queue-spec","queue"]),0)
   with redirect_stdout(io.StringIO()): self.assertEqual(cli.main(["--repository-id","repo","--queue-spec","queue","--registry-path","/tmp/registry.json","--bindings-path","/tmp/bindings.json","--providers-path","/tmp/providers.yaml","--output-root","/tmp/cycles","--single-task-output-root","/tmp/children"]),0)
  self.assertNotIn("registry_path",calls[0][1]); self.assertNotIn("cycle_output_root",calls[0][1])
  self.assertEqual(calls[1][1]["registry_path"],"/tmp/registry.json"); self.assertEqual(calls[1][1]["bindings_path"],"/tmp/bindings.json"); self.assertEqual(calls[1][1]["providers_path"],"/tmp/providers.yaml"); self.assertEqual(calls[1][1]["cycle_output_root"],"/tmp/cycles"); self.assertEqual(calls[1][1]["single_task_output_root"],"/tmp/children")
 def test_worker_command_propagates_identical_custom_configuration_for_fresh_and_resume(self):
  supervisor=RepositoryMultiCycleSupervisor("repo",self.queue,state_root=self.state,cycle_output_root="/tmp/cycles",registry_path="/tmp/registry.json",bindings_path="/tmp/bindings.json",providers_path="/tmp/providers.yaml",single_task_output_root="/tmp/children")
  with patch("automation.orchestration.repository_multi_cycle_supervisor.subprocess.Popen") as popen:
   supervisor._launch(None); fresh=popopen= list(popen.call_args.args[0])
   supervisor._launch("cycle-20260811123456789012"); resumed=list(popen.call_args.args[0])
   supervisor._launch(None,terminal_resume_cycle_run_id="cycle-20260811123456789013"); terminal_resume=list(popen.call_args.args[0])
  for command in (fresh,resumed):
   for flag,value in (("--registry-path","/tmp/registry.json"),("--bindings-path","/tmp/bindings.json"),("--providers-path","/tmp/providers.yaml"),("--output-root","/tmp/cycles"),("--single-task-output-root","/tmp/children")):
    self.assertEqual(command[command.index(flag)+1],value)
  self.assertNotIn("--resume-cycle-run-id",fresh); self.assertEqual(resumed[resumed.index("--resume-cycle-run-id")+1],"cycle-20260811123456789012")
  self.assertEqual(terminal_resume[terminal_resume.index("--resume-terminal-cycle-run-id")+1],"cycle-20260811123456789013")
 def test_custom_cycle_output_root_controls_discovery_and_worker_command(self):
  default=self.root/"default-cycles"; custom=self.cycles; sha=hashlib.sha256(self.queue.read_bytes()).hexdigest()
  (default/"cycle-20260811123456789013").mkdir(parents=True)
  directory=custom/"cycle-20260811123456789014"; directory.mkdir(parents=True); write_checkpoint(directory/"state",{"cycle_run_id":directory.name,"repository_id":"repo","queue_spec_sha256":sha,"lifecycle_status":"active_task","terminal_status":None,"accepted_head_sha":"a"*40})
  calls=[]; supervisor=RepositoryMultiCycleSupervisor("repo",self.queue,state_root=self.state,cycle_output_root=custom,worker_factory=lambda resume:calls.append(resume) or Worker())
  self.assertEqual(supervisor.run_once().cycle_run_id,"cycle-20260811123456789014"); self.assertEqual(calls,["cycle-20260811123456789014"])
 def test_worker_cli_reaches_real_executor_with_isolated_configuration(self):
  fixture=ExecutorTests("test_real_git_chain_and_receipts"); fixture.setUp()
  try:
   run_id="cycle-20260811123456789072"; cycle=fixture.output/run_id; cycle.mkdir(parents=True)
   queue=__import__("automation.orchestration.repository_multi_cycle_task_spec",fromlist=["load_repository_multi_cycle_task_spec"]).load_repository_multi_cycle_task_spec(fixture.queue); task=queue.tasks[0]; _,spec_sha=_runtime_single_task_spec(task,fixture.a); child_id=_child_run_id(run_id,0,task.task_id); child_dir=fixture.base/"child"/child_id; child_dir.mkdir(parents=True)
   active={"task_index":0,"task_id":task.task_id,"expected_parent_sha":fixture.a,"child_run_id":child_id,"child_output_directory":str(child_dir),"child_receipt_path":str(child_dir/"receipt.json"),"task_spec_sha256":spec_sha}; write_checkpoint(cycle/"state",fixture._state(run_id,anchor=fixture.a,active=active))
   output=io.StringIO(); cli=worker_cli_module()
   with redirect_stdout(output): code=cli.main(["--repository-id","repo","--queue-spec",str(fixture.queue),"--resume-cycle-run-id",run_id,"--registry-path",str(fixture.registry),"--bindings-path",str(fixture.bindings),"--providers-path",str(Path("config/providers.yaml").resolve()),"--output-root",str(fixture.output),"--single-task-output-root",str(fixture.base/"child")])
   self.assertEqual(code,2); self.assertIn("reason_code=multi_cycle.resume.child_incomplete",output.getvalue()); self.assertTrue(child_dir.is_dir()); self.assertFalse((child_dir/"receipt.json").exists()); self.assertEqual(git(fixture.source,"rev-parse","HEAD").stdout.strip(),fixture.a); self.assertEqual(git(fixture.source,"status","--porcelain").stdout,"")
  finally: fixture.tearDown()

 def test_heartbeat_and_worker_exit_publish_terminal_status(self):
  supervisor=self.make(); snapshots=[]; writes=[]; original=supervisor._atomic_status
  supervisor._atomic_status=lambda value: writes.append(dict(value)) or original(value)
  class HeartbeatWorker:
   pid=456
   def poll(inner): return None
   def wait(inner): self.terminal("cycle-00000000000000000031"); return 0
  supervisor.worker_factory=lambda resume: HeartbeatWorker()
  def sleep(_):
   snapshots.append(json.loads((supervisor._directory/"status.json").read_text()))
   supervisor.request_shutdown()
  supervisor.sleep=sleep; supervisor.poll_seconds=0
  with patch("automation.orchestration.repository_multi_cycle_supervisor.time.time",side_effect=iter(range(100,120))): self.assertEqual(supervisor.run_forever().reason_code,"supervisor.shutdown")
  self.assertEqual(snapshots[-1]["state"],"worker_active"); self.assertTrue(snapshots[-1]["worker_alive"]); self.assertIn("last_heartbeat_at",snapshots[-1])
  active=[value for value in writes if value["state"]=="worker_active"]; self.assertGreater(active[-1]["updated_at"],active[0]["updated_at"])
  final=json.loads((supervisor._directory/"status.json").read_text())
  self.assertEqual(final["state"],"terminal"); self.assertEqual(final["terminal_status"],"completed"); self.assertFalse(final["worker_alive"])

 def test_read_only_observer_prefers_verified_terminal_and_reports_terminal_actions(self):
  directory=self.terminal("cycle-00000000000000000032","completed")
  status_dir=self.state/hashlib.sha256(b"repo").hexdigest(); status_dir.mkdir(parents=True); (status_dir/"status.json").write_text(json.dumps({"repository_id":"repo","state":"worker_active","worker_pid":999999,"cycle_run_id":directory.name}))
  completed=self.observe(); self.assertEqual(completed["state"],"terminal"); self.assertEqual(completed["terminal_status"],"completed"); self.assertFalse(completed["action_required"])
  self.temp.cleanup(); self.setUp(); self.terminal("cycle-00000000000000000033","blocked"); blocked=self.observe(); self.assertEqual(blocked["state"],"terminal"); self.assertTrue(blocked["action_required"])
  self.temp.cleanup(); self.setUp(); self.terminal("cycle-00000000000000000034","failed"); failed=self.observe(); self.assertEqual(failed["state"],"terminal"); self.assertTrue(failed["action_required"])

 def test_read_only_observer_reports_checkpoint_or_corruption_without_recovery(self):
  directory=self.cycles/"cycle-00000000000000000035"; directory.mkdir(parents=True); sha=hashlib.sha256(self.queue.read_bytes()).hexdigest()
  write_checkpoint(directory/"state",{"cycle_run_id":directory.name,"repository_id":"repo","queue_spec_sha256":sha,"lifecycle_status":"active_task","task_count":2,"completed_count":1,"active_task":{"task_index":1,"task_id":"two"},"source_anchor_sha":"a"*40,"accepted_head_sha":"b"*40,"updated_at":"2026-08-23T00:00:00Z"})
  status_dir=self.state/hashlib.sha256(b"repo").hexdigest(); status_dir.mkdir(parents=True); (status_dir/"status.json").write_text(json.dumps({"repository_id":"repo","state":"worker_active","worker_pid":456,"cycle_run_id":directory.name}))
  active=self.observe(lambda pid: pid==456); self.assertEqual(active["state"],"worker_active"); self.assertFalse(active["action_required"])
  (status_dir/"status.json").unlink()
  observed=self.observe(); self.assertEqual(observed["state"],"interrupted_or_stale"); self.assertTrue(observed["action_required"]); self.assertEqual(observed["current_task_index"],1); self.assertEqual(observed["current_task_id"],"two"); self.assertEqual(observed["phase"],"active_task")
  payload=directory/"state"/"checkpoint-000000.json"; sidecar=directory/"state"/"checkpoint-000000.sha256"; before=(payload.read_bytes(),sidecar.read_bytes(),payload.stat().st_mtime_ns,sidecar.stat().st_mtime_ns)
  self.assertEqual(self.observe()["state"],"interrupted_or_stale"); self.assertEqual(self.observe()["state"],"interrupted_or_stale"); after=(payload.read_bytes(),sidecar.read_bytes(),payload.stat().st_mtime_ns,sidecar.stat().st_mtime_ns); self.assertEqual(before,after)
  sidecar.write_text("0"*64+"  checkpoint-000000.json\n"); corrupt=self.observe(); self.assertEqual(corrupt["state"],"blocked_observation"); self.assertTrue(corrupt["action_required"])

 def test_status_cli_is_read_only_and_returns_zero_for_runtime_states(self):
  directory=self.terminal("cycle-00000000000000000036","failed"); state_dir=self.state/hashlib.sha256(b"repo").hexdigest(); state_dir.mkdir(parents=True); (state_dir/"status.json").write_text(json.dumps({"repository_id":"repo","state":"worker_active","worker_pid":999999,"cycle_run_id":directory.name}))
  files=[self.queue,directory/"receipt.json",directory/"receipt.sha256",state_dir/"status.json"]; before={path:(path.read_bytes(),path.stat().st_mtime_ns) for path in files}; cli=status_cli_module(); output=io.StringIO()
  with redirect_stdout(output),patch("automation.orchestration.repository_multi_cycle_status.subprocess",create=True) as subprocess_mock:
   self.assertEqual(cli.main(["--repository-id","repo","--queue-spec",str(self.queue),"--state-root",str(self.state),"--output-root",str(self.cycles)]),0)
   self.assertEqual(cli.main(["--repository-id","repo","--queue-spec",str(self.queue),"--state-root",str(self.state),"--output-root",str(self.cycles)]),0)
   subprocess_mock.assert_not_called()
  self.assertIn("state=terminal",output.getvalue()); self.assertIn("action_required=true",output.getvalue())
  self.assertEqual(before,{path:(path.read_bytes(),path.stat().st_mtime_ns) for path in files})
