from __future__ import annotations
import hashlib, json, subprocess, sys, tempfile, unittest
from pathlib import Path
from automation.orchestration.repository_multi_cycle_task_executor import _child_run_id, _discover_verified_continuation_base, _runtime_single_task_spec, run_repository_multi_cycle
from automation.orchestration.repository_multi_cycle_state import load_latest_checkpoint, write_checkpoint
from automation.orchestration.repository_profile import APPROVAL_ACTIONS, FORBIDDEN_GIT_OPERATION_IDS
from automation.orchestration.repository_resolved_single_task_controller import run_repository_single_task

PYTHON=str(Path(sys.executable).resolve())
def git(root,*args): return subprocess.run(["git","-C",str(root),*args],text=True,capture_output=True,check=True)
class Adapter:
    name="codex_cli"
    def __init__(self): self.prompts=[]
    def execute_prepared_worktree(self,payload):
        prompt=payload["prompt"]; self.prompts.append(prompt); root=Path(payload["worktree_path"])
        target={"PROMPT_SECRET_ONE":"one.txt","two":"two.txt","three":"three.txt"}[prompt]
        prior={"two":"one.txt","three":"two.txt"}.get(prompt)
        if prior: assert (root/prior).is_file()
        (root/target).write_text(prompt+"\n",encoding="utf-8")
        return {"status":"completed","verify":{"status":"passed","reason":"validation_passed","safe_validation":{"status":"passed"}},"retry":{"attempted":False,"outcome":"not_attempted"}}
class FailingAdapter:
    name="codex_cli"
    def __init__(self): self.prompts=[]
    def execute_prepared_worktree(self,payload): self.prompts.append(payload["prompt"]); raise RuntimeError("execution failure")
class ScopeRecoveryAdapter:
    name="codex_cli"
    def __init__(self): self.prompts=[]; self.scope_repairs=0
    def execute_prepared_worktree(self,payload):
        prompt=payload["prompt"]; self.prompts.append(prompt); root=Path(payload["worktree_path"])
        if prompt=="PROMPT_SECRET_ONE":
            (root/"one.txt").write_text("one\n",encoding="utf-8")
            for path in ("tests/test_one.py","docs/recovery.md"):
                target=root/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_text("x\n",encoding="utf-8")
        elif prompt.startswith("Mode: Repair\nGoal: remove only runner-identified out-of-scope changes"):
            self.scope_repairs+=1; (root/"docs/recovery.md").unlink()
        elif prompt=="two":
            assert (root/"one.txt").is_file(); (root/"two.txt").write_text("two\n",encoding="utf-8")
        else: raise AssertionError(prompt)
        return {"status":"completed","verify":{"status":"passed","reason":"validation_passed","safe_validation":{"status":"passed"}},"retry":{"attempted":False,"outcome":"not_attempted"}}
class ExecutorTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(); self.base=Path(self.t.name); self.source=self.base/"source"; self.source.mkdir(); git(self.source,"init","-b","main"); git(self.source,"config","user.name","T"); git(self.source,"config","user.email","t@example.invalid"); (self.source/"base.txt").write_text("A\n"); git(self.source,"add","--","base.txt"); git(self.source,"commit","-m","A"); self.a=git(self.source,"rev-parse","HEAD").stdout.strip()
  commands=[{"command_id":kind,"kind":kind,"argv":[PYTHON,"-m","py_compile","base.txt"],"cwd":".","timeout_seconds":30,"required":True,"stop_on_failure":True} for kind in ("focused","related_regression","full","compile")]+[{"command_id":"diff","kind":"diff_check","argv":["git","diff","--check"],"cwd":".","timeout_seconds":30,"required":True,"stop_on_failure":True}]; profile={"schema_version":"1","profile_id":"repo","repository_root":str(self.source),"base_branch":"main","python_executable":PYTHON,"validation_commands":commands,"artifact_requirements":[],"forbidden_git_operations":list(FORBIDDEN_GIT_OPERATION_IDS),"max_changed_files":1,"approval_boundary":{x:"automatic" for x in APPROVAL_ACTIONS},"environment_allowlist":[]}; self.profile=self.base/"profile.json"; self.profile.write_text(json.dumps(profile)); self.registry=self.base/"repos.json"; self.registry.write_text(json.dumps({"version":1,"repos":[{"name":"repo","logical_role":"test"}]})); self.bindings=self.base/"bindings.json"; self.bindings.write_text(json.dumps({"version":1,"bindings":[{"repository_id":"repo","profile_path":str(self.profile)}]})); self.queue=self.base/"queue.json"; self.queue.write_text(json.dumps({"schema_version":"1","tasks":[{"task_id":"one","prompt":"PROMPT_SECRET_ONE","allowed_changed_paths":["one.txt"],"commit_message":"B"},{"task_id":"two","prompt":"two","allowed_changed_paths":["two.txt"],"commit_message":"C"},{"task_id":"three","prompt":"three","allowed_changed_paths":["three.txt"],"commit_message":"D"}]})); self.output=self.base/"out"
 def tearDown(self): self.t.cleanup()
 def evaluator(self,**kwargs):
  path=Path(kwargs["work_root"])/"x"; path.mkdir(parents=True); out=path/"out"; out.write_text('TASK_COMPLETION_EVALUATION_JSON_BEGIN\n{"status":"completed","reason_code":"done","satisfied_criteria":[],"unsatisfied_criteria":[],"evidence_refs":[]}\nTASK_COMPLETION_EVALUATION_JSON_END'); return {"status":"completed","stdout_path":str(out)}
 def blocked_evaluator(self,**kwargs):
  path=Path(kwargs["work_root"])/"blocked"; path.mkdir(parents=True); out=path/"out"; out.write_text('TASK_COMPLETION_EVALUATION_JSON_BEGIN\n{"status":"blocked","reason_code":"test.blocked","satisfied_criteria":[],"unsatisfied_criteria":["blocked"],"evidence_refs":[]}\nTASK_COMPLETION_EVALUATION_JSON_END'); return {"status":"completed","stdout_path":str(out)}
 def one_task_queue(self, task_id, prompt):
  path=self.base/f"queue-{task_id}.json"; path.write_text(json.dumps({"schema_version":"1","tasks":[{"task_id":task_id,"prompt":prompt,"allowed_changed_paths":[f"{task_id}.txt"],"commit_message":task_id.upper()}]})); return path
 def terminal_status(self, result, status):
  receipt=Path(result.receipt_path); value=json.loads(receipt.read_text()); value["status"]=status; value["reason_code"]=f"multi_cycle.child.{status}"; payload=json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(",",":")).encode(); receipt.write_bytes(payload); Path(result.receipt_sha256_path).write_text(f"{hashlib.sha256(payload).hexdigest()}  receipt.json\n")
 def test_real_git_chain_and_receipts(self):
  result=run_repository_multi_cycle("repo",self.queue,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:Adapter(),evaluator_runner=self.evaluator)
  self.assertEqual(result.status,"completed",result); self.assertEqual(result.completed_count,3); self.assertEqual(git(self.source,"rev-parse","HEAD").stdout.strip(),self.a)
  receipt=json.loads(Path(result.receipt_path).read_text()); commits=[x["commit_sha"] for x in receipt["executed_task_results"]]; self.assertEqual(git(self.source,"rev-parse",f"{commits[0]}^").stdout.strip(),self.a); self.assertEqual(git(self.source,"rev-parse",f"{commits[1]}^").stdout.strip(),commits[0]); self.assertEqual(git(self.source,"rev-parse",f"{commits[2]}^").stdout.strip(),commits[1]); self.assertEqual(result.accepted_head_sha,commits[2]); self.assertEqual(Path(result.receipt_sha256_path).read_text(),f"{hashlib.sha256(Path(result.receipt_path).read_bytes()).hexdigest()}  receipt.json\n")
  for item in receipt["executed_task_results"]:
   child=Path(item["child_receipt_path"]); child_value=json.loads(child.read_text()); self.assertEqual((child.parent/"receipt.sha256").read_text(),f"{hashlib.sha256(child.read_bytes()).hexdigest()}  receipt.json\n"); self.assertEqual(child_value["source_state_before"]["head_sha"],self.a); self.assertEqual(child_value["source_state_after"]["head_sha"],self.a)
  self.assertNotIn("PROMPT_SECRET_ONE",Path(result.receipt_path).read_text())
  persisted="\n".join(path.read_text(encoding="utf-8",errors="ignore") for path in (self.output/result.cycle_run_id).rglob("*") if path.is_file()); self.assertNotIn("PROMPT_SECRET_ONE",persisted); self.assertFalse(any(path.name.endswith(".runtime.json") for path in (self.output/result.cycle_run_id).rglob("*")))

 def test_recovered_task_is_accepted_and_next_task_continues(self):
  profile=json.loads(self.profile.read_text()); profile["max_changed_files"]=3; self.profile.write_text(json.dumps(profile))
  self.queue.write_text(json.dumps({"schema_version":"1","tasks":[
   {"task_id":"one","prompt":"PROMPT_SECRET_ONE","allowed_changed_paths":["one.txt","tests/test_existing.py"],"commit_message":"B"},
   {"task_id":"two","prompt":"two","allowed_changed_paths":["two.txt"],"commit_message":"C"},
  ]}))
  adapter=ScopeRecoveryAdapter()
  result=run_repository_multi_cycle("repo",self.queue,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:adapter,evaluator_runner=self.evaluator)
  self.assertEqual((result.status,result.completed_count),("completed",2)); self.assertEqual(adapter.scope_repairs,1)
  receipt=json.loads(Path(result.receipt_path).read_text()); first,second=receipt["executed_task_results"]
  first_child=json.loads(Path(first["child_receipt_path"]).read_text())
  self.assertEqual(first_child["scope_recovery_status"],"repair_succeeded")
  self.assertEqual(first_child["unresolved_unexpected_changed_files"],[])
  self.assertEqual(git(self.source,"rev-parse",f"{second['commit_sha']}^").stdout.strip(),first["commit_sha"])

 def test_cross_cycle_continuation_uses_real_git_chain_without_moving_source(self):
  q1=self.one_task_queue("one","PROMPT_SECRET_ONE"); q2=self.one_task_queue("two","two"); q3=self.one_task_queue("three","three")
  self.assertEqual(_discover_verified_continuation_base("repo",str(self.source),self.a,self.output),self.a)
  r1=run_repository_multi_cycle("repo",q1,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:Adapter(),evaluator_runner=self.evaluator); b=r1.accepted_head_sha; self.assertEqual(_discover_verified_continuation_base("repo",str(self.source),b,self.output),b)
  r2=run_repository_multi_cycle("repo",q2,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:Adapter(),evaluator_runner=self.evaluator); c=r2.accepted_head_sha
  r3=run_repository_multi_cycle("repo",q3,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:Adapter(),evaluator_runner=self.evaluator); d=r3.accepted_head_sha
  self.assertEqual(git(self.source,"rev-parse",f"{b}^").stdout.strip(),self.a); self.assertEqual(git(self.source,"rev-parse",f"{c}^").stdout.strip(),b); self.assertEqual(git(self.source,"rev-parse",f"{d}^").stdout.strip(),c)
  self.assertEqual(json.loads(Path(r2.receipt_path).read_text())["continuation_base_sha"],b); self.assertEqual(json.loads(Path(r3.receipt_path).read_text())["continuation_base_sha"],c); self.assertEqual(git(self.source,"rev-parse","HEAD").stdout.strip(),self.a); self.assertEqual(git(self.source,"status","--porcelain").stdout,"")

 def test_partial_terminal_and_resume_use_verified_continuation_base(self):
  q1=self.one_task_queue("one","PROMPT_SECRET_ONE"); q2=self.one_task_queue("two","two"); q3=self.one_task_queue("three","three"); first=run_repository_multi_cycle("repo",q1,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:Adapter(),evaluator_runner=self.evaluator); b=first.accepted_head_sha; self.terminal_status(first,"blocked")
  fresh=run_repository_multi_cycle("repo",q2,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:Adapter(),evaluator_runner=self.evaluator); c=fresh.accepted_head_sha; self.assertEqual(git(self.source,"rev-parse",f"{c}^").stdout.strip(),b)
  resumed_id="cycle-20260823000000000002"; directory=self.output/resumed_id; directory.mkdir(); state={"cycle_run_id":resumed_id,"repository_id":"repo","queue_spec_sha256":hashlib.sha256(q3.read_bytes()).hexdigest(),"registry_sha256":hashlib.sha256(self.registry.read_bytes()).hexdigest(),"bindings_sha256":hashlib.sha256(self.bindings.read_bytes()).hexdigest(),"providers_sha256":hashlib.sha256(Path("config/providers.yaml").read_bytes()).hexdigest(),"source_repository_root":str(self.source),"source_anchor_sha":self.a,"continuation_base_sha":c,"accepted_head_sha":c,"task_count":1,"next_task_index":0,"completed_task_results":[],"active_task":None,"terminal_task_result":None,"lifecycle_status":"accepted_task","terminal_status":None,"terminal_reason_code":None,"terminal_finished_at":None,"stopped_task_id":None,"started_at":"2026-08-23T00:00:00Z","updated_at":"2026-08-23T00:00:00Z"}; write_checkpoint(directory/"state",state)
  result=run_repository_multi_cycle("repo",q3,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:Adapter(),evaluator_runner=self.evaluator,resume_cycle_run_id=resumed_id); self.assertEqual(result.status,"completed"); self.assertEqual(git(self.source,"rev-parse",f"{result.accepted_head_sha}^").stdout.strip(),c); self.assertEqual(git(self.source,"rev-parse","HEAD").stdout.strip(),self.a)

 def test_terminal_prefixes_discover_and_reject_ambiguous_or_corrupt_evidence(self):
  q1=self.one_task_queue("one","PROMPT_SECRET_ONE"); first=run_repository_multi_cycle("repo",q1,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:Adapter(),evaluator_runner=self.evaluator); b=first.accepted_head_sha
  for status in ("blocked","failed"):
   self.terminal_status(first,status); self.assertEqual(_discover_verified_continuation_base("repo",str(self.source),self.a,self.output),b)
  value=json.loads(Path(first.receipt_path).read_text()); value["completed_count"]=0; value["executed_task_results"]=[]; value["final_accepted_head_sha"]=self.a; payload=json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(",",":")).encode(); Path(first.receipt_path).write_bytes(payload); Path(first.receipt_sha256_path).write_text(f"{hashlib.sha256(payload).hexdigest()}  receipt.json\n"); self.assertEqual(_discover_verified_continuation_base("repo",str(self.source),self.a,self.output),self.a)
  value["completed_count"]=1; value["executed_task_results"]=[{"task_id":"one","status":"completed","commit_sha":b,"parent_sha":self.a}]; value["final_accepted_head_sha"]=b; payload=json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(",",":")).encode(); Path(first.receipt_path).write_bytes(payload); Path(first.receipt_sha256_path).write_text(f"{hashlib.sha256(payload).hexdigest()}  receipt.json\n")
  duplicate=self.output/"cycle-20260823000000000000"; duplicate.mkdir(); same=dict(value); same["cycle_run_id"]=duplicate.name; payload=json.dumps(same,ensure_ascii=True,sort_keys=True,separators=(",",":")).encode(); (duplicate/"receipt.json").write_bytes(payload); (duplicate/"receipt.sha256").write_text(f"{hashlib.sha256(payload).hexdigest()}  receipt.json\n"); self.assertEqual(_discover_verified_continuation_base("repo",str(self.source),self.a,self.output),b)
  fork=self.output/"cycle-20260823000000000001"; fork.mkdir(); tree=git(self.source,"show","-s","--format=%T",b).stdout.strip(); x=subprocess.run(["git","-C",str(self.source),"commit-tree",tree,"-p",self.a],input="X\n",text=True,capture_output=True,check=True).stdout.strip(); other=dict(value); other["cycle_run_id"]=fork.name; other["final_accepted_head_sha"]=x; other["executed_task_results"]=[{"task_id":"other","status":"completed","commit_sha":x,"parent_sha":self.a}]; payload=json.dumps(other,ensure_ascii=True,sort_keys=True,separators=(",",":")).encode(); (fork/"receipt.json").write_bytes(payload); (fork/"receipt.sha256").write_text(f"{hashlib.sha256(payload).hexdigest()}  receipt.json\n")
  with self.assertRaisesRegex(ValueError,"multi_cycle.continuation.ambiguous"): _discover_verified_continuation_base("repo",str(self.source),self.a,self.output)
  (fork/"receipt.sha256").write_text("0"*64+"  receipt.json\n")
  with self.assertRaisesRegex(ValueError,"multi_cycle.continuation.evidence_invalid"): _discover_verified_continuation_base("repo",str(self.source),self.a,self.output)

 def _state(self, run_id, *, anchor, active, completed=None, accepted=None, **override):
  completed=[] if completed is None else completed
  values={"cycle_run_id":run_id,"repository_id":"repo","queue_spec_sha256":hashlib.sha256(self.queue.read_bytes()).hexdigest(),"registry_sha256":hashlib.sha256(self.registry.read_bytes()).hexdigest(),"bindings_sha256":hashlib.sha256(self.bindings.read_bytes()).hexdigest(),"providers_sha256":hashlib.sha256(Path("config/providers.yaml").read_bytes()).hexdigest(),"source_repository_root":str(self.source),"source_anchor_sha":anchor,"accepted_head_sha":accepted or anchor,"task_count":3,"next_task_index":len(completed),"completed_task_results":completed,"active_task":active,"lifecycle_status":"active_task" if active else "accepted_task","terminal_status":None,"terminal_reason_code":None,"started_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:00:00Z"}; values.update(override); return values

 def _completed_active_child(self, run_id):
  cycle=self.output/run_id; cycle.mkdir(parents=True); queue=__import__("automation.orchestration.repository_multi_cycle_task_spec",fromlist=["load_repository_multi_cycle_task_spec"]).load_repository_multi_cycle_task_spec(self.queue); task=queue.tasks[0]; spec,sha=_runtime_single_task_spec(task,self.a); child_id=_child_run_id(run_id,0,task.task_id); child_dir=self.base/"child"/child_id
  active={"task_index":0,"task_id":"one","expected_parent_sha":self.a,"child_run_id":child_id,"child_output_directory":str(child_dir),"child_receipt_path":str(child_dir/"receipt.json"),"task_spec_sha256":sha}; write_checkpoint(cycle/"state",self._state(run_id,anchor=self.a,active=active)); adapter=Adapter(); child=run_repository_single_task("repo",None,task_spec_override=spec,registry_path=self.registry,bindings_path=self.bindings,output_root=self.base/"child",adapter_resolver=lambda:adapter,evaluator_runner=self.evaluator,execution_base_sha=self.a,requested_run_id=child_id); self.assertEqual(child.status,"completed"); return queue,task,spec,sha,child_id,child_dir,adapter,child

 def _completed_cycle(self):
  adapter=Adapter(); result=run_repository_multi_cycle("repo",self.queue,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:adapter,evaluator_runner=self.evaluator); self.assertEqual(result.status,"completed"); directory=self.output/result.cycle_run_id; state,_=load_latest_checkpoint(directory/"state"); self.assertEqual(state["lifecycle_status"],"finalizing"); self.assertEqual(state["terminal_status"],"completed"); self.assertEqual(state["terminal_reason_code"],"multi_cycle.completed"); self.assertEqual(json.loads(Path(result.receipt_path).read_text())["finished_at"],state["terminal_finished_at"]); return result,directory,state,adapter

 def _resume_terminal(self, result, adapter):
  adapter.prompts.clear(); calls=[]
  resumed=run_repository_multi_cycle("repo",self.queue,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:adapter,evaluator_runner=self.evaluator,single_task_runner=lambda **kwargs:calls.append(kwargs),resume_cycle_run_id=result.cycle_run_id); self.assertEqual(calls,[]); self.assertEqual(adapter.prompts,[]); self.assertEqual(git(self.source,"rev-parse","HEAD").stdout.strip(),self.a); return resumed

 def _active_terminal_child(self, run_id, status):
  cycle=self.output/run_id; cycle.mkdir(parents=True); queue=__import__("automation.orchestration.repository_multi_cycle_task_spec",fromlist=["load_repository_multi_cycle_task_spec"]).load_repository_multi_cycle_task_spec(self.queue); task=queue.tasks[0]; spec,sha=_runtime_single_task_spec(task,self.a); child_id=_child_run_id(run_id,0,task.task_id); child_dir=self.base/"child"/child_id; active={"task_index":0,"task_id":"one","expected_parent_sha":self.a,"child_run_id":child_id,"child_output_directory":str(child_dir),"child_receipt_path":str(child_dir/"receipt.json"),"task_spec_sha256":sha}; write_checkpoint(cycle/"state",self._state(run_id,anchor=self.a,active=active)); adapter=Adapter() if status=="blocked" else FailingAdapter(); child=run_repository_single_task("repo",None,task_spec_override=spec,registry_path=self.registry,bindings_path=self.bindings,output_root=self.base/"child",adapter_resolver=lambda:adapter,evaluator_runner=self.blocked_evaluator if status=="blocked" else self.evaluator,execution_base_sha=self.a,requested_run_id=child_id); self.assertEqual(child.status,status); return adapter,child,cycle

 def test_blocked_and_failed_children_terminalize_through_finalizing_checkpoint(self):
  for status in ("blocked","failed"):
   with self.subTest(status=status):
    adapter=Adapter() if status=="blocked" else FailingAdapter(); result=run_repository_multi_cycle("repo",self.queue,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:adapter,evaluator_runner=self.blocked_evaluator if status=="blocked" else self.evaluator); self.assertEqual((result.status,result.reason_code),(status,f"multi_cycle.child.{status}")); self.assertEqual((result.completed_count,result.accepted_head_sha,result.stopped_task_id),(0,self.a,"one")); receipt=json.loads(Path(result.receipt_path).read_text()); self.assertEqual(receipt["executed_task_results"],[]); state,_=load_latest_checkpoint(self.output/result.cycle_run_id/"state"); self.assertEqual((state["lifecycle_status"],state["terminal_status"],state["terminal_reason_code"],state["stopped_task_id"]),("finalizing",status,f"multi_cycle.child.{status}","one")); self.assertEqual(state["terminal_task_result"]["status"],status); self.assertEqual(receipt["finished_at"],state["terminal_finished_at"]); self.assertEqual(git(self.source,"rev-parse","HEAD").stdout.strip(),self.a)

 def test_resume_adopts_blocked_and_failed_child_terminal_without_reinvocation(self):
  for number,status in enumerate(("blocked","failed")):
   with self.subTest(status=status):
    adapter,child,cycle=self._active_terminal_child(f"cycle-2026081112345678904{number}",status); adapter.prompts.clear(); calls=[]; result=run_repository_multi_cycle("repo",self.queue,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:adapter,evaluator_runner=self.blocked_evaluator if status=="blocked" else self.evaluator,single_task_runner=lambda **kwargs:calls.append(kwargs),resume_cycle_run_id=cycle.name); self.assertEqual((result.status,result.reason_code),(status,f"multi_cycle.child.{status}")); self.assertEqual((result.completed_count,result.accepted_head_sha),(0,self.a)); self.assertEqual(calls,[]); self.assertEqual(adapter.prompts,[]); state,_=load_latest_checkpoint(cycle/"state"); self.assertEqual(state["terminal_status"],status); self.assertTrue(Path(result.receipt_path).is_file())

 def test_resume_recovers_and_idempotently_reads_blocked_failed_finalizing_pairs(self):
  for number,status in enumerate(("blocked","failed")):
   with self.subTest(status=status):
    adapter=Adapter() if status=="blocked" else FailingAdapter(); result=run_repository_multi_cycle("repo",self.queue,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:adapter,evaluator_runner=self.blocked_evaluator if status=="blocked" else self.evaluator); directory=self.output/result.cycle_run_id; receipt,sidecar=directory/"receipt.json",directory/"receipt.sha256"; checkpoints=sorted((p.name,p.read_bytes()) for p in (directory/"state").iterdir()); receipt.unlink(); sidecar.unlink(); adapter.prompts.clear(); calls=[]; recovered=run_repository_multi_cycle("repo",self.queue,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:adapter,evaluator_runner=self.evaluator,single_task_runner=lambda **kwargs:calls.append(kwargs),resume_cycle_run_id=result.cycle_run_id); self.assertEqual(recovered.status,status); self.assertEqual(calls,[]); self.assertEqual(adapter.prompts,[]); payload,side=receipt.read_bytes(),sidecar.read_bytes(); again=run_repository_multi_cycle("repo",self.queue,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:adapter,evaluator_runner=self.evaluator,single_task_runner=lambda **kwargs:calls.append(kwargs),resume_cycle_run_id=result.cycle_run_id); self.assertEqual(again.status,status); self.assertEqual(receipt.read_bytes(),payload); self.assertEqual(sidecar.read_bytes(),side); self.assertEqual(sorted((p.name,p.read_bytes()) for p in (directory/"state").iterdir()),checkpoints)

 def test_resume_rejects_corrupt_terminal_child_evidence_without_overwrite(self):
  adapter,child,cycle=self._active_terminal_child("cycle-20260811123456789049","blocked"); adapter.prompts.clear(); calls=[]; first=run_repository_multi_cycle("repo",self.queue,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:adapter,evaluator_runner=self.blocked_evaluator,single_task_runner=lambda **kwargs:calls.append(kwargs),resume_cycle_run_id=cycle.name); self.assertEqual(first.status,"blocked"); child_sidecar=Path(child.receipt_sha256_path); child_sidecar.write_text("0"*64+"  receipt.json\n"); receipt,sidecar=Path(first.receipt_path),Path(first.receipt_sha256_path); receipt.unlink(); sidecar.unlink(); checkpoints=sorted((p.name,p.read_bytes()) for p in (cycle/"state").iterdir()); result=run_repository_multi_cycle("repo",self.queue,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:adapter,evaluator_runner=self.evaluator,single_task_runner=lambda **kwargs:calls.append(kwargs),resume_cycle_run_id=cycle.name); self.assertEqual((result.status,result.reason_code),("failed","multi_cycle.resume.terminal_child_invalid")); self.assertEqual(calls,[]); self.assertEqual(adapter.prompts,[]); self.assertEqual(child_sidecar.read_text(),"0"*64+"  receipt.json\n"); self.assertFalse(receipt.exists()); self.assertFalse(sidecar.exists()); self.assertEqual(sorted((p.name,p.read_bytes()) for p in (cycle/"state").iterdir()),checkpoints)

 def test_resume_completes_terminal_receipt_from_finalizing_checkpoint(self):
  result,directory,state,adapter=self._completed_cycle(); receipt=directory/"receipt.json"; sidecar=directory/"receipt.sha256"; checkpoints=sorted((p.name,p.read_bytes()) for p in (directory/"state").iterdir()); refs=git(self.source,"show-ref").stdout; receipt.unlink(); sidecar.unlink()
  resumed=self._resume_terminal(result,adapter); self.assertEqual((resumed.status,resumed.reason_code),("completed","multi_cycle.completed")); self.assertTrue(receipt.is_file()); self.assertTrue(sidecar.is_file()); self.assertEqual(json.loads(receipt.read_text())["finished_at"],state["terminal_finished_at"]); self.assertEqual(sorted((p.name,p.read_bytes()) for p in (directory/"state").iterdir()),checkpoints); self.assertEqual(git(self.source,"show-ref").stdout,refs)

 def test_resume_completes_missing_terminal_sidecar_without_rewriting_receipt(self):
  result,directory,_,adapter=self._completed_cycle(); receipt=directory/"receipt.json"; sidecar=directory/"receipt.sha256"; payload=receipt.read_bytes(); checkpoints=sorted((p.name,p.read_bytes()) for p in (directory/"state").iterdir()); sidecar.unlink()
  resumed=self._resume_terminal(result,adapter); self.assertEqual(resumed.status,"completed"); self.assertEqual(receipt.read_bytes(),payload); self.assertEqual(sidecar.read_text(),f"{hashlib.sha256(payload).hexdigest()}  receipt.json\n"); self.assertEqual(sorted((p.name,p.read_bytes()) for p in (directory/"state").iterdir()),checkpoints)

 def test_resume_completes_missing_terminal_receipt_from_valid_sidecar(self):
  result,directory,_,adapter=self._completed_cycle(); receipt=directory/"receipt.json"; sidecar=directory/"receipt.sha256"; payload,side=receipt.read_bytes(),sidecar.read_bytes(); checkpoints=sorted((p.name,p.read_bytes()) for p in (directory/"state").iterdir()); receipt.unlink()
  resumed=self._resume_terminal(result,adapter); self.assertEqual(resumed.status,"completed"); self.assertEqual(receipt.read_bytes(),payload); self.assertEqual(sidecar.read_bytes(),side); self.assertEqual(sorted((p.name,p.read_bytes()) for p in (directory/"state").iterdir()),checkpoints)

 def test_resume_valid_terminal_cycle_is_idempotent(self):
  result,directory,_,adapter=self._completed_cycle(); receipt=directory/"receipt.json"; sidecar=directory/"receipt.sha256"; payload,side=receipt.read_bytes(),sidecar.read_bytes(); checkpoints=sorted((p.name,p.read_bytes()) for p in (directory/"state").iterdir()); refs=git(self.source,"show-ref").stdout
  resumed=self._resume_terminal(result,adapter); self.assertEqual((resumed.status,resumed.finished_at),("completed",result.finished_at)); self.assertEqual(receipt.read_bytes(),payload); self.assertEqual(sidecar.read_bytes(),side); self.assertEqual(sorted((p.name,p.read_bytes()) for p in (directory/"state").iterdir()),checkpoints); self.assertEqual(git(self.source,"show-ref").stdout,refs)

 def test_resume_rejects_corrupt_terminal_receipt_without_overwrite(self):
  result,directory,_,adapter=self._completed_cycle(); receipt=directory/"receipt.json"; sidecar=directory/"receipt.sha256"; value=json.loads(receipt.read_text()); value["reason_code"]="corrupt"; corrupt=json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(",",":")).encode(); receipt.write_bytes(corrupt); side=sidecar.read_bytes(); checkpoints=sorted((p.name,p.read_bytes()) for p in (directory/"state").iterdir())
  resumed=self._resume_terminal(result,adapter); self.assertEqual((resumed.status,resumed.reason_code),("failed","multi_cycle.resume.terminal_receipt_invalid")); self.assertEqual(receipt.read_bytes(),corrupt); self.assertEqual(sidecar.read_bytes(),side); self.assertEqual(sorted((p.name,p.read_bytes()) for p in (directory/"state").iterdir()),checkpoints)

 def test_resume_rejects_terminal_sidecar_mismatch_without_overwrite(self):
  result,directory,_,adapter=self._completed_cycle(); receipt=directory/"receipt.json"; sidecar=directory/"receipt.sha256"; payload=receipt.read_bytes(); wrong=("0"*64+"  receipt.json\n").encode(); sidecar.write_bytes(wrong); checkpoints=sorted((p.name,p.read_bytes()) for p in (directory/"state").iterdir())
  resumed=self._resume_terminal(result,adapter); self.assertEqual((resumed.status,resumed.reason_code),("failed","multi_cycle.resume.terminal_receipt_invalid")); self.assertEqual(receipt.read_bytes(),payload); self.assertEqual(sidecar.read_bytes(),wrong); self.assertEqual(sorted((p.name,p.read_bytes()) for p in (directory/"state").iterdir()),checkpoints)

 def test_resume_rejects_invalid_finalizing_state_before_child_execution(self):
  run_id="cycle-20260811123456789031"; directory=self.output/run_id; directory.mkdir(parents=True); values=self._state(run_id,anchor=self.a,active=None,completed=[],accepted=self.a,lifecycle_status="finalizing",terminal_status=None,terminal_reason_code=None,terminal_finished_at=None); write_checkpoint(directory/"state",values); adapter=Adapter(); calls=[]
  result=run_repository_multi_cycle("repo",self.queue,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:adapter,evaluator_runner=self.evaluator,single_task_runner=lambda **kwargs:calls.append(kwargs),resume_cycle_run_id=run_id); self.assertEqual((result.status,result.reason_code),("failed","multi_cycle.resume.finalizing_state_invalid")); self.assertEqual(calls,[]); self.assertEqual(adapter.prompts,[]); self.assertFalse((directory/"receipt.json").exists()); self.assertFalse((directory/"receipt.sha256").exists())

 def test_resume_adopts_completed_child_without_reinvocation_and_continues_real_git_chain(self):
  run_id="cycle-20260811123456789012"; cycle=self.output/run_id; cycle.mkdir(parents=True)
  queue=__import__("automation.orchestration.repository_multi_cycle_task_spec",fromlist=["load_repository_multi_cycle_task_spec"]).load_repository_multi_cycle_task_spec(self.queue)
  first=queue.tasks[0]; spec,sha=_runtime_single_task_spec(first,self.a); child_id=_child_run_id(run_id,0,first.task_id); child_dir=self.base/"child"/child_id
  active={"task_index":0,"task_id":"one","expected_parent_sha":self.a,"child_run_id":child_id,"child_output_directory":str(child_dir),"child_receipt_path":str(child_dir/"receipt.json"),"task_spec_sha256":sha}
  write_checkpoint(cycle/"state",self._state(run_id,anchor=self.a,active=active))
  adapter=Adapter(); child=run_repository_single_task("repo",None,task_spec_override=spec,registry_path=self.registry,bindings_path=self.bindings,output_root=self.base/"child",adapter_resolver=lambda:adapter,evaluator_runner=self.evaluator,execution_base_sha=self.a,requested_run_id=child_id)
  self.assertEqual(child.status,"completed"); b=child.commit_sha; self.assertEqual(git(self.source,"rev-parse",f"{b}^").stdout.strip(),self.a)
  adapter.prompts.clear(); calls=[]
  def runner(**kwargs): calls.append(kwargs["task_spec_override"].task_id); return run_repository_single_task(**kwargs)
  result=run_repository_multi_cycle("repo",self.queue,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:adapter,evaluator_runner=self.evaluator,single_task_runner=runner,resume_cycle_run_id=run_id)
  self.assertEqual(result.status,"completed",result); self.assertEqual(calls,["two","three"]); self.assertEqual(adapter.prompts,["two","three"])
  receipt=json.loads(Path(result.receipt_path).read_text()); commits=[x["commit_sha"] for x in receipt["executed_task_results"]]; self.assertEqual(commits[0],b); self.assertEqual(git(self.source,"rev-parse",f"{commits[1]}^").stdout.strip(),b); self.assertEqual(git(self.source,"rev-parse",f"{commits[2]}^").stdout.strip(),commits[1]); self.assertEqual(git(self.source,"rev-list","--all","--count", "--", "one.txt").stdout.strip(),"1"); self.assertEqual(git(self.source,"rev-parse","HEAD").stdout.strip(),self.a)

 def test_resume_rejects_child_receipt_sha_mismatch_without_reinvocation(self):
  run_id="cycle-20260811123456789021"; _,_,_,_,_,child_dir,adapter,child=self._completed_active_child(run_id); b=child.commit_sha; self.assertEqual(git(self.source,"rev-parse",f"{b}^").stdout.strip(),self.a); sidecar=child_dir/"receipt.sha256"; before=sidecar.read_text(); sidecar.write_text("0"*64+"  receipt.json\n"); adapter.prompts.clear(); calls=[]
  result=run_repository_multi_cycle("repo",self.queue,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:adapter,evaluator_runner=self.evaluator,single_task_runner=lambda **kwargs:calls.append(kwargs),resume_cycle_run_id=run_id)
  self.assertEqual(result.status,"failed"); self.assertEqual(result.reason_code,"multi_cycle.child.acceptance_invalid"); self.assertEqual(result.completed_count,0); self.assertEqual(result.accepted_head_sha,self.a); self.assertEqual(calls,[]); self.assertEqual(adapter.prompts,[]); self.assertEqual(sidecar.read_text(),"0"*64+"  receipt.json\n"); self.assertNotEqual(sidecar.read_text(),before); self.assertEqual(git(self.source,"rev-parse","HEAD").stdout.strip(),self.a); self.assertEqual(git(self.source,"cat-file","-e",f"{b}^{{commit}}").returncode,0)

 def test_resume_rejects_actual_child_parent_mismatch_without_reinvocation(self):
  run_id="cycle-20260811123456789022"; _,_,_,_,_,child_dir,adapter,child=self._completed_active_child(run_id); tree=git(self.source,"show","-s","--format=%T",child.commit_sha).stdout.strip()
  def commit(parent,message): return subprocess.run(["git","-C",str(self.source),"commit-tree",tree,"-p",parent],input=message+"\n",text=True,capture_output=True,check=True).stdout.strip()
  intermediate=commit(self.a,"X"); wrong=commit(intermediate,"W"); self.assertNotEqual(intermediate,self.a); self.assertEqual(git(self.source,"rev-parse",f"{wrong}^").stdout.strip(),intermediate)
  receipt=child_dir/"receipt.json"; value=json.loads(receipt.read_text()); value["commit_sha"]=wrong; value["commit_parent_sha"]=self.a; payload=json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(",",":")).encode(); receipt.write_bytes(payload); (child_dir/"receipt.sha256").write_text(f"{hashlib.sha256(payload).hexdigest()}  receipt.json\n"); adapter.prompts.clear(); calls=[]
  result=run_repository_multi_cycle("repo",self.queue,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:adapter,evaluator_runner=self.evaluator,single_task_runner=lambda **kwargs:calls.append(kwargs),resume_cycle_run_id=run_id)
  self.assertEqual(result.status,"failed"); self.assertEqual(result.reason_code,"multi_cycle.child.acceptance_invalid"); self.assertEqual(result.completed_count,0); self.assertEqual(result.accepted_head_sha,self.a); self.assertEqual(calls,[]); self.assertEqual(adapter.prompts,[]); self.assertEqual(git(self.source,"rev-parse","HEAD").stdout.strip(),self.a)

 def test_resume_from_accepted_checkpoint_skips_completed_task(self):
  run_id="cycle-20260811123456789023"; queue,task,_,_,_,_,adapter,child=self._completed_active_child(run_id); b=child.commit_sha; cycle=self.output/run_id; item={"task_id":"one","status":"completed","reason_code":child.reason_code,"commit_sha":b,"parent_sha":self.a,"worktree_preserved":False,"child_receipt_path":child.receipt_path}; write_checkpoint(cycle/"state",self._state(run_id,anchor=self.a,active=None,completed=[item],accepted=b)); adapter.prompts.clear(); calls=[]
  def runner(**kwargs): calls.append(kwargs["task_spec_override"].task_id); return run_repository_single_task(**kwargs)
  result=run_repository_multi_cycle("repo",self.queue,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:adapter,evaluator_runner=self.evaluator,single_task_runner=runner,resume_cycle_run_id=run_id); self.assertEqual(result.status,"completed"); self.assertEqual(calls,["two","three"]); self.assertEqual(adapter.prompts,["two","three"]); receipt=json.loads(Path(result.receipt_path).read_text()); commits=[item["commit_sha"] for item in receipt["executed_task_results"]]; self.assertEqual(commits[0],b); self.assertEqual(git(self.source,"rev-parse",f"{commits[1]}^").stdout.strip(),b); self.assertEqual(git(self.source,"rev-parse",f"{commits[2]}^").stdout.strip(),commits[1]); self.assertEqual(git(self.source,"rev-list","--all","--count","--","one.txt").stdout.strip(),"1"); self.assertEqual(git(self.source,"rev-parse","HEAD").stdout.strip(),self.a)

 def test_completed_child_with_invalid_receipt_does_not_increment_completed_count(self):
  adapter=Adapter(); calls=[]
  def runner(**kwargs):
   calls.append(kwargs["task_spec_override"].task_id); result=run_repository_single_task(**kwargs); self.assertEqual(result.status,"completed"); Path(result.receipt_sha256_path).write_text("0"*64+"  receipt.json\n"); return result
  result=run_repository_multi_cycle("repo",self.queue,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:adapter,evaluator_runner=self.evaluator,single_task_runner=runner); self.assertEqual(result.status,"failed"); self.assertEqual(result.reason_code,"multi_cycle.child.acceptance_invalid"); self.assertEqual(result.completed_count,0); self.assertEqual(result.accepted_head_sha,self.a); self.assertEqual(calls,["one"]); self.assertEqual(adapter.prompts,["PROMPT_SECRET_ONE"]); receipt=json.loads(Path(result.receipt_path).read_text()); self.assertEqual(receipt["completed_count"],0); self.assertEqual(receipt["executed_task_results"],[]); self.assertEqual(git(self.source,"rev-parse","HEAD").stdout.strip(),self.a)

 def test_resume_input_mismatches_do_not_invoke_child(self):
  cases=(("queue_spec_sha256","multi_cycle.resume.queue_mismatch"),("registry_sha256","multi_cycle.resume.registry_mismatch"),("bindings_sha256","multi_cycle.resume.bindings_mismatch"),("providers_sha256","multi_cycle.resume.providers_mismatch"),("source_repository_root","multi_cycle.resume.repository_root_mismatch"),("source_anchor_sha","multi_cycle.resume.source_anchor_mismatch"))
  for number,(field,reason) in enumerate(cases):
   with self.subTest(field=field):
    run_id=f"cycle-202608111234567890{number:02d}"; directory=self.output/run_id; directory.mkdir(parents=True)
    values=self._state(run_id,anchor=self.a,active=None); values[field]="0"*64 if field.endswith("sha") else "/different"; write_checkpoint(directory/"state",values); calls=[]
    result=run_repository_multi_cycle("repo",self.queue,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",single_task_runner=lambda **kwargs:calls.append(kwargs),resume_cycle_run_id=run_id)
    self.assertEqual(result.reason_code,reason); self.assertEqual(calls,[])

 def test_child_id_accepts_legal_task_ids_and_incomplete_child_is_not_reinvoked(self):
  for task_id in ("task.with_dot","task_with_underscore","a"*64): self.assertRegex(_child_run_id("cycle-20260811123456789012",0,task_id),r"^run-[a-z0-9-]{1,80}$")
  run_id="cycle-20260811123456789019"; directory=self.output/run_id; directory.mkdir(parents=True); queue=__import__("automation.orchestration.repository_multi_cycle_task_spec",fromlist=["load_repository_multi_cycle_task_spec"]).load_repository_multi_cycle_task_spec(self.queue); task=queue.tasks[0]; _,sha=_runtime_single_task_spec(task,self.a); child_id=_child_run_id(run_id,0,task.task_id); child_dir=self.base/"child"/child_id; child_dir.mkdir(parents=True); active={"task_index":0,"task_id":"one","expected_parent_sha":self.a,"child_run_id":child_id,"child_output_directory":str(child_dir),"child_receipt_path":str(child_dir/"receipt.json"),"task_spec_sha256":sha}; write_checkpoint(directory/"state",self._state(run_id,anchor=self.a,active=active)); calls=[]
  result=run_repository_multi_cycle("repo",self.queue,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",single_task_runner=lambda **kwargs:calls.append(kwargs),resume_cycle_run_id=run_id); self.assertEqual(result.reason_code,"multi_cycle.resume.child_incomplete"); self.assertEqual(calls,[])
