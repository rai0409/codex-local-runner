from __future__ import annotations
import hashlib, json, subprocess, sys, tempfile, unittest
from pathlib import Path
from automation.orchestration.repository_multi_cycle_task_executor import run_repository_multi_cycle
from automation.orchestration.repository_profile import APPROVAL_ACTIONS, FORBIDDEN_GIT_OPERATION_IDS

PYTHON=str(Path(sys.executable).resolve())
def git(root,*args): return subprocess.run(["git","-C",str(root),*args],text=True,capture_output=True,check=True)
class Adapter:
    name="codex_cli"
    def execute_prepared_worktree(self,payload):
        prompt=payload["prompt"]; root=Path(payload["worktree_path"])
        target={"PROMPT_SECRET_ONE":"one.txt","two":"two.txt","three":"three.txt"}[prompt]
        prior={"two":"one.txt","three":"two.txt"}.get(prompt)
        if prior: assert (root/prior).is_file()
        (root/target).write_text(prompt+"\n",encoding="utf-8")
        return {"status":"completed","verify":{"status":"passed","reason":"validation_passed","safe_validation":{"status":"passed"}},"retry":{"attempted":False,"outcome":"not_attempted"}}
class ExecutorTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(); self.base=Path(self.t.name); self.source=self.base/"source"; self.source.mkdir(); git(self.source,"init","-b","main"); git(self.source,"config","user.name","T"); git(self.source,"config","user.email","t@example.invalid"); (self.source/"base.txt").write_text("A\n"); git(self.source,"add","--","base.txt"); git(self.source,"commit","-m","A"); self.a=git(self.source,"rev-parse","HEAD").stdout.strip()
  commands=[{"command_id":kind,"kind":kind,"argv":[PYTHON,"-m","py_compile","base.txt"],"cwd":".","timeout_seconds":30,"required":True,"stop_on_failure":True} for kind in ("focused","related_regression","full","compile")]+[{"command_id":"diff","kind":"diff_check","argv":["git","diff","--check"],"cwd":".","timeout_seconds":30,"required":True,"stop_on_failure":True}]; profile={"schema_version":"1","profile_id":"repo","repository_root":str(self.source),"base_branch":"main","python_executable":PYTHON,"validation_commands":commands,"artifact_requirements":[],"forbidden_git_operations":list(FORBIDDEN_GIT_OPERATION_IDS),"max_changed_files":1,"approval_boundary":{x:"automatic" for x in APPROVAL_ACTIONS},"environment_allowlist":[]}; self.profile=self.base/"profile.json"; self.profile.write_text(json.dumps(profile)); self.registry=self.base/"repos.json"; self.registry.write_text(json.dumps({"version":1,"repos":[{"name":"repo","logical_role":"test"}]})); self.bindings=self.base/"bindings.json"; self.bindings.write_text(json.dumps({"version":1,"bindings":[{"repository_id":"repo","profile_path":str(self.profile)}]})); self.queue=self.base/"queue.json"; self.queue.write_text(json.dumps({"schema_version":"1","tasks":[{"task_id":"one","prompt":"PROMPT_SECRET_ONE","allowed_changed_paths":["one.txt"],"commit_message":"B"},{"task_id":"two","prompt":"two","allowed_changed_paths":["two.txt"],"commit_message":"C"},{"task_id":"three","prompt":"three","allowed_changed_paths":["three.txt"],"commit_message":"D"}]})); self.output=self.base/"out"
 def tearDown(self): self.t.cleanup()
 def evaluator(self,**kwargs):
  path=Path(kwargs["work_root"])/"x"; path.mkdir(parents=True); out=path/"out"; out.write_text('TASK_COMPLETION_EVALUATION_JSON_BEGIN\n{"status":"completed","reason_code":"done","satisfied_criteria":[],"unsatisfied_criteria":[],"evidence_refs":[]}\nTASK_COMPLETION_EVALUATION_JSON_END'); return {"status":"completed","stdout_path":str(out)}
 def test_real_git_chain_and_receipts(self):
  result=run_repository_multi_cycle("repo",self.queue,registry_path=self.registry,bindings_path=self.bindings,output_root=self.output,single_task_output_root=self.base/"child",adapter_resolver=lambda:Adapter(),evaluator_runner=self.evaluator)
  self.assertEqual(result.status,"completed",result); self.assertEqual(result.completed_count,3); self.assertEqual(git(self.source,"rev-parse","HEAD").stdout.strip(),self.a)
  receipt=json.loads(Path(result.receipt_path).read_text()); commits=[x["commit_sha"] for x in receipt["executed_task_results"]]; self.assertEqual(git(self.source,"rev-parse",f"{commits[0]}^").stdout.strip(),self.a); self.assertEqual(git(self.source,"rev-parse",f"{commits[1]}^").stdout.strip(),commits[0]); self.assertEqual(git(self.source,"rev-parse",f"{commits[2]}^").stdout.strip(),commits[1]); self.assertEqual(result.accepted_head_sha,commits[2]); self.assertEqual(Path(result.receipt_sha256_path).read_text(),f"{hashlib.sha256(Path(result.receipt_path).read_bytes()).hexdigest()}  receipt.json\n")
  for item in receipt["executed_task_results"]:
   child=Path(item["child_receipt_path"]); child_value=json.loads(child.read_text()); self.assertEqual((child.parent/"receipt.sha256").read_text(),f"{hashlib.sha256(child.read_bytes()).hexdigest()}  receipt.json\n"); self.assertEqual(child_value["source_state_before"]["head_sha"],self.a); self.assertEqual(child_value["source_state_after"]["head_sha"],self.a)
  self.assertNotIn("PROMPT_SECRET_ONE",Path(result.receipt_path).read_text())
