You are working inside the repository `rai0409/codex-local-runner`.

Read the repository first. Before proposing changes, you must prove repository reading by listing:
- exact files inspected
- why each file was inspected
- what structured review facts already exist
- which current fields are visibility-only versus decision-relevant
- which facts are source-of-truth versus inspect-derived

Mode:
Implement

Primary goal:
Add a deterministic scoring and recovery-policy layer that converts existing structured review facts into exactly one recovery decision:
- `keep`
- `revise_current_state`
- `reset_and_retry`
- `escalate`

This PR is about deterministic review policy only.

Strict non-goals:
- no autonomous execution
- no auto retry loop
- no auto rollback
- no auto merge
- no GitHub automation
- no hidden state machine
- no background worker
- no redesign of advisory / execution_bridge / mode_visibility into execution triggers
- no replacement of explicit human operator gate
- no execution-path refactor
- do not address remaining validation-not-run helper duplication in `app.py` / adapter code in this PR

Repository-grounded constraints you must preserve:
- advisory is operator aid / visibility
- execution_bridge is conservative visibility, not runtime authorization
- mode_visibility is read-only current-mode visibility
- explicit human decision path remains the current gate
- merge/rollback guardrails must remain intact
- policy output added in this PR must not silently become an execution trigger
- canonical execution result contract from PR-1 must be treated as authoritative where execution facts are needed
- do not introduce new fallback normalization logic for execution facts in inspect/summary/policy code

Primary design rule:
Policy must be derived only from deterministic structured facts already present in the repo, or from narrowly added deterministic derivations grounded in existing artifacts.

No LLM reasoning is allowed inside the implemented policy layer.

Source-of-truth policy inputs to prefer:
- canonical execution result fields already normalized by the execution authority
- machine review payload fields
- ledger-backed job facts
- validation/test result status
- merge gate result
- rollback trace facts
- rollback execution facts
- changed files
- diff stats if already recorded or can be deterministically derived
- required tests declared/executed/passed signals
- forbidden-file-touch signal if deterministically derived

Do not use:
- free-form narrative text scoring
- heuristic prompts to another model
- hidden/manual-only judgment fields
- speculative future execution state
- inspect-only display fields as the primary source of truth
- new adapter-side or inspect-side fallback normalization for missing execution fields

Required implementation outcome:
Implement a deterministic score/policy layer that produces a stable machine-readable output shape.

Required output shape:
```json
{
  "score_total": 0.0,
  "dimension_scores": {
    "correctness": 0.0,
    "scope_control": 0.0,
    "safety": 0.0,
    "repo_alignment": 0.0
  },
  "failure_codes": [],
  "recovery_decision": "revise_current_state",
  "decision_basis": [],
  "requires_human_review": true
}

You may add narrowly justified extra fields, but do not remove or rename the above.

Score contract:

score_total range must be 0.0 to 10.0
exact dimension ranges must be:
correctness: 0.0 to 4.0
scope_control: 0.0 to 2.0
safety: 0.0 to 2.5
repo_alignment: 0.0 to 1.5
score_total = sum(dimension_scores)
same recorded facts must always yield the same score and decision
unknown or missing data must degrade conservatively, not optimistically

Recovery decision thresholds:

keep when score is >= 9.3 and there is no blocking failure code
revise_current_state when score is >= 8.0 and < 9.3
reset_and_retry when score is >= 7.0 and < 8.0
escalate when score is < 7.0 or when blocking failure codes require human judgment

Blocking failure codes should be handled conservatively.

Required baseline failure codes to support if applicable:

scope_explosion
touched_forbidden_file
hidden_runtime_semantics
contract_drift
weak_backward_compat
insufficient_tests
prompt_noncompliance

Allowed files to modify:

scripts/build_operator_summary.py
scripts/inspect_job.py
scripts/operator_review_decision.py only if narrow wiring is strictly needed
existing evaluation-related modules
new files under:
automation/review/score_engine.py
automation/review/recovery_policy.py
docs directly required for this PR
targeted tests

Preferred new docs:

docs/review_scoring_rubric.md
docs/review_decision_policy.md
docs/failure_taxonomy.md

Forbidden files to modify unless strictly required for import/wiring:

run_codex.py
adapters/codex_cli.py
orchestrator/codex_execution.py
merge executor / rollback executor logic
prompt/template/archive assets
GitHub automation files
orchestration pipeline files beyond minimal read-only integration points
adapter execution logic
app.py
ledger schema unless absolutely required and explicitly justified

Implementation constraints:

keep policy logic deterministic and side-effect free
keep visibility fields separate from policy fields
do not collapse advisory into policy output
do not make inspect output the source of truth
ledger/artifact-backed facts remain the source of truth
canonical execution result stays canonical
prefer additive integration over large rewrites

Required repository reading minimum:

scripts/build_operator_summary.py
scripts/inspect_job.py
scripts/operator_review_decision.py
orchestrator/main.py
orchestrator/ledger.py
current evaluation/rubric/merge-gate modules
orchestrator/codex_execution.py
relevant tests
README.md
AGENTS.md

Before coding, output:

files read
structured fact inventory
source-of-truth vs inspect-derived field map
visibility-only vs decision-input field map
proposed scoring rules and threshold mapping
exact files to be changed

Required validation commands:

python -m py_compile scripts/build_operator_summary.py scripts/inspect_job.py scripts/operator_review_decision.py
pytest -q tests/test_inspect_job.py tests/test_operator_review_decision.py

If pytest is unavailable, you must:

report that explicitly
try python -m pytest once
if still unavailable, run the closest equivalent python -m unittest targets
explain the substitution precisely

Required success criteria:

deterministic output shape implemented
score and recovery decision are reproducible
visibility fields remain visibility-only
no execution behavior changes
no new fallback normalization for execution facts is introduced
docs and code agree on vocabulary
targeted tests pass

Required final output:

files inspected and why
structured fact inventory
exact scoring dimensions, thresholds, and failure-code rules
exact files changed
unified diff
validation commands run
exact test results
backward compatibility notes
short PR summary

Do not widen scope into orchestration or execution.
Do not redesign the repo.
Keep this PR policy-only and deterministic.