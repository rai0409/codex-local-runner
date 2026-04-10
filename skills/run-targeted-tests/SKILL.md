# run-targeted-tests

Run only targeted verification commands required for the current change.

## Rules
- Prefer lightweight parse/import/CLI checks.
- Verify new artifacts under `tasks/`.
- Confirm the existing Flask entry path remains importable.
