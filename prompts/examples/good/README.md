# Good Examples Asset Contract

This directory preserves reusable historical prompt assets.

## Asset roles

- Source prompt: standalone prompt text used to run or scope a task.
- Run record: implementation/result record for a run.
- Reference patch: preserved patch artifact for comparison/reference.

## Placement

- Source prompts: `prompts/examples/good/*prompt*.md`
- Run records: `prompts/examples/good/*run-record.md`
- Reference patches: `prompts/examples/good/artifacts/*-reference.patch`

## Manifest

Use `prompts/examples/index.json` as the role map for each preserved example:

- `source_prompt_path`
- `run_record_path`
- `reference_patch_path`
- `asset_status` (`complete` or `partial`)

## Notes

- Legacy preserved prompt names such as `prompt7a_*.md` are kept for compatibility with existing run-record references.
- These assets are metadata/reference material only. They are not runtime execution authority.
