# Task Sizing Rules

Codex should not be asked to "do everything" in one run. Oversized runs increase context bloat, diff size, and correction loops.

## Working Definitions

- `Scout`: inspect code, tests, and behavior; report findings only.
- `Implement`: deliver one scoped change.
- `Repair`: fix one known bug/regression with focused validation.
- `Polish`: refine non-functional quality without changing behavior.

Run only one mode per Codex task.

## Split Triggers

Split the task immediately if any of these are true:
- too many files are in scope
- research and implementation are mixed
- bugfix and redesign are mixed
- multiple success criteria are bundled
- too many test domains are required in one prompt
- prompt asks to include full logs/artifacts inline
- request includes "while you're here" extras

## Tasks That Are Too Large

- "Read the repo, redesign orchestration, implement worktree flow, and update tests/docs."
- "Fix current bug and also refactor adapters and improve CLI UX."
- "Implement feature, run all tests, and summarize every log artifact."

## Correctly Split Examples

1. `Scout`: inspect current worktree behavior and list concrete risks only.
2. `Implement`: update `adapters/codex_cli.py` for one approved behavior change.
3. `Repair`: fix one failing test and verify with targeted unittest command.
4. `Polish`: update docs/checklists only, no runtime code edits.

## Default Rule

- Use `1 task = 1 major deliverable`.
- If the task cannot be described in one sentence with one success condition, split it.
