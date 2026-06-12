# Local Task-Queue Daemon Candidate

`scripts/run_task_queue_daemon.py` is a **bounded foreground daemon candidate**: it consumes
task specs from a queue directory, plans them, runs the effect-verified autonomous live loop
per task, optionally performs a sandbox-only gated commit/tag, and persists run reports,
JSONL logs, daemon state, and a pidfile lock.

It is **not** a production daemon and **not** commercial-grade: no detach/systemd, no
scheduler, single supported task kind (`add_function`), sandbox repos only for commits.

## Queue layout

```
<queue-dir>/
  pending/   # task spec JSON files waiting (consumed oldest-first)
  running/   # the task currently being processed
  done/      # succeeded tasks
  failed/    # failed tasks (including recovery-exhausted ones)
  daemon.lock
```

Enqueue with `automation.orchestration.planned_runner.daemon_queue.enqueue_task(queue_dir, spec)`
or by writing `<task_id>.json` into `pending/`. See `docs/task_queue_daemon.md` for the task
spec schema.

## Running

```bash
python scripts/run_task_queue_daemon.py \
  --queue-dir /tmp/q --runs-dir /tmp/runs --work-dir /tmp/work \
  --max-jobs 1 --max-seconds-total 600 --max-cycles 1 --live-timeout-seconds 90 \
  --autonomous-enable-token LOCAL_AUTONOMOUS_RUNTIME_ENABLE \
  --live-codex-enable-token LOCAL_LIVE_CODEX_GATE_ENABLE \
  [--sandbox-commit-tag --commit-tag-enable-token ENABLE_SANDBOX_COMMIT_TAG_EXECUTION] \
  [--recover-only] [--json]
```

Bounds are hard-capped (`max-jobs` ≤ 5, `max-seconds-total` ≤ 1800, `max-cycles` ≤ 2); there
is no unbounded mode. Exit 0 = all processed jobs succeeded; 1 = a job failed or the lock is
held; 2 = bad usage.

## Safety properties

- Pidfile lock: a second daemon refuses to start while a live process holds the lock; a lock
  left by a dead pid is recovered as stale.
- Crash recovery: tasks found in `running/` at startup are requeued to `pending/` with a
  `_recovery_attempts` counter; tasks exceeding the recovery budget move to `failed/` with
  `_recovery_exhausted` (see `--recover-only` for recovery without processing).
- Per task: explicit enable tokens, effect-spec + test-command verification, failure digest
  on any failure, and commit/tag only via the sandbox-only gate (`/tmp` repos, allowlisted
  files, unique tags). Pushing, PRs, merging, and main-repo commits are impossible by
  construction in this path.

## End-to-end acceptance

```bash
python scripts/run_daemon_candidate_acceptance.py --json
```

Creates a fresh sandbox calculator repo, enqueues one `add_function` task, runs the daemon
bounded (one live Codex invocation), and validates: queue transitions, the real sandbox
change, effect + test verification, sandbox commit+tag, lock release, log/state persistence,
and main-repo non-mutation. Exit 0 on success.
