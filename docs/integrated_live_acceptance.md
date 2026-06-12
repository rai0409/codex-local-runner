# Integrated Live Acceptance Fixture

`scripts/run_integrated_live_acceptance.py` recreates the Prompt625 integrated proof from
scratch as a reproducible acceptance command. It is the canonical way to confirm that the
local autonomous live execution path still works end to end after changes.

## What it proves

One bounded run demonstrates, together:

1. **True two-cycle live execution** — the autonomous live loop runs two cycles
   (`cycle_count=2`), each with a real `codex exec` invocation (`codex_invoked_count=2`).
2. **Real code modification in isolated sandbox repos** — cycle 1 adds `subtract(a, b)` to
   one scratch repo, cycle 2 adds `multiply(a, b)` to a second scratch repo.
3. **Effect-based verification** — each cycle passes an effect spec (expected modified /
   unmodified files, required text, no extra files); success is never inferred from
   returncode or Codex stdout alone.
4. **Verification-only continuation** — the loop observes `commit_tag_gate` per cycle and
   continues without committing or tagging (`--live-loop-verification-continue`).
5. **Runtime non-mutation** — no commit/tag/stage/push/PR/merge anywhere; the main repo's
   `git status` and `HEAD` are compared before and after the run and must be identical.

## What it does NOT prove

- It does not exercise arbitrary, production-grade development tasks. The fixture tasks are
  small, deterministic calculator edits chosen so effects can be verified exactly.
- It does not prove failure recovery (targeted-fix loops), long-running operation, daemon
  operation, or commit/tag automation.
- It does not sandbox Codex beyond `--sandbox workspace-write` with the sandbox repo as the
  working directory; the main-repo guarantee comes from before/after status comparison and
  the effect specs, not OS-level isolation of the main repo.
- A passing run requires the Codex CLI to be installed, authenticated, and able to reach its
  model provider.

## Required tokens

The run is gated by the existing explicit-intent tokens, passed automatically by the script:

- `--autonomous-enable-token LOCAL_AUTONOMOUS_RUNTIME_ENABLE`
- `--live-codex-enable-token LOCAL_LIVE_CODEX_GATE_ENABLE`

## How to run

```bash
python scripts/run_integrated_live_acceptance.py \
  --work-dir /tmp/codex-local-runner-acceptance \
  --out-dir /tmp/codex-local-runner-acceptance-out \
  --max-cycles 2 \
  --max-seconds 300 \
  --live-timeout-seconds 90 \
  --json
```

All flags are optional; the defaults shown above are used when omitted. `--max-cycles` below
2 is refused (exit code 2) because the integrated proof requires two cycles. The work dir
and out dir are recreated from scratch on every run and must be outside the main repo.

Exit code: `0` on acceptance success, `1` on a blocked/failed acceptance, `2` on bad usage.

## Expected success fields

The machine-readable report is written to `<out-dir>/integrated_live_acceptance_report.json`:

- `acceptance_status = "success"`
- `process_returncode = 0`
- `cycle_count = 2`
- `codex_invoked_count = 2`
- `commit_tag_gate_observed_count = 2`
- `effect_verification_cycle1_status = "passed"`
- `effect_verification_cycle2_status = "passed"`
- `cycle1_subtract_present = true`, `cycle2_multiply_present = true`
- `cycle1_test_file_unchanged = true`, `cycle2_test_file_unchanged = true`
- `cycle1_no_extra_files = true`, `cycle2_no_extra_files = true`
- `runtime_commit_or_tag_performed = false`
- `main_repo_source_modified = false`
- `failures = []`

Raw loop output and per-cycle gate artifacts are kept under `<out-dir>` (including
`autonomous_live_loop_state.json`, `loop_stdout.txt`, `loop_stderr.txt`, and
`cycle_*/live_codex_gate/*`).

## Implementation notes

- The loop-level dirty-worktree guard is pointed at a dedicated clean scratch repo created
  inside the work dir, because the main repo may legitimately carry uncommitted work while
  acceptance runs. The main-repo non-mutation guarantee is enforced separately by the
  script's before/after `git status` + `HEAD` comparison.
- Unit tests for the fixture and validator (no Codex required):
  `python -m unittest tests.test_integrated_live_acceptance_fixture`
