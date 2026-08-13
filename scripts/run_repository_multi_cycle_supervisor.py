"""CLI boundary for the local multi-cycle supervisor."""
from __future__ import annotations
import argparse, signal, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from automation.orchestration.repository_multi_cycle_supervisor import RepositoryMultiCycleSupervisor

def main(argv: list[str] | None=None) -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--repository-id",required=True); parser.add_argument("--queue-spec",required=True); parser.add_argument("--poll-seconds",type=float,default=1.0); parser.add_argument("--max-crash-restarts",type=int,default=3); parser.add_argument("--max-backoff-seconds",type=float,default=30.0); parser.add_argument("--registry-path"); parser.add_argument("--bindings-path"); parser.add_argument("--providers-path"); parser.add_argument("--output-root"); parser.add_argument("--single-task-output-root")
    args=parser.parse_args(argv); kwargs={"poll_seconds":args.poll_seconds,"max_crash_restarts":args.max_crash_restarts,"max_backoff_seconds":args.max_backoff_seconds}
    for argument,keyword in (("registry_path","registry_path"),("bindings_path","bindings_path"),("providers_path","providers_path"),("output_root","cycle_output_root"),("single_task_output_root","single_task_output_root")):
        if getattr(args,argument) is not None: kwargs[keyword]=getattr(args,argument)
    supervisor=RepositoryMultiCycleSupervisor(args.repository_id,args.queue_spec,**kwargs)
    signal.signal(signal.SIGTERM,supervisor.request_shutdown); signal.signal(signal.SIGINT,supervisor.request_shutdown); result=supervisor.run_forever()
    for key in ("status","reason_code","repository_id","queue_sha256","cycle_run_id","crash_restart_count"): print(f"{key}={getattr(result,key) or ''}")
    print("READY_REPOSITORY_MULTI_CYCLE_SUPERVISOR" if result.status=="completed" else "BLOCKED_REPOSITORY_MULTI_CYCLE_SUPERVISOR")
    return 0 if result.status in {"completed","idle"} else 2
if __name__=="__main__": raise SystemExit(main())
