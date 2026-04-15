# Archive Index Schema

## Purpose
This document explains the intended shape of `prompts/archive/index.json`.

The archive index is a lightweight registry of archive bundles.

---

## Top-level shape

```json
{
  "repo": "codex-local-runner",
  "version": 1,
  "bundles": []
}
Fields
repo: repository name
version: schema version
bundles: list of archive bundle entries
Bundle entry shape
{
  "bundle_id": "2026-04-14_prompt7c",
  "archive_path": "prompts/archive/2026-04-14_prompt7c",
  "prompt_source_path": "prompts/archive/2026-04-14_prompt7c/prompt.md",
  "run_record_path": "prompts/examples/good/2026-04-7c-mode-visibility-run-record.md",
  "decision": "pass",
  "task_type": "inspect_read_only_extension",
  "status": "completed",
  "notes": [
    "mode_visibility remained inspect-only",
    "no runtime progression introduced"
  ]
}
Required fields
bundle_id

Unique identifier for the bundle directory.

archive_path

Relative path to the bundle directory.

prompt_source_path

Relative path to the archive prompt reference.

decision

Expected values:

pass
revise
rollback
discard
task_type

Short classification of the task.

status

Expected values:

completed
in_progress
archived
Optional fields
run_record_path

Relative path to the corresponding run-record file.

notes

Short list of important observations.

Possible future optional fields
score
files_changed
branch
commit
reviewer_notes

These should only be added when usage becomes stable.

Design rules
keep the index lightweight
prefer stable paths over verbose summaries
do not duplicate full evaluation text here
do not store large diffs here
use archive bundle files as the detailed source
Current repository posture

This index is metadata for review-control-plane assets.

It does not:

trigger execution
authorize merges
replace archive bundles
replace run-record files
