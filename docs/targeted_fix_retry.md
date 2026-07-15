# Targeted-Fix Retry

When an effect-verified live Codex gate run fails, the failure is classified into a
structured digest (`failure_digest.json`, see
`automation/orchestration/planned_runner/failure_digest.py`). For retryable classes
(`effect_verification_failed`, `codex_execution_failed`, `codex_timeout`,
`targeted_fix_required`), `automation/orchestration/planned_runner/targeted_fix_retry.py`
builds a corrective prompt from the digest + effect spec
(`fix_prompt_builder.write_fix_prompt`) and re-runs the gate — bounded by
`max_fix_attempts` (default 1, hard cap 2). Non-retryable failures stop immediately with the
digest's recommended action.

The fix prompt contains: the failure evidence (class, stop reason, verification errors), the
target repo, the exact required effects (files, verbatim required text, forbidden paths),
the original prompt for context, and fixed constraints (no commit/tag/push/new files/outside
edits). The retry never commits or tags.

## Live acceptance

```bash
python scripts/run_targeted_fix_acceptance.py --json
```

Induces a guaranteed first failure (the original prompt forbids changes while the spec
requires `subtract`), then proves digest → fix prompt → one bounded fix attempt → effect
verification passed. Validates the sandbox repo, bounds, and main-repo non-mutation.
Exit 0 on success.

## Limits

- Convergence is only proven for small fixture-grade tasks; complex failures may not
  converge within the cap and will stop with `max_fix_attempts_reached`.
- The retry re-runs the whole gate; it does not do incremental patching.
