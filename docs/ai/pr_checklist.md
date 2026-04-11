# PR Merge Checklist

## Scope and File Hygiene

- Only intended files are changed.
- Out-of-scope edits are removed.
- No generated artifacts are committed.
- No `__pycache__/` directories are committed.
- No `*.pyc` files are committed.
- No stray logs, temp files, or build outputs are committed.

## Validation Evidence

- Required tests were run.
- Exact test commands are recorded.
- Results are recorded (pass/fail/skip and relevant notes).

## PR Description Quality

PR text includes:
- summary
- why
- scope
- validation
- non-goals / not included

## Final Pre-Merge Check

- `git status --short` is clean except intended tracked changes.
- Diff review confirms no hidden process/runtime drift.
