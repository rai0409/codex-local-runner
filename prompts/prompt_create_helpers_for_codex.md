# prompts/prompt_create_helpers_for_codex.md

Use the standing baseline from:
- `prompts/base_contract_rules.md`
- `prompts/base_token_reduction_rules.md`

Implement a narrow deterministic helper PR for these files only:

- `scripts/prepare_git_workflow.py`
- `scripts/render_pr_text.py`
- `automation/orchestration/pr_text_templates.py`
- `automation/orchestration/git_workflow_templates.py`
- `automation/orchestration/approval_actor_policy.py`

This work must be additive-only, token-reduction oriented, and deterministic.

## Primary objective
Reduce repeated ChatGPT/Codex usage for:
- branch name generation
- commit message generation
- PR title/body rendering
- approval actor classification

These helpers must prefer config/template/rule behavior over prose generation.

## Dependencies / assumptions
Assume current or future presence of:
- `config/git_workflow_policy.yaml`
- `config/approval_commands.yaml`

Do not build a large framework.
Do not add broad external dependencies.

## Scope

### In scope
- deterministic template helpers
- deterministic branch/commit/PR rendering
- deterministic approval actor policy helper
- small local CLI scripts for operator use

### Out of scope
- GitHub API execution
- remote branch creation
- merging PRs
- approval reply ingestion
- email sending
- controller/scheduler redesign
- broad UX redesign

## File requirements

### 1. automation/orchestration/pr_text_templates.py
Implement deterministic helpers for PR text rendering.

Required public helpers:
- `render_pr_title(...)`
- `render_pr_summary_block(...)`
- `render_pr_validation_block(...)`
- `render_pr_scope_notes_block(...)`
- `render_pr_body(...)`

Requirements:
- compact output
- stable section order
- no free-form narrative generation
- predictable truncation if needed
- use `config/git_workflow_policy.yaml` where appropriate

### 2. automation/orchestration/git_workflow_templates.py
Implement deterministic helpers for local git workflow text generation.

Required public helpers:
- `normalize_branch_slug(...)`
- `render_branch_name(...)`
- `render_commit_subject(...)`
- `render_commit_message(...)`

Optional:
- compact cleanup-step helper if naturally useful

Requirements:
- deterministic branch naming
- deterministic commit subject generation
- subject-length guard
- stable normalization
- no timestamp/random suffix unless explicitly supplied

### 3. automation/orchestration/approval_actor_policy.py
Implement deterministic actor policy helper for approval flows.

Required responsibilities:
- derive expected actor class or conservative fallback actor class
- support compact actor classes:
  - `self`
  - `operator`
  - `reviewer`
  - `approver`
  - `admin`
  - `unknown`
- expose narrow helper(s) later approval response ingest can use

Requirements:
- deterministic mapping only
- no mailbox lookups
- no external identity service
- compact return shape

### 4. scripts/prepare_git_workflow.py
Implement a local CLI that outputs deterministic git workflow preparation data.

Suggested behavior:
- generate branch name
- generate commit subject
- print compact suggested commands
- optionally emit JSON

Requirements:
- local-only
- no network dependency
- read from config when available
- compact human and/or JSON output
- must not mutate the repo

### 5. scripts/render_pr_text.py
Implement a local CLI that renders PR title/body from compact inputs.

Suggested behavior:
- accept title context / summary context / validation notes / scope notes
- render compact PR title
- render compact PR body
- optionally emit JSON

Requirements:
- local-only
- no GitHub API calls
- deterministic output
- config/template driven
- must not mutate repo state

## Token-reduction rules
These implementations must reduce future LLM usage by:
- replacing repeated PR wording generation with templates
- replacing repeated branch/commit naming consultation with deterministic helpers
- replacing repeated actor-policy discussion with explicit mapping logic

Do not add prose-heavy generation logic.

## Required focused validation
If tests are added or updated, cover at minimum:
- stable branch rendering
- stable commit subject rendering
- stable PR title rendering
- stable PR body section ordering
- stable approval actor fallback / mapping
- compact output shape
- no mutation side effects in scripts

If there is no natural existing focused test file, add the smallest focused tests needed.
Avoid broad unrelated edits.

## Deliverable format
Return:
1. concise summary
2. exact files changed
3. public functions/CLI behavior added
4. validation notes
5. intentionally deferred items
