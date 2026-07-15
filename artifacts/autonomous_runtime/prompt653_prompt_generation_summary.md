# Prompt653 Prompt-Generation — Live Auto-Execution Bridge

**Status:** success (prompt-generation only; no source modified, nothing staged/committed/tagged; archive & handoff_reports untouched)
**Base:** `650c2b7` (latest tagged impl: prompt651) · **Autonomy complete:** false
**Generated prompt:** `prompts/generated/prompt653_live_auto_execution_bridge.md`

## Inspection & base confirmation
HEAD `650c2b7` (clean source). Confirmed the bridge is genuinely missing —
`project_live_execution_bridge.py`, `tests/test_project_live_execution_bridge.py`,
`scripts/run_project_live_bridge.py`, `prompt653_report.json`, and tag
`prompt653-live-auto-execution-bridge` are all **absent**. Confirmed the building-block
APIs (generator / queue population / completion gate / loop controller) and the daemon
interface (`main(argv)->int`, writes `runs/<stem>/run_report.json` with a clean
`task_id`, live tokens, `--max-fix-attempts`).

## Target selected: `live_auto_execution_bridge`
The single critical gap that turns the proven OFFLINE chain into a real autonomous
loop: controller → populated queue → **bounded live daemon execution** → **REAL
run_reports** → completion gate → next project decision. Higher leverage than the
deferred task-kind expansion / soak.

## What the generated prompt mandates
- `run_project_live_execution_bridge(intent, descriptors, output_queue_dir, *,
  enable_live=False, enable_token="", expected_enable_token="I_UNDERSTAND_THIS_RUNS_LIVE_CODEX",
  max_project_cycles=1, max_daemon_jobs=1, max_fix_attempts=1, repo_path_override=None,
  dry_run=True, daemon_runner=None)` → structured result (status, live_execution_performed,
  plan/queue/daemon/completion results, project_complete, next_action). Never raises.
- **Dry-run by default**; **live path strictly gated** by `dry_run=False` + `enable_live=True`
  + matching token + explicit output dir + bounded positive caps (clamped to daemon caps).
  Any unmet condition → safe dry-run fallback with a deterministic warning.
- **Injectable daemon adapter** (real boundary isolated; **fake adapter in tests**);
  ingest REAL run_reports mapped by clean `task_id` into `evaluate_project_completion`;
  **failures never mark complete**; missing/unreadable reports → `unknown` → not complete.
- Bounded iterate (≤ max_project_cycles); no uncontrolled loop; deterministic dry-run.

## Hard boundaries encoded
No live daemon/Codex in tests; no live/default queue mutation; no strict-gate bypass;
no inventing success without real run_reports; no task-kind expansion; no soak; no
network/git beyond final commit/tag on all-PASS; additive only. Tests: dry-run default,
gating (enable/token/dir), fake-adapter success→complete, failure→not-complete,
unknown→partial, bounds, determinism, no side effects, existing suites green.

The generated prompt includes goal, current state, root gap, scope, the full function
signature + structured return, required behavior, integration boundary, required tests,
hard safety boundaries, report requirements, final stdout contract, decision rules,
commit/tag policy, and explicit out-of-scope.

**Next action:** `execute_prompt653_live_auto_execution_bridge`.
