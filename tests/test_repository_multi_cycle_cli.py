from __future__ import annotations
import importlib.util, io, unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock
from automation.orchestration.repository_multi_cycle_task_executor import RepositoryMultiCycleRunResult
def module():
 spec=importlib.util.spec_from_file_location("multi_cli",Path(__file__).resolve().parents[1]/"scripts/run_repository_multi_cycle.py"); value=importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value
def result(status): return RepositoryMultiCycleRunResult("1","r",status,"reason","repo","/r","/s","a"*40,"b"*40,1,None,"start","finish")
class CliTests(unittest.TestCase):
 def test_contract(self):
  cli=module(); self.assertEqual({x for a in cli._parser()._actions for x in a.option_strings}-{ "-h","--help"},{"--repository-id","--queue-spec","--resume-cycle-run-id"})
  for status,code,marker in (("completed",0,"READY_FOR_MULTI_CYCLE_REVIEW"),("blocked",2,"BLOCKED_REPOSITORY_MULTI_CYCLE"),("failed",1,"FAILED_REPOSITORY_MULTI_CYCLE")):
   with self.subTest(status=status),mock.patch.object(cli,"run_repository_multi_cycle",return_value=result(status)):
    output=io.StringIO()
    with redirect_stdout(output): self.assertEqual(cli.main(["--repository-id","repo","--queue-spec","queue"]),code)
    self.assertEqual(output.getvalue().splitlines()[-1],marker)
    self.assertEqual({line.split("=",1)[0] for line in output.getvalue().splitlines()[:-1]},{"status","reason_code","receipt_path","repository_id","source_anchor_sha","accepted_head_sha","completed_count","stopped_task_id"})
