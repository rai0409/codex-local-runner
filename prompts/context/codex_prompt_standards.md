# Codex Prompt Standards

Codex prompts should be concise but high-responsibility.

Default:
- Prefer one vertical slice over tiny metadata-only changes.
- Keep existing architecture and naming style.
- Do not add tests unless requested.
- Run:
  python -m py_compile automation/orchestration/planned_execution_runner.py
  python -m py_compile scripts/run_planned_execution.py
- Run one dry-run only when cheap and already normal.
- Return:
  - files changed
  - builders/functions added
  - key wiring locations
  - validation results
  - observed key values
  - confirmation of what was not added

For autonomous development MVP:
- Expose status and next_action in compact planning summary, supporting truth refs, and final approved restart payload normalized map.
- Preserve safe blocked defaults for external execution, git mutation, and artifact access.
