# Task Specs and Planning

## Task spec schema (v1)

A task spec is a JSON object (validated by
`automation/orchestration/planned_runner/task_spec.py`):

```json
{
  "task_id": "calc-subtract-1",
  "kind": "add_function",
  "repo_path": "/tmp/some_sandbox_repo",
  "target_file": "calculator.py",
  "function_name": "subtract",
  "expression": "a - b",
  "description": "optional human description",
  "expected_unmodified_files": ["test_calculator.py"],
  "verify_commands": [["python", "-c", "from calculator import subtract; assert subtract(7,4)==3"]],
  "allow_extra_files": false
}
```

Rules: `task_id` is a `[a-z0-9._-]` slug; `kind` must be `add_function` (the only planner v1
kind); `target_file` is repo-relative without `..`; `function_name` must be a Python
identifier; `verify_commands` are argv arrays (no shell) whose executables must be
`python`/`python3`/`pytest`, run with cwd = the task repo only.

## Planner

`automation/orchestration/planned_runner/task_planner.py::plan_task(spec, work_dir)` turns a
validated spec into:

- `<task_id>_prompt.md` — the generated Codex prompt,
- `<task_id>_effect_spec.json` — file effects + required text + verify commands,
- `<task_id>_manifest.json` — a single-cycle manifest for the autonomous live loop.

The planner is pure file generation (no Codex, no git). Effect verification then enforces at
runtime that exactly the planned change happened and the verify commands pass.

## Honest scope

Planner v1 handles deterministic single-function fixture tasks. It does not plan arbitrary
development work, multi-file changes, or multi-cycle strategies. Task specs with any other
`kind` are rejected at validation.
