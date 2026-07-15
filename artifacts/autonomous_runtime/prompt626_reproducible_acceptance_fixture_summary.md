# Prompt626 Reproducible Acceptance Fixture Summary

- prompt626_status: success
- base: 6cbafe3 (tag: prompt625-integrated-two-cycle-real-change-effect-verification — confirmed)
- new files: scripts/run_integrated_live_acceptance.py,
  tests/test_integrated_live_acceptance_fixture.py, docs/integrated_live_acceptance.md
- modified files: none (no existing source touched; default behavior trivially preserved)

## Acceptance script

scripts/run_integrated_live_acceptance.py recreates the Prompt625 proof from scratch:
fresh work dir with two sandbox repos (committed fixtures), per-cycle prompts + effect
specs + manifest, a clean dirty-gate repo, then one bounded autonomous live loop run
(max_cycles=2, verification-continue, workspace-write, per-cycle effect verification).
It validates effects in both repos, confirms no runtime commit/tag anywhere and that the
main repo's git status and HEAD are unchanged, and writes
<out-dir>/integrated_live_acceptance_report.json. Refuses --max-cycles < 2 (exit 2,
verified). Exit 0 = acceptance success, 1 = blocked.

## Live acceptance proof (first run, no retries)

- command: python scripts/run_integrated_live_acceptance.py --work-dir
  /tmp/prompt626_integrated_acceptance_work --out-dir /tmp/prompt626_integrated_acceptance_out
  --max-cycles 2 --max-seconds 300 --live-timeout-seconds 90 --json
- acceptance_status=success, process_returncode=0, failures=[]
- cycle_count=2, codex_invoked_count=2, commit_tag_gate_observed_count=2
- effect verification: passed / passed
- cycle1 subtract present, cycle2 multiply present, test files unchanged, no extra files
- runtime_commit_or_tag_performed=False, main_repo_source_modified=False

## Tests and docs

- 6 new unit tests (fixture creation, manifest/spec correctness, validator success and
  failure paths) — all pass via python -m unittest (pytest not installed here).
- 23/23 across all four live-loop/gate test modules.
- docs/integrated_live_acceptance.md documents purpose, limits, tokens, exact command,
  and expected success fields.

## Hygiene

- No commit/tag/stage/push/PR/merge. archive untouched. Dirty-artifact stash not needed.

## Decision

- prompt626_final_decision: success
- prompt626_next_action: commit_tag_reproducible_acceptance_fixture
