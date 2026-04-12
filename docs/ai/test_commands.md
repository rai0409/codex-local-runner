# Verification and Reset Levels

Use one of these levels before merge. Pick the smallest level that gives confidence for the scoped change.

## Level 1: Light Revalidation

Purpose:
- Fast confidence check for a small, localized change.

Typical steps:
- Review changed files: `git diff -- <changed files>`
- Run targeted tests only (repository pattern example): `python -m unittest tests/<target_file>.py -v`
- Capture exact commands and results in PR notes.

## Level 2: Intermediate Cleanup Revalidation

Purpose:
- Re-check behavior after clearing local caches/build remnants that may hide issues.

Typical steps:
- Run Level 1.
- Clear local cache/build state using repository-safe cleanup commands.
- Re-run a broader but still scoped test subset.

Repository-specific command placeholders (fill as needed):
- `<cache cleanup command(s) for this repo>`
- Current CI-enforced contract suite: `python -m unittest tests.test_execution_path tests.test_verify_runner tests.test_run_codex_contract tests.test_worktree -v`

## Level 3: Full Clean Rebuild/Revalidation

Purpose:
- Highest-confidence verification for risky or wide-impact changes.

Typical steps:
- Start from a clean environment/worktree.
- Reinstall/rebuild dependencies from repository instructions.
- Run full validation suite required by project policy.

Repository-specific command placeholders (fill as needed):
- `<clean environment bootstrap command(s)>`
- `python -m unittest tests.test_execution_path tests.test_verify_runner tests.test_run_codex_contract tests.test_worktree -v`

## Guardrails

- Do not use destructive cleanup commands on uncommitted work.
- Prefer explicit placeholders over guessed commands when repository-specific steps are unclear.
