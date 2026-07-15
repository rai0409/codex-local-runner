# Prompt637 Sandbox Generated Artifact Cleanup Policy Summary

- prompt637_status: success
- base: c2bf9bb (tag: prompt636-verify-command-tests), HEAD unchanged
- new module: automation/orchestration/planned_runner/sandbox_cleanup.py
- modified: scripts/run_task_queue_daemon.py, scripts/run_daemon_candidate_acceptance.py

## What changed

- cleanup_generated_python_artifacts(): removes ONLY __pycache__/ dirs, *.pyc, *.pyo inside a
  /tmp sandbox repo. Path safety: resolves real paths first; refuses empty path, '/', non-/tmp
  paths, the main repo (and ancestors/descendants), missing dirs, and /tmp symlinks that
  escape to the main repo. Never follows symlinks; never touches .py/.json/.md/.txt sources.
- Daemon task flow order is now: codex -> effect verification -> verify commands ->
  **cleanup generated artifacts** -> sandbox commit/tag -> **final clean check** -> report.
  A sandbox left dirty after commit/tag fails the task (not hidden).
- Acceptance independently re-verifies: git status --short must be empty, no leftover
  __pycache__/*.pyc/*.pyo may exist, and the run report must record a clean final status.
  New fields: sandbox_final_status_clean/short, sandbox_untracked_after_cleanup,
  sandbox_generated_artifacts_removed, sandbox_generated_artifact_paths_removed.

## Live proof

python scripts/run_daemon_candidate_acceptance.py --work-dir
/tmp/prompt637_daemon_candidate_cleanup_check --json ->
acceptance_status=success, codex_invoked_count=1, effects passed, verify commands used,
sandbox commit+tag performed, sandbox_generated_artifacts_removed=1 (__pycache__/),
sandbox_final_status_clean=true, sandbox_final_status_short=[],
direct `git -C .../sandbox_repo status --short` printed nothing,
find for __pycache__/*.pyc/*.pyo found 0 entries.
Main repo: status md5 identical before/after; no commit/tag/stage.

## Tests

34/34 via python -m unittest (9 new cleanup tests + 4 new acceptance-cleanliness tests +
existing daemon/commit-tag suites).

## Decision

- prompt637_final_decision: success
- prompt637_next_action: commit_tag_sandbox_generated_artifact_cleanup_policy
