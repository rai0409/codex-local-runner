You are working inside the repository `rai0409/codex-local-runner`.

Read the repository first. Before proposing changes, you must prove repository reading by listing:
- exact files inspected
- why each file was inspected
- what reusable prompt assets already exist
- which prompt assets are examples versus reusable building blocks
- which review/policy vocabulary is now canonical versus compatibility-only

Mode:
Implement

Primary goal:
Create a lightweight prompt-building foundation so strict Codex prompts no longer need to be written from scratch each time.

This PR is only about prompt planning and prompt assembly.

Strict non-goals:
- no execution runtime
- no orchestration pipeline
- no GitHub automation
- no new plugin system
- no dynamic rule engine
- no external templating engine unless the repo already uses one and reuse is strictly better than plain markdown assembly
- no speculative template families for workflows not already grounded in the repo
- no schema redesign for execution or policy artifacts
- no expansion of inspect-only visibility fields into execution or policy authority

Repository-grounded constraints you must preserve:
- prompt/archive/example assets are reusable metadata/assets, not execution authority
- repo profile and hard constraints must remain conservative
- prompt output should reinforce narrow diffs, file boundaries, validation commands, and proof-of-reading
- example assets should remain reusable without turning into a hidden control plane
- deterministic policy vocabulary introduced in review artifacts must not be weakened or replaced
- prompt assets must not re-canonicalize legacy compatibility fields as primary vocabulary

Canonical review/policy vocabulary to prefer:
- `recovery_decision`
- `failure_codes`
- `decision_basis`

Compatibility-only vocabulary:
- `recommended_action`
- `policy_reasons`

Rules for vocabulary handling:
- new prompt-building assets must prefer canonical vocabulary
- compatibility-only vocabulary may be surfaced only when strictly needed for backward-readable prompts/examples
- do not make `recommended_action` the primary field in new templates, registries, or repo-profile guidance
- if both are present, canonical vocabulary must appear first and drive template logic

Required implementation outcome:
Build a lightweight prompt assembly layer that:
- classifies task type
- selects a template
- composes prompt blocks
- injects repo profile and hard constraints
- injects validation commands
- injects canonical review/policy vocabulary guidance where relevant
- emits a stable final prompt string

Keep it simple and file-based.

Required assembled prompt sections, in this exact conceptual order:
1. repository identity / read-first requirement
2. mode
3. primary goal
4. non-goals
5. repo-grounded constraints
6. canonical vocabulary / compatibility notes when relevant
7. allowed files
8. forbidden files
9. implementation requirements
10. validation commands
11. success criteria
12. final output requirements

Allowed files to modify:
- new files under `automation/planning/`
- new files under `prompts/repo_profiles/`
- new files under `prompts/blocks/`
- new files under `prompts/templates/`
- `prompts/examples/index.json`
- minimal tests directly needed for this PR
- minimal docs directly needed for this PR

Preferred new implementation files:
- `automation/planning/task_classifier.py`
- `automation/planning/template_registry.py`
- `automation/planning/prompt_builder.py`

Preferred prompt asset files:
- `prompts/repo_profiles/codex_local_runner.md`
- `prompts/blocks/repo_context.md`
- `prompts/blocks/hard_constraints.md`
- `prompts/blocks/canonical_vocabulary.md`
- `prompts/blocks/validation_block.md`
- `prompts/blocks/output_requirements.md`
- `prompts/templates/inspect_read_only.md`
- `prompts/templates/docs_only.md`
- `prompts/templates/test_only.md`
- `prompts/templates/correction_from_current_state.md`
- `prompts/templates/regenerate_after_reset.md`

Forbidden files to modify unless strictly needed for import/test wiring:
- execution modules
- orchestrator runtime modules
- merge/rollback executors
- operator decision scripts
- ledger schema/persistence code
- `scripts/build_operator_summary.py`
- `scripts/inspect_job.py`
- `automation/review/*`
- archive bundle contents
- policy docs created in PR-2, except for a minimal cross-reference note if absolutely required

Archive/examples boundary constraints:
- `prompts/examples/*` must be treated as read-mostly
- only `prompts/examples/index.json` may be updated directly unless a minimal new example file is strictly required
- `prompts/archive/*` must be treated as read-only in this PR
- do not rename existing archive/example assets
- do not mass-normalize old examples
- do not rewrite historical prompt assets just to fit the new builder

Lightweight-only constraints:
- prefer plain Python + plain markdown files
- no plugin architecture
- no class hierarchy unless clearly justified
- no YAML/JSON rule engine unless already clearly established in repo and strictly necessary
- no over-generalized abstraction for future unknown repos
- optimize for `codex-local-runner` first, future extensibility second
- no nested template inheritance
- no runtime-discovered template plugins
- one simple registry is preferred over a generalized framework

Task classification requirements:
Support at minimum:
- `inspect_read_only`
- `docs_only`
- `test_only`
- `correction_from_current_state`
- `regenerate_after_reset`

Fallback rule:
- unknown task types must fall back deterministically to `docs_only`
- no alternative fallback is allowed in this PR
- fallback behavior must be explicitly tested

Prompt assembly requirements:
- stable same-input same-output behavior
- explicit allowed-files / forbidden-files support
- explicit validation command block support
- explicit deliverables block support
- ability to inject repo profile text
- ability to inject canonical vocabulary guidance
- ability to keep examples indexed separately from templates
- templates must not treat inspect-only visibility fields as policy authority
- templates must not imply execution authorization

Prompt contract requirements:
- every assembled prompt must require proof of repository reading
- every assembled prompt must reinforce narrow scope
- every assembled prompt must separate canonical fields from compatibility aliases where relevant
- every assembled prompt must avoid promoting backward-compatibility aliases into primary decision vocabulary

Required repository reading minimum:
- `prompts/examples/*`
- `prompts/archive/*` relevant registry/schema files
- existing repo-profile-like assets if any
- `docs/review_scoring_rubric.md`
- `docs/review_decision_policy.md`
- `docs/failure_taxonomy.md`
- relevant docs about current review-control-plane posture
- `README.md`
- `AGENTS.md`

Before coding, output:
1. files read
2. current prompt asset inventory
3. canonical vs compatibility-only vocabulary map
4. proposed minimal file layout
5. exact task types supported
6. deterministic fallback rule
7. exact files to be changed

Required tests:
- same inputs produce same prompt
- correct template chosen for known task types
- deterministic `docs_only` fallback for unknown type
- prompt includes required sections in correct order
- prompt prefers canonical vocabulary over compatibility aliases
- no execution behavior is introduced

Required validation commands:
```bash
python -m py_compile automation/planning/task_classifier.py automation/planning/template_registry.py automation/planning/prompt_builder.py
pytest -q tests/test_prompt_builder.py tests/test_task_classifier.py

If pytest is unavailable, you must:

report that explicitly
try python -m pytest once
if still unavailable, run the closest equivalent python -m unittest targets
explain the substitution precisely

Required success criteria:

lightweight file-based prompt builder exists
required task types supported
fallback behavior deterministic
prompt output contract is stable
canonical vocabulary is preferred consistently
compatibility aliases are not promoted to primary vocabulary
no execution/orchestration/git automation introduced
diff remains narrow and prompt-foundation scoped

Required final output:

files inspected and why
current prompt asset inventory
canonical vs compatibility vocabulary handling
exact files changed
unified diff
validation commands run
exact test results
example assembled prompt output
short PR summary

Do not over-engineer this.
Do not build a framework.
Do not rewrite history.
Build the smallest reusable prompt foundation that matches the current repo and preserves the policy vocabulary introduced so far.