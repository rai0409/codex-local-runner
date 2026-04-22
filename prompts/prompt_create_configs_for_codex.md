# prompts/prompt_create_configs_for_codex.md

Use the standing baseline from:
- `prompts/base_contract_rules.md`
- `prompts/base_token_reduction_rules.md`

Implement a narrow config scaffolding PR that creates exactly these files:

- `config/approval_commands.yaml`
- `config/git_workflow_policy.yaml`

This work must be deterministic, additive-only, and compact.

## Scope

### In scope
- create `config/approval_commands.yaml`
- create `config/git_workflow_policy.yaml`
- keep both files compact, valid YAML, and immediately usable by future helpers

### Out of scope
- no controller/scheduler redesign
- no broad runtime integration
- no reply ingestion
- no Gmail send logic
- no helper script implementation
- no unrelated config churn

## File 1: config/approval_commands.yaml

Create a compact deterministic command policy for approval replies.

## Required top-level shape

```yaml
version: 1
normalization:
  case_insensitive: true
  trim_outer_whitespace: true
  collapse_internal_whitespace: true
  fuzzy_matching: false
commands:
  "OK RETRY": ...
  "OK REPLAN": ...
  "OK TRUTH": ...
  "OK CLOSE": ...
  "HOLD": ...
  "REJECT": ...
unsupported:
  decision_class: unsupported
  restart_posture: block_restart
```

## Required semantics

Supported commands must include:
- `OK RETRY`
- `OK REPLAN`
- `OK TRUTH`
- `OK CLOSE`
- `HOLD`
- `REJECT`

Each command entry must define compact stable keys for:
- `decision_class`
- `next_direction`
- `restart_posture`

Required command semantics:
- `OK RETRY`
  - approved
  - retry-oriented
- `OK REPLAN`
  - approved
  - `replan_preparation`
- `OK TRUTH`
  - approved
  - `truth_gathering`
- `OK CLOSE`
  - approved
  - `closure_followup`
- `HOLD`
  - held
  - held restart posture
- `REJECT`
  - rejected
  - blocked/manual-followup restart posture

Unsupported command handling must be explicit and conservative.

## File 2: config/git_workflow_policy.yaml

Create a compact deterministic git/PR workflow policy for local helper scripts.

## Required top-level shape

```yaml
version: 1
branch:
  prefixes: ...
  separator: ...
  max_length: ...
commit:
  subject:
    imperative: true
    max_length: ...
    allow_component_prefix: true
    trailing_period: false
pr:
  title:
    prefix_style: ...
    max_length: ...
  body:
    sections:
      - Summary
      - What changed
      - Validation
      - Scope notes
cleanup:
  sync_main_first: true
  delete_local_branch: true
  delete_remote_branch_optional: true
  fetch_prune_before_cleanup: true
```

## Required branch policy
Support deterministic prefixes such as:
- `pr`
- `fix`
- `ops`
- `runtime`
- `approval`

## Required commit policy
Define:
- short imperative subject line
- maximum subject length
- optional component prefix
- no trailing period

## Required PR policy
Define:
- compact prefix style
- title length guard
- ordered body sections:
  - Summary
  - What changed
  - Validation
  - Scope notes

## Required cleanup policy
Define:
- sync main first
- local branch deletion
- remote deletion optionality
- fetch/prune guidance

## Validation expectation
At minimum:
- both YAML files parse successfully
- key ordering/shape is deterministic
- no unrelated files changed

## Deliverable format
Return:
1. concise summary
2. exact files changed
3. final YAML key structure
4. validation notes
5. intentionally deferred items
