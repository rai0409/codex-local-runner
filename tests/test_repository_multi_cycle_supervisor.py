from __future__ import annotations
import hashlib, importlib.util, io, json, signal, tempfile, threading, unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from automation.orchestration.repository_multi_cycle_state import write_checkpoint
from automation.orchestration.repository_multi_cycle_supervisor import RepositoryMultiCycleSupervisor
from automation.orchestration.repository_multi_cycle_task_executor import _child_run_id, _runtime_single_task_spec, run_repository_multi_cycle
from tests.test_repository_multi_cycle_task_executor import ExecutorTests, git

def supervisor_cli_module():
 spec=importlib.util.spec_from_file_location("supervisor_cli",Path(__file__).resolve().parents[1]/"scripts/run_repository_multi_cycle_supervisor.py"); value=importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value

def worker_cli_module():
 spec=importlib.util.spec_from_file_location("worker_cli",Path(__file__).resolve().parents[1]/"scripts/run_repository_multi_cycle.py"); value=importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value

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
  for command in (fresh,resumed):
   for flag,value in (("--registry-path","/tmp/registry.json"),("--bindings-path","/tmp/bindings.json"),("--providers-path","/tmp/providers.yaml"),("--output-root","/tmp/cycles"),("--single-task-output-root","/tmp/children")):
    self.assertEqual(command[command.index(flag)+1],value)
  self.assertNotIn("--resume-cycle-run-id",fresh); self.assertEqual(resumed[resumed.index("--resume-cycle-run-id")+1],"cycle-20260811123456789012")
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
